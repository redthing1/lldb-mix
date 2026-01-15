from __future__ import annotations

from lldb_mix.arch.base import ArchSpec

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


class Arm64Arch(ArchSpec):
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
)
