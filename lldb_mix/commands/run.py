from __future__ import annotations

from lldb_mix.commands.utils import emit_result


def cmd_rr(debugger, command, result, internal_dict) -> None:
    try:
        import lldb
    except Exception:
        print("[lldb-mix] rr not available outside LLDB")
        return

    launch_cmd = _build_launch_cmd(command)

    res = lldb.SBCommandReturnObject()
    was_async = None
    try:
        was_async = debugger.GetAsync()
        debugger.SetAsync(False)
    except Exception:
        was_async = None
    try:
        debugger.GetCommandInterpreter().HandleCommand(launch_cmd, res)
    finally:
        if was_async is not None:
            try:
                debugger.SetAsync(was_async)
            except Exception:
                pass

    if not res.Succeeded():
        err = res.GetError() or "unknown error"
        emit_result(result, f"[lldb-mix] rr failed: {err}", lldb)
        return

    output = res.GetOutput()
    if output:
        emit_result(result, output.rstrip(), lldb)
        return

    try:
        result.SetStatus(lldb.eReturnStatusSuccessFinishResult)
    except Exception:
        pass


def _build_launch_cmd(command: str) -> str:
    args = command.strip()
    launch_cmd = "process launch -s -X true --"
    if args:
        return f"{launch_cmd} {args}"
    return launch_cmd
