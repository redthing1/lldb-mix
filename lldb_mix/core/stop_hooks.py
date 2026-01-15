from __future__ import annotations

from typing import Any


def _run_command(debugger: Any, command: str) -> str:
    try:
        import lldb
    except Exception:
        return ""

    res = lldb.SBCommandReturnObject()
    debugger.GetCommandInterpreter().HandleCommand(command, res)
    return (res.GetOutput() or "") + (res.GetError() or "")


def find_stop_hooks(output: str, command: str) -> list[int]:
    ids: list[int] = []
    current_id: int | None = None
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("Hook:"):
            parts = stripped.split()
            if len(parts) >= 2:
                try:
                    current_id = int(parts[1])
                except ValueError:
                    current_id = None
            continue
        if current_id is None:
            continue
        if stripped and stripped == command:
            ids.append(current_id)
    return ids


def ensure_stop_hook(debugger: Any, command: str) -> None:
    output = _run_command(debugger, "target stop-hook list")
    if find_stop_hooks(output, command):
        return
    _run_command(debugger, f"target stop-hook add -o '{command}'")


def remove_stop_hook(debugger: Any, command: str) -> None:
    output = _run_command(debugger, "target stop-hook list")
    for hook_id in find_stop_hooks(output, command):
        _run_command(debugger, f"target stop-hook delete {hook_id}")
