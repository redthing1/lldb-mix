from __future__ import annotations

import shlex

from lldb_mix.commands.utils import emit_result, eval_expression, parse_int
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
    reg_name = getattr(arch, "return_reg", None)
    if not reg_name:
        emit_result(result, "[lldb-mix] return register unavailable", lldb)
        return

    reg = _find_register(frame, reg_name)
    if not reg:
        emit_result(result, "[lldb-mix] return register missing", lldb)
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
        if not _set_reg_value(reg, value_text):
            emit_result(result, "[lldb-mix] failed to set return value", lldb)
            return

    if not thread.ReturnFromFrame(frame, reg):
        emit_result(result, "[lldb-mix] return failed", lldb)
        return

    message = "[lldb-mix] ret"
    if value_text:
        message += f" value={value_text}"
    emit_result(result, message, lldb)


def _find_register(frame, name: str):
    try:
        reg = frame.FindRegister(name)
        if reg and reg.IsValid():
            return reg
    except Exception:
        pass
    try:
        reg_sets = frame.GetRegisters()
    except Exception:
        return None
    for reg_set in reg_sets:
        for reg in reg_set:
            if (reg.GetName() or "").lower() == name.lower():
                return reg
    return None


def _set_reg_value(reg, value: str) -> bool:
    try:
        return bool(reg.SetValueFromCString(value))
    except Exception:
        return False


def _usage() -> str:
    return "[lldb-mix] usage: ret [value]"
