from __future__ import annotations

from lldb_mix.commands.utils import emit_result, module_fullpath
from lldb_mix.core.memory import read_memory_regions, regions_unavailable_message
from lldb_mix.core.session import Session
from lldb_mix.deref import format_addr


def format_regions_table(regions, ptr_size: int, target, lldb_module) -> list[str]:
    addr_width = len(format_addr(0, ptr_size))
    header = (
        f"{'START':^{addr_width}} {'END':^{addr_width}} "
        f"{'SIZE':^{addr_width}} {'PROT':^4} {'NAME':^16} PATH"
    )
    lines = [header, "-" * len(header)]

    for region in regions:
        start = format_addr(region.start, ptr_size)
        end = format_addr(region.end, ptr_size)
        size = format_addr(region.end - region.start, ptr_size)
        prot = "".join(
            [
                "r" if region.read else "-",
                "w" if region.write else "-",
                "x" if region.execute else "-",
            ]
        )
        name = region.name or ""
        if len(name) > 16:
            name = name[:16]
        path = _module_path(target, region.start, lldb_module)
        lines.append(f"{start} {end} {size} {prot:3} {name:16} {path}".rstrip())
    return lines


def cmd_regions(debugger, command, result, internal_dict) -> None:
    try:
        import lldb
    except Exception:
        print("[lldb-mix] regions not available outside LLDB")
        return

    args = command.split()
    if args and args[0] in ("-h", "--help", "help"):
        emit_result(result, _usage(), lldb)
        return

    session = Session(debugger)
    process = session.process()
    target = session.target()
    if not process or not target:
        emit_result(result, "[lldb-mix] process unavailable", lldb)
        return

    regions = read_memory_regions(process)
    if not regions:
        emit_result(result, regions_unavailable_message(process), lldb)
        return

    ptr_size = target.GetAddressByteSize() or 8
    lines = format_regions_table(regions, ptr_size, target, lldb)
    emit_result(result, "\n".join(lines), lldb)


def _usage() -> str:
    return "[lldb-mix] usage: regions"


def _module_path(target, addr: int, lldb_module) -> str:
    try:
        sbaddr = lldb_module.SBAddress(addr, target)
        module = sbaddr.GetModule()
        if module and module.IsValid():
            return module_fullpath(module)
    except Exception:
        return ""
    return ""
