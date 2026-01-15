from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace

from lldb_mix.arch.abi import select_abi
from lldb_mix.arch.arm64 import ARM64_ARCH
from lldb_mix.arch.base import ArchSpec, UNKNOWN_ARCH
from lldb_mix.arch.x64 import X64_ARCH


def detect_arch(triple: str, reg_names: Iterable[str]) -> ArchSpec:
    triple_lower = (triple or "").lower()
    if "x86_64" in triple_lower or "amd64" in triple_lower:
        return _with_abi(X64_ARCH, triple)
    if "arm64" in triple_lower or "aarch64" in triple_lower:
        return _with_abi(ARM64_ARCH, triple)

    reg_set = {r.lower() for r in reg_names}
    if {"x0", "x1", "sp", "pc"}.issubset(reg_set):
        return _with_abi(ARM64_ARCH, triple)
    if {"rax", "rip", "rsp"}.issubset(reg_set):
        return _with_abi(X64_ARCH, triple)

    return UNKNOWN_ARCH


def _with_abi(arch: ArchSpec, triple: str) -> ArchSpec:
    abi = select_abi(triple, arch.name)
    if not abi:
        return arch
    if arch.abi == abi:
        return arch
    return replace(arch, abi=abi)
