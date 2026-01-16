from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable

from lldb_mix.ui.text import pad_ansi, truncate_ansi, visible_len


StyleFn = Callable[[str, str], str]


@dataclass(frozen=True)
class Column:
    key: str
    label: str
    role: str = "value"
    align: str = "left"
    min_width: int | None = None
    max_width: int | None = None
    optional: bool = False
    truncate: str = "right"
    priority: int = 0
    weight: float = 1.0


@dataclass(frozen=True)
class _ColumnLayout:
    width: int
    min_width: int
    natural_width: int
    max_width: int | None
    priority: int
    optional: bool
    weight: float


def render_table(
    rows: Iterable[dict[str, object]],
    columns: list[Column],
    term_width: int,
    style: StyleFn,
) -> list[str]:
    items = [dict(row) for row in rows]
    if not columns:
        return []

    layout = [_column_layout(items, col) for col in columns]
    active = _drop_optional(layout, term_width)
    layout = _shrink_to_fit(layout, active, term_width)
    layout = _expand_to_fit(layout, active, term_width)

    active_columns = [columns[idx] for idx in active]
    active_layout = [layout[idx] for idx in active]
    table_width = sum(col.width for col in active_layout) + max(len(active) - 1, 0)

    header_parts = []
    for col, spec in zip(active_columns, active_layout):
        header_parts.append(_pad_cell(style(col.label, "label"), spec.width, col.align))
    header = " ".join(header_parts)
    lines = [header, style("-" * max(table_width, 0), "separator")]

    for row in items:
        parts = []
        for col, spec in zip(active_columns, active_layout):
            raw = _stringify(row.get(col.key))
            raw = _truncate(raw, spec.width, col.truncate)
            parts.append(_pad_cell(style(raw, col.role), spec.width, col.align))
        lines.append(" ".join(parts).rstrip())

    return lines


def _stringify(value: object | None) -> str:
    if value is None:
        return ""
    return str(value)


def _column_layout(rows: list[dict[str, object]], col: Column) -> _ColumnLayout:
    natural = len(col.label)
    for row in rows:
        natural = max(natural, len(_stringify(row.get(col.key))))
    min_width = len(col.label) if col.min_width is None else max(col.min_width, len(col.label))
    if col.max_width is not None:
        natural = min(natural, col.max_width)
    width = max(natural, min_width)
    return _ColumnLayout(
        width=width,
        min_width=min_width,
        natural_width=natural,
        max_width=col.max_width,
        priority=col.priority,
        optional=col.optional,
        weight=col.weight,
    )


def _drop_optional(layout: list[_ColumnLayout], term_width: int) -> list[int]:
    active = list(range(len(layout)))
    if term_width <= 0:
        return active

    def _total() -> int:
        return sum(layout[idx].width for idx in active) + max(len(active) - 1, 0)

    while _total() > term_width:
        candidates = [idx for idx in active if layout[idx].optional]
        if not candidates:
            break
        drop_idx = min(candidates, key=lambda idx: (layout[idx].priority, idx))
        active.remove(drop_idx)

    return active


def _shrink_to_fit(
    layout: list[_ColumnLayout],
    active: list[int],
    term_width: int,
) -> list[_ColumnLayout]:
    if term_width <= 0 or not active:
        return layout

    total = sum(layout[idx].width for idx in active) + max(len(active) - 1, 0)
    excess = total - term_width
    if excess <= 0:
        return layout

    order = sorted(active, key=lambda idx: (layout[idx].priority, idx))
    for idx in order:
        if excess <= 0:
            break
        spec = layout[idx]
        shrinkable = spec.width - spec.min_width
        if shrinkable <= 0:
            continue
        shrink = min(shrinkable, excess)
        layout[idx] = _ColumnLayout(
            width=spec.width - shrink,
            min_width=spec.min_width,
            natural_width=spec.natural_width,
            max_width=spec.max_width,
            priority=spec.priority,
            optional=spec.optional,
            weight=spec.weight,
        )
        excess -= shrink

    return layout


def _expand_to_fit(
    layout: list[_ColumnLayout],
    active: list[int],
    term_width: int,
) -> list[_ColumnLayout]:
    if term_width <= 0 or not active:
        return layout

    total = sum(layout[idx].width for idx in active) + max(len(active) - 1, 0)
    extra = term_width - total
    if extra <= 0:
        return layout

    def _capacity(idx: int) -> int:
        return max(layout[idx].natural_width - layout[idx].width, 0)

    while extra > 0:
        candidates = [idx for idx in active if _capacity(idx) > 0]
        if not candidates:
            break
        candidates.sort(key=lambda idx: (-layout[idx].priority, -layout[idx].weight, idx))
        for idx in candidates:
            if extra <= 0:
                break
            if _capacity(idx) <= 0:
                continue
            spec = layout[idx]
            layout[idx] = _ColumnLayout(
                width=spec.width + 1,
                min_width=spec.min_width,
                natural_width=spec.natural_width,
                max_width=spec.max_width,
                priority=spec.priority,
                optional=spec.optional,
                weight=spec.weight,
            )
            extra -= 1

    return layout


def _truncate(text: str, width: int, mode: str) -> str:
    if width <= 0:
        return ""
    if len(text) <= width or mode == "none":
        return text
    if width <= 3:
        return text[:width]
    if mode == "left":
        return "..." + text[-(width - 3) :]
    return text[: width - 3] + "..."


def _pad_cell(text: str, width: int, align: str) -> str:
    if width <= 0:
        return ""
    if visible_len(text) > width:
        text = truncate_ansi(text, width)
    length = visible_len(text)
    if length >= width:
        return text
    padding = width - length
    if align == "right":
        return (" " * padding) + text
    if align == "center":
        left = padding // 2
        right = padding - left
        return (" " * left) + text + (" " * right)
    return pad_ansi(text, width)
