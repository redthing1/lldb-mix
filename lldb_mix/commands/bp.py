from __future__ import annotations

import shlex

from lldb_mix.commands.utils import emit_result
from lldb_mix.core.addressing import parse_int
from lldb_mix.core.breakpoints import clear_breakpoints, collect_breakpoints
from lldb_mix.core.session import Session
from lldb_mix.core.state import SETTINGS
from lldb_mix.deref import format_addr
from lldb_mix.ui.style import colorize
from lldb_mix.ui.table import Column, render_table
from lldb_mix.ui.terminal import get_terminal_size
from lldb_mix.ui.theme import get_theme


def cmd_bp(debugger, command, result, internal_dict) -> None:
    try:
        import lldb
    except Exception:
        print("[lldb-mix] bp not available outside LLDB")
        return

    args = shlex.split(command)
    if not args:
        emit_result(result, "\n".join(_handle_list(debugger)), lldb)
        return

    sub = args[0]
    rest = args[1:]
    if sub in ("-h", "--help", "help"):
        emit_result(result, _usage(), lldb)
        return
    if sub == "list":
        emit_result(result, "\n".join(_handle_list(debugger)), lldb)
        return
    if sub == "enable":
        emit_result(result, _handle_toggle(debugger, rest, True), lldb)
        return
    if sub == "disable":
        emit_result(result, _handle_toggle(debugger, rest, False), lldb)
        return
    if sub == "clear":
        emit_result(result, _handle_clear(debugger, rest), lldb)
        return

    emit_result(result, f"[lldb-mix] unknown bp subcommand: {sub}\n{_usage()}", lldb)


def _handle_list(debugger) -> list[str]:
    session = Session(debugger)
    target = session.target()
    if not target or not target.IsValid():
        return ["[lldb-mix] target unavailable"]

    theme = get_theme(SETTINGS.theme)
    term_width, _ = get_terminal_size()

    def _style(text: str, role: str) -> str:
        return colorize(text, role, theme, SETTINGS.enable_color)

    infos = collect_breakpoints(target)
    header = _style("[lldb-mix] breakpoints:", "title")
    if not infos:
        return [header, _style("(none)", "muted")]

    ptr_size = target.GetAddressByteSize() or 8
    rows = []
    has_module = False
    has_offset = False
    for info in infos:
        addr_text = format_addr(info.addr, ptr_size) if info.addr is not None else ""
        module_text = info.module or ""
        offset_text = f"+0x{info.offset:x}" if info.offset is not None else ""
        if module_text:
            has_module = True
        if offset_text:
            has_offset = True
        rows.append(
            {
                "id": f"#{info.bp_id}",
                "state": "enabled" if info.enabled else "disabled",
                "locs": str(info.locations),
                "addr": addr_text,
                "module": module_text,
                "offset": offset_text,
            }
        )

    columns = [
        Column("id", "ID", role="label", align="right", min_width=2),
        Column("state", "STATE", role="value"),
        Column("locs", "LOCS", role="value", align="right"),
        Column("addr", "ADDR", role="addr"),
    ]
    if has_module:
        columns.append(
            Column("module", "MODULE", role="symbol", optional=True, priority=2)
        )
    if has_offset:
        columns.append(Column("offset", "OFF", role="value", optional=True, priority=1))

    lines = [header]
    lines.extend(render_table(rows, columns, term_width, _style))
    return lines


def _handle_toggle(debugger, args: list[str], enabled: bool) -> str:
    session = Session(debugger)
    target = session.target()
    if not target:
        return "[lldb-mix] target unavailable"
    if len(args) != 1:
        return _usage()
    if args[0] == "all":
        count = 0
        for bp in target.breakpoint_iter():
            if bp and bp.IsValid():
                bp.SetEnabled(enabled)
                count += 1
        state = "enabled" if enabled else "disabled"
        return f"[lldb-mix] {state} {count} breakpoints"
    bp_id = parse_int(args[0])
    if bp_id is None:
        return "[lldb-mix] invalid breakpoint id"
    bp = target.FindBreakpointByID(bp_id)
    if not bp or not bp.IsValid():
        return f"[lldb-mix] breakpoint {bp_id} not found"
    bp.SetEnabled(enabled)
    state = "enabled" if enabled else "disabled"
    return f"[lldb-mix] {state} breakpoint {bp_id}"


def _handle_clear(debugger, args: list[str]) -> str:
    session = Session(debugger)
    target = session.target()
    if not target:
        return "[lldb-mix] target unavailable"
    if len(args) != 1 or args[0] != "all":
        return _usage()
    removed = clear_breakpoints(target)
    return f"[lldb-mix] cleared {removed} breakpoints"


def _usage() -> str:
    return (
        "[lldb-mix] usage: bp [list] | enable <id|all> | disable <id|all> | "
        "clear all"
    )
