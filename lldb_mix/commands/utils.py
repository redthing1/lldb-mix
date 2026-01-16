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


def parse_int(text: str) -> int | None:
    try:
        return int(text, 0)
    except ValueError:
        return None


def default_addr(regs: dict[str, int]) -> int | None:
    sp = _pick_reg(("sp", "rsp", "esp"), regs, require_nonzero=True)
    if sp is not None:
        return sp
    pc = _pick_reg(("pc", "rip", "eip"), regs, require_nonzero=True)
    if pc is not None:
        return pc
    sp = _pick_reg(("sp", "rsp", "esp"), regs, require_nonzero=False)
    if sp is not None:
        return sp
    return _pick_reg(("pc", "rip", "eip"), regs, require_nonzero=False)


def resolve_addr(token: str, regs: dict[str, int]) -> int | None:
    cleaned = token.strip()
    if cleaned.startswith("$"):
        cleaned = cleaned[1:]
    key = cleaned.lower()
    if key == "sp":
        return _pick_reg(("sp", "rsp", "esp"), regs, require_nonzero=False)
    if key == "pc":
        return _pick_reg(("pc", "rip", "eip"), regs, require_nonzero=False)
    if key in regs:
        return regs[key]
    parsed = parse_int(cleaned)
    if parsed is not None:
        return parsed
    return None


def eval_expression(frame, expr: str) -> int | None:
    if not frame or not expr:
        return None
    try:
        value = frame.EvaluateExpression(expr)
    except Exception:
        return None
    if not value or not value.IsValid():
        return None
    try:
        error = value.GetError()
        if error and not error.Success():
            return None
    except Exception:
        pass
    try:
        return int(value.GetValueAsUnsigned())
    except Exception:
        try:
            raw = value.GetValue()
            return int(raw, 0) if raw else None
        except Exception:
            return None


def _pick_reg(
    candidates: tuple[str, ...],
    regs: dict[str, int],
    require_nonzero: bool,
) -> int | None:
    for name in candidates:
        if name not in regs:
            continue
        value = regs[name]
        if require_nonzero and value == 0:
            continue
        return value
    return None
