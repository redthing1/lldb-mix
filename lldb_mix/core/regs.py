from __future__ import annotations

from typing import Any, Iterable


def iter_registers(frame: Any) -> Iterable[Any]:
    if not frame:
        return []
    try:
        reg_sets = frame.GetRegisters()
    except Exception:
        return []
    if not reg_sets:
        return []
    regs: list[Any] = []
    try:
        for reg_set in reg_sets:
            for reg in reg_set:
                regs.append(reg)
    except Exception:
        return regs
    return regs


def find_register(frame: Any, name: str):
    if not frame or not name:
        return None
    try:
        reg = frame.FindRegister(name)
    except Exception:
        return None
    if not reg or not reg.IsValid():
        return None
    return reg


def find_register_any(frame: Any, names: list[str]):
    for name in names:
        if not name:
            continue
        reg = find_register(frame, name)
        if reg:
            return reg
    lowered = [name.lower() for name in names if name]
    if not lowered:
        return None
    for reg in iter_registers(frame):
        try:
            reg_name = reg.GetName() or ""
        except Exception:
            reg_name = ""
        if not reg_name:
            continue
        if reg_name.lower() in lowered:
            return reg
    return None


def read_register_u64(frame: Any, name: str) -> int | None:
    reg = find_register(frame, name)
    if not reg:
        return None
    try:
        return int(reg.GetValueAsUnsigned())
    except Exception:
        try:
            raw = reg.GetValue()
        except Exception:
            return None
        if not raw:
            return None
        try:
            return int(raw, 0)
        except Exception:
            return None


def set_register_value(reg, value: str) -> bool:
    if not reg:
        return False
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
