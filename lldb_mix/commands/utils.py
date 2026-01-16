from __future__ import annotations

from lldb_mix.core.modules import module_fullpath as _module_fullpath


def emit_result(result, message: str, lldb_module) -> None:
    try:
        result.PutCString(message)
        result.SetStatus(lldb_module.eReturnStatusSuccessFinishResult)
    except Exception:
        print(message)


def module_fullpath(module) -> str:
    return _module_fullpath(module)


__all__ = ["emit_result", "module_fullpath"]
