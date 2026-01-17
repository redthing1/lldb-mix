from __future__ import annotations

from typing import Any

from lldb_mix.ui.ansi import RESET

CONTEXT_STOP_HOOK_CLASS = "lldb_mix.core.stop_hooks.ContextStopHook"


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


def find_stop_hook_classes(output: str, class_name: str) -> list[int]:
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
        if class_name in stripped:
            ids.append(current_id)
    return ids


def ensure_stop_hook(debugger: Any, command: str) -> None:
    output = _run_command(debugger, "target stop-hook list")
    if command == "context":
        if find_stop_hook_classes(output, CONTEXT_STOP_HOOK_CLASS):
            return
        for hook_id in find_stop_hooks(output, command):
            _run_command(debugger, f"target stop-hook delete {hook_id}")
        _run_command(
            debugger,
            f"target stop-hook add -P {CONTEXT_STOP_HOOK_CLASS}",
        )
        return
    if find_stop_hooks(output, command):
        return
    _run_command(debugger, f"target stop-hook add -o '{command}'")


def remove_stop_hook(debugger: Any, command: str) -> None:
    output = _run_command(debugger, "target stop-hook list")
    if command == "context":
        for hook_id in find_stop_hook_classes(output, CONTEXT_STOP_HOOK_CLASS):
            _run_command(debugger, f"target stop-hook delete {hook_id}")
    for hook_id in find_stop_hooks(output, command):
        _run_command(debugger, f"target stop-hook delete {hook_id}")


class ContextStopHook:
    def __init__(self, target, extra_args, internal_dict) -> None:
        self.target = target
        self.extra_args = extra_args
        self.internal_dict = internal_dict

    def handle_stop(self, exe_ctx, stream) -> bool:
        try:
            import lldb
        except Exception:
            return True

        debugger = None
        try:
            debugger = exe_ctx.GetTarget().GetDebugger()
        except Exception:
            debugger = None
        if debugger is None:
            debugger = getattr(lldb, "debugger", None)
        if debugger is None:
            return True

        try:
            from lldb_mix.commands.context import render_context
        except Exception:
            return True

        try:
            output = render_context(debugger)
        except Exception:
            return True
        if output:
            if not output.endswith("\n"):
                output += "\n"
            output += RESET
            try:
                stream.Print(output)
            except Exception:
                pass
        return True
