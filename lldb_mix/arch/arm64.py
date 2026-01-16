from __future__ import annotations

from lldb_mix.arch.base import (
    ArchProfile,
    BranchDecision,
    ReadPointer,
    parse_target_operand,
    resolve_reg_operand,
)
from lldb_mix.arch.info import ArchInfo
from lldb_mix.arch.registry import register_profile

_CONDITIONS = {
    "eq": (lambda n, z, c, v: z == 1, "z=1"),
    "ne": (lambda n, z, c, v: z == 0, "z=0"),
    "cs": (lambda n, z, c, v: c == 1, "c=1"),
    "hs": (lambda n, z, c, v: c == 1, "c=1"),
    "cc": (lambda n, z, c, v: c == 0, "c=0"),
    "lo": (lambda n, z, c, v: c == 0, "c=0"),
    "mi": (lambda n, z, c, v: n == 1, "n=1"),
    "pl": (lambda n, z, c, v: n == 0, "n=0"),
    "vs": (lambda n, z, c, v: v == 1, "v=1"),
    "vc": (lambda n, z, c, v: v == 0, "v=0"),
    "hi": (lambda n, z, c, v: c == 1 and z == 0, "c=1 and z=0"),
    "ls": (lambda n, z, c, v: c == 0 or z == 1, "c=0 or z=1"),
    "ge": (lambda n, z, c, v: n == v, "n=v"),
    "lt": (lambda n, z, c, v: n != v, "n!=v"),
    "gt": (lambda n, z, c, v: z == 0 and n == v, "z=0 and n=v"),
    "le": (lambda n, z, c, v: z == 1 or n != v, "z=1 or n!=v"),
    "al": (lambda n, z, c, v: True, ""),
}


class Arm64Arch(ArchProfile):
    def format_flags(self, value: int) -> str:
        bits = [
            ("N", 31),
            ("Z", 30),
            ("C", 29),
            ("V", 28),
            ("A", 8),
            ("I", 7),
            ("F", 6),
        ]
        out = []
        for idx, (flag, bit) in enumerate(bits):
            is_set = bool(value & (1 << bit))
            out.append(flag if is_set else flag.lower())
            if idx != len(bits) - 1:
                out.append(" ")
        return "".join(out)

    def is_conditional_branch(self, mnemonic: str) -> bool:
        return mnemonic.lower().startswith("b.")

    def is_unconditional_branch(self, mnemonic: str) -> bool:
        mnem = mnemonic.lower()
        return mnem in {"b", "br"}

    def is_branch_like(self, mnemonic: str) -> bool:
        mnem = mnemonic.lower()
        if mnem in {"b", "bl", "blr", "br", "ret", "cbz", "cbnz", "tbz", "tbnz"}:
            return True
        return self.is_conditional_branch(mnemonic)

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
        if mnem.startswith("ret"):
            parts = [p.strip() for p in operands.split(",")] if operands else []
            if parts:
                return parse_target_operand(parts[0], regs, aliases)
            return resolve_reg_operand("lr", regs, aliases)

        parts = [p.strip() for p in operands.split(",")] if operands else []
        if mnem in {"cbz", "cbnz"}:
            if len(parts) < 2:
                return None
            return parse_target_operand(parts[1], regs, aliases)
        if mnem in {"tbz", "tbnz"}:
            if len(parts) < 3:
                return None
            return parse_target_operand(parts[2], regs, aliases)

        if not parts:
            return None
        return parse_target_operand(parts[0], regs, aliases)

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
        if mnem in {"cbz", "cbnz"}:
            reg = operands.split(",", 1)[0].strip() if operands else ""
            value = resolve_reg_operand(reg, regs, aliases)
            if value is None:
                return None
            taken = (value == 0) if mnem == "cbz" else (value != 0)
            reason = f"{reg}={'0' if value == 0 else '!=0'}"
            return BranchDecision(taken, reason, "conditional")

        if mnem in {"tbz", "tbnz"}:
            parts = [p.strip() for p in operands.split(",")] if operands else []
            if len(parts) < 2:
                return None
            reg = parts[0]
            value = resolve_reg_operand(reg, regs, aliases)
            if value is None:
                return None
            bit_text = parts[1].lstrip("#")
            try:
                bit = int(bit_text, 0)
            except ValueError:
                return None
            bit_set = (value >> bit) & 1
            taken = (bit_set == 0) if mnem == "tbz" else (bit_set == 1)
            reason = f"{reg}[{bit}]={bit_set}"
            return BranchDecision(taken, reason, "conditional")

        if include_calls and self.is_call(mnemonic):
            return BranchDecision(True, "", "call")
        if include_unconditional and self.is_return(mnemonic):
            return BranchDecision(True, "", "return")
        if include_unconditional and self.is_unconditional_branch(mnemonic):
            return BranchDecision(True, "", "unconditional")
        return None

    def branch_taken(self, mnemonic: str, flags: int) -> tuple[bool, str]:
        mnem = mnemonic.lower()
        if not mnem.startswith("b."):
            return False, ""

        cond = mnem.split(".", 1)[1]
        if cond not in _CONDITIONS:
            return False, ""

        n = 1 if (flags & (1 << 31)) else 0
        z = 1 if (flags & (1 << 30)) else 0
        c = 1 if (flags & (1 << 29)) else 0
        v = 1 if (flags & (1 << 28)) else 0
        func, reason = _CONDITIONS[cond]
        return func(n, z, c, v), reason

    def register_aliases(self, regs: dict[str, int]) -> dict[str, str]:
        aliases: dict[str, str] = {}
        lower = {name.lower() for name in regs}
        if any(name.startswith("x") and name[1:].isdigit() for name in lower):
            for name in lower:
                if name.startswith("x") and name[1:].isdigit():
                    aliases[f"w{name[1:]}"] = name
            if "fp" in lower:
                aliases["x29"] = "fp"
                aliases["w29"] = "fp"
            if "lr" in lower:
                aliases["x30"] = "lr"
                aliases["w30"] = "lr"
        return aliases


_ARM64_GPRS = tuple(f"x{i}" for i in range(29))

ARM64_ARCH = Arm64Arch(
    name="arm64",
    ptr_size=8,
    gpr_names=_ARM64_GPRS + ("fp", "lr", "sp", "pc", "cpsr"),
    pc_reg="pc",
    sp_reg="sp",
    flags_reg="cpsr",
    special_regs=("fp", "lr"),
    max_inst_bytes=4,
    return_reg="x0",
    nop_bytes=b"\x1f\x20\x03\xd5",
    break_bytes=b"\x00\x00\x20\xd4",
    call_mnemonics=("bl", "blr"),
)


def _match_arm64(info: ArchInfo) -> int:
    score = 0
    triple = (info.triple or "").lower()
    arch_name = (info.arch_name or "").lower()
    if "arm64" in triple or "aarch64" in triple:
        score += 100
    if "arm64" in arch_name or "aarch64" in arch_name:
        score += 50
    regs = set(info.gpr_names)
    if {"x0", "x1", "sp", "pc"}.issubset(regs):
        score += 40
    elif "x0" in regs or "sp" in regs:
        score += 20
    if info.ptr_size == 8:
        score += 5
    return score


register_profile(ARM64_ARCH, _match_arm64)
