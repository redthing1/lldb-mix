from __future__ import annotations

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


class RegsPane(Pane):
    name = "regs"
    column = 0

    def render(self, ctx: PaneContext) -> list[str]:
        snapshot = ctx.snapshot
        arch = snapshot.arch
        regs = snapshot.regs
        lines = [self.title(ctx)]
        ptr_size = arch.ptr_size or 8
        reg_names = [name for name in arch.gpr_names if name in regs]
        flags_reg = arch.flags_reg

        if not reg_names:
            lines.append("(no registers)")
            return lines

        name_width = max(len(name) for name in reg_names)
        entries: list[tuple[str, int]] = []
        pointers: list[tuple[str, str, str, str | None]] = []

        for reg_name in reg_names:
            value = regs[reg_name]
            is_flags = bool(flags_reg and reg_name == flags_reg)
            changed = (
                reg_name in ctx.last_regs and ctx.last_regs.get(reg_name) != value
            )
            if is_flags:
                flags_text = arch.format_flags(value)
                value_text = flags_text if flags_text else format_addr(value, ptr_size)
            else:
                value_text = format_addr(value, ptr_size)
            name_text = f"{reg_name:{name_width}}"
            name_colored = self.style(ctx, name_text, "reg_name")
            value_role = "reg_changed" if changed else "reg_value"
            value_colored = self.style(ctx, value_text, value_role)
            sep = self.style(ctx, ": ", "label")
            cell_text = f"{name_colored}{sep}{value_colored}"
            cell_plain = f"{name_text}: {value_text}"
            entries.append((cell_text, len(cell_plain)))

            if not is_flags and ctx.settings.aggressive_deref and ctx.reader:
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
                        addr = last_addr(chain)
                        tag = None
                        if kind == "symbol":
                            tag = region_tag(addr, snapshot.maps)
                        pointers.append((reg_name, summary, kind, tag))

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
            for reg_name, summary, kind, tag in pointers:
                role = "string" if kind == "string" else "symbol"
                if kind == "region":
                    role = "muted"
                reg_text = self.style(ctx, f"{reg_name:<{name_width}}", "reg_name")
                arrow = self.style(ctx, "->", "arrow")
                summary_text = self.style(ctx, summary, role)
                line = f"  {reg_text} {arrow} {summary_text}"
                if tag:
                    tag_text = self.style(ctx, tag, "muted")
                    line = f"{line} {tag_text}"
                lines.append(line)

        return lines
