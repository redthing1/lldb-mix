from __future__ import annotations

from typing import Any

from lldb_mix.core.lldb_settings import read_settings, set_settings
from lldb_mix.core.settings import Settings
from lldb_mix.ui.lldb_format import format_lldb
from lldb_mix.ui.theme import Theme, get_theme

_FORMAT_KEYS = (
    "thread-format",
    "frame-format",
    "thread-stop-format",
)

_DEFAULTS: dict[str, str] | None = None


def _read_settings(debugger: Any) -> dict[str, str]:
    return read_settings(debugger, _FORMAT_KEYS)


def capture_defaults(debugger: Any) -> None:
    global _DEFAULTS
    if _DEFAULTS is None:
        _DEFAULTS = _read_settings(debugger)


def apply_formats(debugger: Any, theme: Theme, enable_color: bool) -> None:
    set_settings(debugger, format_lldb(theme, enable_color), quoted=True)


def restore_defaults(debugger: Any) -> None:
    if not _DEFAULTS:
        return
    set_settings(debugger, _DEFAULTS, quoted=True)


def sync_formats(debugger: Any, settings: Settings) -> None:
    capture_defaults(debugger)
    if settings.lldb_formats:
        apply_formats(debugger, get_theme(settings.theme), settings.enable_color)
    else:
        restore_defaults(debugger)
