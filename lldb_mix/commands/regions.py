from __future__ import annotations

from lldb_mix.commands.utils import emit_result, module_fullpath
from lldb_mix.core.memory import read_memory_regions, regions_unavailable_message
from lldb_mix.core.session import Session
from lldb_mix.core.state import SETTINGS
from lldb_mix.deref import format_addr
from lldb_mix.ui.style import colorize
from lldb_mix.ui.table import Column, render_table
from lldb_mix.ui.terminal import get_terminal_size
from lldb_mix.ui.theme import get_theme


def format_regions_table(
    regions,
    ptr_size: int,
    target,
    lldb_module,
    term_width: int,
    style,
) -> list[str]:
    rows = []
    max_name_len = len("NAME")
    max_path_len = len("PATH")
    has_name = False
    has_path = False

    for region in regions:
        name = (region.name or "").strip()
        path = _module_path(target, region.start, lldb_module)
        if name:
            has_name = True
            max_name_len = max(max_name_len, len(name))
        if path:
            has_path = True
            max_path_len = max(max_path_len, len(path))
        rows.append(
            {
                "start": format_addr(region.start, ptr_size),
                "end": format_addr(region.end, ptr_size),
                "size": format_addr(region.end - region.start, ptr_size),
                "prot": _perm_string(region),
                "name": name,
                "path": path,
            }
        )

    columns = [
        Column("start", "START", role="addr"),
        Column("end", "END", role="addr"),
        Column("size", "SIZE", role="value"),
        Column("prot", "PROT", role="label"),
    ]
    if has_name:
        columns.append(
            Column(
                "name",
                "NAME",
                role="symbol",
                optional=True,
                priority=2,
                max_width=min(max_name_len, 24),
            )
        )
    if has_path:
        columns.append(
            Column(
                "path",
                "PATH",
                role="muted",
                optional=True,
                priority=1,
                truncate="left",
                max_width=max_path_len,
                weight=2.0,
            )
        )

    return render_table(rows, columns, term_width, style)


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
    theme = get_theme(SETTINGS.theme)
    term_width, _ = get_terminal_size()

    def _style(text: str, role: str) -> str:
        return colorize(text, role, theme, SETTINGS.enable_color)

    header = _style(f"[regions] {len(regions)} regions", "title")
    lines = [header]
    lines.extend(format_regions_table(regions, ptr_size, target, lldb, term_width, _style))
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


def _perm_string(region) -> str:
    return "".join(
        [
            "r" if region.read else "-",
            "w" if region.write else "-",
            "x" if region.execute else "-",
        ]
    )
