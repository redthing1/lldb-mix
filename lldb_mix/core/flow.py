from __future__ import annotations

from lldb_mix.arch.base import ArchSpec, BranchDecision


def is_branch_like(mnemonic: str, arch: ArchSpec) -> bool:
    if not arch:
        return False
    return arch.is_branch_like(mnemonic)


def resolve_flow_target(
    mnemonic: str,
    operands: str,
    regs: dict[str, int],
    arch: ArchSpec,
) -> int | None:
    if not arch:
        return None
    return arch.resolve_flow_target(mnemonic, operands, regs)


def branch_decision(
    mnemonic: str,
    operands: str,
    regs: dict[str, int],
    arch: ArchSpec,
    flags: int,
    include_unconditional: bool = False,
    include_calls: bool = False,
) -> BranchDecision | None:
    if not arch:
        return None
    return arch.branch_decision(
        mnemonic,
        operands,
        regs,
        flags,
        include_unconditional=include_unconditional,
        include_calls=include_calls,
    )
