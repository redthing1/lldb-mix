from __future__ import annotations

from lldb_mix.context.manager import ContextManager
from lldb_mix.core.memory import ProcessMemoryReader
from lldb_mix.core.session import Session
from lldb_mix.core.snapshot import capture_snapshot
from lldb_mix.core.state import SETTINGS
from lldb_mix.core.symbols import TargetSymbolResolver
from lldb_mix.ui.theme import get_theme


_MANAGER: ContextManager | None = None


def _manager() -> ContextManager:
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = ContextManager(SETTINGS, get_theme(SETTINGS.theme))
    else:
        _MANAGER.theme = get_theme(SETTINGS.theme)
    return _MANAGER


def render_context(debugger) -> str:
    session = Session(debugger)
    snapshot = capture_snapshot(session)
    if not snapshot:
        return "[lldb-mix] context stub (no target)"

    process = session.process()
    reader = ProcessMemoryReader(process) if process else None
    target = session.target()
    resolver = TargetSymbolResolver(target) if target else None

    lines = _manager().render(snapshot, reader, resolver, target, process)
    return "\n".join(lines)


def cmd_context(debugger, command, result, internal_dict) -> None:
    try:
        import lldb
    except Exception:
        print("[lldb-mix] context not available outside LLDB")
        return

    if command.strip():
        message = "[lldb-mix] context takes no arguments (use conf)"
        try:
            result.PutCString(message)
            result.SetStatus(lldb.eReturnStatusSuccessFinishResult)
        except Exception:
            print(message)
        return

    message = render_context(debugger)
    try:
        result.PutCString(message)
        result.SetStatus(lldb.eReturnStatusSuccessFinishResult)
    except Exception:
        print(message)
