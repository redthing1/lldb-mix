from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lldb_mix.arch.base import ArchSpec


@dataclass(frozen=True)
class Instruction:
    address: int
    bytes: bytes
    mnemonic: str
    operands: str


def read_instructions(target: Any, addr: int, count: int, flavor: str = "intel") -> list[Instruction]:
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
        output.append(
            Instruction(
                address=inst_addr,
                bytes=bytes(bytes_list),
                mnemonic=inst.GetMnemonic(target),
                operands=inst.GetOperands(target),
            )
        )
    return output


def read_instructions_around(
    target: Any,
    pc: int,
    before: int,
    after: int,
    arch: ArchSpec,
    flavor: str = "intel",
) -> list[Instruction]:
    total = before + after + 1
    if pc == 0 or total <= 0:
        return []

    if before <= 0:
        return read_instructions(target, pc, total, flavor)

    max_inst = max(arch.max_inst_bytes, 1)
    start = pc - (before * max_inst)
    if start < 0:
        start = 0

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
