from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace

from lldb_mix.arch.abi import abi_matches_arch, lookup_abi, select_abi
from lldb_mix.arch.arm64 import ARM64_ARCH
from lldb_mix.arch.base import ArchSpec, UNKNOWN_ARCH
from lldb_mix.arch.x64 import X64_ARCH


def detect_arch(
    triple: str,
    reg_names: Iterable[str],
    abi_override: str | None = None,
) -> ArchSpec:
    triple_lower = (triple or "").lower()
    if "x86_64" in triple_lower or "amd64" in triple_lower:
        return _apply_abi_override(_with_abi(X64_ARCH, triple), abi_override)
    if "arm64" in triple_lower or "aarch64" in triple_lower:
        return _apply_abi_override(_with_abi(ARM64_ARCH, triple), abi_override)

    reg_set = {r.lower() for r in reg_names}
    if {"x0", "x1", "sp", "pc"}.issubset(reg_set):
        return _apply_abi_override(_with_abi(ARM64_ARCH, triple), abi_override)
    if {"rax", "rip", "rsp"}.issubset(reg_set):
        return _apply_abi_override(_with_abi(X64_ARCH, triple), abi_override)

    return UNKNOWN_ARCH


def _with_abi(arch: ArchSpec, triple: str) -> ArchSpec:
    abi = select_abi(triple, arch.name)
    if not abi:
        return arch
    if arch.abi == abi:
        return arch
    return replace(arch, abi=abi)


def _apply_abi_override(arch: ArchSpec, abi_override: str | None) -> ArchSpec:
    if not abi_override or abi_override == "auto":
        return arch
    abi = lookup_abi(abi_override)
    if not abi or not abi_matches_arch(abi, arch.name):
        return arch
    if arch.abi == abi:
        return arch
    return replace(arch, abi=abi)
