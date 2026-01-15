from __future__ import annotations

from lldb_mix.ui.ansi import RESET, escape
from lldb_mix.ui.theme import Theme


def colorize(text: str, role: str, theme: Theme, enabled: bool) -> str:
    if not enabled:
        return text
    tokens = theme.colors.get(role)
    if not tokens:
        return text
    prefix = escape(tokens)
    if not prefix:
        return text
    return f"{prefix}{text}{RESET}"
