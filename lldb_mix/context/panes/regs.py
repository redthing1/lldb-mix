from __future__ import annotations

from lldb_mix.context.formatting import (
    DerefSummary,
    deref_summary,
    format_deref_suffix,
)
from lldb_mix.context.panes.base import Pane
from lldb_mix.context.types import PaneContext
from lldb_mix.deref import find_region, format_addr, format_region


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
        pointer_mode = getattr(ctx.settings, "pointer_mode", "smart")
        show_all = pointer_mode == "all"

        if not reg_names:
            lines.append("(no registers)")
            return lines

        name_width = max(len(name) for name in reg_names)
        entries: list[tuple[str, int]] = []
        pointers: list[tuple[str, DerefSummary]] = []

        for reg_name in reg_names:
            value = regs[reg_name]
            is_flags = bool(flags_reg and reg_name == flags_reg)
            changed = reg_name in ctx.last_regs and ctx.last_regs.get(reg_name) != value
            if is_flags:
                flags_text = arch.format_flags(value)
                value_text = flags_text if flags_text else format_addr(value, ptr_size)
            else:
                value_text = format_addr(value, ptr_size)
            name_text = f"{reg_name:{name_width}}"
            name_colored = self.style(ctx, name_text, "reg_name")
            value_role = "reg_changed" if changed else "reg_value"
            value_colored = self.style(ctx, value_text, value_role)
            sep = self.style(ctx, " ", "label")
            cell_text = f"{name_colored}{sep}{value_colored}"
            cell_plain = f"{name_text} {value_text}"
            entries.append((cell_text, len(cell_plain)))

            if not is_flags and ctx.settings.aggressive_deref and ctx.reader:
                info = deref_summary(ctx, value, ptr_size)
                if info:
                    pointers.append((reg_name, info))
                elif show_all:
                    region = find_region(value, snapshot.maps)
                    if region:
                        tag = format_region(region)
                        pointers.append(
                            (
                                reg_name,
                                DerefSummary(format_addr(value, ptr_size), "addr", tag),
                            )
                        )

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
            pointer_name_width = max(len(reg_name) for reg_name, *_ in pointers)
            indent = "  "
            for reg_name, info in pointers:
                reg_text = self.style(
                    ctx,
                    f"{reg_name:<{pointer_name_width}}",
                    "reg_name",
                )
                line = f"{indent}{reg_text} {format_deref_suffix(self, ctx, info)}"
                lines.append(line)

        return lines
