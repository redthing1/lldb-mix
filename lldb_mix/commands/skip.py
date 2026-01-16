from __future__ import annotations

import shlex

from lldb_mix.commands.context import render_context_if_enabled
from lldb_mix.commands.utils import emit_result, parse_int
from lldb_mix.core.disasm import disasm_flavor, read_instructions
from lldb_mix.core.session import Session
from lldb_mix.core.snapshot import capture_snapshot
from lldb_mix.deref import format_addr


def cmd_skip(debugger, command, result, internal_dict) -> None:
    try:
        import lldb
    except Exception:
        print("[lldb-mix] skip not available outside LLDB")
        return

    args = shlex.split(command)
    if args and args[0] in ("-h", "--help", "help"):
        emit_result(result, _usage(), lldb)
        return

    count, error = _parse_count(args)
    if error:
        emit_result(result, f"[lldb-mix] {error}\n{_usage()}", lldb)
        return

    session = Session(debugger)
    snapshot = capture_snapshot(session)
    if not snapshot:
        emit_result(result, "[lldb-mix] skip (no target)", lldb)
        return

    target = session.target()
    frame = session.frame()
    if not target or not frame:
        emit_result(result, "[lldb-mix] target unavailable", lldb)
        return

    pc = snapshot.pc
    if pc == 0:
        emit_result(result, "[lldb-mix] pc unavailable", lldb)
        return

    flavor = disasm_flavor(snapshot.arch.name)
    insts = read_instructions(target, pc, count, flavor=flavor)
    target_addr = _compute_target(pc, insts, count)
    if target_addr is None:
        emit_result(result, "[lldb-mix] instruction size unavailable", lldb)
        return

    reg = _find_pc_register(frame, snapshot.arch.pc_reg)
    if not reg:
        emit_result(result, "[lldb-mix] pc register unavailable", lldb)
        return

    if not _set_reg_value(reg, f"0x{target_addr:x}"):
        emit_result(result, "[lldb-mix] failed to update pc", lldb)
        return

    ptr_size = snapshot.arch.ptr_size or 8
    addr_text = format_addr(target_addr, ptr_size)
    message = f"[lldb-mix] skip {count} -> {addr_text}"
    context_text = render_context_if_enabled(debugger)
    if context_text:
        message = f"{message}\n{context_text}"
    emit_result(result, message, lldb)


def _parse_count(args: list[str]) -> tuple[int, str | None]:
    if not args:
        return 1, None
    if len(args) != 1:
        return 0, "too many arguments"
    parsed = parse_int(args[0])
    if parsed is None or parsed <= 0:
        return 0, "invalid count"
    return parsed, None


def _compute_target(pc: int, insts: list, count: int) -> int | None:
    if count <= 0 or len(insts) < count:
        return None
    total = 0
    for inst in insts[:count]:
        size = len(inst.bytes)
        if size <= 0:
            return None
        total += size
    return pc + total


def _find_pc_register(frame, pc_name: str) -> object | None:
    candidates = [pc_name] if pc_name else []
    candidates.extend(["pc", "rip", "eip"])
    for name in candidates:
        if not name:
            continue
        try:
            reg = frame.FindRegister(name)
        except Exception:
            reg = None
        if reg and reg.IsValid():
            return reg
    return None


def _set_reg_value(reg, value: str) -> bool:
    try:
        return bool(reg.SetValueFromCString(value))
    except Exception:
        try:
            import lldb
        except Exception:
            return False
        error = lldb.SBError()
        try:
            ok = reg.SetValueFromCString(value, error)
        except Exception:
            return False
        return bool(ok) and error.Success()


def _usage() -> str:
    return "[lldb-mix] usage: skip [count]"
