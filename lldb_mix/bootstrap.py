from __future__ import annotations

from lldb_mix.commands.registry import register_commands
from lldb_mix.core.config import load_settings
from lldb_mix.core.state import SETTINGS
from lldb_mix.core.stop_hooks import ensure_stop_hook
from lldb_mix.core.stop_output import apply_quiet, capture_defaults, restore_defaults
from lldb_mix.core.version import parse_lldb_version
from lldb_mix.ui.console import banner, err
from lldb_mix.ui.prompt import (
    prompt_ansi_prefix,
    prompt_ansi_suffix,
    prompt_text,
)


def _set_prompt(debugger) -> None:
    try:
        debugger.HandleCommand(f'settings set prompt "{prompt_text()}"')
        debugger.HandleCommand("settings set use-color true")
        debugger.HandleCommand(
            f'settings set prompt-ansi-prefix "{prompt_ansi_prefix()}"'
        )
        debugger.HandleCommand(
            f'settings set prompt-ansi-suffix "{prompt_ansi_suffix()}"'
        )
    except Exception as exc:
        err(f"failed to set prompt: {exc}")


def _set_sync(debugger) -> None:
    try:
        debugger.SetAsync(False)
    except Exception as exc:
        err(f"failed to set sync mode: {exc}")


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
    _set_sync(debugger)
    capture_defaults(debugger)
    if SETTINGS.auto_context:
        apply_quiet(debugger)
    else:
        restore_defaults(debugger)
    if SETTINGS.auto_context:
        ensure_stop_hook(debugger, "context")
    banner(f"loaded ({version.variant} lldb-{version.major}.{version.minor})")
