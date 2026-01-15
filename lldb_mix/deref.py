from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from lldb_mix.core.memory import MemoryRegion
from lldb_mix.core.settings import Settings
from lldb_mix.core.symbols import SymbolInfo


class MemoryReader(Protocol):
    def read(self, addr: int, size: int) -> bytes | None:
        ...

    def read_pointer(self, addr: int, ptr_size: int) -> int | None:
        ...


class SymbolResolver(Protocol):
    def resolve(self, addr: int) -> SymbolInfo | None:
        ...


def deref_chain(
    addr: int,
    reader: MemoryReader,
    regions: Iterable[MemoryRegion],
    resolver: SymbolResolver | None,
    settings: Settings,
    ptr_size: int,
) -> list[str]:
    if ptr_size <= 0:
        return [format_addr(addr, 1)]
    if addr == 0:
        return [format_addr(addr, ptr_size)]

    chain = [format_addr(addr, ptr_size)]
    seen = set()
    current = addr
    depth = settings.max_deref_depth

    while depth > 0:
        if current in seen:
            chain.append("[loop]")
            break
        seen.add(current)

        region = find_region(current, regions)
        if not region:
            break
        if region.execute:
            if resolver:
                symbol = resolver.resolve(current)
                if symbol:
                    chain.append(format_symbol(symbol))
                    break
            chain.append(format_region(region))
            break
        if not region.read:
            break

        ptr = reader.read_pointer(current, ptr_size)
        if ptr is None:
            break

        chain.append(format_addr(ptr, ptr_size))
        if ptr == 0:
            break

        if resolver:
            symbol = resolver.resolve(ptr)
            if symbol:
                chain.append(format_symbol(symbol))
                break

        target_region = find_region(ptr, regions)
        if target_region and target_region.read and not target_region.execute:
            string_val = read_cstring(reader, ptr, settings.max_string_length)
            if string_val:
                chain.append(f"\"{string_val}\"")
                break

        current = ptr
        depth -= 1

    return chain


def summarize_chain(chain: list[str]) -> str | None:
    if len(chain) <= 1:
        return None
    summary = _pick_best_token(chain[1:])
    if summary == chain[0]:
        return None
    return summary


def classify_token(token: str) -> str:
    if token == "[loop]":
        return "loop"
    if token.startswith("\"") and token.endswith("\""):
        return "string"
    if "!" in token:
        return "symbol"
    if token.startswith("[") and token.endswith("]"):
        return "region"
    if token.startswith("0x"):
        return "addr"
    return "other"


def _pick_best_token(tokens: list[str]) -> str:
    for token in reversed(tokens):
        if classify_token(token) == "string":
            return token
    for token in reversed(tokens):
        if classify_token(token) == "symbol":
            return token
    for token in reversed(tokens):
        if classify_token(token) == "region":
            return token
    return tokens[-1]


def read_cstring(reader: MemoryReader, addr: int, max_len: int) -> str | None:
    data = reader.read(addr, max_len)
    if not data:
        return None

    if b"\x00" in data:
        data = data.split(b"\x00", 1)[0]
    if not data:
        return None

    if not is_printable_ascii(data):
        return None

    try:
        return data.decode("ascii", errors="ignore")
    except Exception:
        return None


def is_printable_ascii(data: bytes) -> bool:
    for byte in data:
        if byte < 0x20 or byte > 0x7e:
            return False
    return True


def find_region(addr: int, regions: Iterable[MemoryRegion]) -> MemoryRegion | None:
    for region in regions:
        if region.contains(addr):
            return region
    return None


def format_addr(addr: int, ptr_size: int) -> str:
    width = max(ptr_size * 2, 1)
    return f"0x{addr:0{width}x}"


def format_symbol(symbol: SymbolInfo) -> str:
    prefix = f"{symbol.module}!" if symbol.module else ""
    if symbol.offset:
        return f"{prefix}{symbol.name}+0x{symbol.offset:x}"
    return f"{prefix}{symbol.name}"


def format_region(region: MemoryRegion) -> str:
    perms = "".join(
        [
            "r" if region.read else "-",
            "w" if region.write else "-",
            "x" if region.execute else "-",
        ]
    )
    name = (region.name or "").strip()
    if name:
        return f"[{perms} {name}]"
    return f"[{perms}]"


def last_addr(chain: list[str]) -> int | None:
    for token in reversed(chain):
        if token.startswith("0x"):
            try:
                return int(token, 16)
            except ValueError:
                continue
    return None


def region_tag(addr: int | None, regions: Iterable[MemoryRegion]) -> str | None:
    if addr is None:
        return None
    region = find_region(addr, regions)
    if not region:
        return None
    if region.execute:
        return format_region(region)
    name = (region.name or "").lower()
    if "stack" in name:
        return format_region(region)
    return None
