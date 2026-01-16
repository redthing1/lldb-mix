from __future__ import annotations

from lldb_mix.context.panes.base import Pane
from lldb_mix.context.types import PaneContext
from lldb_mix.core.disasm import read_instructions
from lldb_mix.core.flow import resolve_flow_target
from lldb_mix.deref import format_addr, format_symbol


class FlowPane(Pane):
    name = "flow"
    column = 0

    def render(self, ctx: PaneContext) -> list[str]:
        snapshot = ctx.snapshot
        arch = snapshot.arch
        lines = [self.title(ctx)]
        pc = snapshot.pc
        ptr_size = arch.ptr_size or 8

        if pc == 0:
            lines.append("(pc unavailable)")
            return lines
        if not ctx.target:
            lines.append("(target unavailable)")
            return lines

        insts = read_instructions(ctx.target, pc, 1)
        if not insts:
            lines.append("(flow unavailable)")
            return lines

        inst = insts[0]
        mnemonic = self.style(ctx, inst.mnemonic, "mnemonic")
        if inst.operands:
            lines.append(f"{mnemonic} {inst.operands}")
        else:
            lines.append(mnemonic)
        target = resolve_flow_target(inst.mnemonic, inst.operands, snapshot.regs)
        if target is None:
            lines.append("(no flow target resolved)")
            return lines

        target_line = self.style(ctx, format_addr(target, ptr_size), "addr")
        if ctx.resolver:
            symbol = ctx.resolver.resolve(target)
            if symbol:
                symbol_text = self.style(ctx, format_symbol(symbol), "symbol")
                target_line = f"{target_line} {symbol_text}"

        label = self.style(ctx, "target:", "label")
        lines.append(f"{label} {target_line}")
        return lines
