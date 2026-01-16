from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class RegInfo:
    name: str
    byte_size: int = 0


def normalize_reg_name(name: str) -> str:
    return (name or "").strip().lower()


def normalize_reg_info(
    regs: Iterable[RegInfo | str | tuple[str, int]],
) -> list[RegInfo]:
    normalized: list[RegInfo] = []
    for reg in regs:
        if isinstance(reg, RegInfo):
            name = normalize_reg_name(reg.name)
            normalized.append(RegInfo(name=name, byte_size=int(reg.byte_size or 0)))
            continue
        if isinstance(reg, tuple) and len(reg) >= 1:
            name = normalize_reg_name(str(reg[0]))
            byte_size = int(reg[1]) if len(reg) > 1 else 0
            normalized.append(RegInfo(name=name, byte_size=byte_size))
            continue
        name = normalize_reg_name(str(reg))
        if name:
            normalized.append(RegInfo(name=name, byte_size=0))
    return normalized


def normalize_reg_values(values: dict[str, int] | None) -> dict[str, int]:
    if not values:
        return {}
    return {normalize_reg_name(name): int(value) for name, value in values.items()}


def select_gpr_set(
    reg_sets: dict[str, tuple[RegInfo, ...]],
    ptr_size: int,
    pc_candidates: tuple[str, ...],
    sp_candidates: tuple[str, ...],
) -> tuple[RegInfo, ...]:
    if not reg_sets:
        return ()
    best_score = -1
    best_regs: tuple[RegInfo, ...] = ()
    for name, regs in reg_sets.items():
        score = score_reg_set(name, regs, ptr_size, pc_candidates, sp_candidates)
        if score > best_score:
            best_score = score
            best_regs = regs
    if best_score < 0:
        return ()
    return best_regs


def score_reg_set(
    name: str,
    regs: tuple[RegInfo, ...],
    ptr_size: int,
    pc_candidates: tuple[str, ...],
    sp_candidates: tuple[str, ...],
) -> int:
    if not regs:
        return -1
    score = 0
    lower = (name or "").lower()
    if ("general" in lower and "purpose" in lower) or "gpr" in lower:
        score += 100
    if ptr_size:
        score += 2 * sum(1 for reg in regs if reg.byte_size == ptr_size)
    names = {reg.name for reg in regs}
    if any(candidate in names for candidate in pc_candidates):
        score += 5
    if any(candidate in names for candidate in sp_candidates):
        score += 5
    score += len(regs)
    return score


def find_candidate(names: tuple[str, ...], candidates: tuple[str, ...]) -> str | None:
    if not names:
        return None
    name_set = {name.lower() for name in names}
    for candidate in candidates:
        if candidate in name_set:
            return candidate
    return None


def find_named_reg(
    gpr_names: tuple[str, ...],
    reg_sets: dict[str, tuple[RegInfo, ...]],
    candidates: tuple[str, ...],
) -> str | None:
    selected = find_candidate(gpr_names, candidates)
    if selected:
        return selected
    for regs in reg_sets.values():
        names = tuple(reg.name for reg in regs)
        selected = find_candidate(names, candidates)
        if selected:
            return selected
    return None


def find_reg_by_value(
    reg_sets: dict[str, tuple[RegInfo, ...]],
    reg_values: dict[str, int],
    ptr_size: int,
    target: int,
) -> str | None:
    if not reg_values:
        return None
    matches: list[str] = []
    seen: set[str] = set()
    for regs in reg_sets.values():
        for reg in regs:
            name = reg.name
            if not name or name in seen:
                continue
            seen.add(name)
            if ptr_size and reg.byte_size and reg.byte_size != ptr_size:
                continue
            value = reg_values.get(name)
            if value is None:
                continue
            if value == target:
                matches.append(name)
                if len(matches) > 1:
                    return None
    if len(matches) == 1:
        return matches[0]
    return None
