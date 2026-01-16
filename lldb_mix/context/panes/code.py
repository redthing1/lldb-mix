from __future__ import annotations

import re

from lldb_mix.context.panes.base import Pane
from lldb_mix.context.types import PaneContext
from lldb_mix.core.disasm import read_instructions, read_instructions_around
from lldb_mix.core.flow import is_branch_like, resolve_flow_target
from lldb_mix.deref import (
    classify_token,
    deref_chain,
    format_addr,
    format_symbol,
    summarize_chain,
)
from lldb_mix.ui.ansi import RESET, strip_ansi


BRANCH_VIEW_MIN_WIDTH = 120
BRANCH_MIN_COL_WIDTH = 50
BRANCH_COLUMN_GAP = 4


class CodePane(Pane):
    name = "code"
    full_width = True

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

        bytes_pad = 0
        bytes_texts: list[str] = [""] * len(insts)
        if ctx.settings.show_opcodes:
            bytes_texts = [" ".join(f"{b:02x}" for b in inst.bytes) for inst in insts]
            bytes_pad = max((len(text) for text in bytes_texts), default=0)

        current_idx = next(
            (idx for idx, inst in enumerate(insts) if inst.address == pc),
            None,
        )
        if current_idx is None:
            lines.append("(disassembly unavailable)")
            return lines

        branch_lines = _render_branch_split(
            self,
            ctx,
            insts,
            current_idx,
            flags,
            ptr_size,
            bytes_texts,
            bytes_pad,
            flavor,
        )
        if branch_lines:
            lines.extend(branch_lines)
            return lines

        for idx, inst in enumerate(insts):
            bytes_text = bytes_texts[idx] if bytes_texts else ""
            lines.append(
                _format_inst_line(
                    self,
                    ctx,
                    inst,
                    ptr_size,
                    bytes_text,
                    bytes_pad,
                    inst.address == pc,
                    flags,
                    include_comment=inst.address == pc,
                    tone="normal",
                )
            )

        return lines


_REG_BOUNDARY = r"(?<![A-Za-z0-9_])(?:{name})(?![A-Za-z0-9_])"


def _operand_annotations(
    operands: str,
    regs: dict[str, int],
    ptr_size: int,
    reader,
    regions,
    resolver,
    settings,
    max_regs: int = 3,
) -> list[str]:
    if not operands or not regs:
        return []

    reg_map = {name.lower(): name for name in regs}
    reg_map.update(_alias_registers(regs))
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
        summary = _annotation_for_addr(
            value, reader, regions, resolver, settings, ptr_size
        )
        if summary:
            pieces.append(f"{display}={addr_text}->{summary}")
        else:
            pieces.append(f"{display}={addr_text}")

    mem_addr = _compute_mem_addr(operands, regs, pattern)
    if mem_addr is not None:
        mem_text = format_addr(mem_addr, ptr_size)
        summary = _annotation_for_addr(
            mem_addr, reader, regions, resolver, settings, ptr_size
        )
        if summary:
            pieces.append(f"mem={mem_text}->{summary}")
        else:
            pieces.append(f"mem={mem_text}")
    return pieces


def _annotation_for_addr(
    addr, reader, regions, resolver, settings, ptr_size: int
) -> str | None:
    if not reader or not settings or not settings.aggressive_deref:
        return None
    chain = deref_chain(addr, reader, regions or [], resolver, settings, ptr_size)
    summary = summarize_chain(chain)
    if not summary:
        return None
    kind = classify_token(summary)
    if kind in ("string", "symbol", "region"):
        return summary
    return None


def _compute_mem_addr(
    operands: str, regs: dict[str, int], pattern: re.Pattern[str]
) -> int | None:
    for expr in re.findall(r"\[([^\]]+)\]", operands):
        cleaned = expr.replace("#", "").replace("!", "")
        regs_in = _regs_in_text(cleaned, regs, pattern)
        if len(regs_in) != 1:
            continue
        base = regs.get(regs_in[0])
        if base is None:
            continue
        offset = _parse_offset(cleaned)
        return base + offset
    return None


def _regs_in_text(
    text: str, regs: dict[str, int], pattern: re.Pattern[str]
) -> list[str]:
    reg_map = {name.lower(): name for name in regs}
    reg_map.update(_alias_registers(regs))
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
    decision = _branch_decision(mnemonic, operands, regs, arch, flags)
    if not decision:
        return None
    taken, reason = decision
    if reason:
        return f"{'taken' if taken else 'not taken'} ({reason})"
    return "taken" if taken else "not taken"


def _branch_decision(
    mnemonic: str,
    operands: str,
    regs: dict[str, int],
    arch,
    flags: int,
) -> tuple[bool, str] | None:
    if arch.is_conditional_branch(mnemonic):
        taken, reason = arch.branch_taken(mnemonic, flags)
        if not reason:
            return None
        return taken, reason

    mnem = mnemonic.lower()
    if mnem in {"cbz", "cbnz"}:
        reg = operands.split(",", 1)[0].strip()
        value = _reg_value(reg, regs)
        if value is None:
            return None
        taken = (value == 0) if mnem == "cbz" else (value != 0)
        reason = f"{reg}={'0' if value == 0 else '!=0'}"
        return taken, reason

    if mnem in {"tbz", "tbnz"}:
        parts = [p.strip() for p in operands.split(",")]
        if len(parts) < 2:
            return None
        reg = parts[0]
        value = _reg_value(reg, regs)
        if value is None:
            return None
        bit_text = parts[1].lstrip("#")
        try:
            bit = int(bit_text, 0)
        except ValueError:
            return None
        bit_set = (value >> bit) & 1
        taken = (bit_set == 0) if mnem == "tbz" else (bit_set == 1)
        reason = f"{reg}[{bit}]={bit_set}"
        return taken, reason

    return None


def _reg_value(token: str, regs: dict[str, int]) -> int | None:
    key = token.strip().lower()
    reg_map = {name.lower(): name for name in regs}
    reg_map.update(_alias_registers(regs))
    canon = reg_map.get(key)
    if not canon:
        return None
    return regs.get(canon)


def _alias_registers(regs: dict[str, int]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    lower = {name.lower() for name in regs}
    if any(name.startswith("x") and name[1:].isdigit() for name in lower):
        for name in lower:
            if name.startswith("x") and name[1:].isdigit():
                aliases[f"w{name[1:]}"] = name
        if "fp" in lower:
            aliases["x29"] = "fp"
            aliases["w29"] = "fp"
        if "lr" in lower:
            aliases["x30"] = "lr"
            aliases["w30"] = "lr"
    if "rax" in lower:
        pairs = {
            "eax": "rax",
            "ebx": "rbx",
            "ecx": "rcx",
            "edx": "rdx",
            "esi": "rsi",
            "edi": "rdi",
            "ebp": "rbp",
            "esp": "rsp",
            "eip": "rip",
        }
        aliases.update({alias: reg for alias, reg in pairs.items() if reg in lower})
        for idx in range(8, 16):
            reg = f"r{idx}"
            if reg in lower:
                aliases[f"r{idx}d"] = reg
    return aliases


def _render_branch_split(
    pane: CodePane,
    ctx: PaneContext,
    insts,
    current_idx: int,
    flags: int,
    ptr_size: int,
    bytes_texts: list[str],
    bytes_pad: int,
    flavor: str,
) -> list[str] | None:
    snapshot = ctx.snapshot
    arch = snapshot.arch
    current = insts[current_idx]
    decision = _branch_decision(
        current.mnemonic, current.operands, snapshot.regs, arch, flags
    )
    if not decision:
        return None

    if ctx.term_width < BRANCH_VIEW_MIN_WIDTH:
        return None
    if ctx.term_width < BRANCH_MIN_COL_WIDTH * 2 + BRANCH_COLUMN_GAP:
        return None

    target = resolve_flow_target(
        current.mnemonic,
        current.operands,
        snapshot.regs,
    )
    fallthrough = _fallthrough_addr(insts, current_idx, arch)
    if target is None or fallthrough is None:
        return None

    block_lines = max(ctx.settings.code_lines_after, 0)
    if block_lines <= 0:
        return None
    left_insts = read_instructions(ctx.target, fallthrough, block_lines, flavor)
    right_insts = read_instructions(ctx.target, target, block_lines, flavor)
    if not left_insts or not right_insts:
        return None

    lines: list[str] = []
    for idx in range(current_idx + 1):
        inst = insts[idx]
        bytes_text = bytes_texts[idx] if bytes_texts else ""
        lines.append(
            _format_inst_line(
                pane,
                ctx,
                inst,
                ptr_size,
                bytes_text,
                bytes_pad,
                inst.address == snapshot.pc,
                flags,
                include_comment=inst.address == snapshot.pc,
                tone="normal",
            )
        )

    taken, _ = decision
    left_tone = "normal" if not taken else "muted"
    right_tone = "normal" if taken else "muted"

    show_opcodes = ctx.settings.show_opcodes
    left_bytes = _bytes_texts(left_insts) if show_opcodes else ["" for _ in left_insts]
    right_bytes = _bytes_texts(right_insts) if show_opcodes else ["" for _ in right_insts]
    block_pad = max(
        max((len(text) for text in left_bytes), default=0),
        max((len(text) for text in right_bytes), default=0),
    )

    left_lines = [
        _format_inst_line(
            pane,
            ctx,
            inst,
            ptr_size,
            left_bytes[idx] if left_bytes else "",
            block_pad,
            False,
            flags,
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
            ptr_size,
            right_bytes[idx] if right_bytes else "",
            block_pad,
            False,
            flags,
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
                ptr_size,
                ctx.reader,
                ctx.snapshot.maps,
                ctx.resolver,
                ctx.settings,
            )
        )
        if is_branch_like(inst.mnemonic):
            target = resolve_flow_target(
                inst.mnemonic,
                inst.operands,
                ctx.snapshot.regs,
            )
            if target is not None:
                target_text = format_addr(target, ptr_size)
                if ctx.resolver:
                    symbol = ctx.resolver.resolve(target)
                    if symbol:
                        target_text = f"{target_text} {format_symbol(symbol)}"
                comment_parts.append(f"target={target_text}")

        if comment_parts:
            comment = "; " + " | ".join(comment_parts)
            text += f" {pane.style(ctx, comment, 'comment')}"

    return text


def _fallthrough_addr(insts, current_idx: int, arch) -> int | None:
    if current_idx + 1 < len(insts):
        return insts[current_idx + 1].address
    current = insts[current_idx]
    if current.bytes:
        return current.address + len(current.bytes)
    if arch.max_inst_bytes:
        return current.address + arch.max_inst_bytes
    return None


def _bytes_texts(insts) -> list[str]:
    return [" ".join(f"{b:02x}" for b in inst.bytes) for inst in insts]


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
        left_text = _pad_line(_truncate_ansi(left[idx], left_width), left_width)
        right_text = _pad_line(_truncate_ansi(right[idx], right_width), right_width)
        gap = _branch_gap(pane, ctx, idx, taken)
        lines.append(f"{left_text}{gap}{right_text}".rstrip())
    return lines


def _branch_gap(pane: CodePane, ctx: PaneContext, row_idx: int, taken: bool) -> str:
    if row_idx != 0 or BRANCH_COLUMN_GAP < 2:
        return " " * BRANCH_COLUMN_GAP
    arrow = pane.style(ctx, "->", "arrow" if taken else "muted")
    padding = " " * max(BRANCH_COLUMN_GAP - 2, 0)
    return f"{padding}{arrow}"


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _truncate_ansi(text: str, width: int) -> str:
    if width <= 0:
        return ""
    plain = strip_ansi(text)
    if len(plain) <= width:
        return text
    if width <= 3:
        return plain[:width]

    target = width - 3
    out: list[str] = []
    visible = 0
    idx = 0
    had_ansi = False
    while idx < len(text) and visible < target:
        if text[idx] == "\x1b":
            match = _ANSI_RE.match(text, idx)
            if match:
                out.append(match.group(0))
                had_ansi = True
                idx = match.end()
                continue
        out.append(text[idx])
        visible += 1
        idx += 1
    out.append("...")
    if had_ansi:
        out.append(RESET)
    return "".join(out)


def _pad_line(text: str, width: int) -> str:
    length = len(strip_ansi(text))
    if length >= width:
        return text
    return text + (" " * (width - length))


def _max_visible_width(lines: list[str]) -> int:
    if not lines:
        return 0
    return max(len(strip_ansi(line)) for line in lines)


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
