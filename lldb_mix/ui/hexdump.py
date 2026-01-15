from __future__ import annotations

from typing import Callable


def hexdump(
    data: bytes,
    base_addr: int,
    bytes_per_line: int = 16,
    colorize: Callable[[str, str], str] | None = None,
) -> list[str]:
    lines: list[str] = []
    for offset in range(0, len(data), bytes_per_line):
        chunk = data[offset : offset + bytes_per_line]
        hex_bytes = " ".join(f"{b:02x}" for b in chunk)
        ascii_bytes = "".join(chr(b) if 0x20 <= b <= 0x7e else "." for b in chunk)
        pad = " " * (bytes_per_line * 3 - 1 - len(hex_bytes))
        addr_text = f"0x{base_addr + offset:016x}"
        if colorize:
            addr_text = colorize(addr_text, "addr")
            hex_bytes = colorize(hex_bytes, "byte")
            ascii_bytes = colorize(ascii_bytes, "muted")
        line = f"{addr_text}: {hex_bytes}{pad}  {ascii_bytes}"
        lines.append(line)
    return lines
