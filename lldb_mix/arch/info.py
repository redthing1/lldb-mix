from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from lldb_mix.arch.reginfo import (
    RegInfo,
    find_named_reg,
    find_reg_by_value,
    normalize_reg_info,
    normalize_reg_name,
    normalize_reg_values,
    select_gpr_set,
)

_PC_CANDIDATES = ("pc", "rip", "eip")
_SP_CANDIDATES = ("sp", "rsp", "esp")
_FLAGS_CANDIDATES = ("cpsr", "rflags", "eflags", "flags", "psr")


@dataclass(frozen=True)
class ArchInfo:
    triple: str
    arch_name: str
    ptr_size: int
    gpr_names: tuple[str, ...]
    reg_sets: dict[str, tuple[RegInfo, ...]]
    pc_value: int | None
    sp_value: int | None
    pc_reg_name: str | None
    sp_reg_name: str | None
    flags_reg_name: str | None

    @staticmethod
    def from_lldb(target: Any | None, frame: Any | None) -> "ArchInfo":
        triple = _safe_get_triple(target)
        arch_name = _safe_get_arch_name(target, triple)
        ptr_size = _safe_get_ptr_size(target)
        reg_sets = _safe_get_reg_sets(frame)
        gpr_regs = select_gpr_set(reg_sets, ptr_size, _PC_CANDIDATES, _SP_CANDIDATES)
        gpr_names = tuple(reg.name for reg in gpr_regs)
        pc_value = _safe_get_pc(frame)
        sp_value = _safe_get_sp(frame)
        reg_values = _safe_get_reg_values(frame)
        pc_reg_name = find_named_reg(gpr_names, reg_sets, _PC_CANDIDATES)
        sp_reg_name = find_named_reg(gpr_names, reg_sets, _SP_CANDIDATES)
        flags_reg_name = find_named_reg(gpr_names, reg_sets, _FLAGS_CANDIDATES)
        if pc_reg_name is None and pc_value is not None:
            pc_reg_name = find_reg_by_value(reg_sets, reg_values, ptr_size, pc_value)
        if sp_reg_name is None and sp_value is not None:
            sp_reg_name = find_reg_by_value(reg_sets, reg_values, ptr_size, sp_value)
        return ArchInfo(
            triple=triple,
            arch_name=arch_name,
            ptr_size=ptr_size,
            gpr_names=gpr_names,
            reg_sets=reg_sets,
            pc_value=pc_value,
            sp_value=sp_value,
            pc_reg_name=pc_reg_name,
            sp_reg_name=sp_reg_name,
            flags_reg_name=flags_reg_name,
        )

    @staticmethod
    def from_register_sets(
        triple: str,
        arch_name: str,
        ptr_size: int,
        reg_sets: dict[str, Iterable[RegInfo | str | tuple[str, int]]],
        pc_value: int | None = None,
        sp_value: int | None = None,
        reg_values: dict[str, int] | None = None,
        pc_reg_name: str | None = None,
        sp_reg_name: str | None = None,
        flags_reg_name: str | None = None,
    ) -> "ArchInfo":
        normalized = {name: tuple(normalize_reg_info(regs)) for name, regs in reg_sets.items()}
        gpr_regs = select_gpr_set(normalized, ptr_size, _PC_CANDIDATES, _SP_CANDIDATES)
        gpr_names = tuple(reg.name for reg in gpr_regs)
        reg_values_norm = normalize_reg_values(reg_values)
        if not pc_reg_name:
            pc_reg_name = find_named_reg(gpr_names, normalized, _PC_CANDIDATES)
            if pc_reg_name is None and pc_value is not None:
                pc_reg_name = find_reg_by_value(
                    normalized, reg_values_norm, ptr_size, pc_value
                )
        if not sp_reg_name:
            sp_reg_name = find_named_reg(gpr_names, normalized, _SP_CANDIDATES)
            if sp_reg_name is None and sp_value is not None:
                sp_reg_name = find_reg_by_value(
                    normalized, reg_values_norm, ptr_size, sp_value
                )
        if not flags_reg_name:
            flags_reg_name = find_named_reg(
                gpr_names, normalized, _FLAGS_CANDIDATES
            )
        return ArchInfo(
            triple=triple or "",
            arch_name=arch_name or "",
            ptr_size=ptr_size or 0,
            gpr_names=gpr_names,
            reg_sets=normalized,
            pc_value=pc_value,
            sp_value=sp_value,
            pc_reg_name=pc_reg_name,
            sp_reg_name=sp_reg_name,
            flags_reg_name=flags_reg_name,
        )


def _safe_get_triple(target: Any | None) -> str:
    if not target:
        return ""
    try:
        return target.GetTriple() or ""
    except Exception:
        return ""


def _safe_get_arch_name(target: Any | None, triple: str) -> str:
    if target:
        try:
            arch = target.GetArchitecture()
            name = arch.GetName() if arch else ""
            if name:
                return name
        except Exception:
            pass
    if triple:
        return triple.split("-", 1)[0]
    return ""


def _safe_get_ptr_size(target: Any | None) -> int:
    if not target:
        return 0
    try:
        return int(target.GetAddressByteSize() or 0)
    except Exception:
        return 0


def _safe_get_pc(frame: Any | None) -> int | None:
    if not frame:
        return None
    try:
        return int(frame.GetPC())
    except Exception:
        return None


def _safe_get_sp(frame: Any | None) -> int | None:
    if not frame:
        return None
    try:
        return int(frame.GetSP())
    except Exception:
        return None


def _safe_get_reg_sets(frame: Any | None) -> dict[str, tuple[RegInfo, ...]]:
    reg_sets: dict[str, tuple[RegInfo, ...]] = {}
    if not frame:
        return reg_sets
    try:
        sets = frame.GetRegisters()
    except Exception:
        return reg_sets
    if not sets:
        return reg_sets
    try:
        count = sets.GetSize()
    except Exception:
        return reg_sets
    for idx in range(count):
        try:
            reg_set = sets.GetValueAtIndex(idx)
        except Exception:
            continue
        if not reg_set:
            continue
        try:
            set_name = reg_set.GetName() or f"reg_set_{idx}"
        except Exception:
            set_name = f"reg_set_{idx}"
        regs: list[RegInfo] = []
        try:
            child_count = reg_set.GetNumChildren()
        except Exception:
            child_count = 0
        for child_idx in range(child_count):
            try:
                reg = reg_set.GetChildAtIndex(child_idx)
            except Exception:
                continue
            if not reg:
                continue
            try:
                reg_name = reg.GetName() or ""
            except Exception:
                reg_name = ""
            if not reg_name:
                continue
            try:
                byte_size = int(reg.GetByteSize() or 0)
            except Exception:
                byte_size = 0
            regs.append(
                RegInfo(name=normalize_reg_name(reg_name), byte_size=byte_size)
            )
        reg_sets[set_name] = tuple(regs)
    return reg_sets


def _safe_get_reg_values(frame: Any | None) -> dict[str, int]:
    values: dict[str, int] = {}
    if not frame:
        return values
    try:
        sets = frame.GetRegisters()
    except Exception:
        return values
    for reg_set in sets:
        for reg in reg_set:
            try:
                name = reg.GetName() or ""
            except Exception:
                name = ""
            if not name:
                continue
            try:
                value = int(reg.GetValueAsUnsigned())
            except Exception:
                continue
            values[_normalize_reg_name(name)] = value
    return values


def _normalize_reg_name(name: str) -> str:
    return normalize_reg_name(name)
