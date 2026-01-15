from __future__ import annotations


def is_branch_like(mnemonic: str) -> bool:
    mnem = mnemonic.lower()
    if mnem in {"b", "bl", "blr", "br", "ret", "cbz", "cbnz", "tbz", "tbnz"}:
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

    op = operands.split(",", 1)[0].strip()
    return _parse_target_operand(op, regs)


def _parse_target_operand(op: str, regs: dict[str, int]) -> int | None:
    if op.startswith("#"):
        op = op[1:]
    if op.startswith("0x"):
        try:
            return int(op, 16)
        except ValueError:
            return None
    if op in regs:
        return regs.get(op)
    return None
