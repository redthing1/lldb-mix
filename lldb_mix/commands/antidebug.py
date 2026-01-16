from __future__ import annotations

import shlex
import struct

from lldb_mix.commands.utils import emit_result
from lldb_mix.arch.registry import detect_arch_from_frame
from lldb_mix.core.disasm import read_instructions
from lldb_mix.core.regs import find_register, read_register_u64, set_register_value
from lldb_mix.core.session import Session
from lldb_mix.core.state import SETTINGS


ANTIDEBUG_SYSCTL_OLDP: list[int] = []
ANTIDEBUG_TARGETS: set[int] = set()


def cmd_antidebug(debugger, command, result, internal_dict) -> None:
    try:
        import lldb
    except Exception:
        print("[lldb-mix] antidebug not available outside LLDB")
        return

    args = shlex.split(command)
    if args and args[0] in ("-h", "--help", "help"):
        emit_result(result, _usage(), lldb)
        return

    session = Session(debugger)
    target = session.target()
    if not target:
        emit_result(result, "[lldb-mix] target unavailable", lldb)
        return

    if _is_antidebug_enabled(target):
        emit_result(result, "[lldb-mix] antidebug already enabled", lldb)
        return

    bps: list[tuple[str, int]] = []
    bps.append(
        _register_bp(
            target,
            "sysctl",
            "/usr/lib/system/libsystem_c.dylib",
            "lldb_mix.commands.antidebug.antidebug_callback_step1",
        )
    )
    bps.append(
        _register_bp(
            target,
            "ptrace",
            "/usr/lib/system/libsystem_kernel.dylib",
            "lldb_mix.commands.antidebug.antidebug_ptrace_callback",
        )
    )
    bps.append(
        _register_bp(
            target,
            "task_get_exception_ports",
            "/usr/lib/system/libsystem_kernel.dylib",
            "lldb_mix.commands.antidebug.antidebug_task_exception_ports_callback",
        )
    )
    bps.append(
        _register_bp(
            target,
            "task_set_exception_ports",
            "/usr/lib/system/libsystem_kernel.dylib",
            "lldb_mix.commands.antidebug.antidebug_task_exception_ports_callback",
        )
    )

    created = [name for name, count in bps if count >= 0]
    summary = ", ".join(f"{name}:{count}" for name, count in bps)
    if created:
        ANTIDEBUG_TARGETS.add(_target_key(target))
        emit_result(result, f"[lldb-mix] antidebug enabled ({summary})", lldb)
    else:
        emit_result(result, "[lldb-mix] antidebug failed to set breakpoints", lldb)


def antidebug_callback_step1(frame, bp_loc, internal_dict):
    if frame is None:
        return 0

    try:
        import lldb
    except Exception:
        return 0

    arch = detect_arch_from_frame(frame, SETTINGS.abi)
    if arch is None:
        return 0
    abi = getattr(arch, "abi", None)
    if not abi or not getattr(abi, "int_arg_regs", None):
        return 0

    process = frame.GetThread().GetProcess()
    target = process.GetTarget()
    error = lldb.SBError()

    mib_reg = arch.arg_reg(0)
    oldp_reg = arch.arg_reg(2)
    if not mib_reg or not oldp_reg:
        return 0
    mib_addr = read_register_u64(frame, mib_reg)
    if mib_addr is None:
        return 0

    mib0 = process.ReadUnsignedFromMemory(mib_addr, 4, error)
    if not error.Success():
        return 0
    mib1 = process.ReadUnsignedFromMemory(mib_addr + 4, 4, error)
    if not error.Success():
        return 0
    mib2 = process.ReadUnsignedFromMemory(mib_addr + 8, 4, error)
    if not error.Success():
        return 0

    if mib0 == 1 and mib1 == 14 and mib2 == 1:
        oldp = read_register_u64(frame, oldp_reg)
        if oldp:
            ANTIDEBUG_SYSCTL_OLDP.append(oldp)
            pc = frame.GetPC()
            flavor = arch.disasm_flavor()
            insts = read_instructions(target, pc, 64, flavor=flavor)
            for inst in insts:
                if inst.mnemonic.lower().startswith("ret"):
                    bp = target.BreakpointCreateByAddress(inst.address)
                    bp.SetOneShot(True)
                    thread = frame.GetThread()
                    if thread:
                        bp.SetThreadID(thread.GetThreadID())
                    bp.SetScriptCallbackFunction(
                        "lldb_mix.commands.antidebug.antidebug_callback_step2"
                    )
                    break

    process.Continue()
    return 0


def antidebug_callback_step2(frame, bp_loc, internal_dict):
    if frame is None:
        return 0

    try:
        import lldb
    except Exception:
        return 0

    process = frame.GetThread().GetProcess()
    error = lldb.SBError()
    for oldp in list(ANTIDEBUG_SYSCTL_OLDP):
        ANTIDEBUG_SYSCTL_OLDP.remove(oldp)
        value = process.ReadUnsignedFromMemory(oldp + 0x20, 4, error)
        if not error.Success():
            continue
        if value & 0x800:
            value ^= 0x800
        patch = struct.pack("<I", value)
        process.WriteMemory(oldp + 0x20, patch, error)
    process.Continue()
    return 0


def antidebug_ptrace_callback(frame, bp_loc, internal_dict):
    if frame is None:
        return 0

    arch = detect_arch_from_frame(frame, SETTINGS.abi)
    if arch is None:
        return 0
    abi = getattr(arch, "abi", None)
    if not abi or not getattr(abi, "int_arg_regs", None):
        return 0

    request_reg = arch.arg_reg(0)
    if not request_reg:
        return 0
    request = _reg_u64(frame, request_reg)
    if request != 31:
        frame.GetThread().GetProcess().Continue()
        return 0

    ret_reg = getattr(abi, "return_reg", None) or getattr(arch, "return_reg", None)
    if not ret_reg:
        return 0
    reg = find_register(frame, ret_reg)
    if reg and set_register_value(reg, "0x0"):
        thread = frame.GetThread()
        thread.ReturnFromFrame(frame, reg)
    frame.GetThread().GetProcess().Continue()
    return 0


def antidebug_task_exception_ports_callback(frame, bp_loc, internal_dict):
    if frame is None:
        return 0

    arch = detect_arch_from_frame(frame, SETTINGS.abi)
    if arch is None:
        return 0
    abi = getattr(arch, "abi", None)
    if not abi or not getattr(abi, "int_arg_regs", None):
        return 0

    mask_reg = arch.arg_reg(1)
    if not mask_reg:
        return 0
    mask = read_register_u64(frame, mask_reg)
    if mask:
        reg = find_register(frame, mask_reg)
        if reg:
            set_register_value(reg, "0x0")
    frame.GetThread().GetProcess().Continue()
    return 0


def _register_bp(target, symbol: str, module: str, callback: str) -> tuple[str, int]:
    bp = target.BreakpointCreateByName(symbol, module)
    if not bp or not bp.IsValid():
        return symbol, -1
    bp.AddName("lldb-mix-antidebug")
    bp.SetScriptCallbackFunction(callback)
    return symbol, bp.GetNumLocations()


def _is_antidebug_enabled(target) -> bool:
    key = _target_key(target)
    return key in ANTIDEBUG_TARGETS


def _target_key(target) -> int:
    for attr in ("GetID", "GetUniqueID", "GetTargetID"):
        func = getattr(target, attr, None)
        if callable(func):
            try:
                return int(func())
            except Exception:
                continue
    return id(target)


def _usage() -> str:
    return "[lldb-mix] usage: antidebug"
