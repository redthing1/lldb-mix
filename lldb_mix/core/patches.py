from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class PatchEntry:
    addr: int
    original: bytes
    patched: bytes

    @property
    def size(self) -> int:
        return len(self.patched)


class PatchStore:
    def __init__(self) -> None:
        self._entries: dict[int, PatchEntry] = {}

    def list(self) -> list[PatchEntry]:
        return [self._entries[key] for key in sorted(self._entries.keys())]

    def get(self, addr: int) -> PatchEntry | None:
        return self._entries.get(addr)

    def add(
        self, addr: int, original: bytes, patched: bytes
    ) -> tuple[bool, str | None]:
        if not patched:
            return False, "patch is empty"
        if addr in self._entries:
            return False, "patch already exists"
        overlap = self._find_overlap(addr, len(patched))
        if overlap is not None:
            return False, f"patch overlaps existing patch at 0x{overlap.addr:x}"
        self._entries[addr] = PatchEntry(addr=addr, original=original, patched=patched)
        return True, None

    def remove(self, addr: int) -> bool:
        return self._entries.pop(addr, None) is not None

    def clear(self) -> None:
        self._entries.clear()

    def _find_overlap(self, addr: int, size: int) -> PatchEntry | None:
        end = addr + size
        for entry in self._entries.values():
            entry_end = entry.addr + entry.size
            if not (end <= entry.addr or addr >= entry_end):
                return entry
        return None


def parse_hex_bytes(text: str) -> bytes | None:
    raw = text.strip()
    if not raw:
        return None
    cleaned = raw.replace("0x", "").replace("0X", "")
    if re.search(r"[^0-9a-fA-F\s,_]", cleaned):
        return None
    cleaned = re.sub(r"[\s,_]+", "", cleaned)
    if not cleaned or len(cleaned) % 2 != 0:
        return None
    try:
        return bytes.fromhex(cleaned)
    except ValueError:
        return None


def format_bytes(data: bytes) -> str:
    return " ".join(f"{byte:02x}" for byte in data)
