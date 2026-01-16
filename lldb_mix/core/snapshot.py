from __future__ import annotations

from dataclasses import dataclass
import time

from lldb_mix.arch.view import ArchView
from lldb_mix.core.memory import MemoryRegion, read_memory_regions
from lldb_mix.core.session import Session


@dataclass(frozen=True)
class ContextSnapshot:
    arch: ArchView
    pc: int | None
    sp: int | None
    regs: dict[str, int]
    maps: list[MemoryRegion]
    timestamp: float

    def has_pc(self) -> bool:
        return self.pc is not None

    def has_sp(self) -> bool:
        return self.sp is not None


def capture_snapshot(session: Session) -> ContextSnapshot | None:
    if not session:
        return None

    arch = session.arch()
    regs = session.read_registers()
    pc = arch.pc_value
    if pc is None and arch.pc_reg:
        pc = regs.get(arch.pc_reg)
    sp = arch.sp_value
    if sp is None and arch.sp_reg:
        sp = regs.get(arch.sp_reg)
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
