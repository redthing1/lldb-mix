from __future__ import annotations

from lldb_mix.ui.ansi import AnsiToken, Color, Style
from lldb_mix.ui.theme import Theme

_LLDB_NORMAL = "${ansi.normal}"

_STYLE_NAMES = {
    Style.BOLD: "bold",
    Style.DIM: "faint",
    Style.ITALIC: "italic",
    Style.UNDERLINE: "underline",
    Style.REVERSE: "reverse",
}

_ROLE_MAP = {
    "pc": "addr",
    "file": "addr",
    "line": "reg_changed",
    "thread": "string",
    "stop": "pc_marker",
}

def format_lldb(theme: Theme, enable_color: bool) -> dict[str, str]:
    def color(role: str, text: str) -> str:
        prefix = _theme_prefix(theme, role, enable_color)
        if not prefix:
            return text
        return f"{prefix}{text}{_LLDB_NORMAL}"

    file_text = color("file", "${line.file.basename}")
    line_text = color("line", "${line.number}")
    col_text = color("line", "${line.column}")
    file_loc = file_text + ":" + line_text + "{:" + col_text + "}"

    thread_name = color("thread", "'${thread.name}'")
    thread_queue = color("thread", "'${thread.queue}'")
    thread_activity = color("thread", "'${thread.info.activity.name}'")
    stop_reason = color("stop", "${thread.stop-reason}")
    frame_pc = color("pc", "${frame.pc}")

    thread_format = (
        "thread #${thread.index}: tid = ${thread.id%tid}"
        "{, ${frame.pc}}"
        "{ ${module.file.basename}{`${function.name-with-args}{${frame.no-debug}${function.pc-offset}}}}"
        "{ at "
        + file_loc
        + "}"
        "{, name = "
        + thread_name
        + "}"
        "{, queue = "
        + thread_queue
        + "}"
        "{, activity = "
        + thread_activity
        + "}"
        "{, ${thread.info.trace_messages} messages}"
        "{, stop reason = "
        + stop_reason
        + "}"
        "{\nReturn value: ${thread.return-value}}"
        "{\nCompleted expression: ${thread.completed-expression}}\n"
    )

    frame_format = (
        "frame #${frame.index}: "
        + frame_pc
        + "{ ${module.file.basename}{`${function.name-with-args}{${frame.no-debug}${function.pc-offset}}}}"
        "{ at "
        + file_loc
        + "}"
        "{${function.is-optimized} [opt]}{${function.is-inlined} [inlined]}"
        "{${frame.is-artificial} [artificial]}\n"
    )

    thread_stop_format = (
        "thread #${thread.index}"
        "{, name = '${thread.name}'}"
        "{, queue = "
        + thread_queue
        + "}"
        "{, activity = "
        + thread_activity
        + "}"
        "{, ${thread.info.trace_messages} messages}"
        "{, stop reason = "
        + stop_reason
        + "}"
        "{\nReturn value: ${thread.return-value}}"
        "{\nCompleted expression: ${thread.completed-expression}}\n"
    )

    return {
        "thread-format": thread_format,
        "frame-format": frame_format,
        "thread-stop-format": thread_stop_format,
    }


def _theme_prefix(theme: Theme, role: str, enable_color: bool) -> str:
    if not enable_color:
        return ""
    tokens = theme.colors.get(_ROLE_MAP[role])
    if not tokens:
        return ""
    return _prefix_from_tokens(tokens)


def _prefix_from_tokens(tokens: tuple[AnsiToken, ...]) -> str:
    styles: list[Style] = []
    fg: Color | None = None
    bg: Color | None = None
    for token in tokens:
        if isinstance(token, Style):
            styles.append(token)
        elif isinstance(token, Color):
            if token.name.startswith("BG_"):
                bg = token
            else:
                fg = token

    style_set = dict.fromkeys(styles)
    parts: list[str] = []

    if fg is not None:
        bright, fg_name = _color_name(fg)
        if bright and Style.BOLD not in style_set:
            style_set[Style.BOLD] = None
        if fg_name:
            parts.append(_ansi_fg(fg_name))

    if bg is not None:
        bright, bg_name = _color_name(bg)
        if bright and Style.BOLD not in style_set:
            style_set[Style.BOLD] = None
        if bg_name:
            parts.append(_ansi_bg(bg_name))

    for style in style_set:
        name = _STYLE_NAMES.get(style)
        if name:
            parts.append(_ansi_style(name))

    return "".join(parts)


def _ansi_style(name: str) -> str:
    return f"${{ansi.{name}}}"


def _ansi_fg(name: str) -> str:
    return f"${{ansi.fg.{name}}}"


def _ansi_bg(name: str) -> str:
    return f"${{ansi.bg.{name}}}"


def _color_name(token: Color) -> tuple[bool, str | None]:
    name = token.name
    if name.startswith("BG_"):
        name = name[3:]
    bright = name.startswith("BRIGHT_")
    if bright:
        name = name[7:]
    if name in {"BLACK", "RED", "GREEN", "YELLOW", "BLUE", "MAGENTA", "CYAN", "WHITE"}:
        return bright, name.lower()
    return bright, None
