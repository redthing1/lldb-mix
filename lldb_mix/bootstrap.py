from __future__ import annotations

from lldb_mix.commands.registry import register_commands
from lldb_mix.core.config import load_settings
from lldb_mix.core.state import SETTINGS
from lldb_mix.core.stop_hooks import ensure_stop_hook
from lldb_mix.core.stop_output import apply_quiet, capture_defaults, restore_defaults
from lldb_mix.core.version import parse_lldb_version
from lldb_mix.ui.ansi import Color, Style, RESET, escape
from lldb_mix.ui.console import banner, err


def _set_prompt(debugger) -> None:
    try:
        debugger.SetPrompt("mix> ")
        debugger.HandleCommand("settings set use-color true")
        prefix = escape((Style.BOLD, Color.BRIGHT_CYAN))
        debugger.HandleCommand(f'settings set prompt-ansi-prefix "{prefix}"')
        debugger.HandleCommand(f'settings set prompt-ansi-suffix "{RESET}"')
    except Exception as exc:
        err(f"failed to set prompt: {exc}")


def init(debugger, internal_dict) -> None:
    version_str = "unknown"
    try:
        version_str = debugger.GetVersionString().splitlines()[0]
    except Exception:
        pass
    version = parse_lldb_version(version_str)

    register_commands(debugger)

    load_settings(SETTINGS)
    _set_prompt(debugger)
    capture_defaults(debugger)
    if SETTINGS.auto_context:
        apply_quiet(debugger)
    else:
        restore_defaults(debugger)
    if SETTINGS.auto_context:
        ensure_stop_hook(debugger, "context")
    banner(f"loaded ({version.variant} lldb-{version.major}.{version.minor})")
