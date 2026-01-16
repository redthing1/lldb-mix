from __future__ import annotations

from lldb_mix.commands.utils import eval_expression, resolve_addr
from lldb_mix.context.panes.base import Pane
from lldb_mix.context.types import PaneContext
from lldb_mix.deref import (
    classify_token,
    deref_chain,
    format_addr,
    last_addr,
    region_tag,
    summarize_chain,
)


class WatchPane(Pane):
    name = "watch"
    column = 1

    def visible(self, ctx: PaneContext) -> bool:
        return bool(ctx.watchlist.items())

    def render(self, ctx: PaneContext) -> list[str]:
        lines = [self.title(ctx)]
        entries = ctx.watchlist.items()
        if not entries:
            lines.append("(no watches)")
            return lines

        snapshot = ctx.snapshot
        ptr_size = snapshot.arch.ptr_size or 8
        frame = _selected_frame(ctx.process)

        for entry in entries:
            expr_text = self.style(ctx, entry.expr, "reg_name")
            idx_text = self.style(ctx, f"#{entry.wid}", "label")
            label_text = ""
            if entry.label:
                label_text = f" ({self.style(ctx, entry.label, 'label')})"
            sep = self.style(ctx, " = ", "label")

            value = resolve_addr(entry.expr, snapshot.regs)
            if value is None:
                value = eval_expression(frame, entry.expr)
            if value is None:
                unresolved = self.style(ctx, "<unresolved>", "muted")
                lines.append(f"  {idx_text} {expr_text}{label_text}{sep}{unresolved}")
                continue

            value_text = self.style(ctx, format_addr(value, ptr_size), "value")
            line = f"  {idx_text} {expr_text}{label_text}{sep}{value_text}"

            if ctx.settings.aggressive_deref and ctx.reader:
                chain = deref_chain(
                    value,
                    ctx.reader,
                    snapshot.maps,
                    ctx.resolver,
                    ctx.settings,
                    ptr_size,
                )
                summary = summarize_chain(chain)
                if summary:
                    kind = classify_token(summary)
                    role = "string" if kind == "string" else "symbol"
                    if kind == "region":
                        role = "muted"
                    arrow = self.style(ctx, "->", "arrow")
                    summary_text = self.style(ctx, summary, role)
                    line = f"{line} {arrow} {summary_text}"
                    if kind == "symbol":
                        tag = region_tag(last_addr(chain), snapshot.maps)
                        if tag:
                            tag_text = self.style(ctx, tag, "muted")
                            line = f"{line} {tag_text}"

            lines.append(line)

        return lines


def _selected_frame(process):
    if not process:
        return None
    thread = process.GetSelectedThread()
    if not thread or not thread.IsValid():
        return None
    frame = thread.GetSelectedFrame()
    if not frame or not frame.IsValid():
        return None
    return frame
