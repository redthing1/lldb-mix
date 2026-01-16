from __future__ import annotations

from typing import Any

_SETTINGS = (
    "stop-disassembly-display",
    "stop-disassembly-count",
    "stop-line-count-before",
    "stop-line-count-after",
    "thread-stop-format",
    "thread-format",
    "frame-format",
)

_QUIET_VALUES = {
    "stop-disassembly-display": "never",
    "stop-disassembly-count": "0",
    "stop-line-count-before": "0",
    "stop-line-count-after": "0",
    "thread-stop-format": "\"\"",
    "thread-format": "\"\"",
    "frame-format": "\"\"",
}

_DEFAULTS: dict[str, str] | None = None
_SAVED: dict[str, str] | None = None


def _run_command(debugger: Any, command: str) -> str:
    try:
        import lldb
    except Exception:
        return ""

    res = lldb.SBCommandReturnObject()
    debugger.GetCommandInterpreter().HandleCommand(command, res)
    return (res.GetOutput() or "") + (res.GetError() or "")


def _parse_setting_value(output: str) -> str | None:
    for line in output.splitlines():
        if "=" not in line:
            continue
        return line.split("=", 1)[1].strip()
    return None


def _read_settings(debugger: Any) -> dict[str, str]:
    values: dict[str, str] = {}
    for name in _SETTINGS:
        value = _parse_setting_value(_run_command(debugger, f"settings show {name}"))
        if value is not None:
            values[name] = value
    return values


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
    for command in (
        "settings set stop-disassembly-display never",
        "settings set stop-disassembly-count 0",
        "settings set stop-line-count-before 0",
        "settings set stop-line-count-after 0",
        "settings set -- thread-stop-format \"\"",
        "settings set -- thread-format \"\"",
        "settings set -- frame-format \"\"",
    ):
        _run_command(debugger, command)


def restore_defaults(debugger: Any) -> None:
    global _SAVED
    current = _read_settings(debugger)
    if current and not _is_quiet(current):
        _SAVED = None
        return
    values = _SAVED or _DEFAULTS
    if not values:
        return
    for name, value in values.items():
        _run_command(debugger, f"settings set -- {name} {value}")
    _SAVED = None


def _is_quiet(values: dict[str, str]) -> bool:
    for name, quiet_value in _QUIET_VALUES.items():
        current = values.get(name)
        if current is None:
            return False
        if current != quiet_value:
            return False
    return True
