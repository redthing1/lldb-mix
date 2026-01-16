from __future__ import annotations

from lldb_mix.arch.base import (
    ArchProfile,
    BranchDecision,
    ReadPointer,
    parse_target_operand,
)
from lldb_mix.arch.info import ArchInfo
from lldb_mix.arch.registry import register_profile

_FLAG_BITS = {
    "cf": 0,
    "pf": 2,
    "af": 4,
    "zf": 6,
    "sf": 7,
    "tf": 8,
    "if": 9,
    "df": 10,
    "of": 11,
}

_COND_MNEMONICS = {
    "jo",
    "jno",
    "js",
    "jns",
    "je",
    "jz",
    "jne",
    "jnz",
    "jb",
    "jc",
    "jnae",
    "jnb",
    "jnc",
    "jae",
    "jbe",
    "jna",
    "ja",
    "jnbe",
    "jp",
    "jpe",
    "jnp",
    "jpo",
    "jl",
    "jnge",
    "jge",
    "jnl",
    "jle",
    "jng",
    "jg",
    "jnle",
}

_LOOP_MNEMONICS = {
    "loop",
    "loope",
    "loopne",
    "loopnz",
    "loopz",
}

_JCXZ_MNEMONICS = {"jcxz", "jecxz", "jrcxz"}


class X64Arch(ArchProfile):
    def format_flags(self, value: int) -> str:
        bits = [
            ("O", _FLAG_BITS["of"]),
            ("D", _FLAG_BITS["df"]),
            ("I", _FLAG_BITS["if"]),
            ("T", _FLAG_BITS["tf"]),
            ("S", _FLAG_BITS["sf"]),
            ("Z", _FLAG_BITS["zf"]),
            ("A", _FLAG_BITS["af"]),
            ("P", _FLAG_BITS["pf"]),
            ("C", _FLAG_BITS["cf"]),
        ]
        out = []
        for idx, (flag, bit) in enumerate(bits):
            is_set = bool(value & (1 << bit))
            out.append(flag if is_set else flag.lower())
            if idx != len(bits) - 1:
                out.append(" ")
        return "".join(out)

    def is_conditional_branch(self, mnemonic: str) -> bool:
        return mnemonic.lower() in _COND_MNEMONICS

    def is_unconditional_branch(self, mnemonic: str) -> bool:
        return mnemonic.lower().startswith("jmp")

    def is_branch_like(self, mnemonic: str) -> bool:
        mnem = mnemonic.lower()
        if mnem.startswith("ret"):
            return True
        if mnem in _LOOP_MNEMONICS or mnem in _JCXZ_MNEMONICS:
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
        if not self.is_branch_like(mnemonic):
            return None
        mnem = mnemonic.lower()
        if mnem.startswith("ret"):
            if not read_pointer or not ptr_size:
                return None
            sp = regs.get(self.sp_reg)
            if sp is None:
                return None
            return read_pointer(sp, ptr_size)
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
        if mnem in _JCXZ_MNEMONICS:
            value = regs.get("rcx")
            if value is None:
                return None
            bits = 64
            reg_label = "rcx"
            if mnem == "jcxz":
                bits = 16
                reg_label = "cx"
            elif mnem == "jecxz":
                bits = 32
                reg_label = "ecx"
            masked = _to_unsigned(value, bits)
            taken = masked == 0
            return BranchDecision(taken, f"{reg_label}=0", "conditional")

        if mnem in _LOOP_MNEMONICS:
            value = regs.get("rcx")
            if value is None:
                return None
            next_val = _to_unsigned(value - 1, 64)
            taken = next_val != 0
            reason = "rcx-1!=0"
            zf = bool(flags & (1 << _FLAG_BITS["zf"]))
            if mnem in {"loope", "loopz"}:
                taken = taken and zf
                reason = "rcx-1!=0 and zf=1"
            if mnem in {"loopne", "loopnz"}:
                taken = taken and (not zf)
                reason = "rcx-1!=0 and zf=0"
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
        cf = bool(flags & (1 << _FLAG_BITS["cf"]))
        pf = bool(flags & (1 << _FLAG_BITS["pf"]))
        zf = bool(flags & (1 << _FLAG_BITS["zf"]))
        sf = bool(flags & (1 << _FLAG_BITS["sf"]))
        of = bool(flags & (1 << _FLAG_BITS["of"]))

        if mnem in ("jo",):
            return of, "of=1"
        if mnem in ("jno",):
            return (not of), "of=0"
        if mnem in ("js",):
            return sf, "sf=1"
        if mnem in ("jns",):
            return (not sf), "sf=0"
        if mnem in ("je", "jz"):
            return zf, "zf=1"
        if mnem in ("jne", "jnz"):
            return (not zf), "zf=0"
        if mnem in ("jb", "jc", "jnae"):
            return cf, "cf=1"
        if mnem in ("jnb", "jnc", "jae"):
            return (not cf), "cf=0"
        if mnem in ("jbe", "jna"):
            return (cf or zf), "cf=1 or zf=1"
        if mnem in ("ja", "jnbe"):
            return (not cf and not zf), "cf=0 and zf=0"
        if mnem in ("jp", "jpe"):
            return pf, "pf=1"
        if mnem in ("jnp", "jpo"):
            return (not pf), "pf=0"
        if mnem in ("jl", "jnge"):
            return (sf != of), "sf!=of"
        if mnem in ("jge", "jnl"):
            return (sf == of), "sf=of"
        if mnem in ("jle", "jng"):
            return (zf or sf != of), "zf=1 or sf!=of"
        if mnem in ("jg", "jnle"):
            return (not zf and sf == of), "zf=0 and sf=of"

        return False, ""

    def register_aliases(self, regs: dict[str, int]) -> dict[str, str]:
        aliases: dict[str, str] = {}
        lower = {name.lower() for name in regs}
        if "rax" in lower:
            pairs = {
                "eax": "rax",
                "ebx": "rbx",
                "ecx": "rcx",
                "edx": "rdx",
                "esi": "rsi",
                "edi": "rdi",
                "ebp": "rbp",
                "esp": "rsp",
                "eip": "rip",
            }
            aliases.update({alias: reg for alias, reg in pairs.items() if reg in lower})
            for idx in range(8, 16):
                reg = f"r{idx}"
                if reg in lower:
                    aliases[f"r{idx}d"] = reg
        return aliases


def _to_unsigned(value: int, bits: int) -> int:
    if bits <= 0:
        return value
    mask = (1 << bits) - 1
    return value & mask


X64_ARCH = X64Arch(
    name="x86_64",
    ptr_size=8,
    gpr_names=(
        "rax",
        "rbx",
        "rcx",
        "rdx",
        "rsi",
        "rdi",
        "rbp",
        "rsp",
        "r8",
        "r9",
        "r10",
        "r11",
        "r12",
        "r13",
        "r14",
        "r15",
        "rip",
        "rflags",
    ),
    pc_reg="rip",
    sp_reg="rsp",
    flags_reg="rflags",
    special_regs=("cs", "ss", "ds", "es", "fs", "gs"),
    max_inst_bytes=15,
    return_reg="rax",
    nop_bytes=b"\x90",
    break_bytes=b"\xcc",
    call_mnemonics=("call", "callq"),
)


def _match_x64(info: ArchInfo) -> int:
    score = 0
    triple = (info.triple or "").lower()
    arch_name = (info.arch_name or "").lower()
    if "x86_64" in triple or "amd64" in triple:
        score += 100
    if "x86_64" in arch_name or "amd64" in arch_name or arch_name == "x64":
        score += 50
    regs = set(info.gpr_names)
    if {"rax", "rip", "rsp"}.issubset(regs):
        score += 40
    elif "rax" in regs or "rip" in regs:
        score += 20
    if info.ptr_size == 8:
        score += 5
    return score


register_profile(X64_ARCH, _match_x64)
