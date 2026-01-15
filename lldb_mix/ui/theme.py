from __future__ import annotations

from dataclasses import dataclass

from lldb_mix.ui.ansi import AnsiToken, Color, Style


@dataclass(frozen=True)
class Theme:
    name: str
    colors: dict[str, tuple[AnsiToken, ...]]


def _t(*tokens: AnsiToken) -> tuple[AnsiToken, ...]:
    return tokens


BASE_THEME = Theme(
    name="base",
    colors={
        "title": _t(Style.BOLD, Color.BRIGHT_CYAN),
        "label": _t(Color.BRIGHT_BLACK),
        "muted": _t(Color.BRIGHT_BLACK),
        "separator": _t(Color.BRIGHT_BLACK),
        "reg_name": _t(Color.BRIGHT_GREEN),
        "reg_value": _t(Color.BRIGHT_WHITE),
        "reg_changed": _t(Style.BOLD, Color.BRIGHT_YELLOW),
        "value": _t(Color.BRIGHT_WHITE),
        "addr": _t(Color.CYAN),
        "symbol": _t(Color.BRIGHT_MAGENTA),
        "string": _t(Color.GREEN),
        "arrow": _t(Color.BRIGHT_BLACK),
        "pc_marker": _t(Style.BOLD, Color.BRIGHT_RED),
        "mnemonic": _t(Color.BRIGHT_WHITE),
        "opcode": _t(Color.BRIGHT_BLACK),
        "comment": _t(Color.BRIGHT_BLACK),
        "byte": _t(Color.BRIGHT_BLACK),
    },
)


LRT_DARK = Theme(
    name="lrt-dark",
    colors={
        "title": _t(Style.BOLD, Color.CYAN),
        "label": _t(Color.BRIGHT_BLACK),
        "muted": _t(Color.BRIGHT_BLACK),
        "separator": _t(Color.BRIGHT_BLACK),
        "reg_name": _t(Color.GREEN),
        "reg_value": _t(Color.WHITE),
        "reg_changed": _t(Color.RED),
        "value": _t(Color.WHITE),
        "addr": _t(Color.WHITE),
        "symbol": _t(Color.BLUE),
        "string": _t(Color.GREEN),
        "arrow": _t(Color.BRIGHT_BLACK),
        "pc_marker": _t(Color.RED),
        "mnemonic": _t(Color.WHITE),
        "opcode": _t(Color.WHITE),
        "comment": _t(Color.GREEN),
        "byte": _t(Color.WHITE),
    },
)


THEMES = {
    BASE_THEME.name: BASE_THEME,
    LRT_DARK.name: LRT_DARK,
}

DEFAULT_THEME = BASE_THEME


def get_theme(name: str) -> Theme:
    return THEMES.get(name, DEFAULT_THEME)
