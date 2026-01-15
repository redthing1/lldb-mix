from __future__ import annotations

import os
from typing import Any


def module_fullpath(module: Any) -> str:
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
    return _filespec_path(spec)


def module_name(module: Any) -> str:
    if not module:
        return ""
    try:
        spec = module.GetFileSpec()
        if spec:
            name = spec.GetFilename() or ""
            if name:
                return name
    except Exception:
        pass
    path = module_fullpath(module)
    return os.path.basename(path) if path else ""


def module_for_address(target: Any, addr: int):
    try:
        import lldb
    except Exception:
        return None
    if not target or not target.IsValid():
        return None
    try:
        sbaddr = lldb.SBAddress(addr, target)
        module = sbaddr.GetModule()
        if module and module.IsValid():
            return module
    except Exception:
        return None
    return None


def module_base(target: Any, module: Any, lldb_module=None) -> int | None:
    invalid = 0xFFFFFFFFFFFFFFFF
    if lldb_module is None:
        try:
            import lldb

            lldb_module = lldb
        except Exception:
            lldb_module = None
    if lldb_module is not None:
        invalid = getattr(lldb_module, "LLDB_INVALID_ADDRESS", invalid)

    header = module.GetObjectFileHeaderAddress()
    if header and header.IsValid():
        base = header.GetLoadAddress(target)
        if base not in (invalid, 0xFFFFFFFFFFFFFFFF):
            return base
    section = module.GetSectionAtIndex(0)
    if section and section.IsValid():
        base = section.GetLoadAddress(target)
        if base not in (invalid, 0xFFFFFFFFFFFFFFFF):
            return base
    return None


def find_module(target: Any, token: str):
    for module in target.module_iter():
        name = module_name(module)
        path = module_fullpath(module)
        if token == name or token == path:
            return module
        if path and path.endswith(f"/{token}"):
            return module
    return None


def module_offset(target: Any, addr: int) -> tuple[str, int] | None:
    module = module_for_address(target, addr)
    if not module:
        return None
    base = module_base(target, module)
    if base is None or addr < base:
        return None
    name = module_name(module) or module_fullpath(module)
    if not name:
        return None
    return name, addr - base


def format_module_offset(target: Any, addr: int) -> str | None:
    info = module_offset(target, addr)
    if not info:
        return None
    name, offset = info
    return f"{name}+0x{offset:x}"


def _filespec_path(spec: Any) -> str:
    if not spec:
        return ""
    try:
        path = spec.GetPath() or ""
    except Exception:
        path = ""
    if path:
        return path
    try:
        filename = spec.GetFilename() or ""
    except Exception:
        filename = ""
    try:
        directory = spec.GetDirectory() or ""
    except Exception:
        directory = ""
    if directory and filename:
        return f"{directory}/{filename}"
    return filename
