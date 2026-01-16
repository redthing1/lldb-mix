from __future__ import annotations

from dataclasses import dataclass
import re

from lldb_mix.arch.abi import AbiSpec


@dataclass(frozen=True)
class BranchDecision:
    taken: bool
    reason: str
    kind: str

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

    def is_branch_like(self, mnemonic: str) -> bool:
        mnem = (mnemonic or "").lower()
        if mnem.startswith("ret"):
            return True
        return (
            self.is_conditional_branch(mnemonic)
            or self.is_unconditional_branch(mnemonic)
            or self.is_call(mnemonic)
        )

    def resolve_flow_target(
        self, mnemonic: str, operands: str, regs: dict[str, int]
    ) -> int | None:
        if not self.is_branch_like(mnemonic):
            return None
        if not operands:
            return None
        op = operands.split(",", 1)[0].strip()
        return parse_target_operand(op, regs)

    def branch_decision(
        self,
        mnemonic: str,
        operands: str,
        regs: dict[str, int],
        flags: int,
        include_unconditional: bool = False,
        include_calls: bool = False,
    ) -> BranchDecision | None:
        if self.is_conditional_branch(mnemonic):
            taken, reason = self.branch_taken(mnemonic, flags)
            if reason:
                return BranchDecision(taken, reason, "conditional")
        if include_calls and self.is_call(mnemonic):
            return BranchDecision(True, "", "call")
        if include_unconditional and self.is_unconditional_branch(mnemonic):
            return BranchDecision(True, "", "unconditional")
        return None

    def register_aliases(self, regs: dict[str, int]) -> dict[str, str]:
        _ = regs
        return {}


def parse_immediate(text: str) -> int | None:
    if not text:
        return None
    op = text.strip()
    if op.startswith("#"):
        op = op[1:]
    try:
        return int(op, 0)
    except ValueError:
        return None


def parse_leading_int(text: str) -> int | None:
    if not text:
        return None
    match = re.match(r"^[-+]?0x[0-9a-fA-F]+|^[-+]?\d+", text.strip())
    if not match:
        return None
    try:
        return int(match.group(0), 0)
    except ValueError:
        return None


def resolve_reg_operand(
    op: str,
    regs: dict[str, int],
    aliases: dict[str, str] | None = None,
) -> int | None:
    key = (op or "").lower()
    if key in regs:
        return regs.get(key)
    if aliases and key in aliases:
        return regs.get(aliases[key])
    return None


def parse_target_operand(
    op: str,
    regs: dict[str, int],
    aliases: dict[str, str] | None = None,
) -> int | None:
    if not op:
        return None
    parsed = parse_immediate(op)
    if parsed is None:
        parsed = parse_leading_int(op)
    if parsed is not None:
        return parsed
    return resolve_reg_operand(op, regs, aliases)


UNKNOWN_ARCH = ArchSpec(
    name="unknown",
    ptr_size=0,
    gpr_names=(),
    pc_reg="",
    sp_reg="",
    flags_reg=None,
    special_regs=(),
)
