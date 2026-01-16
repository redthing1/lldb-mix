from __future__ import annotations

from dataclasses import replace
import importlib
import pkgutil
from typing import Callable

from lldb_mix.arch.abi import abi_matches_arch, lookup_abi, select_abi
from lldb_mix.arch.base import ArchProfile
from lldb_mix.arch.info import ArchInfo
from lldb_mix.arch.view import ArchView

_MATCHERS: list[tuple[ArchProfile, Callable[[ArchInfo], int]]] = []
_PROFILES_LOADED = False
_ARCH_FAMILIES: dict[str, tuple[str, ...]] = {
    "x86_64": ("x86_64", "amd64", "x64"),
    "arm64": ("arm64", "aarch64"),
    "riscv": ("riscv", "rv32", "rv64"),
}


def register_profile(profile: ArchProfile, matcher: Callable[[ArchInfo], int]) -> None:
    _MATCHERS.append((profile, matcher))


def detect_arch(target, frame, abi_override: str | None = None) -> ArchView:
    info = ArchInfo.from_lldb(target, frame)
    return detect_arch_info(info, abi_override)


def detect_arch_from_frame(frame, abi_override: str | None = None) -> ArchView:
    target = None
    if frame is not None:
        try:
            thread = frame.GetThread()
            process = thread.GetProcess() if thread else None
            target = process.GetTarget() if process else None
        except Exception:
            target = None
    return detect_arch(target, frame, abi_override)


def detect_arch_info(info: ArchInfo, abi_override: str | None = None) -> ArchView:
    profile = select_profile(info)
    profile = _with_abi(profile, info)
    profile = _apply_abi_override(profile, abi_override)
    return ArchView(info=info, profile=profile)


def select_profile(info: ArchInfo) -> ArchProfile | None:
    _ensure_profiles_loaded()
    family = _explicit_family(info)
    best: ArchProfile | None = None
    best_score = 0
    for profile, matcher in _MATCHERS:
        if family and not _profile_matches_family(profile, family):
            continue
        try:
            score = int(matcher(info))
        except Exception:
            score = 0
        if score > best_score:
            best = profile
            best_score = score
    if best_score <= 0:
        return None
    return best


def _explicit_family(info: ArchInfo) -> str | None:
    text = f"{info.triple} {info.arch_name}".lower()
    matches = [
        name for name, tokens in _ARCH_FAMILIES.items() if any(t in text for t in tokens)
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def _profile_matches_family(profile: ArchProfile, family: str) -> bool:
    name = (profile.name or "").lower()
    if family == "x86_64":
        return "x86_64" in name or "amd64" in name or name == "x64"
    return family in name


def _ensure_profiles_loaded() -> None:
    global _PROFILES_LOADED
    if _PROFILES_LOADED:
        return
    # Importing modules registers profiles via register_profile.
    import lldb_mix.arch as arch_pkg

    excluded = {"abi", "base", "info", "view", "registry"}
    for module in pkgutil.iter_modules(arch_pkg.__path__):
        name = module.name
        if name in excluded:
            continue
        importlib.import_module(f"{arch_pkg.__name__}.{name}")
    _PROFILES_LOADED = True


def _with_abi(profile: ArchProfile | None, info: ArchInfo) -> ArchProfile | None:
    if not profile:
        return None
    if profile.abi is not None:
        return profile
    abi = select_abi(info.triple, profile.name)
    if not abi:
        return profile
    if profile.abi == abi:
        return profile
    return replace(profile, abi=abi)


def _apply_abi_override(
    profile: ArchProfile | None, abi_override: str | None
) -> ArchProfile | None:
    if not profile:
        return None
    if not abi_override or abi_override == "auto":
        return profile
    abi = lookup_abi(abi_override)
    if not abi or not abi_matches_arch(abi, profile.name):
        return profile
    if profile.abi == abi:
        return profile
    return replace(profile, abi=abi)
