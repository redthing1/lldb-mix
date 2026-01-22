from __future__ import annotations

from typing import Any

from lldb_mix.core.lldb_settings import read_settings, set_settings

_QUIET_SETTINGS = {
    "stop-disassembly-display": "never",
    "stop-disassembly-count": "0",
    "stop-line-count-before": "0",
    "stop-line-count-after": "0",
}

_DEFAULTS: dict[str, str] | None = None
_SAVED: dict[str, str] | None = None


def _read_settings(debugger: Any) -> dict[str, str]:
    return read_settings(debugger, _QUIET_SETTINGS.keys())


def capture_defaults(debugger: Any) -> None:
    global _DEFAULTS
    if _DEFAULTS is None:
        _DEFAULTS = _read_settings(debugger)


def apply_quiet(debugger: Any) -> None:
    global _SAVED
    if _SAVED is None:
        current = _read_settings(debugger)
        if current and not _is_quiet(current):
            _SAVED = current
    set_settings(debugger, _QUIET_SETTINGS, quoted=False)


def restore_defaults(debugger: Any) -> None:
    global _SAVED
    current = _read_settings(debugger)
    if current and not _is_quiet(current):
        _SAVED = None
        return
    values = _SAVED or _DEFAULTS
    if not values:
        return
    set_settings(debugger, values, quoted=False)
    _SAVED = None


def _is_quiet(values: dict[str, str]) -> bool:
    return all(values.get(name) == quiet_value for name, quiet_value in _QUIET_SETTINGS.items())
