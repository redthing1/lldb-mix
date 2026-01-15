from __future__ import annotations

from lldb_mix.context.panes.base import Pane
from lldb_mix.context.types import PaneContext
from lldb_mix.deref import (
    classify_token,
    deref_chain,
    format_addr,
    summarize_chain,
)


class StackPane(Pane):
    name = "stack"

    def render(self, ctx: PaneContext) -> list[str]:
        snapshot = ctx.snapshot
        arch = snapshot.arch
        lines = [self.title(ctx)]
        sp = snapshot.sp
        ptr_size = arch.ptr_size or 8

        if sp == 0:
            lines.append("(sp unavailable)")
            return lines
        if not ctx.reader or not hasattr(ctx.reader, "read_pointer"):
            lines.append("(memory reader unavailable)")
            return lines

        for idx in range(ctx.settings.stack_lines):
            slot_addr = sp + idx * ptr_size
            value = ctx.reader.read_pointer(slot_addr, ptr_size)
            if value is None:
                addr_text = self.style(ctx, format_addr(slot_addr, ptr_size), "addr")
                label = self.style(ctx, ": ", "label")
                unreadable = self.style(ctx, "<unreadable>", "muted")
                lines.append(f"{addr_text}{label}{unreadable}")
                continue

            addr_text = self.style(ctx, format_addr(slot_addr, ptr_size), "addr")
            value_text = format_addr(value, ptr_size)
            value_colored = self.style(ctx, value_text, "value")
            label = self.style(ctx, ": ", "label")
            line = f"{addr_text}{label}{value_colored}"

            if ctx.settings.aggressive_deref:
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
                    if kind in ("string", "symbol"):
                        role = "string" if kind == "string" else "symbol"
                        arrow = self.style(ctx, "->", "arrow")
                        summary_text = self.style(ctx, summary, role)
                        line = f"{line} {arrow} {summary_text}"

            lines.append(line)

        return lines
