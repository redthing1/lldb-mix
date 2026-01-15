from __future__ import annotations

from lldb_mix.context.panes.base import Pane
from lldb_mix.context.types import PaneContext
from lldb_mix.core.disasm import read_instructions_around
from lldb_mix.deref import format_addr


class CodePane(Pane):
    name = "code"

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

        flags = 0
        if arch.flags_reg:
            flags = snapshot.regs.get(arch.flags_reg, 0)

        flavor = "intel" if arch.name.startswith("x86") else ""
        insts = read_instructions_around(
            ctx.target,
            pc,
            ctx.settings.code_lines_before,
            ctx.settings.code_lines_after,
            arch,
            flavor=flavor,
        )
        if not insts:
            lines.append("(disassembly unavailable)")
            return lines

        for inst in insts:
            prefix = "=>" if inst.address == pc else "  "
            addr_text = format_addr(inst.address, ptr_size)
            bytes_text = ""
            if ctx.settings.show_opcodes:
                bytes_text = " ".join(f"{b:02x}" for b in inst.bytes)
                bytes_text = f"{bytes_text:<24}" if bytes_text else ""

            prefix_role = "pc_marker" if inst.address == pc else "muted"
            prefix_colored = self.style(ctx, prefix, prefix_role)
            addr_colored = self.style(ctx, addr_text, "addr")
            bytes_colored = self.style(ctx, bytes_text, "opcode") if bytes_text else ""
            mnemonic_colored = self.style(ctx, inst.mnemonic, "mnemonic")

            text = f"{prefix_colored} {addr_colored} "
            if bytes_colored:
                text += bytes_colored
            text += mnemonic_colored
            if inst.operands:
                text += f" {inst.operands}"
            if inst.address == pc and arch.is_conditional_branch(inst.mnemonic):
                taken, reason = arch.branch_taken(inst.mnemonic, flags)
                if reason:
                    comment = f"; {'taken' if taken else 'not taken'} ({reason})"
                else:
                    comment = f"; {'taken' if taken else 'not taken'}"
                text += f" {self.style(ctx, comment, 'comment')}"
            lines.append(text)

        return lines
