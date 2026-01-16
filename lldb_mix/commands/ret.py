from __future__ import annotations

import shlex

from lldb_mix.commands.context import render_context_if_enabled
from lldb_mix.commands.utils import emit_result
from lldb_mix.core.addressing import eval_expression, parse_int
from lldb_mix.core.regs import set_register_value
from lldb_mix.core.session import Session


def cmd_ret(debugger, command, result, internal_dict) -> None:
    try:
        import lldb
    except Exception:
        print("[lldb-mix] ret not available outside LLDB")
        return

    args = shlex.split(command)
    if args and args[0] in ("-h", "--help", "help"):
        emit_result(result, _usage(), lldb)
        return
    if len(args) > 1:
        emit_result(result, _usage(), lldb)
        return

    session = Session(debugger)
    thread = session.thread()
    frame = session.frame()
    if not thread or not frame:
        emit_result(result, "[lldb-mix] frame unavailable", lldb)
        return

    arch = session.arch()
    reg = arch.find_return_register(frame)
    if not reg:
        emit_result(result, "[lldb-mix] return register unavailable", lldb)
        return

    value_text = ""
    if args:
        value = parse_int(args[0])
        if value is None:
            value = eval_expression(frame, args[0])
        if value is None:
            emit_result(result, "[lldb-mix] invalid return value", lldb)
            return
        value_text = format(value, "#x")
        if not set_register_value(reg, value_text):
            emit_result(result, "[lldb-mix] failed to set return value", lldb)
            return

    if not thread.ReturnFromFrame(frame, reg):
        emit_result(result, "[lldb-mix] return failed", lldb)
        return

    message = "[lldb-mix] ret"
    if value_text:
        message += f" value={value_text}"
    context_text = render_context_if_enabled(debugger)
    if context_text:
        message = f"{message}\n{context_text}"
    emit_result(result, message, lldb)


def _usage() -> str:
    return "[lldb-mix] usage: ret [value]"
