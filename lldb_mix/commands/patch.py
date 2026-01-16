from __future__ import annotations

import shlex

from lldb_mix.commands.utils import (
    emit_result,
    eval_expression,
    parse_int,
    resolve_addr,
)
from lldb_mix.core.patches import format_bytes, parse_hex_bytes
from lldb_mix.core.session import Session
from lldb_mix.core.snapshot import capture_snapshot
from lldb_mix.core.state import PATCHES
from lldb_mix.deref import format_addr


def cmd_patch(debugger, command, result, internal_dict) -> None:
    try:
        import lldb
    except Exception:
        print("[lldb-mix] patch not available outside LLDB")
        return

    args = shlex.split(command)
    if not args or args[0] in ("-h", "--help", "help"):
        emit_result(result, _usage(), lldb)
        return

    session = Session(debugger)
    snapshot = capture_snapshot(session)
    frame = session.frame()
    ptr_size = snapshot.arch.ptr_size if snapshot else 8
    if not ptr_size:
        ptr_size = 8

    subcmd = args[0]
    if subcmd == "list":
        emit_result(result, _list_patches(ptr_size), lldb)
        return

    process = session.process()
    if not process:
        emit_result(result, "[lldb-mix] process unavailable", lldb)
        return

    arch = snapshot.arch if snapshot else session.arch()
    regs = snapshot.regs if snapshot else {}

    if subcmd == "restore":
        addr, error = _parse_addr(args[1:], regs, frame)
        if error:
            emit_result(result, f"[lldb-mix] {error}\n{_usage()}", lldb)
            return
        entry = PATCHES.get(addr)
        if not entry:
            emit_result(result, "[lldb-mix] patch not found", lldb)
            return
        if not _write_memory(process, addr, entry.original, lldb):
            emit_result(result, "[lldb-mix] patch restore failed", lldb)
            return
        PATCHES.remove(addr)
        emit_result(
            result,
            f"[lldb-mix] patch restored {format_addr(addr, ptr_size)} len={entry.size}",
            lldb,
        )
        return

    addr, count, payload, error = _parse_patch_args(subcmd, args[1:], regs, frame, arch)
    if error:
        emit_result(result, f"[lldb-mix] {error}\n{_usage()}", lldb)
        return

    if not payload:
        emit_result(result, "[lldb-mix] patch bytes missing", lldb)
        return

    original = _read_memory(process, addr, len(payload), lldb)
    if original is None:
        emit_result(result, "[lldb-mix] failed to read memory", lldb)
        return

    ok, reason = PATCHES.add(addr, original, payload)
    if not ok:
        emit_result(result, f"[lldb-mix] {reason}", lldb)
        return

    if not _write_memory(process, addr, payload, lldb):
        PATCHES.remove(addr)
        emit_result(result, "[lldb-mix] patch write failed", lldb)
        return

    summary = (
        f"[lldb-mix] patch {subcmd} {format_addr(addr, ptr_size)} len={len(payload)}"
    )
    if count > 1 and subcmd in ("nop", "int3", "null"):
        summary += f" count={count}"
    emit_result(result, summary, lldb)


def _parse_addr(tokens: list[str], regs: dict[str, int], frame):
    if len(tokens) != 1:
        return 0, "invalid address"
    addr = _resolve_addr(tokens[0], regs, frame)
    if addr is None:
        return 0, "invalid address"
    return addr, None


def _parse_patch_args(
    subcmd: str, tokens: list[str], regs: dict[str, int], frame, arch
):
    if subcmd == "write":
        if len(tokens) < 2:
            return 0, 0, b"", "missing write arguments"
        addr = _resolve_addr(tokens[0], regs, frame)
        if addr is None:
            return 0, 0, b"", "invalid address"
        payload = parse_hex_bytes(" ".join(tokens[1:]))
        if not payload:
            return 0, 0, b"", "invalid hex bytes"
        return addr, len(payload), payload, None

    if subcmd in ("nop", "int3", "null"):
        if len(tokens) not in (1, 2):
            return 0, 0, b"", "invalid patch arguments"
        addr = _resolve_addr(tokens[0], regs, frame)
        if addr is None:
            return 0, 0, b"", "invalid address"
        count = 1
        if len(tokens) == 2:
            parsed = parse_int(tokens[1])
            if parsed is None or parsed <= 0:
                return 0, 0, b"", "invalid count"
            count = parsed

        if subcmd == "null":
            return addr, count, b"\x00" * count, None

        unit = arch.nop_bytes if subcmd == "nop" else arch.break_bytes
        if not unit:
            return 0, 0, b"", f"{subcmd} not supported on this architecture"
        return addr, count, unit * count, None

    return 0, 0, b"", "unknown patch subcommand"


def _resolve_addr(token: str, regs: dict[str, int], frame):
    addr = resolve_addr(token, regs)
    if addr is not None:
        return addr
    if frame:
        return eval_expression(frame, token)
    return None


def _read_memory(process, addr: int, size: int, lldb_module):
    error = lldb_module.SBError()
    data = process.ReadMemory(addr, size, error)
    if not error.Success():
        return None
    return bytes(data)


def _write_memory(process, addr: int, data: bytes, lldb_module) -> bool:
    error = lldb_module.SBError()
    written = process.WriteMemory(addr, data, error)
    if not error.Success():
        return False
    return written == len(data)


def _list_patches(ptr_size: int) -> str:
    entries = PATCHES.list()
    if not entries:
        return "[lldb-mix] patches: (none)"
    lines = ["[lldb-mix] patches:"]
    for entry in entries:
        addr_text = format_addr(entry.addr, ptr_size)
        bytes_text = format_bytes(entry.patched)
        lines.append(f"{addr_text} len={entry.size} bytes={bytes_text}")
    return "\n".join(lines)


def _usage() -> str:
    return (
        "[lldb-mix] usage: patch write <addr|expr> <hex> | "
        "nop <addr|expr> [count] | int3 <addr|expr> [count] | "
        "null <addr|expr> [count] | restore <addr|expr> | list"
    )
