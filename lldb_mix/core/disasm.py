from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lldb_mix.arch.view import ArchView
from lldb_mix.core.memory import MemoryRegion


@dataclass(frozen=True)
class Instruction:
    address: int
    bytes: bytes
    mnemonic: str
    operands: str
    byte_size: int = 0

    def __post_init__(self) -> None:
        if self.byte_size <= 0 and self.bytes:
            object.__setattr__(self, "byte_size", len(self.bytes))

    @property
    def opcode_bytes(self) -> bytes:
        if self.byte_size > 0 and len(self.bytes) > self.byte_size:
            return self.bytes[: self.byte_size]
        return self.bytes


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except Exception:
        return 0


def _instruction_byte_size(inst: Any, data: Any) -> int:
    size = _safe_int(inst.GetByteSize())
    if size > 0:
        return size
    if data is not None and data.IsValid():
        size = _safe_int(data.GetByteSize())
        if size > 0:
            return size
    return 0


def disasm_flavor(arch) -> str:
    if arch is None:
        return ""
    if hasattr(arch, "disasm_flavor"):
        try:
            return arch.disasm_flavor()
        except Exception:
            return ""
    name = (arch or "").lower()
    if name.startswith("x86") or name in {"x64", "amd64", "i386"}:
        return "intel"
    return ""


def read_instructions(
    target: Any, addr: int, count: int, flavor: str = "intel"
) -> list[Instruction]:
    try:
        import lldb
    except Exception:
        return []

    if not target or not target.IsValid() or count <= 0:
        return []

    sb_addr = lldb.SBAddress()
    sb_addr.SetLoadAddress(addr, target)
    insts = target.ReadInstructions(sb_addr, count, flavor)
    output: list[Instruction] = []
    for inst in insts:
        inst_addr = inst.GetAddress().GetLoadAddress(target)
        data = inst.GetData(target)
        bytes_list = list(data.uint8) if data.IsValid() else []
        byte_size = _instruction_byte_size(inst, data)
        if byte_size > 0 and len(bytes_list) > byte_size:
            bytes_list = bytes_list[:byte_size]
        output.append(
            Instruction(
                address=inst_addr,
                bytes=bytes(bytes_list),
                mnemonic=inst.GetMnemonic(target),
                operands=inst.GetOperands(target),
                byte_size=byte_size,
            )
        )
    return output


def read_instructions_around(
    target: Any,
    pc: int | None,
    before: int,
    after: int,
    arch: ArchView,
    regions: list[MemoryRegion] | None = None,
    flavor: str = "intel",
) -> list[Instruction]:
    total = before + after + 1
    if pc is None or total <= 0:
        return []

    if before <= 0:
        return read_instructions(target, pc, total, flavor)

    max_inst = max(arch.max_inst_bytes, 1)
    start = pc - (before * max_inst)
    if start < 0:
        start = 0
    if regions:
        region = next((region for region in regions if region.contains(pc)), None)
        if region and start < region.start:
            start = region.start
            if start > pc:
                return read_instructions(target, pc, total, flavor)

    fetch_count = total + before * 3
    insts = read_instructions(target, start, fetch_count, flavor)
    if not insts:
        return []

    idx = next((i for i, inst in enumerate(insts) if inst.address == pc), None)
    if idx is None:
        return read_instructions(target, pc, total, flavor)

    start_idx = max(0, idx - before)
    end_idx = min(len(insts), idx + after + 1)
    return insts[start_idx:end_idx]
