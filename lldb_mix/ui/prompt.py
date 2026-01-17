from __future__ import annotations

from lldb_mix.ui.ansi import (
    CLEAR_LINE,
    CARRIAGE_RETURN,
    Color,
    RESET,
    Style,
    escape,
)

PROMPT_TEXT = "mix> "
PROMPT_STYLE = (Style.BOLD, Color.CYAN)


def prompt_text() -> str:
    return PROMPT_TEXT


def prompt_ansi_prefix() -> str:
    return f"{CLEAR_LINE}{CARRIAGE_RETURN}{escape(PROMPT_STYLE)}"


def prompt_ansi_suffix() -> str:
    return RESET
