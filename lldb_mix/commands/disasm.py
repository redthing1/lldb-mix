from __future__ import annotations

import shlex

from lldb_mix.commands.utils import (
    default_addr,
    emit_result,
    eval_expression,
    parse_int,
    resolve_addr,
)
from lldb_mix.core.disasm import disasm_flavor, read_instructions
from lldb_mix.core.session import Session
from lldb_mix.core.snapshot import capture_snapshot
from lldb_mix.core.state import SETTINGS
from lldb_mix.deref import format_addr
from lldb_mix.ui.style import colorize
from lldb_mix.ui.theme import get_theme


def cmd_u(debugger, command, result, internal_dict) -> None:
    try:
        import lldb
    except Exception:
        print("[lldb-mix] u not available outside LLDB")
        return

    args = shlex.split(command)
    if args and args[0] in ("-h", "--help", "help"):
        emit_result(result, _usage(), lldb)
        return

    session = Session(debugger)
    snapshot = capture_snapshot(session)
    if not snapshot:
        emit_result(result, "[lldb-mix] u (no target)", lldb)
        return

    addr, count, error = _parse_args(args, snapshot.regs, session.frame())
    if error:
        emit_result(result, f"[lldb-mix] {error}\n{_usage()}", lldb)
        return

    target = session.target()
    if not target:
        emit_result(result, "[lldb-mix] target unavailable", lldb)
        return

    if addr is None:
        emit_result(result, "[lldb-mix] u address unavailable", lldb)
        return

    flavor = disasm_flavor(snapshot.arch.name)
    insts = read_instructions(target, addr, count, flavor=flavor)
    if not insts:
        emit_result(result, "[lldb-mix] disassembly unavailable", lldb)
        return

    theme = get_theme(SETTINGS.theme)
    ptr_size = snapshot.arch.ptr_size or 8
    header = f"[u] {format_addr(addr, ptr_size)} count={count}"
    header = colorize(header, "title", theme, SETTINGS.enable_color)

    def _style(text: str, role: str) -> str:
        return colorize(text, role, theme, SETTINGS.enable_color)

    lines = [header]
    lines.extend(
        _format_instructions(
            insts,
            ptr_size,
            SETTINGS.show_opcodes,
            _style,
        )
    )

    emit_result(result, "\n".join(lines), lldb)


def _parse_args(
    args: list[str],
    regs: dict[str, int],
    frame,
) -> tuple[int | None, int, str | None]:
    count = _default_count()

    if not args:
        addr = resolve_addr("pc", regs)
        if addr is None:
            addr = default_addr(regs)
        return addr, count, None

    if len(args) > 2:
        return None, count, "too many arguments"

    addr = resolve_addr(args[0], regs)
    if addr is None:
        addr = eval_expression(frame, args[0])
    if addr is None:
        return None, count, "invalid address or expression"

    if len(args) == 2:
        parsed = parse_int(args[1])
        if parsed is None or parsed <= 0:
            return None, count, "invalid count"
        count = parsed

    return addr, count, None


def _default_count() -> int:
    return max(1, SETTINGS.code_lines_before + SETTINGS.code_lines_after + 1)


def _usage() -> str:
    return "[lldb-mix] usage: u [<addr|reg|pc>] [count]"


def _format_instructions(
    insts: list,
    ptr_size: int,
    show_opcodes: bool,
    style,
) -> list[str]:
    if style is None:
        style = _passthrough_style

    bytes_pad = 0
    bytes_texts: list[str] = []
    if show_opcodes:
        for inst in insts:
            bytes_texts.append(" ".join(f"{b:02x}" for b in inst.bytes))
        bytes_pad = max((len(text) for text in bytes_texts), default=0)

    lines: list[str] = []
    for idx, inst in enumerate(insts):
        prefix = "=>" if idx == 0 else "  "
        prefix_role = "pc_marker" if idx == 0 else "muted"
        prefix_colored = style(prefix, prefix_role)
        addr_colored = style(format_addr(inst.address, ptr_size), "addr")
        bytes_text = ""
        if show_opcodes:
            bytes_text = bytes_texts[idx]
            bytes_text = f"{bytes_text:<{bytes_pad}}" if bytes_text else ""
        bytes_colored = style(bytes_text, "opcode") if bytes_text else ""
        mnemonic_colored = style(inst.mnemonic, "mnemonic")
        line = f"{prefix_colored} {addr_colored} "
        if bytes_colored:
            line += bytes_colored
            line += " "
        line += mnemonic_colored
        if inst.operands:
            line += f" {inst.operands}"
        lines.append(line)
    return lines


def _passthrough_style(text: str, role: str) -> str:
    _ = role
    return text
