from __future__ import annotations

import shlex

from lldb_mix.commands.utils import emit_result, parse_int
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
        emit_result(result, _handle_add(rest), lldb)
        return
    if sub in ("del", "rm", "remove"):
        emit_result(result, _handle_del(rest), lldb)
        return
    if sub == "list":
        emit_result(result, _handle_list(), lldb)
        return
    if sub == "clear":
        emit_result(result, _handle_clear(), lldb)
        return

    emit_result(result, f"[lldb-mix] unknown watch subcommand: {sub}\n{_usage()}", lldb)


def _handle_add(args: list[str]) -> str:
    if not args:
        return _usage()
    expr = args[0]
    label = " ".join(args[1:]) if len(args) > 1 else None
    entry = WATCHLIST.add(expr, label)
    if label:
        return f"[lldb-mix] watch #{entry.wid} added: {expr} ({label})"
    return f"[lldb-mix] watch #{entry.wid} added: {expr}"


def _handle_del(args: list[str]) -> str:
    if len(args) != 1:
        return _usage()
    wid = parse_int(args[0])
    if wid is None or wid <= 0:
        return "[lldb-mix] invalid watch id"
    if WATCHLIST.remove(wid):
        return f"[lldb-mix] watch #{wid} removed"
    return f"[lldb-mix] watch #{wid} not found"


def _handle_list() -> str:
    items = WATCHLIST.items()
    if not items:
        return "[lldb-mix] no watches"
    lines = ["[lldb-mix] watches:"]
    for entry in items:
        label = f" ({entry.label})" if entry.label else ""
        lines.append(f"#{entry.wid} {entry.expr}{label}")
    return "\n".join(lines)


def _handle_clear() -> str:
    WATCHLIST.clear()
    return "[lldb-mix] watches cleared"


def _usage() -> str:
    return "[lldb-mix] usage: watch add <expr> [label] | del <id> | list | clear"
