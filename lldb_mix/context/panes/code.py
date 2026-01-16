from __future__ import annotations

import re

from lldb_mix.context.panes.base import Pane
from lldb_mix.context.types import PaneContext
from lldb_mix.core.disasm import read_instructions_around
from lldb_mix.core.flow import is_branch_like, resolve_flow_target
from lldb_mix.deref import (
    classify_token,
    deref_chain,
    format_addr,
    format_symbol,
    summarize_chain,
)


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
        bytes_texts: list[str] = []
        if ctx.settings.show_opcodes:
            for inst in insts:
                bytes_texts.append(" ".join(f"{b:02x}" for b in inst.bytes))
            bytes_pad = max((len(text) for text in bytes_texts), default=0)

        for idx, inst in enumerate(insts):
            prefix = "=>" if inst.address == pc else "  "
            addr_text = format_addr(inst.address, ptr_size)
            bytes_text = ""
            if ctx.settings.show_opcodes:
                bytes_text = bytes_texts[idx]
                bytes_text = f"{bytes_text:<{bytes_pad}}" if bytes_text else ""

            prefix_role = "pc_marker" if inst.address == pc else "muted"
            prefix_colored = self.style(ctx, prefix, prefix_role)
            addr_colored = self.style(ctx, addr_text, "addr")
            bytes_colored = self.style(ctx, bytes_text, "opcode") if bytes_text else ""
            mnemonic_colored = self.style(ctx, inst.mnemonic, "mnemonic")

            text = f"{prefix_colored} {addr_colored} "
            if bytes_colored:
                text += bytes_colored
                text += " "
            text += mnemonic_colored
            if inst.operands:
                text += f" {inst.operands}"

            comment_parts: list[str] = []
            if inst.address == pc:
                hint = _branch_taken_hint(
                    inst.mnemonic, inst.operands, snapshot.regs, arch, flags
                )
                if hint:
                    comment_parts.append(hint)
                comment_parts.extend(
                    _operand_annotations(
                        inst.operands,
                        snapshot.regs,
                        ptr_size,
                        ctx.reader,
                        snapshot.maps,
                        ctx.resolver,
                        ctx.settings,
                    )
                )
                if is_branch_like(inst.mnemonic):
                    target = resolve_flow_target(
                        inst.mnemonic, inst.operands, snapshot.regs
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
                text += f" {self.style(ctx, comment, 'comment')}"
            lines.append(text)

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
        summary = _annotation_for_addr(value, reader, regions, resolver, settings, ptr_size)
        if summary:
            pieces.append(f"{display}={addr_text}->{summary}")
        else:
            pieces.append(f"{display}={addr_text}")

    mem_addr = _compute_mem_addr(operands, regs, pattern)
    if mem_addr is not None:
        mem_text = format_addr(mem_addr, ptr_size)
        summary = _annotation_for_addr(mem_addr, reader, regions, resolver, settings, ptr_size)
        if summary:
            pieces.append(f"mem={mem_text}->{summary}")
        else:
            pieces.append(f"mem={mem_text}")
    return pieces


def _annotation_for_addr(addr, reader, regions, resolver, settings, ptr_size: int) -> str | None:
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
    if arch.is_conditional_branch(mnemonic):
        taken, reason = arch.branch_taken(mnemonic, flags)
        if reason:
            return f"{'taken' if taken else 'not taken'} ({reason})"
        return "taken" if taken else "not taken"

    mnem = mnemonic.lower()
    if mnem in {"cbz", "cbnz"}:
        reg = operands.split(",", 1)[0].strip()
        value = _reg_value(reg, regs)
        if value is None:
            return None
        taken = (value == 0) if mnem == "cbz" else (value != 0)
        return f"{'taken' if taken else 'not taken'} ({reg}={'0' if value == 0 else '!=0'})"

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
        return f"{'taken' if taken else 'not taken'} ({reg}[{bit}]={bit_set})"

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
