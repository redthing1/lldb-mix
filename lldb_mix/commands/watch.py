from __future__ import annotations

import shlex

from lldb_mix.commands.context import render_context_if_enabled
from lldb_mix.commands.utils import emit_result
from lldb_mix.core.addressing import parse_int
from lldb_mix.core.state import WATCHLIST


def cmd_watch(debugger, command, result, internal_dict) -> None:
    try:
        import lldb
    except Exception:
        print("[lldb-mix] watch not available outside LLDB")
        return

    args = shlex.split(command)
    if not args:
        emit_result(result, _handle_list(), lldb)
        return

    sub = args[0]
    rest = args[1:]
    if sub in ("-h", "--help", "help"):
        emit_result(result, _usage(), lldb)
        return
    if sub == "add":
        if not rest:
            emit_result(result, _usage(), lldb)
            return
        message = _handle_add(rest)
        _emit_with_context(result, debugger, message, lldb, True)
        return
    if sub in ("del", "rm", "remove"):
        if len(rest) != 1:
            emit_result(result, _usage(), lldb)
            return
        message, changed = _handle_del(rest)
        _emit_with_context(result, debugger, message, lldb, changed)
        return
    if sub == "list":
        emit_result(result, _handle_list(), lldb)
        return
    if sub == "clear":
        if rest:
            emit_result(result, _usage(), lldb)
            return
        message, changed = _handle_clear()
        _emit_with_context(result, debugger, message, lldb, changed)
        return

    emit_result(result, f"[lldb-mix] unknown watch subcommand: {sub}\n{_usage()}", lldb)


def _handle_add(args: list[str]) -> str:
    expr = args[0]
    label = " ".join(args[1:]) if len(args) > 1 else None
    entry = WATCHLIST.add(expr, label)
    if label:
        return f"[lldb-mix] watch #{entry.wid} added: {expr} ({label})"
    return f"[lldb-mix] watch #{entry.wid} added: {expr}"


def _handle_del(args: list[str]) -> tuple[str, bool]:
    wid = parse_int(args[0]) if args else None
    if wid is None or wid <= 0:
        return "[lldb-mix] invalid watch id", False
    if WATCHLIST.remove(wid):
        return f"[lldb-mix] watch #{wid} removed", True
    return f"[lldb-mix] watch #{wid} not found", False


def _handle_list() -> str:
    items = WATCHLIST.items()
    if not items:
        return "[lldb-mix] no watches"
    lines = ["[lldb-mix] watches:"]
    for entry in items:
        label = f" ({entry.label})" if entry.label else ""
        lines.append(f"#{entry.wid} {entry.expr}{label}")
    return "\n".join(lines)


def _handle_clear() -> tuple[str, bool]:
    had_items = bool(WATCHLIST.items())
    WATCHLIST.clear()
    return "[lldb-mix] watches cleared", had_items


def _usage() -> str:
    return "[lldb-mix] usage: watch add <expr> [label] | del <id> | list | clear"


def _emit_with_context(
    result,
    debugger,
    message: str,
    lldb_module,
    changed: bool,
) -> None:
    context_text = render_context_if_enabled(debugger) if changed else None
    if context_text:
        message = f"{message}\n{context_text}"
    emit_result(result, message, lldb_module)
