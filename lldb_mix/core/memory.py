from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

RegionKey = tuple[int, int, bool, bool, bool, Optional[str]]


@dataclass(frozen=True)
class MemoryRegion:
    start: int
    end: int
    read: bool
    write: bool
    execute: bool
    name: str | None = None

    def contains(self, addr: int) -> bool:
        return self.start <= addr < self.end


class ProcessMemoryReader:
    def __init__(self, process: Any):
        self.process = process

    def read(self, addr: int, size: int) -> bytes | None:
        try:
            import lldb
        except Exception:
            return None

        if not self.process or not self.process.IsValid():
            return None

        error = lldb.SBError()
        data = self.process.ReadMemory(addr, size, error)
        if not error.Success():
            return None
        return data

    def read_pointer(self, addr: int, ptr_size: int) -> int | None:
        data = self.read(addr, ptr_size)
        if not data or len(data) < ptr_size:
            return None
        return int.from_bytes(data[:ptr_size], byteorder="little")


def read_memory_regions(process: Any) -> list[MemoryRegion]:
    try:
        import lldb
    except Exception:
        return []

    if not process or not process.IsValid():
        return []

    output = _regions_from_list(process, lldb)
    if output:
        return output
    return _fallback_memory_regions(process, lldb)


def _fallback_memory_regions(process: Any, lldb_module: Any) -> list[MemoryRegion]:
    # gdb-remote often returns empty region lists even when per-address queries work.
    output: list[MemoryRegion] = []
    seen: set[RegionKey] = set()
    info = lldb_module.SBMemoryRegionInfo()
    for addr in _seed_region_addrs(process, lldb_module):
        if not _query_region_info(process, addr, info, lldb_module):
            continue
        _append_region(output, seen, info, lldb_module)
    output.sort(key=lambda region: region.start)
    return output


def _regions_from_list(process: Any, lldb_module: Any) -> list[MemoryRegion]:
    regions = process.GetMemoryRegions()
    if not regions or regions.GetSize() == 0:
        return []
    output: list[MemoryRegion] = []
    seen: set[RegionKey] = set()
    info = lldb_module.SBMemoryRegionInfo()
    for idx in range(regions.GetSize()):
        if not regions.GetMemoryRegionAtIndex(idx, info):
            continue
        _append_region(output, seen, info, lldb_module)
    return output


def _seed_region_addrs(process: Any, lldb_module: Any) -> list[int]:
    seeds: set[int] = set()
    target = process.GetTarget() if process else None
    if target and target.IsValid():
        for idx in range(target.GetNumModules()):
            module = target.GetModuleAtIndex(idx)
            if not module or not module.IsValid():
                continue
            for sec_idx in range(module.GetNumSections()):
                _collect_section_addrs(
                    module.GetSectionAtIndex(sec_idx),
                    target,
                    seeds,
                    lldb_module,
                )

    thread = process.GetSelectedThread() if process else None
    if thread and thread.IsValid():
        frame = thread.GetFrameAtIndex(0)
        if frame and frame.IsValid():
            for addr in (frame.GetPC(), frame.GetSP(), frame.GetFP()):
                if addr != lldb_module.LLDB_INVALID_ADDRESS:
                    seeds.add(addr)
    return sorted(seeds)


def _collect_section_addrs(section: Any, target: Any, seeds: set[int], lldb_module: Any) -> None:
    if not section or not section.IsValid():
        return
    addr = section.GetLoadAddress(target)
    if addr != lldb_module.LLDB_INVALID_ADDRESS:
        seeds.add(addr)
    for idx in range(section.GetNumSubSections()):
        _collect_section_addrs(section.GetSubSectionAtIndex(idx), target, seeds, lldb_module)


def _query_region_info(process: Any, addr: int, info: Any, lldb_module: Any) -> bool:
    try:
        result = process.GetMemoryRegionInfo(addr, info)
    except Exception:
        return False
    if hasattr(result, "Success"):
        return result.Success()
    if isinstance(result, bool):
        return result
    return False


def _append_region(
    output: list[MemoryRegion],
    seen: set[RegionKey],
    info: Any,
    lldb_module: Any,
) -> None:
    region = _region_from_info(info, lldb_module)
    if not region:
        return
    key = _region_key(region)
    if key in seen:
        return
    seen.add(key)
    output.append(region)


def _region_from_info(info: Any, lldb_module: Any) -> MemoryRegion | None:
    if hasattr(info, "IsMapped") and not info.IsMapped():
        return None
    start = info.GetRegionBase()
    end = info.GetRegionEnd()
    if (
        start == lldb_module.LLDB_INVALID_ADDRESS
        or end == lldb_module.LLDB_INVALID_ADDRESS
        or end <= start
    ):
        return None
    name = None
    if hasattr(info, "GetName"):
        name = info.GetName() or None
    return MemoryRegion(
        start=start,
        end=end,
        read=info.IsReadable(),
        write=info.IsWritable(),
        execute=info.IsExecutable(),
        name=name,
    )


def _region_key(region: MemoryRegion) -> RegionKey:
    return (
        region.start,
        region.end,
        region.read,
        region.write,
        region.execute,
        region.name,
    )
