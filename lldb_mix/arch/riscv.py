from __future__ import annotations

import re

from lldb_mix.arch.abi import RISCV_ABI, RISCV_X_ABI
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

RISCV_ALIAS_TO_X = {
    "zero": "x0",
    "ra": "x1",
    "sp": "x2",
    "gp": "x3",
    "tp": "x4",
    "t0": "x5",
    "t1": "x6",
    "t2": "x7",
    "s0": "x8",
    "fp": "x8",
    "s1": "x9",
    "a0": "x10",
    "a1": "x11",
    "a2": "x12",
    "a3": "x13",
    "a4": "x14",
    "a5": "x15",
    "a6": "x16",
    "a7": "x17",
    "s2": "x18",
    "s3": "x19",
    "s4": "x20",
    "s5": "x21",
    "s6": "x22",
    "s7": "x23",
    "s8": "x24",
    "s9": "x25",
    "s10": "x26",
    "s11": "x27",
    "t3": "x28",
    "t4": "x29",
    "t5": "x30",
    "t6": "x31",
}

RISCV_X_TO_ALIAS = {
    "x0": "zero",
    "x1": "ra",
    "x2": "sp",
    "x3": "gp",
    "x4": "tp",
    "x5": "t0",
    "x6": "t1",
    "x7": "t2",
    "x8": "s0",
    "x9": "s1",
    "x10": "a0",
    "x11": "a1",
    "x12": "a2",
    "x13": "a3",
    "x14": "a4",
    "x15": "a5",
    "x16": "a6",
    "x17": "a7",
    "x18": "s2",
    "x19": "s3",
    "x20": "s4",
    "x21": "s5",
    "x22": "s6",
    "x23": "s7",
    "x24": "s8",
    "x25": "s9",
    "x26": "s10",
    "x27": "s11",
    "x28": "t3",
    "x29": "t4",
    "x30": "t5",
    "x31": "t6",
}

_RISCV_X_GPRS = tuple(f"x{i}" for i in range(32))
_RISCV_ABI_GPRS = (
    "zero",
    "ra",
    "sp",
    "gp",
    "tp",
    "t0",
    "t1",
    "t2",
    "s0",
    "fp",
    "s1",
    "a0",
    "a1",
    "a2",
    "a3",
    "a4",
    "a5",
    "a6",
    "a7",
    "s2",
    "s3",
    "s4",
    "s5",
    "s6",
    "s7",
    "s8",
    "s9",
    "s10",
    "s11",
    "t3",
    "t4",
    "t5",
    "t6",
)

_CALL_MNEMONICS = (
    "jal",
    "jalr",
    "call",
    "c.jal",
    "c.jalr",
)

_RISCV_BRANCHES = {
    "beq",
    "bne",
    "blt",
    "bge",
    "bltu",
    "bgeu",
    "beqz",
    "bnez",
    "c.beqz",
    "c.bnez",
}

_RISCV_JUMPS = {
    "b",
    "j",
    "jr",
    "jal",
    "jalr",
    "c.j",
    "c.jr",
    "c.jal",
    "c.jalr",
    "ret",
}

_BASE_OFFSET_RE = re.compile(
    r"^(?P<offset>[-+]?0x[0-9a-fA-F]+|[-+]?\d+)?\((?P<reg>[^)]+)\)$"
)


class RiscvArch(ArchProfile):
    def is_unconditional_branch(self, mnemonic: str) -> bool:
        mnem = mnemonic.lower()
        return mnem in {"b", "j", "jr", "c.j", "c.jr"}

    def is_branch_like(self, mnemonic: str) -> bool:
        mnem = mnemonic.lower()
        if mnem in _RISCV_BRANCHES or mnem in _RISCV_JUMPS:
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

        mnem = mnemonic.lower()
        aliases = self.register_aliases(regs)

        if mnem == "ret":
            return resolve_reg_operand("ra", regs, aliases)

        parts = [p.strip() for p in operands.split(",")] if operands else []
        if mnem in _RISCV_BRANCHES:
            if mnem in {"beqz", "bnez", "c.beqz", "c.bnez"}:
                if len(parts) < 2:
                    return None
                return _parse_target_operand(parts[1], regs, aliases)
            if len(parts) < 3:
                return None
            return _parse_target_operand(parts[2], regs, aliases)

        if mnem in {"b", "j", "c.j"}:
            if not parts:
                return None
            return _parse_target_operand(parts[0], regs, aliases)

        if mnem == "jal":
            if len(parts) == 1:
                return _parse_target_operand(parts[0], regs, aliases)
            return _parse_target_operand(parts[1], regs, aliases)

        if mnem in {"jalr", "jr", "c.jr", "c.jalr"}:
            if not parts:
                return None
            if mnem in {"jr", "c.jr"}:
                base = _parse_base_offset(parts[0], regs, aliases)
                if base is not None:
                    return base
                return resolve_reg_operand(parts[0], regs, aliases)
            if len(parts) == 1:
                return resolve_reg_operand(parts[0], regs, aliases)
            base = _parse_base_offset(parts[1], regs, aliases)
            if base is None:
                base = resolve_reg_operand(parts[1], regs, aliases)
            if base is None:
                return None
            offset = 0
            if len(parts) >= 3:
                parsed = parse_immediate(parts[2])
                if parsed is not None:
                    offset = parsed
            return base + offset

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

        mnem = mnemonic.lower()
        aliases = self.register_aliases(regs)
        if mnem in _RISCV_BRANCHES:
            if mnem in {"beqz", "bnez", "c.beqz", "c.bnez"}:
                parts = [p.strip() for p in operands.split(",")] if operands else []
                if not parts:
                    return None
                reg = parts[0]
                value = resolve_reg_operand(reg, regs, aliases)
                if value is None:
                    return None
                taken = value == 0 if mnem in {"beqz", "c.beqz"} else value != 0
                reason = f"{reg}={'0' if value == 0 else '!=0'}"
                return BranchDecision(taken, reason, "conditional")

            parts = [p.strip() for p in operands.split(",")] if operands else []
            if len(parts) < 2:
                return None
            lhs = resolve_reg_operand(parts[0], regs, aliases)
            rhs = resolve_reg_operand(parts[1], regs, aliases)
            if lhs is None or rhs is None:
                return None
            bits = max(getattr(self, "ptr_size", 0), 1) * 8
            if mnem == "beq":
                return BranchDecision(lhs == rhs, f"{parts[0]}=={parts[1]}", "conditional")
            if mnem == "bne":
                return BranchDecision(lhs != rhs, f"{parts[0]}!={parts[1]}", "conditional")
            if mnem in {"blt", "bge"}:
                lhs_signed = _to_signed(lhs, bits)
                rhs_signed = _to_signed(rhs, bits)
                taken = lhs_signed < rhs_signed if mnem == "blt" else lhs_signed >= rhs_signed
                op = "<" if mnem == "blt" else ">="
                return BranchDecision(taken, f"{parts[0]}{op}{parts[1]}", "conditional")
            if mnem in {"bltu", "bgeu"}:
                lhs_u = _to_unsigned(lhs, bits)
                rhs_u = _to_unsigned(rhs, bits)
                taken = lhs_u < rhs_u if mnem == "bltu" else lhs_u >= rhs_u
                op = "<" if mnem == "bltu" else ">="
                return BranchDecision(taken, f"{parts[0]}{op}{parts[1]}", "conditional")

        if include_unconditional and mnem in {"jal", "jalr", "c.jal", "c.jalr"}:
            rd = _riscv_rd(operands)
            if rd and _reg_is_zero(rd):
                return BranchDecision(True, "", "unconditional")

        if include_calls and self.is_call(mnemonic):
            return BranchDecision(True, "", "call")
        if include_unconditional and self.is_return(mnemonic):
            return BranchDecision(True, "", "return")
        if include_unconditional and self.is_unconditional_branch(mnemonic):
            return BranchDecision(True, "", "unconditional")
        return None

    def register_aliases(self, regs: dict[str, int]) -> dict[str, str]:
        aliases: dict[str, str] = {}
        lower = {name.lower() for name in regs}
        for alias, reg in RISCV_ALIAS_TO_X.items():
            if reg in lower:
                aliases[alias] = reg
        for reg, alias in RISCV_X_TO_ALIAS.items():
            if alias in lower:
                aliases[reg] = alias
        return aliases

    def mem_operand_targets(self, operands: str, regs: dict[str, int]) -> list[int]:
        if not operands or not regs:
            return []
        aliases = self.register_aliases(regs)
        targets: list[int] = []
        parts = [part.strip() for part in operands.split(",") if part.strip()]
        for part in parts:
            base = _parse_base_offset(part, regs, aliases)
            if base is not None:
                targets.append(base)
        if targets:
            return targets
        return super().mem_operand_targets(operands, regs)


RISCV32_X_ARCH = RiscvArch(
    name="riscv32",
    ptr_size=4,
    gpr_names=_RISCV_X_GPRS + ("pc",),
    pc_reg="pc",
    sp_reg="x2",
    flags_reg=None,
    special_regs=(),
    max_inst_bytes=4,
    return_reg="x10",
    nop_bytes=b"\x13\x00\x00\x00",
    break_bytes=b"\x73\x00\x10\x00",
    abi=RISCV_X_ABI,
    call_mnemonics=_CALL_MNEMONICS,
)

RISCV64_X_ARCH = RiscvArch(
    name="riscv64",
    ptr_size=8,
    gpr_names=_RISCV_X_GPRS + ("pc",),
    pc_reg="pc",
    sp_reg="x2",
    flags_reg=None,
    special_regs=(),
    max_inst_bytes=4,
    return_reg="x10",
    nop_bytes=b"\x13\x00\x00\x00",
    break_bytes=b"\x73\x00\x10\x00",
    abi=RISCV_X_ABI,
    call_mnemonics=_CALL_MNEMONICS,
)

RISCV32_ABI_ARCH = RiscvArch(
    name="riscv32",
    ptr_size=4,
    gpr_names=_RISCV_ABI_GPRS + ("pc",),
    pc_reg="pc",
    sp_reg="sp",
    flags_reg=None,
    special_regs=(),
    max_inst_bytes=4,
    return_reg="a0",
    nop_bytes=b"\x13\x00\x00\x00",
    break_bytes=b"\x73\x00\x10\x00",
    abi=RISCV_ABI,
    call_mnemonics=_CALL_MNEMONICS,
)

RISCV64_ABI_ARCH = RiscvArch(
    name="riscv64",
    ptr_size=8,
    gpr_names=_RISCV_ABI_GPRS + ("pc",),
    pc_reg="pc",
    sp_reg="sp",
    flags_reg=None,
    special_regs=(),
    max_inst_bytes=4,
    return_reg="a0",
    nop_bytes=b"\x13\x00\x00\x00",
    break_bytes=b"\x73\x00\x10\x00",
    abi=RISCV_ABI,
    call_mnemonics=_CALL_MNEMONICS,
)


def _match_riscv(info: ArchInfo, bits: int, prefer_abi: bool) -> int:
    score = 0
    triple = (info.triple or "").lower()
    arch_name = (info.arch_name or "").lower()
    regs = set(info.gpr_names)

    if "riscv" in triple or "riscv" in arch_name or "rv" in triple:
        score += 40
    if bits == 64 and ("riscv64" in triple or "rv64" in triple):
        score += 60
    if bits == 32 and ("riscv32" in triple or "rv32" in triple):
        score += 60
    if info.ptr_size == 8 and bits == 64:
        score += 5
    if info.ptr_size == 4 and bits == 32:
        score += 5

    if prefer_abi:
        if regs.intersection({"a0", "a1", "ra", "gp", "tp", "zero"}):
            score += 30
        elif "sp" in regs:
            score += 5
        elif regs.intersection({"x10", "x1", "x2"}):
            score -= 5
    else:
        if regs.intersection({"x0", "x1", "x10"}):
            score += 30
        elif "x2" in regs:
            score += 5
        elif regs.intersection({"a0", "ra"}):
            score -= 5

    return score


register_profile(RISCV32_ABI_ARCH, lambda info: _match_riscv(info, 32, True))
register_profile(RISCV32_X_ARCH, lambda info: _match_riscv(info, 32, False))
register_profile(RISCV64_ABI_ARCH, lambda info: _match_riscv(info, 64, True))
register_profile(RISCV64_X_ARCH, lambda info: _match_riscv(info, 64, False))


def _parse_target_operand(
    op: str, regs: dict[str, int], aliases: dict[str, str]
) -> int | None:
    if not op:
        return None
    parsed = parse_immediate(op)
    if parsed is None:
        parsed = parse_leading_int(op)
    if parsed is not None:
        return parsed
    return resolve_reg_operand(op, regs, aliases)


def _parse_base_offset(
    op: str, regs: dict[str, int], aliases: dict[str, str]
) -> int | None:
    match = _BASE_OFFSET_RE.match(op.strip())
    if not match:
        return None
    reg_name = match.group("reg").strip()
    base = resolve_reg_operand(reg_name, regs, aliases)
    if base is None:
        return None
    offset_text = match.group("offset") or "0"
    offset = parse_immediate(offset_text)
    if offset is None:
        return None
    return base + offset


def _riscv_rd(operands: str) -> str | None:
    parts = [p.strip() for p in operands.split(",") if p.strip()]
    if not parts:
        return None
    return parts[0]


def _reg_is_zero(name: str) -> bool:
    key = name.strip().lower()
    return key in {"x0", "zero"}


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
