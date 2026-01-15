from __future__ import annotations

from dataclasses import dataclass

from lldb_mix.core.memory import ProcessMemoryReader
from lldb_mix.core.session import Session
from lldb_mix.core.snapshot import capture_snapshot
from lldb_mix.core.state import SETTINGS
from lldb_mix.deref import format_addr
from lldb_mix.ui.hexdump import hexdump
from lldb_mix.ui.style import colorize
from lldb_mix.ui.theme import get_theme


@dataclass
class DumpArgs:
    addr: int
    length: int
    width: int


def cmd_dump(debugger, command, result, internal_dict) -> None:
    try:
        import lldb
    except Exception:
        print("[lldb-mix] dump not available outside LLDB")
        return

    args = command.split()
    if args and args[0] in ("-h", "--help", "help"):
        _emit_result(result, _usage(), lldb)
        return

    session = Session(debugger)
    snapshot = capture_snapshot(session)
    if not snapshot:
        _emit_result(result, "[lldb-mix] dump (no target)", lldb)
        return

    parsed, error = _parse_args(args, snapshot.regs)
    if error:
        _emit_result(result, f"[lldb-mix] {error}\n{_usage()}", lldb)
        return

    if parsed.addr == 0:
        _emit_result(result, "[lldb-mix] dump address is 0", lldb)
        return

    process = session.process()
    if not process:
        _emit_result(result, "[lldb-mix] process unavailable", lldb)
        return

    reader = ProcessMemoryReader(process)
    data = reader.read(parsed.addr, parsed.length)
    theme = get_theme(SETTINGS.theme)
    ptr_size = snapshot.arch.ptr_size or 8
    header = (
        f"[dump] {format_addr(parsed.addr, ptr_size)} "
        f"len={parsed.length} width={parsed.width}"
    )
    header = colorize(header, "title", theme, SETTINGS.enable_color)
    if not data:
        _emit_result(result, f"{header}\n(memory unreadable)", lldb)
        return

    def _style(text: str, role: str) -> str:
        return colorize(text, role, theme, SETTINGS.enable_color)

    lines = [header]
    lines.extend(
        hexdump(
            data,
            parsed.addr,
            bytes_per_line=parsed.width,
            colorize=_style,
        )
    )
    _emit_result(result, "\n".join(lines), lldb)


def _emit_result(result, message: str, lldb_module) -> None:
    try:
        result.PutCString(message)
        result.SetStatus(lldb_module.eReturnStatusSuccessFinishResult)
    except Exception:
        print(message)


def _parse_args(args: list[str], regs: dict[str, int]) -> tuple[DumpArgs, str | None]:
    length = SETTINGS.memory_window_bytes
    width = SETTINGS.memory_bytes_per_line
    length_set = False
    tokens: list[str] = []

    it = iter(args)
    for arg in it:
        if arg in ("-l", "--length"):
            value = next(it, None)
            if value is None:
                return _default_args(), "missing length value"
            parsed = _parse_int(value)
            if parsed is None or parsed <= 0:
                return _default_args(), "invalid length value"
            length = parsed
            length_set = True
            continue
        if arg in ("-w", "--width"):
            value = next(it, None)
            if value is None:
                return _default_args(), "missing width value"
            parsed = _parse_int(value)
            if parsed is None or parsed <= 0:
                return _default_args(), "invalid width value"
            width = parsed
            continue
        tokens.append(arg)

    if len(tokens) > 2:
        return _default_args(), "too many arguments"

    addr = _resolve_addr(tokens[0], regs) if tokens else _default_addr(regs)
    if addr is None:
        return _default_args(), "invalid address or register"

    if len(tokens) == 2:
        if length_set:
            return _default_args(), "length set twice"
        parsed_len = _parse_int(tokens[1])
        if parsed_len is None or parsed_len <= 0:
            return _default_args(), "invalid length value"
        length = parsed_len

    return DumpArgs(addr=addr, length=length, width=width), None


def _default_args() -> DumpArgs:
    return DumpArgs(
        addr=0,
        length=SETTINGS.memory_window_bytes,
        width=SETTINGS.memory_bytes_per_line,
    )


def _default_addr(regs: dict[str, int]) -> int | None:
    for name in ("sp", "rsp", "esp"):
        if name in regs and regs[name]:
            return regs[name]
    for name in ("pc", "rip", "eip"):
        if name in regs and regs[name]:
            return regs[name]
    return None


def _resolve_addr(token: str, regs: dict[str, int]) -> int | None:
    cleaned = token.strip()
    if cleaned.startswith("$"):
        cleaned = cleaned[1:]
    key = cleaned.lower()
    if key == "sp":
        return _pick_reg(("sp", "rsp", "esp"), regs)
    if key == "pc":
        return _pick_reg(("pc", "rip", "eip"), regs)
    reg_map = {name.lower(): value for name, value in regs.items()}
    if key in reg_map:
        return reg_map[key]
    try:
        return int(cleaned, 0)
    except ValueError:
        return None


def _parse_int(text: str) -> int | None:
    try:
        return int(text, 0)
    except ValueError:
        return None


def _pick_reg(candidates: tuple[str, ...], regs: dict[str, int]) -> int | None:
    reg_map = {name.lower(): value for name, value in regs.items()}
    for name in candidates:
        value = reg_map.get(name)
        if value:
            return value
    return None


def _usage() -> str:
    return (
        "[lldb-mix] usage: dump [<addr|reg|sp|pc>] [len] "
        "[-l len] [-w width]"
    )
