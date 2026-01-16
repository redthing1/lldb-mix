from __future__ import annotations

from lldb_mix.arch.base import ArchSpec

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


class X64Arch(ArchSpec):
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
