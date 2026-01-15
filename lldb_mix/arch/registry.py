from __future__ import annotations

from collections.abc import Iterable

from lldb_mix.arch.arm64 import ARM64_ARCH
from lldb_mix.arch.base import ArchSpec, UNKNOWN_ARCH
from lldb_mix.arch.x64 import X64_ARCH


def detect_arch(triple: str, reg_names: Iterable[str]) -> ArchSpec:
    triple_lower = (triple or "").lower()
    if "x86_64" in triple_lower or "amd64" in triple_lower:
        return X64_ARCH
    if "arm64" in triple_lower or "aarch64" in triple_lower:
        return ARM64_ARCH

    reg_set = {r.lower() for r in reg_names}
    if {"x0", "x1", "sp", "pc"}.issubset(reg_set):
        return ARM64_ARCH
    if {"rax", "rip", "rsp"}.issubset(reg_set):
        return X64_ARCH

    return UNKNOWN_ARCH
