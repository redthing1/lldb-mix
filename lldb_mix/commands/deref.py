from __future__ import annotations

from dataclasses import dataclass
import shlex

from lldb_mix.commands.utils import emit_result
from lldb_mix.core.addressing import AddressResolver, parse_int
from lldb_mix.core.memory import ProcessMemoryReader
from lldb_mix.core.modules import format_module_offset
from lldb_mix.core.settings import Settings
from lldb_mix.core.session import Session
from lldb_mix.core.snapshot import capture_snapshot
from lldb_mix.core.state import SETTINGS
from lldb_mix.core.symbols import TargetSymbolResolver
from lldb_mix.deref import (
    classify_token,
    deref_chain,
    find_region,
    format_addr,
    format_region,
    format_symbol,
)
from lldb_mix.ui.style import colorize
from lldb_mix.ui.theme import get_theme


@dataclass(frozen=True)
class DerefArgs:
    token: str | None
    depth: int | None


def cmd_deref(debugger, command, result, internal_dict) -> None:
    try:
        import lldb
    except Exception:
        print("[lldb-mix] deref not available outside LLDB")
        return

    args = shlex.split(command)
    if args and args[0] in ("-h", "--help", "help"):
        emit_result(result, _usage(), lldb)
        return

    session = Session(debugger)
    snapshot = capture_snapshot(session)
    if not snapshot:
        emit_result(result, "[lldb-mix] deref (no target)", lldb)
        return

    parsed, error = _parse_args(args)
    if error:
        emit_result(result, f"[lldb-mix] {error}\n{_usage()}", lldb)
        return

    frame = session.frame()
    resolver = AddressResolver(snapshot.regs, snapshot.arch, frame)
    addr = resolver.resolve(parsed.token)
    if addr is None:
        emit_result(result, "[lldb-mix] invalid address", lldb)
        return

    process = session.process()
    target = session.target()
    if not process or not target:
        emit_result(result, "[lldb-mix] process unavailable", lldb)
        return

    settings = _settings_with_depth(parsed.depth)
    reader = ProcessMemoryReader(process)
    resolver = TargetSymbolResolver(target)
    ptr_size = snapshot.arch.ptr_size or 8
    chain = deref_chain(
        addr,
        reader,
        snapshot.maps,
        resolver,
        settings,
        ptr_size,
    )

    theme = get_theme(SETTINGS.theme)

    def _style(text: str, role: str) -> str:
        return colorize(text, role, theme, SETTINGS.enable_color)

    header = _style(f"[deref] {format_addr(addr, ptr_size)}", "title")
    lines = [header]

    region = find_region(addr, snapshot.maps)
    if region:
        label = _style("region:", "label")
        lines.append(f"{label} {_style(format_region(region), 'muted')}")

    symbol = resolver.resolve(addr)
    if symbol:
        label = _style("symbol:", "label")
        lines.append(f"{label} {_style(format_symbol(symbol), 'symbol')}")
    else:
        module_text = format_module_offset(target, addr)
        if module_text:
            label = _style("module:", "label")
            lines.append(f"{label} {_style(module_text, 'symbol')}")

    if chain:
        label = _style("chain:", "label")
        parts: list[str] = []
        for token in chain:
            kind = classify_token(token)
            role = _token_role(kind)
            parts.append(_style(token, role))
        lines.append(f"{label} {' -> '.join(parts)}")

    emit_result(result, "\n".join(lines), lldb)


def _parse_args(args: list[str]) -> tuple[DerefArgs, str | None]:
    depth = None
    tokens: list[str] = []
    it = iter(args)
    for arg in it:
        if arg in ("-d", "--depth"):
            raw = next(it, None)
            if raw is None:
                return DerefArgs(None, None), "missing depth value"
            parsed = parse_int(raw)
            if parsed is None or parsed <= 0:
                return DerefArgs(None, None), "invalid depth value"
            depth = parsed
            continue
        tokens.append(arg)

    if len(tokens) > 1:
        return DerefArgs(None, None), "too many arguments"

    token = tokens[0] if tokens else None
    return DerefArgs(token=token, depth=depth), None


def _settings_with_depth(depth: int | None) -> Settings:
    if depth is None:
        return SETTINGS
    cloned = Settings(**vars(SETTINGS))
    cloned.max_deref_depth = depth
    return cloned


def _token_role(kind: str) -> str:
    if kind == "string":
        return "string"
    if kind == "symbol":
        return "symbol"
    if kind in ("region", "loop"):
        return "muted"
    return "addr"


def _usage() -> str:
    return "[lldb-mix] usage: deref [<addr|reg|expr>] [-d depth]"
