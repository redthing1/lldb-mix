from __future__ import annotations

import re
from dataclasses import dataclass

from lldb_mix.arch.view import ArchView
from lldb_mix.context.formatting import deref_summary
from lldb_mix.context.panes.base import Pane
from lldb_mix.context.types import PaneContext
from lldb_mix.core.disasm import read_instructions, read_instructions_around
from lldb_mix.core.flow import branch_decision, is_branch_like, resolve_flow_target
from lldb_mix.deref import format_addr, format_symbol
from lldb_mix.ui.text import pad_ansi, truncate_ansi, visible_len


BRANCH_VIEW_MIN_WIDTH = 120
BRANCH_MIN_COL_WIDTH = 50
BRANCH_COLUMN_GAP = 4


@dataclass(frozen=True)
class _CodeState:
    ptr_size: int
    flags: int
    bytes_texts: list[str]
    bytes_pad: int
    flavor: str




class CodePane(Pane):
    name = "code"
    full_width = True

    def render(self, ctx: PaneContext) -> list[str]:
        snapshot = ctx.snapshot
        arch = snapshot.arch
        lines = [self.title(ctx)]
        pc = snapshot.pc
        ptr_size = arch.ptr_size or 8

        if not snapshot.has_pc():
            lines.append("(pc unavailable)")
            return lines
        if not ctx.target:
            lines.append("(target unavailable)")
            return lines

        flags = 0
        if arch.flags_reg:
            flags = snapshot.regs.get(arch.flags_reg, 0)

        flavor = arch.disasm_flavor()
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

        bytes_texts, bytes_pad = _opcode_texts(insts, ctx.settings.show_opcodes)

        current_idx = _pc_index(insts, pc)
        if current_idx is None:
            lines.append("(disassembly unavailable)")
            return lines

        state = _CodeState(
            ptr_size=ptr_size,
            flags=flags,
            bytes_texts=bytes_texts,
            bytes_pad=bytes_pad,
            flavor=flavor,
        )
        branch_lines = _render_branch_split(
            self,
            ctx,
            insts,
            current_idx,
            state,
        )
        if branch_lines:
            lines.extend(branch_lines)
            return lines

        lines.extend(_render_linear(self, ctx, insts, state, pc))

        return lines


_REG_BOUNDARY = r"(?<![A-Za-z0-9_])(?:{name})(?![A-Za-z0-9_])"


def _opcode_texts(insts, show_opcodes: bool) -> tuple[list[str], int]:
    if not show_opcodes:
        return [""] * len(insts), 0
    texts = [" ".join(f"{b:02x}" for b in inst.bytes) for inst in insts]
    pad = max((len(text) for text in texts), default=0)
    return texts, pad


def _pc_index(insts, pc: int) -> int | None:
    return next((idx for idx, inst in enumerate(insts) if inst.address == pc), None)


def _render_linear(
    pane: CodePane,
    ctx: PaneContext,
    insts,
    state: _CodeState,
    pc: int,
) -> list[str]:
    lines: list[str] = []
    for idx, inst in enumerate(insts):
        is_pc = inst.address == pc
        bytes_text = state.bytes_texts[idx] if state.bytes_texts else ""
        lines.append(
            _format_inst_line(
                pane,
                ctx,
                inst,
                state.ptr_size,
                bytes_text,
                state.bytes_pad,
                is_pc,
                state.flags,
                include_comment=is_pc,
                tone="normal",
            )
        )
    return lines


def _operand_annotations(
    operands: str,
    regs: dict[str, int],
    ctx: PaneContext,
    ptr_size: int,
    max_regs: int = 3,
) -> list[str]:
    if not operands or not regs:
        return []

    reg_map = {name.lower(): name for name in regs}
    reg_map.update(_alias_registers(ctx.snapshot.arch, regs))
    reg_names = sorted(reg_map.keys(), key=len, reverse=True)
    pattern = re.compile(
        _REG_BOUNDARY.format(name="|".join(re.escape(name) for name in reg_names)),
        re.IGNORECASE,
    )

    seen: set[str] = set()
    reg_hits: list[tuple[str, str]] = []
    for match in pattern.finditer(operands):
        key = match.group(0).lower()
        canon = reg_map.get(key)
        if not canon or canon in seen:
            continue
        seen.add(canon)
        reg_hits.append((match.group(0), canon))
        if len(reg_hits) >= max_regs:
            break

    pieces: list[str] = []
    for display, canon in reg_hits:
        value = regs[canon]
        addr_text = format_addr(value, ptr_size)
        summary = _annotation_for_addr(ctx, value, ptr_size)
        if summary:
            pieces.append(f"{display}={addr_text}->{summary}")
        else:
            pieces.append(f"{display}={addr_text}")

    mem_addr = _compute_mem_addr(operands, regs, pattern, ctx.snapshot.arch)
    if mem_addr is not None:
        mem_text = format_addr(mem_addr, ptr_size)
        summary = _annotation_for_addr(ctx, mem_addr, ptr_size)
        if summary:
            pieces.append(f"mem={mem_text}->{summary}")
        else:
            pieces.append(f"mem={mem_text}")
    return pieces


def _annotation_for_addr(ctx: PaneContext, addr: int, ptr_size: int) -> str | None:
    info = deref_summary(ctx, addr, ptr_size)
    if not info:
        return None
    return info.text


def _compute_mem_addr(
    operands: str,
    regs: dict[str, int],
    pattern: re.Pattern[str],
    arch: ArchView,
) -> int | None:
    targets = arch.mem_operand_targets(operands, regs)
    if targets:
        return targets[0]
    for expr in re.findall(r"\[([^\]]+)\]", operands):
        cleaned = expr.replace("#", "").replace("!", "")
        regs_in = _regs_in_text(cleaned, regs, pattern, arch)
        if len(regs_in) != 1:
            continue
        base = regs.get(regs_in[0])
        if base is None:
            continue
        offset = _parse_offset(cleaned)
        return base + offset
    return None


def _regs_in_text(
    text: str,
    regs: dict[str, int],
    pattern: re.Pattern[str],
    arch: ArchView,
) -> list[str]:
    reg_map = {name.lower(): name for name in regs}
    reg_map.update(_alias_registers(arch, regs))
    seen: set[str] = set()
    out: list[str] = []
    for match in pattern.finditer(text):
        key = match.group(0).lower()
        canon = reg_map.get(key)
        if not canon or canon in seen:
            continue
        seen.add(canon)
        out.append(canon)
    return out


def _parse_offset(expr: str) -> int:
    match = re.search(r"([+-])\s*(0x[0-9a-fA-F]+|\d+)", expr)
    if not match:
        return 0
    sign = -1 if match.group(1) == "-" else 1
    try:
        value = int(match.group(2), 0)
    except ValueError:
        return 0
    return sign * value


def _branch_taken_hint(
    mnemonic: str,
    operands: str,
    regs: dict[str, int],
    arch,
    flags: int,
) -> str | None:
    decision = branch_decision(
        mnemonic,
        operands,
        regs,
        arch,
        flags,
        include_unconditional=False,
        include_calls=False,
    )
    if not decision:
        return None
    if decision.kind != "conditional":
        return None
    taken = decision.taken
    reason = decision.reason
    if reason:
        return f"{'taken' if taken else 'not taken'} ({reason})"
    return "taken" if taken else "not taken"


def _alias_registers(arch: ArchView, regs: dict[str, int]) -> dict[str, str]:
    try:
        return arch.register_aliases(regs)
    except Exception:
        return {}


def _render_branch_split(
    pane: CodePane,
    ctx: PaneContext,
    insts,
    current_idx: int,
    state: _CodeState,
) -> list[str] | None:
    snapshot = ctx.snapshot
    arch = snapshot.arch
    current = insts[current_idx]
    decision = branch_decision(
        current.mnemonic,
        current.operands,
        snapshot.regs,
        arch,
        state.flags,
        include_unconditional=True,
        include_calls=True,
    )
    if not decision:
        return None

    if ctx.term_width < BRANCH_VIEW_MIN_WIDTH:
        return None
    if ctx.term_width < BRANCH_MIN_COL_WIDTH * 2 + BRANCH_COLUMN_GAP:
        return None

    read_pointer = getattr(ctx.reader, "read_pointer", None)
    target = resolve_flow_target(
        current.mnemonic,
        current.operands,
        snapshot.regs,
        arch,
        read_pointer=read_pointer,
        ptr_size=state.ptr_size,
    )
    fallthrough = _fallthrough_addr(insts, current_idx, arch)
    if target is None or fallthrough is None:
        return None

    block_lines = max(ctx.settings.code_lines_after, 0)
    if block_lines <= 0:
        return None
    left_insts = read_instructions(ctx.target, fallthrough, block_lines, state.flavor)
    right_insts = read_instructions(ctx.target, target, block_lines, state.flavor)
    if not left_insts or not right_insts:
        return None

    lines: list[str] = []
    for idx in range(current_idx + 1):
        inst = insts[idx]
        bytes_text = state.bytes_texts[idx] if state.bytes_texts else ""
        lines.append(
            _format_inst_line(
                pane,
                ctx,
                inst,
                state.ptr_size,
                bytes_text,
                state.bytes_pad,
                inst.address == snapshot.pc,
                state.flags,
                include_comment=inst.address == snapshot.pc,
                tone="normal",
            )
        )

    taken = decision.taken
    left_tone = "normal" if not taken else "muted"
    right_tone = "normal" if taken else "muted"

    show_opcodes = ctx.settings.show_opcodes
    left_bytes, left_pad = _opcode_texts(left_insts, show_opcodes)
    right_bytes, right_pad = _opcode_texts(right_insts, show_opcodes)
    block_pad = max(left_pad, right_pad)

    left_lines = [
        _format_inst_line(
            pane,
            ctx,
            inst,
            state.ptr_size,
            left_bytes[idx] if left_bytes else "",
            block_pad,
            False,
            state.flags,
            include_comment=False,
            tone=left_tone,
        )
        for idx, inst in enumerate(left_insts)
    ]
    right_lines = [
        _format_inst_line(
            pane,
            ctx,
            inst,
            state.ptr_size,
            right_bytes[idx] if right_bytes else "",
            block_pad,
            False,
            state.flags,
            include_comment=False,
            tone=right_tone,
        )
        for idx, inst in enumerate(right_insts)
    ]

    widths = _branch_widths(ctx.term_width, left_lines, right_lines)
    if not widths:
        return None
    left_width, right_width = widths
    lines.extend(
        _join_branch_blocks(
            pane,
            ctx,
            left_lines,
            right_lines,
            left_width,
            right_width,
            taken,
        )
    )
    return lines


def _format_inst_line(
    pane: CodePane,
    ctx: PaneContext,
    inst,
    ptr_size: int,
    bytes_text: str,
    bytes_pad: int,
    is_pc: bool,
    flags: int,
    include_comment: bool,
    tone: str,
) -> str:
    prefix = "=>" if is_pc else "  "
    addr_text = format_addr(inst.address, ptr_size)
    bytes_text = f"{bytes_text:<{bytes_pad}}" if bytes_text else ""

    if tone == "muted":
        text = f"{prefix} {addr_text}"
        if bytes_text:
            text += f" {bytes_text}"
        text += f" {inst.mnemonic}"
        if inst.operands:
            text += f" {inst.operands}"
        return pane.style(ctx, text, "muted")

    prefix_role = "pc_marker" if is_pc else "muted"
    prefix_colored = pane.style(ctx, prefix, prefix_role)
    addr_colored = pane.style(ctx, addr_text, "addr")
    bytes_colored = pane.style(ctx, bytes_text, "opcode") if bytes_text else ""
    mnemonic_colored = pane.style(ctx, inst.mnemonic, "mnemonic")

    text = f"{prefix_colored} {addr_colored} "
    if bytes_colored:
        text += bytes_colored
        text += " "
    text += mnemonic_colored
    if inst.operands:
        text += f" {inst.operands}"

    if include_comment:
        comment = _inst_comment(ctx, inst, ptr_size, flags)
        if comment:
            text += f" {pane.style(ctx, comment, 'comment')}"

    return text


def _inst_comment(ctx: PaneContext, inst, ptr_size: int, flags: int) -> str | None:
    comment_parts: list[str] = []
    hint = _branch_taken_hint(
        inst.mnemonic,
        inst.operands,
        ctx.snapshot.regs,
        ctx.snapshot.arch,
        flags,
    )
    if hint:
        comment_parts.append(hint)
    comment_parts.extend(
        _operand_annotations(
            inst.operands,
            ctx.snapshot.regs,
            ctx,
            ptr_size,
        )
    )
    if is_branch_like(inst.mnemonic, ctx.snapshot.arch):
        read_pointer = getattr(ctx.reader, "read_pointer", None)
        target = resolve_flow_target(
            inst.mnemonic,
            inst.operands,
            ctx.snapshot.regs,
            ctx.snapshot.arch,
            read_pointer=read_pointer,
            ptr_size=ptr_size,
        )
        if target is not None:
            target_text = format_addr(target, ptr_size)
            if ctx.resolver:
                symbol = ctx.resolver.resolve(target)
                if symbol:
                    target_text = f"{target_text} {format_symbol(symbol)}"
            comment_parts.append(f"target={target_text}")

    if not comment_parts:
        return None
    return "; " + " | ".join(comment_parts)


def _fallthrough_addr(insts, current_idx: int, arch) -> int | None:
    if current_idx + 1 < len(insts):
        return insts[current_idx + 1].address
    current = insts[current_idx]
    if current.bytes:
        return current.address + len(current.bytes)
    if arch.max_inst_bytes:
        return current.address + arch.max_inst_bytes
    return None


def _join_branch_blocks(
    pane: CodePane,
    ctx: PaneContext,
    left_lines: list[str],
    right_lines: list[str],
    left_width: int,
    right_width: int,
    taken: bool,
) -> list[str]:
    height = max(len(left_lines), len(right_lines))
    left = list(left_lines)
    right = list(right_lines)
    if len(left) < height:
        left.extend([" " * left_width] * (height - len(left)))
    if len(right) < height:
        right.extend([" " * right_width] * (height - len(right)))

    lines: list[str] = []
    for idx in range(height):
        left_text = pad_ansi(truncate_ansi(left[idx], left_width), left_width)
        right_text = pad_ansi(truncate_ansi(right[idx], right_width), right_width)
        gap = _branch_gap(pane, ctx, idx, taken)
        lines.append(f"{left_text}{gap}{right_text}".rstrip())
    return lines


def _branch_gap(pane: CodePane, ctx: PaneContext, row_idx: int, taken: bool) -> str:
    if row_idx != 0 or BRANCH_COLUMN_GAP < 2:
        return " " * BRANCH_COLUMN_GAP
    arrow = pane.style(ctx, "->", "arrow" if taken else "muted")
    padding = " " * max(BRANCH_COLUMN_GAP - 2, 0)
    return f"{padding}{arrow}"


def _max_visible_width(lines: list[str]) -> int:
    if not lines:
        return 0
    return max(visible_len(line) for line in lines)


def _branch_widths(
    term_width: int,
    left_lines: list[str],
    right_lines: list[str],
) -> tuple[int, int] | None:
    if term_width < BRANCH_VIEW_MIN_WIDTH:
        return None
    available = term_width - BRANCH_COLUMN_GAP
    if available < BRANCH_MIN_COL_WIDTH * 2:
        return None

    left_target = max(_max_visible_width(left_lines), BRANCH_MIN_COL_WIDTH)
    right_target = max(_max_visible_width(right_lines), BRANCH_MIN_COL_WIDTH)
    if left_target + right_target <= available:
        return left_target, right_target

    total = max(left_target + right_target, 1)
    left_width = int(available * (left_target / total))
    left_width = max(
        BRANCH_MIN_COL_WIDTH,
        min(left_width, available - BRANCH_MIN_COL_WIDTH),
    )
    right_width = available - left_width
    if right_width < BRANCH_MIN_COL_WIDTH:
        return None
    return left_width, right_width
