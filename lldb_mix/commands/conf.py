from __future__ import annotations

import shlex

from lldb_mix.commands.utils import emit_result
from lldb_mix.core.config import (
    format_setting,
    list_specs,
    load_settings,
    reset_settings,
    save_settings,
    set_setting,
)
from lldb_mix.core.state import SETTINGS
from lldb_mix.core.stop_hooks import ensure_stop_hook, remove_stop_hook
from lldb_mix.core.stop_output import apply_quiet, capture_defaults, restore_defaults


def cmd_conf(debugger, command, result, internal_dict) -> None:
    try:
        import lldb
    except Exception:
        print("[lldb-mix] conf not available outside LLDB")
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
    if sub == "list":
        emit_result(result, _handle_list(), lldb)
        return
    if sub == "get":
        emit_result(result, _handle_get(rest), lldb)
        return
    if sub == "set":
        emit_result(result, _handle_set(debugger, rest), lldb)
        return
    if sub == "save":
        emit_result(result, _handle_save(), lldb)
        return
    if sub == "load":
        emit_result(result, _handle_load(debugger), lldb)
        return
    if sub == "default":
        emit_result(result, _handle_default(debugger), lldb)
        return

    emit_result(result, f"[lldb-mix] unknown conf subcommand: {sub}\n{_usage()}", lldb)


def _handle_list() -> str:
    lines = ["[lldb-mix] conf settings:"]
    for spec in list_specs():
        value = format_setting(SETTINGS, spec.key)
        if value is None:
            continue
        lines.append(f"{spec.key} = {value}")
    return "\n".join(lines)


def _handle_get(args: list[str]) -> str:
    if len(args) != 1:
        return _usage()
    key = args[0]
    value = format_setting(SETTINGS, key)
    if value is None:
        return f"[lldb-mix] unknown setting: {key}"
    return f"[lldb-mix] {key} = {value}"


def _handle_set(debugger, args: list[str]) -> str:
    if len(args) < 2:
        return _usage()
    key = args[0]
    ok, message = set_setting(SETTINGS, key, args[1:])
    if not ok:
        return f"[lldb-mix] {message}"
    if key == "auto_context":
        _sync_auto_context(debugger)
    return f"[lldb-mix] {key} = {message}"


def _handle_save() -> str:
    if save_settings(SETTINGS):
        return "[lldb-mix] settings saved"
    return "[lldb-mix] failed to save settings"


def _handle_load(debugger) -> str:
    if not load_settings(SETTINGS):
        return "[lldb-mix] no settings found"
    _sync_auto_context(debugger)
    return "[lldb-mix] settings loaded"


def _handle_default(debugger) -> str:
    reset_settings(SETTINGS)
    _sync_auto_context(debugger)
    return "[lldb-mix] settings reset to defaults"


def _sync_auto_context(debugger) -> None:
    capture_defaults(debugger)
    if SETTINGS.auto_context:
        ensure_stop_hook(debugger, "context")
        apply_quiet(debugger)
    else:
        remove_stop_hook(debugger, "context")
        restore_defaults(debugger)


def _usage() -> str:
    return (
        "[lldb-mix] usage: conf [list] | get <key> | set <key> <value...> | "
        "save | load | default"
    )
