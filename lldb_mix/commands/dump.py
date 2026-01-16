from __future__ import annotations

from dataclasses import dataclass

from lldb_mix.core.memory import ProcessMemoryReader
from lldb_mix.commands.utils import (
    default_addr,
    emit_result,
    parse_int,
    resolve_addr,
)
from lldb_mix.core.session import Session
from lldb_mix.core.snapshot import capture_snapshot
from lldb_mix.core.state import SETTINGS
from lldb_mix.deref import format_addr
from lldb_mix.ui.hexdump import hexdump, hexdump_words
from lldb_mix.ui.style import colorize
from lldb_mix.ui.theme import get_theme


DEFAULT_DUMP_LEN = 64
DEFAULT_DUMP_WIDTH = 16
DEFAULT_WORD_DUMP_LEN = 0x100


@dataclass
class DumpArgs:
    addr: int
    length: int
    width: int


@dataclass
class SimpleDumpArgs:
    addr: int
    length: int


def cmd_dump(debugger, command, result, internal_dict) -> None:
    try:
        import lldb
    except Exception:
        print("[lldb-mix] dump not available outside LLDB")
        return

    args = command.split()
    if args and args[0] in ("-h", "--help", "help"):
        emit_result(result, _usage(), lldb)
        return

    session = Session(debugger)
    snapshot = capture_snapshot(session)
    if not snapshot:
        emit_result(result, "[lldb-mix] dump (no target)", lldb)
        return

    parsed, error = _parse_args(args, snapshot.regs)
    if error:
        emit_result(result, f"[lldb-mix] {error}\n{_usage()}", lldb)
        return

    if parsed.addr == 0:
        emit_result(result, "[lldb-mix] dump address is 0", lldb)
        return

    process = session.process()
    if not process:
        emit_result(result, "[lldb-mix] process unavailable", lldb)
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
        emit_result(result, f"{header}\n(memory unreadable)", lldb)
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
    emit_result(result, "\n".join(lines), lldb)


def _parse_args(args: list[str], regs: dict[str, int]) -> tuple[DumpArgs, str | None]:
    length = DEFAULT_DUMP_LEN
    width = DEFAULT_DUMP_WIDTH
    length_set = False
    tokens: list[str] = []

    it = iter(args)
    for arg in it:
        if arg in ("-l", "--length"):
            value = next(it, None)
            if value is None:
                return _default_args(), "missing length value"
            parsed = parse_int(value)
            if parsed is None or parsed <= 0:
                return _default_args(), "invalid length value"
            length = parsed
            length_set = True
            continue
        if arg in ("-w", "--width"):
            value = next(it, None)
            if value is None:
                return _default_args(), "missing width value"
            parsed = parse_int(value)
            if parsed is None or parsed <= 0:
                return _default_args(), "invalid width value"
            width = parsed
            continue
        tokens.append(arg)

    if len(tokens) > 2:
        return _default_args(), "too many arguments"

    addr = resolve_addr(tokens[0], regs) if tokens else default_addr(regs)
    if addr is None:
        return _default_args(), "invalid address or register"

    if len(tokens) == 2:
        if length_set:
            return _default_args(), "length set twice"
        parsed_len = parse_int(tokens[1])
        if parsed_len is None or parsed_len <= 0:
            return _default_args(), "invalid length value"
        length = parsed_len

    return DumpArgs(addr=addr, length=length, width=width), None


def _default_args() -> DumpArgs:
    return DumpArgs(
        addr=0,
        length=DEFAULT_DUMP_LEN,
        width=DEFAULT_DUMP_WIDTH,
    )


def _usage() -> str:
    return (
        "[lldb-mix] usage: dump [<addr|reg|sp|pc>] [len] "
        "[-l len] [-w width]"
    )


def cmd_db(debugger, command, result, internal_dict) -> None:
    _cmd_word_dump(debugger, command, result, "db", word_size=1)


def cmd_dw(debugger, command, result, internal_dict) -> None:
    _cmd_word_dump(debugger, command, result, "dw", word_size=2)


def cmd_dd(debugger, command, result, internal_dict) -> None:
    _cmd_word_dump(debugger, command, result, "dd", word_size=4)


def cmd_dq(debugger, command, result, internal_dict) -> None:
    _cmd_word_dump(debugger, command, result, "dq", word_size=8)


def _cmd_word_dump(
    debugger,
    command: str,
    result,
    label: str,
    word_size: int,
) -> None:
    try:
        import lldb
    except Exception:
        print(f"[lldb-mix] {label} not available outside LLDB")
        return

    args = command.split()
    if args and args[0] in ("-h", "--help", "help"):
        emit_result(result, _usage_word(label), lldb)
        return

    session = Session(debugger)
    snapshot = capture_snapshot(session)
    if not snapshot:
        emit_result(result, f"[lldb-mix] {label} (no target)", lldb)
        return

    parsed, error = _parse_simple_args(args, snapshot.regs)
    if error:
        emit_result(result, f"[lldb-mix] {error}\n{_usage_word(label)}", lldb)
        return

    if parsed.addr == 0:
        emit_result(result, f"[lldb-mix] {label} address is 0", lldb)
        return

    process = session.process()
    if not process:
        emit_result(result, "[lldb-mix] process unavailable", lldb)
        return

    reader = ProcessMemoryReader(process)
    data = reader.read(parsed.addr, parsed.length)
    theme = get_theme(SETTINGS.theme)
    ptr_size = snapshot.arch.ptr_size or 8
    bytes_per_line = _word_bytes_per_line(word_size)
    header = (
        f"[{label}] {format_addr(parsed.addr, ptr_size)} "
        f"len={parsed.length} word={word_size}"
    )
    header = colorize(header, "title", theme, SETTINGS.enable_color)
    if not data:
        emit_result(result, f"{header}\n(memory unreadable)", lldb)
        return

    def _style(text: str, role: str) -> str:
        return colorize(text, role, theme, SETTINGS.enable_color)

    lines = [header]
    lines.extend(
        hexdump_words(
            data,
            parsed.addr,
            word_size=word_size,
            bytes_per_line=bytes_per_line,
            colorize=_style,
        )
    )
    emit_result(result, "\n".join(lines), lldb)


def _parse_simple_args(
    args: list[str], regs: dict[str, int]
) -> tuple[SimpleDumpArgs, str | None]:
    if len(args) > 2:
        return SimpleDumpArgs(addr=0, length=DEFAULT_WORD_DUMP_LEN), "too many arguments"

    addr = resolve_addr(args[0], regs) if args else default_addr(regs)
    if addr is None:
        return SimpleDumpArgs(addr=0, length=DEFAULT_WORD_DUMP_LEN), "invalid address or register"

    length = DEFAULT_WORD_DUMP_LEN
    if len(args) == 2:
        parsed_len = parse_int(args[1])
        if parsed_len is None or parsed_len <= 0:
            return SimpleDumpArgs(addr=0, length=DEFAULT_WORD_DUMP_LEN), "invalid length value"
        length = parsed_len

    return SimpleDumpArgs(addr=addr, length=length), None


def _word_bytes_per_line(word_size: int) -> int:
    if word_size >= 8:
        return 32
    return 16


def _usage_word(label: str) -> str:
    return f"[lldb-mix] usage: {label} [<addr|reg|sp|pc>] [len]"
