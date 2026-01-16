from __future__ import annotations

from lldb_mix.context.types import PaneContext
from lldb_mix.core.modules import format_module_offset
from lldb_mix.deref import format_addr, format_symbol
from lldb_mix.ui.ansi import strip_ansi
from lldb_mix.ui.style import colorize


def render_header(ctx: PaneContext) -> list[str]:
    term_width = max(ctx.term_width, 20)
    header = _build_header_line(ctx, term_width)
    sep = _separator_line(ctx, term_width)
    return [sep, header, sep]


def _build_header_line(ctx: PaneContext, term_width: int) -> str:
    snapshot = ctx.snapshot
    target = ctx.target
    process = ctx.process
    thread = _selected_thread(process)
    ptr_size = snapshot.arch.ptr_size or 8

    parts: list[tuple[str, str, str]] = []
    target_name = _target_name(target)
    if target_name:
        parts.append(("target", target_name, "value"))

    pid = _process_id(process)
    if pid is not None:
        parts.append(("pid", str(pid), "value"))

    tid = _thread_id(thread)
    if tid is not None:
        parts.append(("tid", str(tid), "value"))

    stop = _stop_reason(thread)
    if stop:
        parts.append(("stop", stop, "value"))

    if snapshot.has_pc():
        parts.append(("pc", format_addr(snapshot.pc, ptr_size), "addr"))

    sym_text = ""
    if snapshot.has_pc():
        if ctx.resolver:
            symbol = ctx.resolver.resolve(snapshot.pc)
            if symbol:
                sym_text = format_symbol(symbol)
        if not sym_text and target:
            sym_text = format_module_offset(target, snapshot.pc) or ""
    if sym_text:
        parts.append(("sym", sym_text, "symbol"))

    arch_text = snapshot.arch.name
    abi = getattr(snapshot.arch, "abi", None)
    if abi and getattr(abi, "name", ""):
        arch_text = f"{arch_text}/{abi.name}"
    if arch_text:
        parts.append(("arch", arch_text, "value"))

    sep_text = _style(ctx, " | ", "label")
    title = _style(ctx, "[lldb-mix]", "title")
    rendered: list[str] = [title]
    for key, value, role in parts:
        label = _style(ctx, f"{key}=", "label")
        rendered.append(label + _style(ctx, value, role))

    line = sep_text.join(rendered)
    return _truncate_line(line, term_width)


def _separator_line(ctx: PaneContext, term_width: int) -> str:
    return _style(ctx, "-" * term_width, "separator")


def _truncate_line(text: str, width: int) -> str:
    if width <= 0:
        return ""
    plain = strip_ansi(text)
    if len(plain) <= width:
        return text
    clipped = plain[: max(width - 3, 0)].rstrip()
    return f"{clipped}..."


def _style(ctx: PaneContext, text: str, role: str) -> str:
    return colorize(text, role, ctx.theme, ctx.settings.enable_color)


def _selected_thread(process):
    if not process:
        return None
    thread = process.GetSelectedThread()
    if not thread or not thread.IsValid():
        return None
    return thread


def _target_name(target) -> str:
    if not target:
        return ""
    try:
        spec = target.GetExecutable()
        if spec:
            name = spec.GetFilename() or ""
            if name:
                return name
    except Exception:
        return ""
    return ""


def _process_id(process) -> int | None:
    if not process:
        return None
    try:
        return int(process.GetProcessID())
    except Exception:
        return None


def _thread_id(thread) -> int | None:
    if not thread:
        return None
    try:
        return int(thread.GetIndexID())
    except Exception:
        return None


def _stop_reason(thread) -> str:
    if not thread:
        return ""
    try:
        desc = thread.GetStopDescription(256)
        if desc:
            return str(desc).strip()
    except Exception:
        pass
    try:
        import lldb

        reason = thread.GetStopReason()
        if reason == lldb.eStopReasonBreakpoint:
            return "breakpoint"
        if reason == lldb.eStopReasonWatchpoint:
            return "watchpoint"
        if reason == lldb.eStopReasonSignal:
            return "signal"
        if reason == lldb.eStopReasonException:
            return "exception"
        if reason == lldb.eStopReasonPlanComplete:
            return "plan-complete"
        if reason == lldb.eStopReasonThreadExiting:
            return "thread-exit"
    except Exception:
        pass
    return ""
