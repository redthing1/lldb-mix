from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable, Optional

from lldb_mix.arch.abi import AbiSpec

ReadPointer = Callable[[int, int], Optional[int]]


@dataclass(frozen=True)
class BranchDecision:
    taken: bool
    reason: str
    kind: str


_REG_BOUNDARY = r"(?<![A-Za-z0-9_])(?:{name})(?![A-Za-z0-9_])"


@dataclass(frozen=True)
class ArchProfile:
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

    def disasm_flavor(self) -> str:
        name = (self.name or "").lower()
        if name.startswith("x86") or name in {"x64", "amd64", "i386"}:
            return "intel"
        return ""

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

    def is_return(self, mnemonic: str) -> bool:
        return (mnemonic or "").lower().startswith("ret")

    def is_branch_like(self, mnemonic: str) -> bool:
        return (
            self.is_return(mnemonic)
            or self.is_conditional_branch(mnemonic)
            or self.is_unconditional_branch(mnemonic)
            or self.is_call(mnemonic)
        )

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
        if include_unconditional and self.is_return(mnemonic):
            return BranchDecision(True, "", "return")
        if include_unconditional and self.is_unconditional_branch(mnemonic):
            return BranchDecision(True, "", "unconditional")
        return None

    def register_aliases(self, regs: dict[str, int]) -> dict[str, str]:
        _ = regs
        return {}

    def mem_operand_targets(self, operands: str, regs: dict[str, int]) -> list[int]:
        if not operands or not regs:
            return []
        aliases = self.register_aliases(regs)
        reg_map = {name.lower(): name for name in regs}
        reg_map.update(aliases)
        reg_names = sorted(reg_map.keys(), key=len, reverse=True)
        if not reg_names:
            return []
        pattern = re.compile(
            _REG_BOUNDARY.format(name="|".join(re.escape(name) for name in reg_names)),
            re.IGNORECASE,
        )
        targets: list[int] = []
        for expr in re.findall(r"\[([^\]]+)\]", operands):
            cleaned = expr.replace("#", "").replace("!", "")
            regs_in = _regs_in_text(cleaned, pattern, reg_map)
            if len(regs_in) != 1:
                continue
            base = regs.get(regs_in[0])
            if base is None:
                continue
            offset = _parse_offset(cleaned)
            targets.append(base + offset)
        return targets


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

def _regs_in_text(
    text: str,
    pattern: re.Pattern[str],
    reg_map: dict[str, str],
) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for match in pattern.finditer(text):
        key = match.group(0).lower()
        canon = reg_map.get(key)
        if not canon or canon in seen:
            continue
        seen.add(canon)
        out.append(canon)
    return out


def _parse_offset(expr: str) -> int:
    match = re.search(r"([+-])\\s*(0x[0-9a-fA-F]+|\\d+)", expr)
    if not match:
        return 0
    sign = -1 if match.group(1) == "-" else 1
    try:
        value = int(match.group(2), 0)
    except ValueError:
        return 0
    return sign * value

