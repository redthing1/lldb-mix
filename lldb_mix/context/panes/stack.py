from __future__ import annotations

from lldb_mix.context.panes.base import Pane
from lldb_mix.context.types import PaneContext
from lldb_mix.deref import (
    classify_token,
    deref_chain,
    format_addr,
    format_symbol,
    last_addr,
    region_tag,
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

        frame_lines = _frame_lines(ctx, ptr_size, self.style)
        if frame_lines:
            lines.append(self.style(ctx, "frames:", "label"))
            lines.extend(frame_lines)

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
                    if kind in ("string", "symbol", "region"):
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


def _frame_lines(
    ctx: PaneContext, ptr_size: int, style
) -> list[str]:
    process = ctx.process
    if not process or not ctx.settings.stack_frame_lines:
        return []
    thread = process.GetSelectedThread()
    if not thread or not thread.IsValid():
        return []

    num_frames = min(thread.GetNumFrames(), ctx.settings.stack_frame_lines)
    if num_frames <= 0:
        return []

    lines: list[str] = []
    for idx in range(num_frames):
        frame = thread.GetFrameAtIndex(idx)
        if not frame:
            continue
        pc = frame.GetPC()
        name = frame.GetFunctionName() or ""
        if not name and frame.GetSymbol():
            name = frame.GetSymbol().GetName() or ""
        if not name and ctx.resolver:
            symbol = ctx.resolver.resolve(pc)
            if symbol:
                name = format_symbol(symbol)
        if not name:
            name = "?"

        idx_text = style(ctx, f"#{idx}", "label")
        role = "symbol" if name and name != "?" else "muted"
        name_text = style(ctx, name, role)
        addr_text = style(ctx, format_addr(pc, ptr_size), "addr")
        lines.append(f"  {idx_text} {name_text} {addr_text}")
    return lines
