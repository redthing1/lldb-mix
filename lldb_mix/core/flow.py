from __future__ import annotations

from lldb_mix.arch.base import BranchDecision, ReadPointer
from lldb_mix.arch.view import ArchView


def is_branch_like(mnemonic: str, arch: ArchView) -> bool:
    if not arch:
        return False
    return arch.is_branch_like(mnemonic)


def resolve_flow_target(
    mnemonic: str,
    operands: str,
    regs: dict[str, int],
    arch: ArchView,
    read_pointer: ReadPointer | None = None,
    ptr_size: int | None = None,
) -> int | None:
    if not arch:
        return None
    return arch.resolve_flow_target(
        mnemonic,
        operands,
        regs,
        read_pointer=read_pointer,
        ptr_size=ptr_size,
    )


def branch_decision(
    mnemonic: str,
    operands: str,
    regs: dict[str, int],
    arch: ArchView,
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
