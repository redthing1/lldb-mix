from __future__ import annotations

from lldb_mix.core.config import load_settings
from lldb_mix.core.state import SETTINGS
from lldb_mix.core.stop_hooks import ensure_stop_hook
from lldb_mix.core.version import parse_lldb_version
from lldb_mix.ui.console import banner, err


def _register_command(debugger, command: str) -> None:
    try:
        import lldb
    except Exception as exc:
        err(f"failed to import lldb for command registration: {exc}")
        return

    res = lldb.SBCommandReturnObject()
    debugger.GetCommandInterpreter().HandleCommand(command, res)
    if not res.Succeeded():
        err(f"failed to register command: {command}")


def init(debugger, internal_dict) -> None:
    version_str = "unknown"
    try:
        version_str = debugger.GetVersionString().splitlines()[0]
    except Exception:
        pass
    version = parse_lldb_version(version_str)

    try:
        debugger.HandleCommand("script import lldb_mix.commands.context")
        debugger.HandleCommand("script import lldb_mix.commands.dump")
    except Exception as exc:
        err(f"failed to import commands via lldb script: {exc}")
        return

    _register_command(
        debugger,
        "command script add -f lldb_mix.commands.context.cmd_context context",
    )
    _register_command(debugger, "command alias -- ctx context")
    _register_command(
        debugger,
        "command script add -f lldb_mix.commands.dump.cmd_dump dump",
    )

    load_settings(SETTINGS)
    if SETTINGS.auto_context:
        target = debugger.GetSelectedTarget()
        if target and target.IsValid():
            ensure_stop_hook(debugger, "context")
    banner(f"loaded ({version.variant} lldb-{version.major}.{version.minor})")
