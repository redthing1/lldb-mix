from __future__ import annotations

from dataclasses import dataclass

from lldb_mix.context.types import PaneContext
from lldb_mix.deref import (
    classify_token,
    deref_chain,
    last_addr,
    region_tag,
    summarize_chain,
)


@dataclass(frozen=True)
class DerefSummary:
    text: str
    kind: str
    tag: str | None


def deref_summary(
    ctx: PaneContext,
    value: int,
    ptr_size: int,
    allow_kinds: tuple[str, ...] | None = ("string", "symbol", "region"),
) -> DerefSummary | None:
    if not ctx.settings.aggressive_deref or not ctx.reader:
        return None

    chain = deref_chain(
        value,
        ctx.reader,
        ctx.snapshot.maps,
        ctx.resolver,
        ctx.settings,
        ptr_size,
    )
    summary = summarize_chain(chain)
    if not summary:
        return None
    kind = classify_token(summary)
    if allow_kinds is not None and kind not in allow_kinds:
        return None

    tag = None
    if kind == "symbol":
        tag = region_tag(last_addr(chain), ctx.snapshot.maps)
    return DerefSummary(summary, kind, tag)


def deref_role(kind: str) -> str:
    if kind == "string":
        return "string"
    if kind == "symbol":
        return "symbol"
    if kind == "addr":
        return "addr"
    return "muted"


def format_deref_suffix(pane, ctx: PaneContext, info: DerefSummary) -> str:
    arrow = pane.style(ctx, "->", "arrow")
    summary_text = pane.style(ctx, info.text, deref_role(info.kind))
    suffix = f"{arrow} {summary_text}"
    if info.tag:
        suffix = f"{suffix} {pane.style(ctx, info.tag, 'muted')}"
    return suffix
