from __future__ import annotations

import os

from lldb_mix.context.panes.base import Pane
from lldb_mix.context.types import PaneContext


class SourcePane(Pane):
    name = "source"
    full_width = True

    def visible(self, ctx: PaneContext) -> bool:
        info = _source_info(ctx)
        if not info:
            return False
        path, _ = info
        return bool(path and os.path.isfile(path))

    def render(self, ctx: PaneContext) -> list[str]:
        info = _source_info(ctx)
        if not info:
            return []

        path, line = info
        path = _resolve_path(path)
        file_name = os.path.basename(path) if path else ""

        header = self.style(ctx, "[source]", "title")
        if file_name and line > 0:
            location = self.style(ctx, f"{file_name}:{line}", "label")
            header = f"{header} {location}"

        lines = [header]
        if not path or not os.path.isfile(path):
            lines.append(self.style(ctx, "(source unavailable)", "muted"))
            return lines

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as handle:
                source_lines = handle.readlines()
        except OSError:
            lines.append(self.style(ctx, "(source unavailable)", "muted"))
            return lines

        total = len(source_lines)
        if line <= 0 or line > total:
            lines.append(self.style(ctx, "(source unavailable)", "muted"))
            return lines

        before = max(ctx.settings.code_lines_before, 0)
        after = max(ctx.settings.code_lines_after, 0)
        start = max(1, line - before)
        end = min(total, line + after)
        number_width = len(str(end))

        for lineno in range(start, end + 1):
            text = source_lines[lineno - 1].rstrip("\n").expandtabs(4)
            prefix = "=>" if lineno == line else "  "
            prefix_role = "pc_marker" if lineno == line else "muted"
            number_role = "label" if lineno == line else "muted"
            prefix_text = self.style(ctx, prefix, prefix_role)
            number_text = self.style(ctx, f"{lineno:>{number_width}}", number_role)
            lines.append(f"{prefix_text} {number_text} {text}")

        return lines


def _resolve_path(path: str) -> str:
    if not path:
        return ""
    if os.path.isabs(path):
        return path
    candidate = os.path.abspath(path)
    if os.path.isfile(candidate):
        return candidate
    return path


def _source_info(ctx: PaneContext) -> tuple[str, int] | None:
    process = ctx.process
    if not process:
        return None
    thread = process.GetSelectedThread()
    if not thread or not thread.IsValid():
        return None
    frame = thread.GetSelectedFrame()
    if not frame or not frame.IsValid():
        return None
    line_entry = frame.GetLineEntry()
    if not line_entry or not line_entry.IsValid():
        return None
    line = line_entry.GetLine()
    if line <= 0:
        return None
    file_spec = line_entry.GetFileSpec()
    path = _file_spec_path(file_spec)
    if not path:
        return None
    return path, line


def _file_spec_path(file_spec) -> str:
    if not file_spec:
        return ""
    try:
        path = file_spec.GetPath()
    except Exception:
        path = ""
    if path:
        return path
    directory = ""
    filename = ""
    try:
        directory = file_spec.GetDirectory() or ""
    except Exception:
        directory = ""
    try:
        filename = file_spec.GetFilename() or ""
    except Exception:
        filename = ""
    if directory and filename:
        return os.path.join(directory, filename)
    return filename
