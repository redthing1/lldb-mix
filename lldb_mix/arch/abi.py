from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AbiSpec:
    name: str
    int_arg_regs: tuple[str, ...]
    float_arg_regs: tuple[str, ...] = ()
    return_reg: str | None = None
    return_float_reg: str | None = None
    stack_alignment: int | None = None
    red_zone: int | None = None
    callee_saved: tuple[str, ...] = ()
    caller_saved: tuple[str, ...] = ()


SYSV_X64 = AbiSpec(
    name="sysv",
    int_arg_regs=("rdi", "rsi", "rdx", "rcx", "r8", "r9"),
    return_reg="rax",
    stack_alignment=16,
    red_zone=128,
    callee_saved=("rbx", "rbp", "r12", "r13", "r14", "r15", "rsp"),
    caller_saved=("rax", "rcx", "rdx", "rsi", "rdi", "r8", "r9", "r10", "r11"),
)

WIN64 = AbiSpec(
    name="win64",
    int_arg_regs=("rcx", "rdx", "r8", "r9"),
    return_reg="rax",
    stack_alignment=16,
    callee_saved=("rbx", "rbp", "rdi", "rsi", "r12", "r13", "r14", "r15", "rsp"),
    caller_saved=("rax", "rcx", "rdx", "r8", "r9", "r10", "r11"),
)

AAPCS64 = AbiSpec(
    name="aapcs64",
    int_arg_regs=("x0", "x1", "x2", "x3", "x4", "x5", "x6", "x7"),
    return_reg="x0",
    stack_alignment=16,
    callee_saved=(
        "x19",
        "x20",
        "x21",
        "x22",
        "x23",
        "x24",
        "x25",
        "x26",
        "x27",
        "x28",
        "fp",
        "sp",
    ),
    caller_saved=("x0", "x1", "x2", "x3", "x4", "x5", "x6", "x7", "x8"),
)

RISCV_ABI = AbiSpec(
    name="riscv",
    int_arg_regs=("a0", "a1", "a2", "a3", "a4", "a5", "a6", "a7"),
    return_reg="a0",
    stack_alignment=16,
)

RISCV_X_ABI = AbiSpec(
    name="riscv-x",
    int_arg_regs=("x10", "x11", "x12", "x13", "x14", "x15", "x16", "x17"),
    return_reg="x10",
    stack_alignment=16,
)


ABI_BY_NAME = {
    SYSV_X64.name: SYSV_X64,
    WIN64.name: WIN64,
    AAPCS64.name: AAPCS64,
    RISCV_ABI.name: RISCV_ABI,
    RISCV_X_ABI.name: RISCV_X_ABI,
}

ABI_ARCHES = {
    "sysv": ("x86_64", "amd64"),
    "win64": ("x86_64", "amd64"),
    "aapcs64": ("arm64", "aarch64"),
    "riscv": ("riscv64", "riscv32", "riscv"),
    "riscv-x": ("riscv64", "riscv32", "riscv"),
}


def lookup_abi(name: str) -> AbiSpec | None:
    return ABI_BY_NAME.get((name or "").lower())


def abi_matches_arch(abi: AbiSpec, arch_name: str) -> bool:
    if not abi or not arch_name:
        return False
    targets = ABI_ARCHES.get(abi.name, ())
    arch_lower = arch_name.lower()
    return any(token in arch_lower for token in targets)


def select_abi(triple: str, arch_name: str) -> AbiSpec | None:
    triple_lower = (triple or "").lower()
    arch_lower = (arch_name or "").lower()

    if "x86_64" in arch_lower or "amd64" in arch_lower:
        if any(token in triple_lower for token in ("windows", "mingw", "msvc")):
            return WIN64
        return SYSV_X64

    if "arm64" in arch_lower or "aarch64" in arch_lower:
        return AAPCS64
    if "riscv" in arch_lower:
        return RISCV_ABI

    return None
