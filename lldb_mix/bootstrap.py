from __future__ import annotations

from lldb_mix.core.config import load_settings
from lldb_mix.core.state import SETTINGS
from lldb_mix.core.stop_hooks import ensure_stop_hook
from lldb_mix.core.version import parse_lldb_version
from lldb_mix.ui.ansi import Color, Style, RESET, escape
from lldb_mix.ui.console import banner, err


def _register_command(debugger, command: str) -> None:
    try:
        import lldb
    except Exception as exc:
        err(f"failed to import lldb for command registration: {exc}")
        return

    res = lldb.SBCommandReturnObject()
    debugger.GetCommandInterpreter().HandleCommand(command, res)
    if res.Succeeded():
        return
    error = res.GetError() or ""
    if _is_duplicate_command_error(error):
        return
    if error:
        err(f"failed to register command: {command} ({error.strip()})")
        return
    err(f"failed to register command: {command}")


def _is_duplicate_command_error(error: str) -> bool:
    text = error.lower()
    return "already exists" in text or "already a command" in text


def _set_prompt(debugger) -> None:
    try:
        debugger.SetPrompt("mix> ")
        debugger.HandleCommand("settings set use-color true")
        prefix = escape((Style.BOLD, Color.BRIGHT_CYAN))
        debugger.HandleCommand(f"settings set prompt-ansi-prefix \"{prefix}\"")
        debugger.HandleCommand(f"settings set prompt-ansi-suffix \"{RESET}\"")
    except Exception as exc:
        err(f"failed to set prompt: {exc}")


def init(debugger, internal_dict) -> None:
    version_str = "unknown"
    try:
        version_str = debugger.GetVersionString().splitlines()[0]
    except Exception:
        pass
    version = parse_lldb_version(version_str)

    try:
        debugger.HandleCommand("script import lldb_mix.commands.context")
        debugger.HandleCommand("script import lldb_mix.commands.conf")
        debugger.HandleCommand("script import lldb_mix.commands.dump")
        debugger.HandleCommand("script import lldb_mix.commands.run")
        debugger.HandleCommand("script import lldb_mix.commands.breakpoints")
        debugger.HandleCommand("script import lldb_mix.commands.regions")
        debugger.HandleCommand("script import lldb_mix.commands.disasm")
        debugger.HandleCommand("script import lldb_mix.commands.search")
        debugger.HandleCommand("script import lldb_mix.commands.antidebug")
        debugger.HandleCommand("script import lldb_mix.commands.skip")
        debugger.HandleCommand("script import lldb_mix.commands.watch")
        debugger.HandleCommand("script import lldb_mix.commands.bp")
        debugger.HandleCommand("script import lldb_mix.commands.session")
        debugger.HandleCommand("script import lldb_mix.commands.patch")
        debugger.HandleCommand("script import lldb_mix.commands.ret")
        debugger.HandleCommand("script import lldb_mix.commands.deref")
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
        "command script add -f lldb_mix.commands.conf.cmd_conf conf",
    )
    _register_command(
        debugger,
        "command script add -f lldb_mix.commands.dump.cmd_dump dump",
    )
    _register_command(
        debugger,
        "command script add -f lldb_mix.commands.dump.cmd_db db",
    )
    _register_command(
        debugger,
        "command script add -f lldb_mix.commands.dump.cmd_dw dw",
    )
    _register_command(
        debugger,
        "command script add -f lldb_mix.commands.dump.cmd_dd dd",
    )
    _register_command(
        debugger,
        "command script add -f lldb_mix.commands.dump.cmd_dq dq",
    )
    _register_command(
        debugger,
        "command script add -f lldb_mix.commands.disasm.cmd_u u",
    )
    _register_command(
        debugger,
        "command script add -f lldb_mix.commands.search.cmd_findmem findmem",
    )
    _register_command(
        debugger,
        "command script add -f lldb_mix.commands.run.cmd_rr rr",
    )
    _register_command(
        debugger,
        "command script add -f lldb_mix.commands.breakpoints.cmd_bpm bpm",
    )
    _register_command(
        debugger,
        "command script add -f lldb_mix.commands.breakpoints.cmd_bpt bpt",
    )
    _register_command(
        debugger,
        "command script add -f lldb_mix.commands.breakpoints.cmd_bpn bpn",
    )
    _register_command(
        debugger,
        "command script add -f lldb_mix.commands.regions.cmd_regions regions",
    )
    _register_command(debugger, "command alias -- vmmap regions")
    _register_command(
        debugger,
        "command script add -f lldb_mix.commands.antidebug.cmd_antidebug antidebug",
    )
    _register_command(
        debugger,
        "command script add -f lldb_mix.commands.skip.cmd_skip skip",
    )
    _register_command(
        debugger,
        "command script add -f lldb_mix.commands.watch.cmd_watch watch",
    )
    _register_command(
        debugger,
        "command script add -f lldb_mix.commands.bp.cmd_bp bp",
    )
    _register_command(
        debugger,
        "command script add -f lldb_mix.commands.session.cmd_session sess",
    )
    _register_command(
        debugger,
        "command script add -f lldb_mix.commands.patch.cmd_patch patch",
    )
    _register_command(
        debugger,
        "command script add -f lldb_mix.commands.ret.cmd_ret ret",
    )
    _register_command(
        debugger,
        "command script add -f lldb_mix.commands.deref.cmd_deref deref",
    )

    load_settings(SETTINGS)
    _set_prompt(debugger)
    if SETTINGS.auto_context:
        target = debugger.GetSelectedTarget()
        if target and target.IsValid():
            ensure_stop_hook(debugger, "context")
    banner(f"loaded ({version.variant} lldb-{version.major}.{version.minor})")
