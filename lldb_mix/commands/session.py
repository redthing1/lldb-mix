from __future__ import annotations

import shlex

from lldb_mix.commands.context import render_context_if_enabled
from lldb_mix.commands.utils import emit_result
from lldb_mix.core.breakpoints import clear_breakpoints
from lldb_mix.core.session import Session
from lldb_mix.core.session_store import (
    apply_session,
    build_session_data,
    default_session_path,
    list_sessions,
    load_session,
    save_session,
)
from lldb_mix.core.state import SETTINGS, WATCHLIST
from lldb_mix.ui.style import colorize
from lldb_mix.ui.table import Column, render_table
from lldb_mix.ui.terminal import get_terminal_size
from lldb_mix.ui.theme import get_theme


def cmd_session(debugger, command, result, internal_dict) -> None:
    try:
        import lldb
    except Exception:
        print("[lldb-mix] session not available outside LLDB")
        return

    args = shlex.split(command)
    if not args:
        emit_result(result, _usage(), lldb)
        return

    sub = args[0]
    rest = args[1:]
    if sub in ("-h", "--help", "help"):
        emit_result(result, _usage(), lldb)
        return
    if sub == "save":
        emit_result(result, _handle_save(debugger, rest), lldb)
        return
    if sub == "load":
        emit_result(result, _handle_load(debugger, rest), lldb)
        return
    if sub == "list":
        emit_result(result, _handle_list(), lldb)
        return

    emit_result(
        result,
        f"[lldb-mix] unknown sess subcommand: {sub}\n{_usage()}",
        lldb,
    )


def _handle_save(debugger, args: list[str]) -> str:
    session = Session(debugger)
    target = session.target()
    path = args[0] if args else default_session_path(target)
    if not path:
        return "[lldb-mix] target unavailable"
    data = build_session_data(target, WATCHLIST)
    if not save_session(path, data):
        return "[lldb-mix] failed to save session"
    bps = data.get("breakpoints")
    watches = data.get("watches")
    bp_count = len(bps) if isinstance(bps, list) else 0
    watch_count = len(watches) if isinstance(watches, list) else 0
    return (
        f"[lldb-mix] session saved to {path} "
        f"(bps={bp_count}, watches={watch_count})"
    )


def _handle_load(debugger, args: list[str]) -> str:
    session = Session(debugger)
    target = session.target()
    path = args[0] if args else default_session_path(target)
    if not path:
        return "[lldb-mix] target unavailable"
    data = load_session(path)
    if not data:
        return "[lldb-mix] session not found"
    if target:
        clear_breakpoints(target)
    WATCHLIST.clear()
    bp_count, watch_count = apply_session(target, WATCHLIST, data)
    message = (
        f"[lldb-mix] session loaded from {path} "
        f"(bps={bp_count}, watches={watch_count})"
    )
    context_text = render_context_if_enabled(debugger)
    if context_text:
        message = f"{message}\n{context_text}"
    return message


def _handle_list() -> str:
    sessions = list_sessions()
    if not sessions:
        return "[lldb-mix] no sessions"

    theme = get_theme(SETTINGS.theme)
    term_width, _ = get_terminal_size()

    def _style(text: str, role: str) -> str:
        return colorize(text, role, theme, SETTINGS.enable_color)

    rows = [{"session": path} for path in sessions]
    columns = [Column("session", "SESSION", role="muted", truncate="left")]

    lines = [_style("[lldb-mix] sessions:", "title")]
    lines.extend(render_table(rows, columns, term_width, _style))
    return "\n".join(lines)


def _usage() -> str:
    return "[lldb-mix] usage: sess save [path] | load [path] | list"
