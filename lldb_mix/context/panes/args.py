from __future__ import annotations

from lldb_mix.context.formatting import deref_summary, format_deref_suffix
from lldb_mix.context.panes.base import Pane
from lldb_mix.context.types import PaneContext
from lldb_mix.core.disasm import disasm_flavor, read_instructions
from lldb_mix.core.flow import resolve_flow_target
from lldb_mix.deref import format_addr, format_symbol


class ArgsPane(Pane):
    name = "args"
    column = 1

    def title(self, ctx: PaneContext | None = None) -> str:
        if ctx is None:
            return super().title(ctx)
        return self.style(ctx, f"[{self.name}]", "title")

    def visible(self, ctx: PaneContext) -> bool:
        abi = getattr(ctx.snapshot.arch, "abi", None)
        if not abi or not getattr(abi, "int_arg_regs", None):
            return False
        regs = ctx.snapshot.regs
        return any(reg in regs for reg in abi.int_arg_regs)

    def render(self, ctx: PaneContext) -> list[str]:
        snapshot = ctx.snapshot
        arch = snapshot.arch
        abi = getattr(arch, "abi", None)
        regs = snapshot.regs
        lines = [self.title(ctx)]
        if not abi or not getattr(abi, "int_arg_regs", None):
            lines.append("(args unavailable)")
            return lines

        arg_regs = [reg for reg in abi.int_arg_regs if reg in regs]
        if not arg_regs:
            lines.append("(no args)")
            return lines

        ptr_size = arch.ptr_size or 8
        call_inst = _current_call_inst(ctx, arch, snapshot.pc)
        abi_label = self._abi_label(ctx, abi)
        if abi_label:
            lines.append(abi_label)
        if call_inst:
            header = self._call_header(ctx, call_inst, regs, ptr_size)
            lines.append(header)

        name_width = max(len(reg) for reg in arg_regs)

        for reg_name in arg_regs:
            value = regs[reg_name]
            name_text = f"{reg_name:{name_width}}"
            name_colored = self.style(ctx, name_text, "reg_name")
            value_text = format_addr(value, ptr_size)
            value_colored = self.style(ctx, value_text, "value")
            sep = self.style(ctx, ": ", "label")
            line = f"{name_colored}{sep}{value_colored}"

            info = deref_summary(ctx, value, ptr_size)
            if info:
                line = f"{line} {format_deref_suffix(self, ctx, info)}"

            lines.append(line)

        return lines

    def _call_header(
        self, ctx: PaneContext, inst, regs: dict[str, int], ptr_size: int
    ) -> str:
        label = self.style(ctx, "call args", "label")
        target = resolve_flow_target(
            inst.mnemonic, inst.operands, regs, ctx.snapshot.arch
        )
        if target is None:
            return label
        arrow = self.style(ctx, "->", "arrow")
        addr_text = self.style(ctx, format_addr(target, ptr_size), "addr")
        line = f"{label} {arrow} {addr_text}"
        if ctx.resolver:
            symbol = ctx.resolver.resolve(target)
            if symbol:
                sym_text = self.style(ctx, format_symbol(symbol), "symbol")
                line = f"{line} {sym_text}"
        return line

    def _abi_label(self, ctx: PaneContext, abi) -> str | None:
        name = getattr(abi, "name", "") if abi else ""
        if not name:
            return None
        return self.style(ctx, f"abi: {name}", "muted")


def _current_call_inst(ctx: PaneContext, arch, pc: int | None):
    if not ctx.target or pc is None:
        return None
    flavor = disasm_flavor(arch.name)
    try:
        insts = read_instructions(ctx.target, pc, 1, flavor)
    except Exception:
        return None
    if not insts:
        return None
    inst = insts[0]
    if inst.address != pc:
        return None
    if not arch.is_call(inst.mnemonic):
        return None
    return inst
