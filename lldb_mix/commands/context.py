from __future__ import annotations

from lldb_mix.context.manager import ContextManager
from lldb_mix.core.config import load_settings, save_settings
from lldb_mix.core.memory import ProcessMemoryReader
from lldb_mix.core.session import Session
from lldb_mix.core.snapshot import capture_snapshot
from lldb_mix.core.state import SETTINGS
from lldb_mix.core.stop_hooks import ensure_stop_hook, remove_stop_hook
from lldb_mix.core.symbols import TargetSymbolResolver
from lldb_mix.ui.theme import THEMES, get_theme


_MANAGER: ContextManager | None = None


def _manager() -> ContextManager:
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = ContextManager(SETTINGS, get_theme(SETTINGS.theme))
    else:
        _MANAGER.theme = get_theme(SETTINGS.theme)
    return _MANAGER


def cmd_context(debugger, command, result, internal_dict) -> None:
    try:
        import lldb
    except Exception:
        print("[lldb-mix] context not available outside LLDB")
        return

    args = command.split()
    if args:
        sub = args[0]
        message = _handle_subcommand(debugger, sub, args[1:])
        if message is not None:
            try:
                result.PutCString(message)
                result.SetStatus(lldb.eReturnStatusSuccessFinishResult)
            except Exception:
                print(message)
            return

    session = Session(debugger)
    snapshot = capture_snapshot(session)
    if not snapshot:
        message = "[lldb-mix] context stub (no target)"
        try:
            result.PutCString(message)
            result.SetStatus(lldb.eReturnStatusSuccessFinishResult)
        except Exception:
            print(message)
        return

    process = session.process()
    reader = ProcessMemoryReader(process) if process else None
    target = session.target()
    resolver = TargetSymbolResolver(target) if target else None

    lines = _manager().render(snapshot, reader, resolver, target, process)
    message = "\n".join(lines)
    try:
        result.PutCString(message)
        result.SetStatus(lldb.eReturnStatusSuccessFinishResult)
    except Exception:
        print(message)


def _handle_subcommand(debugger, sub: str, rest: list[str]) -> str | None:
    if sub == "auto":
        return _handle_auto(debugger, rest)
    if sub == "layout":
        return _handle_layout(rest)
    if sub == "theme":
        return _handle_theme(rest)
    if sub == "save":
        return _handle_save()
    if sub == "load":
        return _handle_load()
    if sub == "help":
        return _usage()
    return f"[lldb-mix] unknown context subcommand: {sub}"


def _handle_auto(debugger, args: list[str]) -> str:
    if not args or args[0] == "status":
        status = "on" if SETTINGS.auto_context else "off"
        return f"[lldb-mix] auto context is {status}"
    if args[0] == "on":
        SETTINGS.auto_context = True
        ensure_stop_hook(debugger, "context")
        return "[lldb-mix] auto context enabled"
    if args[0] == "off":
        SETTINGS.auto_context = False
        remove_stop_hook(debugger, "context")
        return "[lldb-mix] auto context disabled"
    return _usage()


def _handle_layout(args: list[str]) -> str:
    if not args:
        return f"[lldb-mix] layout: {' '.join(SETTINGS.layout)}"
    SETTINGS.layout = args
    return f"[lldb-mix] layout set: {' '.join(SETTINGS.layout)}"


def _usage() -> str:
    return (
        "[lldb-mix] usage: context [auto on|off|status] | [layout <panes...>] | "
        "[theme <name|list|status>] | [save|load] | [help]"
    )


def _handle_save() -> str:
    if save_settings(SETTINGS):
        return "[lldb-mix] settings saved"
    return "[lldb-mix] failed to save settings"


def _handle_load() -> str:
    if load_settings(SETTINGS):
        return "[lldb-mix] settings loaded"
    return "[lldb-mix] no settings found"


def _handle_theme(args: list[str]) -> str:
    if not args or args[0] == "status":
        return f"[lldb-mix] theme: {SETTINGS.theme}"
    if args[0] == "list":
        names = ", ".join(sorted(THEMES.keys()))
        return f"[lldb-mix] themes: {names}"
    name = args[0]
    if name not in THEMES:
        return f"[lldb-mix] unknown theme: {name}"
    SETTINGS.theme = name
    return f"[lldb-mix] theme set: {name}"
