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


def select_abi(triple: str, arch_name: str) -> AbiSpec | None:
    triple_lower = (triple or "").lower()
    arch_lower = (arch_name or "").lower()

    if "x86_64" in arch_lower or "amd64" in arch_lower:
        if any(token in triple_lower for token in ("windows", "mingw", "msvc")):
            return WIN64
        return SYSV_X64

    if "arm64" in arch_lower or "aarch64" in arch_lower:
        return AAPCS64

    return None
