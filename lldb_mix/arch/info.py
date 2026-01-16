from __future__ import annotations

from dataclasses import dataclass
from typing import Any


_PC_CANDIDATES = ("pc", "rip", "eip")
_SP_CANDIDATES = ("sp", "rsp", "esp")
_FLAGS_CANDIDATES = ("cpsr", "rflags", "eflags", "flags", "psr")


@dataclass(frozen=True)
class ArchInfo:
    triple: str
    arch_name: str
    ptr_size: int
    gpr_names: tuple[str, ...]
    reg_sets: dict[str, tuple[str, ...]]
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
        gpr_names = _select_gpr_set(reg_sets)
        pc_value = _safe_get_pc(frame)
        sp_value = _safe_get_sp(frame)
        pc_reg_name = _find_candidate(gpr_names, _PC_CANDIDATES)
        sp_reg_name = _find_candidate(gpr_names, _SP_CANDIDATES)
        flags_reg_name = _find_candidate(gpr_names, _FLAGS_CANDIDATES)
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
        reg_sets: dict[str, list[str] | tuple[str, ...]],
        pc_value: int | None = None,
        sp_value: int | None = None,
        pc_reg_name: str | None = None,
        sp_reg_name: str | None = None,
        flags_reg_name: str | None = None,
    ) -> "ArchInfo":
        normalized = {
            name: tuple(_normalize_reg_name(reg) for reg in regs if reg)
            for name, regs in reg_sets.items()
        }
        gpr_names = _select_gpr_set(normalized)
        if not pc_reg_name:
            pc_reg_name = _find_candidate(gpr_names, _PC_CANDIDATES)
        if not sp_reg_name:
            sp_reg_name = _find_candidate(gpr_names, _SP_CANDIDATES)
        if not flags_reg_name:
            flags_reg_name = _find_candidate(gpr_names, _FLAGS_CANDIDATES)
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


def _safe_get_reg_sets(frame: Any | None) -> dict[str, tuple[str, ...]]:
    reg_sets: dict[str, tuple[str, ...]] = {}
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
        names: list[str] = []
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
            names.append(_normalize_reg_name(reg_name))
        reg_sets[set_name] = tuple(names)
    return reg_sets


def _select_gpr_set(reg_sets: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    if not reg_sets:
        return ()
    candidates: list[tuple[int, tuple[str, ...]]] = []
    for name, regs in reg_sets.items():
        lower = (name or "").lower()
        if ("general" in lower and "purpose" in lower) or "gpr" in lower:
            candidates.append((len(regs), regs))
    if candidates:
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]
    # Fallback: choose the largest register set.
    fallback = max(reg_sets.values(), key=len, default=())
    return fallback


def _find_candidate(names: tuple[str, ...], candidates: tuple[str, ...]) -> str | None:
    if not names:
        return None
    name_set = {name.lower() for name in names}
    for candidate in candidates:
        if candidate in name_set:
            return candidate
    return None


def _normalize_reg_name(name: str) -> str:
    return (name or "").strip().lower()
