from __future__ import annotations

from dataclasses import dataclass
import time

from lldb_mix.arch.base import ArchSpec, UNKNOWN_ARCH
from lldb_mix.core.memory import MemoryRegion, read_memory_regions
from lldb_mix.core.session import Session


@dataclass(frozen=True)
class ContextSnapshot:
    arch: ArchSpec
    pc: int
    sp: int
    regs: dict[str, int]
    maps: list[MemoryRegion]
    timestamp: float


def capture_snapshot(session: Session) -> ContextSnapshot | None:
    if not session:
        return None

    arch = session.arch() or UNKNOWN_ARCH
    regs = session.read_registers()
    pc = regs.get(arch.pc_reg, 0) if arch.pc_reg else 0
    sp = regs.get(arch.sp_reg, 0) if arch.sp_reg else 0
    process = session.process()
    maps = read_memory_regions(process) if process else []

    return ContextSnapshot(
        arch=arch,
        pc=pc,
        sp=sp,
        regs=regs,
        maps=maps,
        timestamp=time.time(),
    )
