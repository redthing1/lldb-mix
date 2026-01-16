from __future__ import annotations

import re

from lldb_mix.arch.riscv import RISCV_ALIAS_TO_X, RISCV_X_TO_ALIAS

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
    "j",
    "jr",
    "jal",
    "jalr",
    "c.j",
    "c.jr",
    "c.jal",
    "c.jalr",
}

_X86_LOOP_MNEMONICS = {
    "loop",
    "loope",
    "loopne",
    "loopnz",
    "loopz",
    "jcxz",
    "jecxz",
    "jrcxz",
}

_BASE_OFFSET_RE = re.compile(
    r"^(?P<offset>[-+]?0x[0-9a-fA-F]+|[-+]?\d+)?\((?P<reg>[^)]+)\)$"
)


def is_branch_like(mnemonic: str) -> bool:
    mnem = mnemonic.lower()
    if mnem in {"b", "bl", "blr", "br", "ret", "cbz", "cbnz", "tbz", "tbnz"}:
        return True
    if mnem.startswith("b."):
        return True
    if mnem in _RISCV_BRANCHES or mnem in _RISCV_JUMPS:
        return True
    if mnem in _X86_LOOP_MNEMONICS:
        return True
    if mnem.startswith("j"):
        return True
    if mnem.startswith("call"):
        return True
    if mnem.startswith("ret"):
        return True
    if mnem == "jmp":
        return True
    return False


def resolve_flow_target(
    mnemonic: str, operands: str, regs: dict[str, int]
) -> int | None:
    if not is_branch_like(mnemonic):
        return None

    mnem = mnemonic.lower()
    if not operands and not mnem.startswith("ret"):
        return None

    if mnem.startswith("ret"):
        if "lr" in regs:
            return regs.get("lr")
        if "ra" in regs:
            return regs.get("ra")
        if "x1" in regs:
            return regs.get("x1")
        return None

    if mnem in {"cbz", "cbnz"}:
        parts = [p.strip() for p in operands.split(",")]
        if len(parts) < 2:
            return None
        op = parts[1]
        return _parse_target_operand(op, regs)

    if mnem in {"tbz", "tbnz"}:
        parts = [p.strip() for p in operands.split(",")]
        if len(parts) < 3:
            return None
        op = parts[2]
        return _parse_target_operand(op, regs)

    if mnem in _RISCV_BRANCHES:
        parts = [p.strip() for p in operands.split(",")]
        if mnem in {"beqz", "bnez", "c.beqz", "c.bnez"}:
            if len(parts) < 2:
                return None
            return _parse_target_operand(parts[1], regs)
        if len(parts) < 3:
            return None
        return _parse_target_operand(parts[2], regs)

    if mnem in {"j", "c.j"}:
        op = operands.split(",", 1)[0].strip()
        return _parse_target_operand(op, regs)

    if mnem in {"jal"}:
        parts = [p.strip() for p in operands.split(",")]
        if len(parts) == 1:
            return _parse_target_operand(parts[0], regs)
        return _parse_target_operand(parts[1], regs)

    if mnem in {"jalr", "jr", "c.jr", "c.jalr"}:
        parts = [p.strip() for p in operands.split(",")]
        if not parts:
            return None
        if mnem in {"jr", "c.jr"}:
            base_op = parts[0]
            base = _parse_base_offset(base_op, regs)
            if base is not None:
                return base
            return _resolve_reg_operand(base_op, regs)
        if len(parts) == 1:
            base = _resolve_reg_operand(parts[0], regs)
            return base
        base_op = parts[1]
        base = _parse_base_offset(base_op, regs)
        if base is None:
            base = _resolve_reg_operand(base_op, regs)
        if base is None:
            return None
        offset = 0
        if len(parts) >= 3:
            parsed = _parse_immediate(parts[2])
            if parsed is not None:
                offset = parsed
        return base + offset

    op = operands.split(",", 1)[0].strip()
    return _parse_target_operand(op, regs)


def _parse_target_operand(op: str, regs: dict[str, int]) -> int | None:
    if not op:
        return None
    if op.startswith("#"):
        op = op[1:]
    parsed = _parse_immediate(op)
    if parsed is None:
        parsed = _parse_leading_int(op)
    if parsed is not None:
        return parsed
    value = _resolve_reg_operand(op, regs)
    if value is not None:
        return value
    return None


def _parse_immediate(text: str) -> int | None:
    if not text:
        return None
    op = text.strip()
    if op.startswith("#"):
        op = op[1:]
    try:
        return int(op, 0)
    except ValueError:
        return None


def _parse_leading_int(text: str) -> int | None:
    if not text:
        return None
    match = re.match(r"^[-+]?0x[0-9a-fA-F]+|^[-+]?\d+", text.strip())
    if not match:
        return None
    try:
        return int(match.group(0), 0)
    except ValueError:
        return None


def _parse_base_offset(op: str, regs: dict[str, int]) -> int | None:
    match = _BASE_OFFSET_RE.match(op.strip())
    if not match:
        return None
    reg_name = match.group("reg").strip()
    base = _resolve_reg_operand(reg_name, regs)
    if base is None:
        return None
    offset_text = match.group("offset") or "0"
    offset = _parse_immediate(offset_text)
    if offset is None:
        return None
    return base + offset


def _resolve_reg_operand(op: str, regs: dict[str, int]) -> int | None:
    key = (op or "").lower()
    if key in regs:
        return regs.get(key)
    alias = RISCV_ALIAS_TO_X.get(key)
    if alias and alias in regs:
        return regs.get(alias)
    alias = RISCV_X_TO_ALIAS.get(key)
    if alias and alias in regs:
        return regs.get(alias)
    return None
