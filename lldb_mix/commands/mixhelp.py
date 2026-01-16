from __future__ import annotations

import shlex

from lldb_mix.commands.registry import COMMANDS
from lldb_mix.commands.utils import emit_result
from lldb_mix.core.state import SETTINGS
from lldb_mix.ui.style import colorize
from lldb_mix.ui.table import Column, render_table
from lldb_mix.ui.terminal import get_terminal_size
from lldb_mix.ui.theme import get_theme


def cmd_mixhelp(debugger, command, result, internal_dict) -> None:
    try:
        import lldb
    except Exception:
        print("[lldb-mix] mixhelp not available outside LLDB")
        return

    args = shlex.split(command)
    if args and args[0] in ("-h", "--help", "help"):
        emit_result(result, _usage(), lldb)
        return

    verbose, pattern, error = _parse_args(args)
    if error:
        emit_result(result, f"[lldb-mix] {error}\n{_usage()}", lldb)
        return

    theme = get_theme(SETTINGS.theme)
    term_width, _ = get_terminal_size()

    def _style(text: str, role: str) -> str:
        return colorize(text, role, theme, SETTINGS.enable_color)

    rows = _command_rows(pattern)
    if pattern:
        header = _style(f"[lldb-mix] commands matching '{pattern}'", "title")
    else:
        header = _style("[lldb-mix] commands:", "title")

    if not rows:
        emit_result(result, f"{header}\n{_style('(none)', 'muted')}", lldb)
        return

    columns = [
        Column("name", "NAME", role="label"),
        Column("aliases", "ALIASES", role="symbol", optional=True, priority=2),
        Column(
            "help",
            "HELP",
            role="value",
            optional=True,
            priority=3,
            weight=2.0,
        ),
    ]
    if verbose:
        columns.append(
            Column(
                "handler",
                "HANDLER",
                role="muted",
                optional=True,
                priority=1,
                truncate="left",
            )
        )

    lines = [header]
    lines.extend(render_table(rows, columns, term_width, _style))
    emit_result(result, "\n".join(lines), lldb)


def _parse_args(args: list[str]) -> tuple[bool, str | None, str | None]:
    verbose = False
    tokens: list[str] = []
    for arg in args:
        if arg in ("-v", "--verbose"):
            verbose = True
            continue
        if arg.startswith("-"):
            return False, None, f"unknown option: {arg}"
        tokens.append(arg)
    pattern = " ".join(tokens).strip().lower() if tokens else None
    return verbose, pattern or None, None


def _command_rows(pattern: str | None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for spec in COMMANDS:
        aliases = ", ".join(alias.name for alias in spec.aliases)
        row = {
            "name": spec.name,
            "aliases": aliases,
            "help": spec.help,
            "handler": spec.handler,
        }
        if pattern and not _matches(pattern, row):
            continue
        rows.append(row)
    return rows


def _matches(pattern: str, row: dict[str, str]) -> bool:
    for key in ("name", "aliases", "help", "handler"):
        value = row.get(key, "")
        if pattern in value.lower():
            return True
    return False


def _usage() -> str:
    return "[lldb-mix] usage: mixhelp [-v] [pattern]"
