from __future__ import annotations

ARCH_FAMILIES: dict[str, tuple[str, ...]] = {
    "x86_64": ("x86_64", "amd64", "x64"),
    "arm64": ("arm64", "aarch64"),
    "arm32": ("armv", "arm32", "arm-", "thumb"),
    "riscv": ("riscv", "rv32", "rv64"),
}


def family_in_text(text: str, family: str) -> bool:
    tokens = ARCH_FAMILIES.get(family, ())
    if not tokens:
        return False
    lowered = (text or "").lower()
    return any(token in lowered for token in tokens)


def explicit_family(text: str) -> str | None:
    lowered = (text or "").lower()
    matches = [
        name for name, tokens in ARCH_FAMILIES.items() if any(t in lowered for t in tokens)
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def allows_family(triple: str, arch_name: str, family: str) -> bool:
    triple_text = (triple or "").lower()
    arch_text = (arch_name or "").lower()
    if triple_text:
        if family_in_text(triple_text, family):
            return True
        if any(
            family_in_text(triple_text, other)
            for other in ARCH_FAMILIES
            if other != family
        ):
            return False
    if arch_text:
        if family_in_text(arch_text, family):
            return True
        if any(
            family_in_text(arch_text, other)
            for other in ARCH_FAMILIES
            if other != family
        ):
            return False
    return True
