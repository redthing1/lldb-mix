from __future__ import annotations

from dataclasses import replace

from lldb_mix.context.panes.base import Pane
from lldb_mix.context.types import PaneContext
from lldb_mix.ui.ansi import strip_ansi

COLUMN_GAP = 2
MIN_COLUMN_WIDTH = 60
MAX_COLUMNS = 2


def layout_panes(panes: list[Pane], term_width: int) -> list[list[Pane]]:
    allow_columns = term_width >= (MIN_COLUMN_WIDTH * MAX_COLUMNS + COLUMN_GAP)
    rows: list[list[Pane]] = []
    current: list[Pane] = []

    for pane in panes:
        if pane.full_width or not allow_columns:
            if current:
                rows.append(current)
                current = []
            rows.append([pane])
            continue
        current.append(pane)
        if len(current) >= MAX_COLUMNS:
            rows.append(current)
            current = []

    if current:
        rows.append(current)
    return rows


def render_rows(rows: list[list[Pane]], ctx: PaneContext) -> list[str]:
    lines: list[str] = []
    for row_idx, row in enumerate(rows):
        if row_idx:
            lines.append("")
        if len(row) == 1:
            lines.extend(row[0].render(ctx))
            continue
        col_width = _column_width(ctx.term_width, len(row))
        lines.extend(_render_row(row, ctx, col_width))
    return lines


def _column_width(term_width: int, cols: int) -> int:
    usable = max(term_width - COLUMN_GAP * (cols - 1), 1)
    return max(1, usable // cols)


def _render_row(row: list[Pane], ctx: PaneContext, col_width: int) -> list[str]:
    rendered: list[list[str]] = []
    widths: list[int] = []
    heights: list[int] = []
    for pane in row:
        sub_ctx = replace(ctx, term_width=col_width)
        pane_lines = pane.render(sub_ctx)
        rendered.append(pane_lines)
        max_width = max((_visible_len(line) for line in pane_lines), default=0)
        widths.append(max(col_width, max_width))
        heights.append(len(pane_lines))

    row_height = max(heights, default=0)
    padded_blocks: list[list[str]] = []
    for pane_lines, width in zip(rendered, widths):
        padded = [_pad_line(line, width) for line in pane_lines]
        if len(padded) < row_height:
            padded.extend([" " * width] * (row_height - len(padded)))
        padded_blocks.append(padded)

    joined: list[str] = []
    gap = " " * COLUMN_GAP
    for idx in range(row_height):
        line = gap.join(block[idx] for block in padded_blocks).rstrip()
        joined.append(line)
    return joined


def _visible_len(text: str) -> int:
    return len(strip_ansi(text))


def _pad_line(text: str, width: int) -> str:
    length = _visible_len(text)
    if length >= width:
        return text
    return text + (" " * (width - length))
