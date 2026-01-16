from __future__ import annotations

from lldb_mix.context.panes.base import Pane
from lldb_mix.context.types import PaneContext
from lldb_mix.core.disasm import read_instructions
from lldb_mix.core.flow import resolve_flow_target
from lldb_mix.deref import (
    classify_token,
    deref_chain,
    format_addr,
    format_symbol,
    last_addr,
    region_tag,
    summarize_chain,
)


class ArgsPane(Pane):
    name = "args"
    column = 1

    def title(self, ctx: PaneContext | None = None) -> str:
        if ctx is None:
            return super().title(ctx)
        abi = getattr(ctx.snapshot.arch, "abi", None)
        label = self.name
        if abi and getattr(abi, "name", ""):
            label = f"{self.name}:{abi.name}"
        return self.style(ctx, f"[{label}]", "title")

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
        if call_inst:
            header = self._call_header(ctx, call_inst, regs, ptr_size)
        else:
            header = self.style(ctx, "arg regs", "label")
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

    def _call_header(self, ctx: PaneContext, inst, regs: dict[str, int], ptr_size: int) -> str:
        label = self.style(ctx, "call args", "label")
        target = resolve_flow_target(inst.mnemonic, inst.operands, regs)
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


def _current_call_inst(ctx: PaneContext, arch, pc: int):
    if not ctx.target or pc == 0:
        return None
    flavor = "intel" if arch.name.startswith("x86") else ""
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
