from __future__ import annotations

from dataclasses import dataclass

from lldb_mix.arch.abi import AbiSpec


@dataclass(frozen=True)
class ArchSpec:
    name: str
    ptr_size: int
    gpr_names: tuple[str, ...]
    pc_reg: str
    sp_reg: str
    flags_reg: str | None = None
    special_regs: tuple[str, ...] = ()
    max_inst_bytes: int = 4
    return_reg: str | None = None
    nop_bytes: bytes = b""
    break_bytes: bytes = b""
    abi: AbiSpec | None = None
    call_mnemonics: tuple[str, ...] = ()

    def format_flags(self, value: int) -> str:
        return ""

    def is_conditional_branch(self, mnemonic: str) -> bool:
        _ = mnemonic
        return False

    def is_unconditional_branch(self, mnemonic: str) -> bool:
        _ = mnemonic
        return False

    def branch_taken(self, mnemonic: str, flags: int) -> tuple[bool, str]:
        _ = mnemonic
        _ = flags
        return False, ""

    def is_call(self, mnemonic: str) -> bool:
        mnem = mnemonic.lower()
        if self.call_mnemonics:
            return mnem in self.call_mnemonics
        return mnem.startswith("call")


UNKNOWN_ARCH = ArchSpec(
    name="unknown",
    ptr_size=0,
    gpr_names=(),
    pc_reg="",
    sp_reg="",
    flags_reg=None,
    special_regs=(),
)
