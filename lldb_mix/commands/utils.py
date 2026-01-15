from __future__ import annotations


def emit_result(result, message: str, lldb_module) -> None:
    try:
        result.PutCString(message)
        result.SetStatus(lldb_module.eReturnStatusSuccessFinishResult)
    except Exception:
        print(message)


def module_fullpath(module) -> str:
    if not module:
        return ""
    try:
        file_obj = getattr(module, "file", None)
        if file_obj:
            path = getattr(file_obj, "fullpath", "") or ""
            if path:
                return path
    except Exception:
        pass

    try:
        spec = module.GetFileSpec()
    except Exception:
        return ""

    filename = _filespec_get_filename(spec)
    directory = _filespec_get_directory(spec)
    if directory and filename:
        return f"{directory}/{filename}"
    return filename or ""


def parse_int(text: str) -> int | None:
    try:
        return int(text, 0)
    except ValueError:
        return None


def default_addr(regs: dict[str, int]) -> int | None:
    for name in ("sp", "rsp", "esp"):
        if name in regs and regs[name]:
            return regs[name]
    for name in ("pc", "rip", "eip"):
        if name in regs and regs[name]:
            return regs[name]
    return None


def resolve_addr(token: str, regs: dict[str, int]) -> int | None:
    cleaned = token.strip()
    if cleaned.startswith("$"):
        cleaned = cleaned[1:]
    key = cleaned.lower()
    if key == "sp":
        return _pick_reg(("sp", "rsp", "esp"), regs)
    if key == "pc":
        return _pick_reg(("pc", "rip", "eip"), regs)
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
        return int(value.GetValueAsUnsigned())
    except Exception:
        try:
            raw = value.GetValue()
            return int(raw, 0) if raw else None
        except Exception:
            return None


def _pick_reg(candidates: tuple[str, ...], regs: dict[str, int]) -> int | None:
    for name in candidates:
        value = regs.get(name)
        if value:
            return value
    return None


def _filespec_get_filename(spec) -> str:
    if not spec:
        return ""
    try:
        return spec.GetFilename() or ""
    except Exception:
        return ""


def _filespec_get_directory(spec) -> str:
    if not spec:
        return ""
    try:
        return spec.GetDirectory() or ""
    except Exception:
        return ""
