from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SymbolInfo:
    name: str
    module: str
    offset: int


class TargetSymbolResolver:
    def __init__(self, target: Any):
        self.target = target

    def resolve(self, addr: int) -> SymbolInfo | None:
        return resolve_symbol(self.target, addr)


def resolve_symbol(target: Any, address: int) -> SymbolInfo | None:
    try:
        import lldb
    except Exception:
        return None

    if not target or not target.IsValid():
        return None

    sb_addr = lldb.SBAddress()
    sb_addr.SetLoadAddress(address, target)
    symbol = sb_addr.GetSymbol()
    if not symbol or not symbol.IsValid():
        return None

    name = symbol.GetName() or ""
    if not name:
        return None

    module = ""
    mod = sb_addr.GetModule()
    if mod and mod.IsValid():
        spec = mod.GetFileSpec()
        module = spec.GetFilename() if spec else ""

    start = symbol.GetStartAddress().GetLoadAddress(target)
    offset = address - start if start != lldb.LLDB_INVALID_ADDRESS else 0

    return SymbolInfo(name=name, module=module, offset=offset)
