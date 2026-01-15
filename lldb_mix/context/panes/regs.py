from __future__ import annotations

from lldb_mix.context.panes.base import Pane
from lldb_mix.context.types import PaneContext
from lldb_mix.deref import (
    classify_token,
    deref_chain,
    format_addr,
    summarize_chain,
)


class RegsPane(Pane):
    name = "regs"

    def render(self, ctx: PaneContext) -> list[str]:
        snapshot = ctx.snapshot
        arch = snapshot.arch
        regs = snapshot.regs
        lines = [self.title(ctx)]
        ptr_size = arch.ptr_size or 8
        reg_names = [name for name in arch.gpr_names if name in regs]

        if not reg_names:
            lines.append("(no registers)")
            return lines

        name_width = max(len(name) for name in reg_names)
        entries: list[tuple[str, int]] = []
        pointers: list[tuple[str, str, str]] = []

        for reg_name in reg_names:
            value = regs[reg_name]
            changed = (
                reg_name in ctx.last_regs and ctx.last_regs.get(reg_name) != value
            )
            value_text = format_addr(value, ptr_size)
            name_text = f"{reg_name:{name_width}}"
            name_colored = self.style(ctx, name_text, "reg_name")
            value_role = "reg_changed" if changed else "reg_value"
            value_colored = self.style(ctx, value_text, value_role)
            sep = self.style(ctx, ": ", "label")
            cell_text = f"{name_colored}{sep}{value_colored}"
            cell_plain = f"{name_text}: {value_text}"
            entries.append((cell_text, len(cell_plain)))

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
                    if kind in ("string", "symbol"):
                        pointers.append((reg_name, summary, kind))

        cell_width = max(length for _, length in entries)
        col_sep = 2
        cols = max(1, (ctx.term_width + col_sep) // (cell_width + col_sep))
        cols = min(cols, len(entries))
        for start in range(0, len(entries), cols):
            row = entries[start : start + cols]
            line_parts: list[str] = []
            for text, length in row:
                padding = " " * (cell_width - length)
                line_parts.append(f"{text}{padding}")
            lines.append((" " * col_sep).join(line_parts).rstrip())

        if pointers:
            lines.append(self.style(ctx, "pointers:", "label"))
            for reg_name, summary, kind in pointers:
                role = "string" if kind == "string" else "symbol"
                reg_text = self.style(ctx, reg_name, "reg_name")
                arrow = self.style(ctx, "->", "arrow")
                summary_text = self.style(ctx, summary, role)
                lines.append(f"  {reg_text} {arrow} {summary_text}")

        return lines
