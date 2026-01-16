from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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

    regions = process.GetMemoryRegions()
    if not regions or regions.GetSize() == 0:
        return []
    output: list[MemoryRegion] = []
    info = lldb.SBMemoryRegionInfo()
    for idx in range(regions.GetSize()):
        if not regions.GetMemoryRegionAtIndex(idx, info):
            continue
        region = _region_from_info(info, lldb)
        if region:
            output.append(region)
    return output


def regions_unavailable_message(process: Any) -> str:
    plugin = _process_plugin_name(process)
    if "gdb-remote" in plugin:
        return "[lldb-mix] no memory regions (gdb-remote)"
    return "[lldb-mix] no memory regions"


def _process_plugin_name(process: Any) -> str:
    if not process:
        return ""
    try:
        name = process.GetPluginName()
    except Exception:
        return ""
    return (name or "").lower()


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
