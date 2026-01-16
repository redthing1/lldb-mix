from __future__ import annotations

from lldb_mix.commands.utils import eval_expression, resolve_addr
from lldb_mix.context.formatting import deref_summary, format_deref_suffix
from lldb_mix.context.panes.base import Pane
from lldb_mix.context.types import PaneContext
from lldb_mix.deref import format_addr


class WatchPane(Pane):
    name = "watch"
    column = 1

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

            info = deref_summary(ctx, value, ptr_size)
            if info:
                line = f"{line} {format_deref_suffix(self, ctx, info)}"

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
