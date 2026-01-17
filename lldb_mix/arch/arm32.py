from __future__ import annotations

from lldb_mix.arch.abi import AAPCS32
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

_BRANCH_BASES = {"b", "bl", "bx", "blx"}
_CALL_BASES = {"bl", "blx"}
_CB_MNEMONICS = {"cbz", "cbnz"}


def _split_condition(mnemonic: str) -> tuple[str, str | None]:
    mnem = (mnemonic or "").lower()
    if "." in mnem:
        base, cond = mnem.split(".", 1)
        if cond in _CONDITIONS:
            return base, cond
    if len(mnem) > 2:
        suffix = mnem[-2:]
        if suffix in _CONDITIONS:
            return mnem[:-2], suffix
    return mnem, None


class Arm32Arch(ArchProfile):
    def format_flags(self, value: int) -> str:
        bits = [
            ("N", 31),
            ("Z", 30),
            ("C", 29),
            ("V", 28),
            ("Q", 27),
            ("A", 8),
            ("I", 7),
            ("F", 6),
            ("T", 5),
        ]
        out = []
        for idx, (flag, bit) in enumerate(bits):
            is_set = bool(value & (1 << bit))
            out.append(flag if is_set else flag.lower())
            if idx != len(bits) - 1:
                out.append(" ")
        return "".join(out)

    def is_conditional_branch(self, mnemonic: str) -> bool:
        mnem = (mnemonic or "").lower()
        if mnem in _CB_MNEMONICS:
            return True
        base, cond = _split_condition(mnem)
        if cond and base in _BRANCH_BASES:
            return True
        return False

    def is_unconditional_branch(self, mnemonic: str) -> bool:
        base, cond = _split_condition(mnemonic)
        return base in {"b", "bx"} and (cond is None or cond == "al")

    def is_call(self, mnemonic: str) -> bool:
        base, _ = _split_condition(mnemonic)
        return base in _CALL_BASES

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
        parts = [p.strip() for p in operands.split(",")] if operands else []

        if mnem in _CB_MNEMONICS:
            if len(parts) < 2:
                return None
            return parse_target_operand(parts[1], regs, aliases)

        base, _ = _split_condition(mnem)
        if base in _BRANCH_BASES:
            if not parts:
                return None
            return parse_target_operand(parts[0], regs, aliases)

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
        mnem = (mnemonic or "").lower()
        if mnem in _CB_MNEMONICS:
            parts = [p.strip() for p in operands.split(",")] if operands else []
            if len(parts) < 2:
                return None
            reg = parts[0]
            aliases = self.register_aliases(regs)
            value = resolve_reg_operand(reg, regs, aliases)
            if value is None:
                return None
            taken = (value == 0) if mnem == "cbz" else (value != 0)
            reason = f"{reg}={'0' if value == 0 else '!=0'}"
            return BranchDecision(taken, reason, "conditional")

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

        if include_calls and self.is_call(mnemonic):
            return BranchDecision(True, "", "call")
        if include_unconditional and self.is_unconditional_branch(mnemonic):
            return BranchDecision(True, "", "unconditional")
        return None

    def branch_taken(self, mnemonic: str, flags: int) -> tuple[bool, str]:
        _, cond = _split_condition(mnemonic)
        if not cond or cond not in _CONDITIONS:
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
        reg_aliases = {
            "r13": "sp",
            "r14": "lr",
            "r15": "pc",
            "sp": "r13",
            "lr": "r14",
            "pc": "r15",
            "r12": "ip",
            "ip": "r12",
            "r11": "fp",
            "fp": "r11",
            "r10": "sl",
            "sl": "r10",
            "r9": "sb",
            "sb": "r9",
        }
        for alias, reg in reg_aliases.items():
            if reg in lower and alias not in lower:
                aliases[alias] = reg
        return aliases


_ARM32_GPRS = tuple(f"r{i}" for i in range(13))

ARM32_ARCH = Arm32Arch(
    name="arm32",
    ptr_size=4,
    gpr_names=_ARM32_GPRS + ("sp", "lr", "pc", "r13", "r14", "r15", "cpsr", "psr"),
    pc_reg="pc",
    sp_reg="sp",
    flags_reg="cpsr",
    special_regs=("sp", "lr", "pc"),
    max_inst_bytes=4,
    return_reg="r0",
    nop_bytes=b"\x00\x00\xa0\xe1",
    break_bytes=b"\x70\x00\x20\xe1",
    abi=AAPCS32,
    call_mnemonics=("bl", "blx"),
)


def _match_arm32(info: ArchInfo) -> int:
    score = 0
    triple = (info.triple or "").lower()
    arch_name = (info.arch_name or "").lower()
    regs = set(info.gpr_names)
    if "arm64" in triple or "aarch64" in triple:
        return 0
    if "arm64" in arch_name or "aarch64" in arch_name:
        return 0
    if "armv" in triple or "thumb" in triple:
        score += 80
    if "armv" in arch_name or ("arm" in arch_name and "arm64" not in arch_name):
        score += 50
    if "thumb" in arch_name:
        score += 30
    if {"r0", "r1"}.issubset(regs):
        score += 30
    elif "r0" in regs or "r1" in regs:
        score += 15
    if regs.intersection({"sp", "r13"}) and regs.intersection({"pc", "r15"}):
        score += 25
    elif regs.intersection({"sp", "r13"}) or regs.intersection({"pc", "r15"}):
        score += 10
    if regs.intersection({"lr", "r14"}):
        score += 5
    if "cpsr" in regs or "psr" in regs:
        score += 5
    if info.ptr_size == 4:
        score += 5
    return score


register_profile(ARM32_ARCH, _match_arm32)
