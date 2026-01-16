from __future__ import annotations

import shlex

from lldb_mix.commands.utils import emit_result
from lldb_mix.core.addressing import parse_int
from lldb_mix.core.breakpoints import clear_breakpoints, format_breakpoint_list
from lldb_mix.core.session import Session


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
    return format_breakpoint_list(target)


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
