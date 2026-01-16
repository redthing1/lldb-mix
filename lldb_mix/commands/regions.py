from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from lldb_mix.commands.utils import emit_result, module_fullpath
from lldb_mix.core.memory import read_memory_regions, regions_unavailable_message
from lldb_mix.core.session import Session
from lldb_mix.core.state import SETTINGS
from lldb_mix.deref import format_addr
from lldb_mix.ui.style import colorize
from lldb_mix.ui.terminal import get_terminal_size
from lldb_mix.ui.text import pad_ansi, truncate_ansi, visible_len
from lldb_mix.ui.theme import get_theme


StyleFn = Callable[[str, str], str]


def _identity(text: str, _width: int) -> str:
    return text


@dataclass(frozen=True)
class RegionRow:
    start: str
    end: str
    size: str
    prot: str
    name: str
    path: str


@dataclass(frozen=True)
class RegionStats:
    has_name: bool
    has_path: bool
    max_name_len: int
    max_path_len: int


@dataclass(frozen=True)
class ColumnSpec:
    label: str
    width: int
    role: str
    align: str
    getter: Callable[[RegionRow], str]
    formatter: Callable[[str, int], str] = _identity


@dataclass(frozen=True)
class OptionalWidths:
    name_width: int = 0
    path_width: int = 0
    show_name: bool = False
    show_path: bool = False


def format_regions_table(
    regions,
    ptr_size: int,
    target,
    lldb_module,
    term_width: int,
    style: StyleFn,
) -> list[str]:
    rows, stats = _collect_rows(regions, ptr_size, target, lldb_module)
    columns = _build_columns(stats, ptr_size, term_width)
    return _render_table(rows, columns, style)


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


def _collect_rows(regions, ptr_size: int, target, lldb_module) -> tuple[list[RegionRow], RegionStats]:
    rows: list[RegionRow] = []
    has_name = False
    has_path = False
    max_name_len = len("NAME")
    max_path_len = len("PATH")

    for region in regions:
        row = RegionRow(
            start=format_addr(region.start, ptr_size),
            end=format_addr(region.end, ptr_size),
            size=format_addr(region.end - region.start, ptr_size),
            prot=_perm_string(region),
            name=(region.name or "").strip(),
            path=_module_path(target, region.start, lldb_module),
        )
        rows.append(row)
        if row.name:
            has_name = True
            max_name_len = max(max_name_len, len(row.name))
        if row.path:
            has_path = True
            max_path_len = max(max_path_len, len(row.path))

    return rows, RegionStats(
        has_name=has_name,
        has_path=has_path,
        max_name_len=max_name_len,
        max_path_len=max_path_len,
    )


def _build_columns(stats: RegionStats, ptr_size: int, term_width: int) -> list[ColumnSpec]:
    addr_width = max(len(format_addr(0, ptr_size)), len("START"))
    size_width = max(addr_width, len("SIZE"))
    prot_width = max(4, len("PROT"))

    columns = [
        ColumnSpec("START", addr_width, "addr", "left", lambda r: r.start),
        ColumnSpec("END", addr_width, "addr", "left", lambda r: r.end),
        ColumnSpec("SIZE", size_width, "value", "left", lambda r: r.size),
        ColumnSpec("PROT", prot_width, "label", "left", lambda r: r.prot),
    ]

    optional = _compute_optional_widths(stats, term_width, columns)
    if optional.show_name and optional.name_width > 0:
        columns.append(
            ColumnSpec(
                "NAME",
                optional.name_width,
                "symbol",
                "left",
                lambda r: r.name,
            )
        )
    if optional.show_path and optional.path_width > 0:
        columns.append(
            ColumnSpec(
                "PATH",
                optional.path_width,
                "muted",
                "left",
                lambda r: r.path,
                _truncate_path_left,
            )
        )

    return columns


def _compute_optional_widths(
    stats: RegionStats, term_width: int, base_columns: list[ColumnSpec]
) -> OptionalWidths:
    if not stats.has_name and not stats.has_path:
        return OptionalWidths()

    base_width = sum(col.width for col in base_columns) + (len(base_columns) - 1)
    min_name = len("NAME")
    min_path = len("PATH")
    max_name = max(min_name, min(stats.max_name_len, 24))

    def _available(optional_cols: int) -> int:
        return term_width - base_width - optional_cols

    def _clamp(value: int, min_width: int, max_width: int) -> int:
        return max(min_width, min(max_width, value))

    if stats.has_name and stats.has_path:
        available = _available(2)
        if available >= min_name + min_path:
            name_width = _clamp(min(stats.max_name_len, available - min_path), min_name, max_name)
            path_width = _clamp(
                min(stats.max_path_len, available - name_width),
                min_path,
                stats.max_path_len,
            )
            return OptionalWidths(name_width, path_width, True, True)

    if stats.has_name:
        available = _available(1)
        if available >= min_name:
            name_width = _clamp(min(stats.max_name_len, available), min_name, max_name)
            return OptionalWidths(name_width, 0, True, False)

    if stats.has_path:
        available = _available(1)
        if available >= min_path:
            path_width = _clamp(min(stats.max_path_len, available), min_path, stats.max_path_len)
            return OptionalWidths(0, path_width, False, True)

    return OptionalWidths()


def _render_table(rows: list[RegionRow], columns: list[ColumnSpec], style: StyleFn) -> list[str]:
    sep = " "
    table_width = sum(col.width for col in columns) + (len(columns) - 1)

    header_parts = [_pad_cell(style(col.label, "label"), col.width, col.align) for col in columns]
    header = sep.join(header_parts)
    lines = [header, style("-" * max(table_width, 0), "separator")]

    for row in rows:
        parts = []
        for col in columns:
            raw_value = col.getter(row)
            raw_value = col.formatter(raw_value, col.width)
            parts.append(_pad_cell(style(raw_value, col.role), col.width, col.align))
        lines.append(sep.join(parts).rstrip())

    return lines


def _pad_cell(text: str, width: int, align: str) -> str:
    if width <= 0:
        return ""
    if visible_len(text) > width:
        text = truncate_ansi(text, width)
    length = visible_len(text)
    if length >= width:
        return text
    padding = width - length
    if align == "right":
        return (" " * padding) + text
    if align == "center":
        left = padding // 2
        right = padding - left
        return (" " * left) + text + (" " * right)
    return pad_ansi(text, width)


def _truncate_path_left(path: str, width: int) -> str:
    if width <= 0:
        return ""
    if len(path) <= width:
        return path
    if width <= 3:
        return path[:width]
    return "..." + path[-(width - 3) :]


def _perm_string(region) -> str:
    return "".join(
        [
            "r" if region.read else "-",
            "w" if region.write else "-",
            "x" if region.execute else "-",
        ]
    )


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
