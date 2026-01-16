from __future__ import annotations

import re

from lldb_mix.ui.ansi import RESET, strip_ansi


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def visible_len(text: str) -> int:
    return len(strip_ansi(text))


def truncate_ansi(text: str, width: int) -> str:
    if width <= 0:
        return ""
    plain = strip_ansi(text)
    if len(plain) <= width:
        return text
    if width <= 3:
        return plain[:width]

    target = width - 3
    out: list[str] = []
    visible = 0
    idx = 0
    had_ansi = False
    while idx < len(text) and visible < target:
        if text[idx] == "\x1b":
            match = _ANSI_RE.match(text, idx)
            if match:
                out.append(match.group(0))
                had_ansi = True
                idx = match.end()
                continue
        out.append(text[idx])
        visible += 1
        idx += 1
    out.append("...")
    if had_ansi:
        out.append(RESET)
    return "".join(out)


def pad_ansi(text: str, width: int) -> str:
    length = visible_len(text)
    if length >= width:
        return text
    return text + (" " * (width - length))
