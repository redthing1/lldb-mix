from __future__ import annotations

ARCH_FAMILIES: dict[str, tuple[str, ...]] = {
    "x86_64": ("x86_64", "x86-64", "amd64", "x64"),
    "x86": ("i386", "i486", "i586", "i686", "i86pc", "x86", "x86_32", "x86-32"),
    "arm64": ("arm64", "aarch64"),
    "arm32": ("arm32", "arm", "armv", "thumb"),
    "riscv": ("riscv", "rv32", "rv64"),
    "mips": ("mips",),
}

_GENERIC_ARCH_TOKENS = {"", "unknown", "none", "generic"}


def family_from_token(token: str) -> str | None:
    normalized = _normalize_arch_token(token)
    if not normalized or normalized in _GENERIC_ARCH_TOKENS:
        return None
    if (
        normalized in ARCH_FAMILIES["x86_64"]
        or normalized.startswith("x86_64")
        or normalized.startswith("x86-64")
    ):
        return "x86_64"
    if normalized in ARCH_FAMILIES["x86"]:
        return "x86"
    if normalized.startswith("arm64") or normalized.startswith("aarch64"):
        return "arm64"
    if (
        normalized == "arm"
        or normalized == "arm32"
        or normalized.startswith("armv")
        or normalized.startswith("thumb")
    ):
        return "arm32"
    if (
        normalized.startswith("riscv")
        or normalized.startswith("rv32")
        or normalized.startswith("rv64")
    ):
        return "riscv"
    if normalized.startswith("mips"):
        return "mips"
    return None


def declared_family(triple: str, arch_name: str) -> str | None:
    triple_token = triple_arch_token(triple)
    triple_family = family_from_token(triple_token)
    if triple_family:
        return triple_family
    if _is_explicit_arch_token(triple_token):
        return None
    return family_from_token(arch_name_token(arch_name))


def is_explicitly_unsupported_arch(triple: str, arch_name: str) -> bool:
    triple_token = triple_arch_token(triple)
    triple_family = family_from_token(triple_token)
    if triple_family:
        return False
    if _is_explicit_arch_token(triple_token):
        return True
    arch_token = arch_name_token(arch_name)
    return _is_explicit_arch_token(arch_token) and family_from_token(arch_token) is None


def profile_family(profile_name: str) -> str | None:
    return family_from_token(arch_name_token(profile_name))


def triple_arch_token(triple: str) -> str:
    if not triple:
        return ""
    return triple.split("-", 1)[0].strip().lower()


def arch_name_token(arch_name: str) -> str:
    if not arch_name:
        return ""
    return _normalize_arch_token(str(arch_name).split(None, 1)[0])


def _normalize_arch_token(value: str) -> str:
    return (value or "").strip().lower()


def _is_explicit_arch_token(token: str) -> bool:
    return bool(token and token not in _GENERIC_ARCH_TOKENS)
