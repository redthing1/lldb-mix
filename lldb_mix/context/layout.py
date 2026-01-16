from __future__ import annotations

from dataclasses import replace

from lldb_mix.context.panes.base import Pane
from lldb_mix.context.types import PaneContext
from lldb_mix.ui.text import pad_ansi, truncate_ansi

COLUMN_GAP = 2
MIN_COLUMN_WIDTH = 60
MAX_COLUMNS = 2


def layout_panes(panes: list[Pane], term_width: int) -> list[list[Pane]]:
    allow_columns = term_width >= (MIN_COLUMN_WIDTH * MAX_COLUMNS + COLUMN_GAP)
    groups: list[list[Pane]] = []
    current: list[Pane] = []

    for pane in panes:
        if pane.full_width or not allow_columns:
            if current:
                groups.append(current)
                current = []
            groups.append([pane])
            continue
        current.append(pane)

    if current:
        groups.append(current)
    return groups


def render_rows(groups: list[list[Pane]], ctx: PaneContext) -> list[str]:
    lines: list[str] = []
    allow_columns = ctx.term_width >= (MIN_COLUMN_WIDTH * MAX_COLUMNS + COLUMN_GAP)
    for idx, group in enumerate(groups):
        if idx:
            lines.append("")
        if len(group) == 1:
            lines.extend(group[0].render(ctx))
            continue
        if allow_columns and _has_column_hints(group):
            lines.extend(_render_columns(group, ctx))
        elif allow_columns:
            lines.extend(_render_row_pairs(group, ctx))
        else:
            lines.extend(_render_single_column(group, ctx))
    return lines


def _column_width(term_width: int, cols: int) -> int:
    usable = max(term_width - COLUMN_GAP * (cols - 1), 1)
    return max(1, usable // cols)


def _render_single_column(group: list[Pane], ctx: PaneContext) -> list[str]:
    lines: list[str] = []
    for pane in group:
        if lines:
            lines.append("")
        lines.extend(pane.render(ctx))
    return lines


def _render_row_pairs(group: list[Pane], ctx: PaneContext) -> list[str]:
    rows: list[list[Pane]] = []
    current: list[Pane] = []
    for pane in group:
        current.append(pane)
        if len(current) >= MAX_COLUMNS:
            rows.append(current)
            current = []
    if current:
        rows.append(current)

    lines: list[str] = []
    for row_idx, row in enumerate(rows):
        if row_idx:
            lines.append("")
        if len(row) == 1:
            lines.extend(row[0].render(ctx))
            continue
        col_width = _column_width(ctx.term_width, len(row))
        blocks = [_render_pane(pane, ctx, col_width) for pane in row]
        lines.extend(_join_columns(blocks, col_width))
    return lines


def _render_columns(group: list[Pane], ctx: PaneContext) -> list[str]:
    columns: dict[int, list[Pane]] = {0: [], 1: []}
    for pane in group:
        col = pane.column if pane.column is not None else _assign_column(columns)
        columns[col].append(pane)

    if not columns[1]:
        return _render_single_column(columns[0], ctx)
    if not columns[0]:
        return _render_single_column(columns[1], ctx)

    col_width = _column_width(ctx.term_width, MAX_COLUMNS)
    left = _render_column(columns[0], ctx, col_width)
    right = _render_column(columns[1], ctx, col_width)
    return _join_columns([left, right], col_width)


def _render_column(panes: list[Pane], ctx: PaneContext, col_width: int) -> list[str]:
    lines: list[str] = []
    for pane in panes:
        if lines:
            lines.append(" " * col_width)
        lines.extend(_render_pane(pane, ctx, col_width))
    return lines


def _render_pane(pane: Pane, ctx: PaneContext, width: int) -> list[str]:
    sub_ctx = replace(ctx, term_width=width)
    pane_lines = pane.render(sub_ctx)
    return [pad_ansi(truncate_ansi(line, width), width) for line in pane_lines]


def _join_columns(blocks: list[list[str]], col_width: int) -> list[str]:
    heights = [len(block) for block in blocks]
    row_height = max(heights, default=0)
    padded_blocks: list[list[str]] = []
    for block in blocks:
        padded = list(block)
        if len(padded) < row_height:
            padded.extend([" " * col_width] * (row_height - len(padded)))
        padded_blocks.append(padded)

    joined: list[str] = []
    gap = " " * COLUMN_GAP
    for idx in range(row_height):
        line = gap.join(block[idx] for block in padded_blocks).rstrip()
        joined.append(line)
    return joined


def _assign_column(columns: dict[int, list[Pane]]) -> int:
    if len(columns[0]) <= len(columns[1]):
        return 0
    return 1


def _has_column_hints(group: list[Pane]) -> bool:
    return any(pane.column is not None for pane in group)

