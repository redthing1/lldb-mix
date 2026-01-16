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
        ascii_bytes = "".join(chr(b) if 0x20 <= b <= 0x7E else "." for b in chunk)
        pad = " " * (bytes_per_line * 3 - 1 - len(hex_bytes))
        addr_text = f"0x{base_addr + offset:016x}"
        if colorize:
            addr_text = colorize(addr_text, "addr")
            hex_bytes = colorize(hex_bytes, "byte")
            ascii_bytes = colorize(ascii_bytes, "muted")
        line = f"{addr_text}: {hex_bytes}{pad}  {ascii_bytes}"
        lines.append(line)
    return lines


def hexdump_words(
    data: bytes,
    base_addr: int,
    word_size: int = 2,
    bytes_per_line: int = 16,
    colorize: Callable[[str, str], str] | None = None,
) -> list[str]:
    if word_size <= 0:
        word_size = 1
    words_per_line = max(1, bytes_per_line // word_size)
    bytes_per_line = words_per_line * word_size
    word_width = word_size * 2
    total_hex_len = words_per_line * word_width + max(words_per_line - 1, 0)

    lines: list[str] = []
    for offset in range(0, len(data), bytes_per_line):
        chunk = data[offset : offset + bytes_per_line]
        words: list[str] = []
        for word_offset in range(0, bytes_per_line, word_size):
            word_bytes = chunk[word_offset : word_offset + word_size]
            if len(word_bytes) < word_size:
                words.append(" " * word_width)
                continue
            value = int.from_bytes(word_bytes, byteorder="little")
            words.append(f"{value:0{word_width}x}")
        hex_words = " ".join(words)
        pad = " " * max(total_hex_len - len(hex_words), 0)
        ascii_bytes = "".join(chr(b) if 0x20 <= b <= 0x7E else "." for b in chunk)
        ascii_bytes += " " * (bytes_per_line - len(chunk))
        addr_text = f"0x{base_addr + offset:016x}"
        if colorize:
            addr_text = colorize(addr_text, "addr")
            hex_words = colorize(hex_words, "byte")
            ascii_bytes = colorize(ascii_bytes, "muted")
        line = f"{addr_text}: {hex_words}{pad}  {ascii_bytes}"
        lines.append(line)
    return lines
