from __future__ import annotations

import shlex

from lldb_mix.commands.utils import emit_result
from lldb_mix.core.addressing import AddressResolver, parse_int
from lldb_mix.core.modules import find_module, module_base, module_name
from lldb_mix.core.disasm import read_instructions
from lldb_mix.core.session import Session
from lldb_mix.core.snapshot import capture_snapshot
from lldb_mix.deref import format_addr


def cmd_bpm(debugger, command, result, internal_dict) -> None:
    try:
        import lldb
    except Exception:
        print("[lldb-mix] bpm not available outside LLDB")
        return

    args = command.split()
    if not args or args[0] in ("-h", "--help", "help") or len(args) != 2:
        emit_result(result, _usage(), lldb)
        return

    module_token = args[0]
    offset = parse_int(args[1])
    if offset is None:
        emit_result(result, "[lldb-mix] invalid offset\n" + _usage(), lldb)
        return

    target = debugger.GetSelectedTarget()
    if not target or not target.IsValid():
        emit_result(result, "[lldb-mix] target unavailable", lldb)
        return

    module = find_module(target, module_token)
    if not module:
        emit_result(result, f"[lldb-mix] module not found: {module_token}", lldb)
        return

    base = module_base(target, module, lldb)
    if base is None:
        emit_result(result, "[lldb-mix] module base unavailable", lldb)
        return

    addr = base + offset
    bp = target.BreakpointCreateByAddress(addr)
    if not bp or not bp.IsValid():
        emit_result(result, "[lldb-mix] failed to create breakpoint", lldb)
        return

    ptr_size = target.GetAddressByteSize() or 8
    mod_name = module_name(module) or module_token
    addr_text = format_addr(addr, ptr_size)
    emit_result(
        result,
        f"[lldb-mix] bpm {mod_name}+0x{offset:x} -> {addr_text} (bp {bp.GetID()})",
        lldb,
    )


def _usage() -> str:
    return "[lldb-mix] usage: bpm <module> <offset>"


def cmd_bpt(debugger, command, result, internal_dict) -> None:
    try:
        import lldb
    except Exception:
        print("[lldb-mix] bpt not available outside LLDB")
        return

    args = shlex.split(command)
    if not args or args[0] in ("-h", "--help", "help") or len(args) != 1:
        emit_result(result, _usage_bpt(), lldb)
        return

    session = Session(debugger)
    snapshot = capture_snapshot(session)
    frame = session.frame()
    if not snapshot:
        emit_result(result, "[lldb-mix] bpt (no target)", lldb)
        return

    resolver = AddressResolver(snapshot.regs, snapshot.arch, frame)
    addr = resolver.resolve(args[0])
    if addr is None:
        emit_result(result, f"[lldb-mix] invalid address\n{_usage_bpt()}", lldb)
        return

    target = session.target()
    if not target:
        emit_result(result, "[lldb-mix] target unavailable", lldb)
        return

    bp = target.BreakpointCreateByAddress(addr)
    if not bp or not bp.IsValid():
        emit_result(result, "[lldb-mix] failed to create breakpoint", lldb)
        return
    bp.SetOneShot(True)
    thread = session.thread()
    if thread:
        bp.SetThreadID(thread.GetThreadID())

    ptr_size = snapshot.arch.ptr_size or 8
    emit_result(
        result,
        f"[lldb-mix] bpt {format_addr(addr, ptr_size)} (bp {bp.GetID()})",
        lldb,
    )


def cmd_bpn(debugger, command, result, internal_dict) -> None:
    try:
        import lldb
    except Exception:
        print("[lldb-mix] bpn not available outside LLDB")
        return

    args = shlex.split(command)
    if args:
        if args[0] in ("-h", "--help", "help"):
            emit_result(result, _usage_bpn(), lldb)
            return
        emit_result(result, f"[lldb-mix] too many arguments\n{_usage_bpn()}", lldb)
        return

    session = Session(debugger)
    snapshot = capture_snapshot(session)
    if not snapshot:
        emit_result(result, "[lldb-mix] bpn (no target)", lldb)
        return

    target = session.target()
    if not target:
        emit_result(result, "[lldb-mix] target unavailable", lldb)
        return

    pc = snapshot.pc
    if not snapshot.has_pc():
        emit_result(result, "[lldb-mix] bpn pc unavailable", lldb)
        return

    flavor = snapshot.arch.disasm_flavor()
    insts = read_instructions(target, pc, 1, flavor=flavor)
    if not insts or insts[0].address != pc:
        emit_result(result, "[lldb-mix] failed to read instruction", lldb)
        return
    size = insts[0].byte_size
    if size <= 0:
        emit_result(result, "[lldb-mix] instruction size unavailable", lldb)
        return

    next_addr = pc + size
    bp = target.BreakpointCreateByAddress(next_addr)
    if not bp or not bp.IsValid():
        emit_result(result, "[lldb-mix] failed to create breakpoint", lldb)
        return
    bp.SetOneShot(True)
    thread = session.thread()
    if thread:
        bp.SetThreadID(thread.GetThreadID())

    ptr_size = snapshot.arch.ptr_size or 8
    emit_result(
        result,
        f"[lldb-mix] bpn {format_addr(next_addr, ptr_size)} (bp {bp.GetID()})",
        lldb,
    )


def _usage_bpt() -> str:
    return "[lldb-mix] usage: bpt <addr|expression>"


def _usage_bpn() -> str:
    return "[lldb-mix] usage: bpn"
