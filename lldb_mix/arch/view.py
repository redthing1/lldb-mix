from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lldb_mix.arch.base import ArchProfile, BranchDecision, ReadPointer
from lldb_mix.arch import abi as arch_abi
from lldb_mix.arch.info import ArchInfo
from lldb_mix.core.regs import find_register_any


@dataclass(frozen=True)
class ArchView:
    info: ArchInfo
    profile: ArchProfile | None = None

    @property
    def name(self) -> str:
        if self.profile and getattr(self.profile, "name", ""):
            return self.profile.name
        return self.info.arch_name or "unknown"

    @property
    def ptr_size(self) -> int:
        if self.info.ptr_size:
            return self.info.ptr_size
        if self.profile and getattr(self.profile, "ptr_size", 0):
            return int(self.profile.ptr_size)
        return 0

    @property
    def gpr_names(self) -> tuple[str, ...]:
        if self.profile and getattr(self.profile, "gpr_names", None):
            if self.profile.gpr_names:
                return self.profile.gpr_names
        return self.info.gpr_names

    @property
    def pc_reg(self) -> str:
        if self.profile and getattr(self.profile, "pc_reg", ""):
            return self.profile.pc_reg
        return self.info.pc_reg_name or ""

    @property
    def sp_reg(self) -> str:
        if self.profile and getattr(self.profile, "sp_reg", ""):
            return self.profile.sp_reg
        return self.info.sp_reg_name or ""

    @property
    def flags_reg(self) -> str | None:
        if self.profile and getattr(self.profile, "flags_reg", None):
            return self.profile.flags_reg
        return self.info.flags_reg_name

    @property
    def special_regs(self) -> tuple[str, ...]:
        if self.profile and getattr(self.profile, "special_regs", None) is not None:
            return self.profile.special_regs
        return ()

    @property
    def max_inst_bytes(self) -> int:
        if self.profile and getattr(self.profile, "max_inst_bytes", 0):
            return int(self.profile.max_inst_bytes)
        return 0

    @property
    def return_reg(self) -> str | None:
        if self.profile and getattr(self.profile, "return_reg", None):
            return self.profile.return_reg
        abi = self.abi
        if abi and getattr(abi, "return_reg", None):
            return abi.return_reg
        return None

    @property
    def nop_bytes(self) -> bytes:
        if self.profile and getattr(self.profile, "nop_bytes", None) is not None:
            return self.profile.nop_bytes
        return b""

    @property
    def break_bytes(self) -> bytes:
        if self.profile and getattr(self.profile, "break_bytes", None) is not None:
            return self.profile.break_bytes
        return b""

    @property
    def abi(self):
        if self.profile and getattr(self.profile, "abi", None):
            return self.profile.abi
        return None

    @property
    def call_mnemonics(self) -> tuple[str, ...]:
        if self.profile and getattr(self.profile, "call_mnemonics", None):
            return self.profile.call_mnemonics
        return ()

    @property
    def pc_value(self) -> int | None:
        return self.info.pc_value

    @property
    def sp_value(self) -> int | None:
        return self.info.sp_value

    def disasm_flavor(self) -> str:
        if self.profile and hasattr(self.profile, "disasm_flavor"):
            return self.profile.disasm_flavor()
        return ""

    def format_flags(self, value: int) -> str:
        if self.profile and hasattr(self.profile, "format_flags"):
            return self.profile.format_flags(value)
        return ""

    def is_conditional_branch(self, mnemonic: str) -> bool:
        if self.profile and hasattr(self.profile, "is_conditional_branch"):
            return self.profile.is_conditional_branch(mnemonic)
        return False

    def is_unconditional_branch(self, mnemonic: str) -> bool:
        if self.profile and hasattr(self.profile, "is_unconditional_branch"):
            return self.profile.is_unconditional_branch(mnemonic)
        return False

    def is_call(self, mnemonic: str) -> bool:
        if self.profile and hasattr(self.profile, "is_call"):
            return self.profile.is_call(mnemonic)
        return False

    def is_return(self, mnemonic: str) -> bool:
        if self.profile and hasattr(self.profile, "is_return"):
            return self.profile.is_return(mnemonic)
        return False

    def is_branch_like(self, mnemonic: str) -> bool:
        if self.profile and hasattr(self.profile, "is_branch_like"):
            return self.profile.is_branch_like(mnemonic)
        return False

    def resolve_flow_target(
        self,
        mnemonic: str,
        operands: str,
        regs: dict[str, int],
        read_pointer: ReadPointer | None = None,
        ptr_size: int | None = None,
    ) -> int | None:
        if self.profile and hasattr(self.profile, "resolve_flow_target"):
            return self.profile.resolve_flow_target(
                mnemonic,
                operands,
                regs,
                read_pointer=read_pointer,
                ptr_size=ptr_size,
            )
        return None

    def branch_decision(
        self,
        mnemonic: str,
        operands: str,
        regs: dict[str, int],
        flags: int,
        include_unconditional: bool = False,
        include_calls: bool = False,
    ) -> BranchDecision | None:
        if self.profile and hasattr(self.profile, "branch_decision"):
            return self.profile.branch_decision(
                mnemonic,
                operands,
                regs,
                flags,
                include_unconditional=include_unconditional,
                include_calls=include_calls,
            )
        return None

    def register_aliases(self, regs: dict[str, int]) -> dict[str, str]:
        if self.profile and hasattr(self.profile, "register_aliases"):
            return self.profile.register_aliases(regs)
        return {}

    def mem_operand_targets(self, operands: str, regs: dict[str, int]) -> list[int]:
        if self.profile and hasattr(self.profile, "mem_operand_targets"):
            return self.profile.mem_operand_targets(operands, regs)
        return []

    def arg_reg(self, index: int) -> str | None:
        return arch_abi.arg_reg(self.abi, index)

    def find_pc_register(self, frame: Any | None):
        if not frame:
            return None
        candidates = []
        if self.pc_reg:
            candidates.append(self.pc_reg)
        candidates.extend(["pc", "rip", "eip"])
        return find_register_any(frame, candidates)

    def find_return_register(self, frame: Any | None):
        if not frame:
            return None
        if self.return_reg:
            return find_register_any(frame, [self.return_reg])
        return None
