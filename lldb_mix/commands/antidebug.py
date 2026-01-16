from __future__ import annotations

import shlex
import struct

from lldb_mix.commands.utils import emit_result
from lldb_mix.core.disasm import disasm_flavor, read_instructions
from lldb_mix.core.session import Session


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

    arch = _arch_kind(frame)
    if arch is None:
        return 0

    process = frame.GetThread().GetProcess()
    target = process.GetTarget()
    error = lldb.SBError()

    mib_reg = "rdi" if arch == "x64" else "x0"
    oldp_reg = "rdx" if arch == "x64" else "x2"
    mib_addr = _reg_u64(frame, mib_reg)
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
        oldp = _reg_u64(frame, oldp_reg)
        if oldp:
            ANTIDEBUG_SYSCTL_OLDP.append(oldp)
            pc = frame.GetPC()
            flavor = disasm_flavor(arch)
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

    arch = _arch_kind(frame)
    if arch is None:
        return 0

    request_reg = "rdi" if arch == "x64" else "x0"
    request = _reg_u64(frame, request_reg)
    if request != 31:
        frame.GetThread().GetProcess().Continue()
        return 0

    ret_reg = "rax" if arch == "x64" else "x0"
    reg = _reg_value(frame, ret_reg)
    if reg and _set_reg_value(reg, "0x0"):
        thread = frame.GetThread()
        thread.ReturnFromFrame(frame, reg)
    frame.GetThread().GetProcess().Continue()
    return 0


def antidebug_task_exception_ports_callback(frame, bp_loc, internal_dict):
    if frame is None:
        return 0

    arch = _arch_kind(frame)
    if arch is None:
        return 0

    mask_reg = "rsi" if arch == "x64" else "x1"
    mask = _reg_u64(frame, mask_reg)
    if mask:
        reg = _reg_value(frame, mask_reg)
        if reg:
            _set_reg_value(reg, "0x0")
    frame.GetThread().GetProcess().Continue()
    return 0


def _arch_kind(frame) -> str | None:
    if _reg_value(frame, "rdi") is not None:
        return "x64"
    if _reg_value(frame, "x0") is not None:
        return "arm64"
    return None


def _reg_u64(frame, name: str) -> int | None:
    reg = _reg_value(frame, name)
    if reg is None:
        return None
    try:
        return int(reg.GetValueAsUnsigned())
    except Exception:
        try:
            return int(reg.GetValue(), 0)
        except Exception:
            return None


def _reg_value(frame, name: str):
    try:
        reg = frame.FindRegister(name)
    except Exception:
        return None
    if not reg or not reg.IsValid():
        return None
    return reg


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
            return bool(reg.SetValueFromCString(value, error))
        except Exception:
            return False


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
