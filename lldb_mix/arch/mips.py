from __future__ import annotations

from lldb_mix.arch.base import (
    ArchProfile,
    BranchDecision,
    ReadPointer,
    parse_immediate,
    parse_leading_int,
    resolve_reg_operand,
)
from lldb_mix.arch.info import ArchInfo
from lldb_mix.arch.registry import register_profile

_MIPS_CALLS = ("jal", "jalr", "bal")

_MIPS_EQ_NE_BRANCHES = {"beq", "beql", "bne", "bnel"}
_MIPS_ZERO_BRANCHES = {
    "beqz",
    "beqzl",
    "bnez",
    "bnezl",
    "bgez",
    "bgezl",
    "bgtz",
    "bgtzl",
    "blez",
    "blezl",
    "bltz",
    "bltzl",
    "bgezal",
    "bltzal",
}
_MIPS_UNCONDITIONAL_BRANCHES = {"b", "j", "jr"}

_MIPS_N64_REG_BY_INDEX: dict[int, str] = {
    0: "zero",
    1: "at",
    2: "v0",
    3: "v1",
    4: "a0",
    5: "a1",
    6: "a2",
    7: "a3",
    8: "a4",
    9: "a5",
    10: "a6",
    11: "a7",
    12: "t0",
    13: "t1",
    14: "t2",
    15: "t3",
    16: "s0",
    17: "s1",
    18: "s2",
    19: "s3",
    20: "s4",
    21: "s5",
    22: "s6",
    23: "s7",
    24: "t8",
    25: "t9",
    26: "k0",
    27: "k1",
    28: "gp",
    29: "sp",
    30: "fp",
    31: "ra",
}

_MIPS_ALIAS_TO_INDEX: dict[str, int] = {f"r{index}": index for index in range(32)}
_MIPS_ALIAS_TO_INDEX.update(
    {name: index for index, name in _MIPS_N64_REG_BY_INDEX.items()}
)
_MIPS_ALIAS_TO_INDEX.update(
    {
        "s8": 30,
        # O32 compatibility aliases for r12-r15.
        "t4": 12,
        "t5": 13,
        "t6": 14,
        "t7": 15,
    }
)

_MIPS_GPRS = (
    tuple(_MIPS_N64_REG_BY_INDEX[index] for index in range(32))
    + tuple(f"r{index}" for index in range(32))
    + ("s8", "pc")
)


class Mips64ElArch(ArchProfile):
    def is_conditional_branch(self, mnemonic: str) -> bool:
        mnem = (mnemonic or "").lower()
        return mnem in _MIPS_EQ_NE_BRANCHES or mnem in _MIPS_ZERO_BRANCHES

    def is_unconditional_branch(self, mnemonic: str) -> bool:
        return (mnemonic or "").lower() in _MIPS_UNCONDITIONAL_BRANCHES

    def is_branch_like(self, mnemonic: str) -> bool:
        mnem = (mnemonic or "").lower()
        if (
            mnem in _MIPS_EQ_NE_BRANCHES
            or mnem in _MIPS_ZERO_BRANCHES
            or mnem in _MIPS_UNCONDITIONAL_BRANCHES
            or mnem in _MIPS_CALLS
            or mnem.startswith("ret")
        ):
            return True
        return super().is_branch_like(mnemonic)

    def resolve_flow_target(
        self,
        mnemonic: str,
        operands: str,
        regs: dict[str, int],
        read_pointer: ReadPointer | None = None,
        ptr_size: int | None = None,
    ) -> int | None:
        _ = read_pointer
        _ = ptr_size
        if not self.is_branch_like(mnemonic):
            return None

        mnem = (mnemonic or "").lower()
        aliases = self.register_aliases(regs)
        parts = [part.strip() for part in operands.split(",")] if operands else []

        if mnem.startswith("ret"):
            return resolve_reg_operand("ra", regs, aliases)

        if mnem in _MIPS_EQ_NE_BRANCHES:
            if len(parts) < 3:
                return None
            return _parse_target_operand(parts[2], regs, aliases)

        if mnem in _MIPS_ZERO_BRANCHES:
            if len(parts) < 2:
                return None
            return _parse_target_operand(parts[1], regs, aliases)

        if mnem in {"jalr", "jr"}:
            if not parts:
                return None
            target_op = parts[-1] if (mnem == "jalr" and len(parts) > 1) else parts[0]
            return _parse_target_operand(target_op, regs, aliases)

        if mnem in {"j", "jal", "b", "bal"}:
            if not parts:
                return None
            return _parse_target_operand(parts[-1], regs, aliases)

        if not parts:
            return None
        return _parse_target_operand(parts[0], regs, aliases)

    def branch_decision(
        self,
        mnemonic: str,
        operands: str,
        regs: dict[str, int],
        flags: int,
        include_unconditional: bool = False,
        include_calls: bool = False,
    ) -> BranchDecision | None:
        decision = super().branch_decision(
            mnemonic,
            operands,
            regs,
            flags,
            include_unconditional=False,
            include_calls=False,
        )
        if decision:
            return decision

        mnem = (mnemonic or "").lower()
        aliases = self.register_aliases(regs)
        parts = [part.strip() for part in operands.split(",")] if operands else []

        if mnem in _MIPS_EQ_NE_BRANCHES:
            if len(parts) < 2:
                return None
            lhs = _resolve_operand_value(parts[0], regs, aliases)
            rhs = _resolve_operand_value(parts[1], regs, aliases)
            if lhs is None or rhs is None:
                return None
            taken = lhs == rhs if mnem.startswith("beq") else lhs != rhs
            op = "==" if mnem.startswith("beq") else "!="
            return BranchDecision(taken, f"{parts[0]}{op}{parts[1]}", "conditional")

        if mnem in _MIPS_ZERO_BRANCHES:
            if not parts:
                return None
            value = _resolve_operand_value(parts[0], regs, aliases)
            if value is None:
                return None
            bits = max(getattr(self, "ptr_size", 0), 1) * 8
            signed = _to_signed(value, bits)
            if mnem.startswith("beqz"):
                return BranchDecision(signed == 0, f"{parts[0]}==0", "conditional")
            if mnem.startswith("bnez"):
                return BranchDecision(signed != 0, f"{parts[0]}!=0", "conditional")
            if mnem.startswith("bgez"):
                return BranchDecision(signed >= 0, f"{parts[0]}>=0", "conditional")
            if mnem.startswith("bgtz"):
                return BranchDecision(signed > 0, f"{parts[0]}>0", "conditional")
            if mnem.startswith("blez"):
                return BranchDecision(signed <= 0, f"{parts[0]}<=0", "conditional")
            if mnem.startswith("bltz"):
                return BranchDecision(signed < 0, f"{parts[0]}<0", "conditional")

        if include_calls and self.is_call(mnemonic):
            return BranchDecision(True, "", "call")
        if include_unconditional and self.is_return(mnemonic):
            return BranchDecision(True, "", "return")
        if include_unconditional and self.is_unconditional_branch(mnemonic):
            return BranchDecision(True, "", "unconditional")
        return None

    def register_aliases(self, regs: dict[str, int]) -> dict[str, str]:
        aliases: dict[str, str] = {}
        lowered = {name.lower() for name in regs}
        for alias, index in _MIPS_ALIAS_TO_INDEX.items():
            if alias in lowered:
                continue
            reg_name = _find_register_for_index(index, lowered)
            if reg_name:
                aliases[alias] = reg_name
        return aliases


MIPS64EL_ARCH = Mips64ElArch(
    name="mips64el",
    ptr_size=8,
    gpr_names=_MIPS_GPRS,
    pc_reg="pc",
    sp_reg="sp",
    flags_reg=None,
    special_regs=("gp", "fp", "ra"),
    max_inst_bytes=4,
    return_reg="v0",
    nop_bytes=b"\x00\x00\x00\x00",
    break_bytes=b"\x0d\x00\x00\x00",
    call_mnemonics=_MIPS_CALLS,
)


def _match_mips64el(info: ArchInfo) -> int:
    score = 0
    triple = (info.triple or "").lower()
    arch_name = (info.arch_name or "").lower()
    regs = set(info.gpr_names)

    if _is_big_endian_mips64_token(triple):
        return 0
    if _is_big_endian_mips64_token(arch_name) and "mips64el" not in triple:
        return 0

    if "mips64el" in triple:
        score += 100
    if "mips64el" in arch_name:
        score += 70
    if "mips64" in triple or "mips64" in arch_name:
        score += 20
    if "mips" in triple or "mips" in arch_name:
        score += 10

    if info.ptr_size and info.ptr_size != 8:
        return 0
    if info.ptr_size == 8:
        score += 5

    if regs.intersection({"at", "v0", "v1", "a4", "a5", "a6", "a7", "k0", "k1"}):
        score += 35
    if regs.intersection({"r28", "r29", "r30", "r31"}):
        score += 20

    return score


register_profile(MIPS64EL_ARCH, _match_mips64el)


def _normalize_operand(op: str) -> str:
    return (op or "").strip().lstrip("$")


def _parse_target_operand(
    op: str,
    regs: dict[str, int],
    aliases: dict[str, str],
) -> int | None:
    cleaned = _normalize_operand(op)
    if not cleaned:
        return None
    parsed = parse_immediate(cleaned)
    if parsed is None:
        parsed = parse_leading_int(cleaned)
    if parsed is not None:
        return parsed
    return resolve_reg_operand(cleaned, regs, aliases)


def _resolve_operand_value(
    op: str,
    regs: dict[str, int],
    aliases: dict[str, str],
) -> int | None:
    return _parse_target_operand(op, regs, aliases)


def _find_register_for_index(index: int, reg_names: set[str]) -> str | None:
    reg_name = f"r{index}"
    if reg_name in reg_names:
        return reg_name
    alias = _MIPS_N64_REG_BY_INDEX.get(index)
    if alias and alias in reg_names:
        return alias
    if index == 30 and "s8" in reg_names:
        return "s8"
    if index == 12 and "t4" in reg_names:
        return "t4"
    if index == 13 and "t5" in reg_names:
        return "t5"
    if index == 14 and "t6" in reg_names:
        return "t6"
    if index == 15 and "t7" in reg_names:
        return "t7"
    return None


def _is_big_endian_mips64_token(token: str) -> bool:
    value = (token or "").strip().lower()
    return value.startswith("mips64") and not value.startswith("mips64el")


def _to_unsigned(value: int, bits: int) -> int:
    if bits <= 0:
        return value
    mask = (1 << bits) - 1
    return value & mask


def _to_signed(value: int, bits: int) -> int:
    if bits <= 0:
        return value
    masked = _to_unsigned(value, bits)
    sign_bit = 1 << (bits - 1)
    if masked & sign_bit:
        return masked - (1 << bits)
    return masked
