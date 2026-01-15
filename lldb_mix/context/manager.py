from __future__ import annotations

from lldb_mix.context.panes.base import Pane
from lldb_mix.context.panes.code import CodePane
from lldb_mix.context.panes.flow import FlowPane
from lldb_mix.context.panes.regs import RegsPane
from lldb_mix.context.panes.stack import StackPane
from lldb_mix.context.panes.threads import ThreadsPane
from lldb_mix.context.types import PaneContext
from lldb_mix.core.settings import Settings
from lldb_mix.core.snapshot import ContextSnapshot
from lldb_mix.ui.terminal import get_terminal_size
from lldb_mix.ui.theme import Theme


class ContextManager:
    def __init__(self, settings: Settings, theme: Theme):
        self.settings = settings
        self.theme = theme
        self.last_regs: dict[str, int] = {}
        self.panes: dict[str, Pane] = {
            "regs": RegsPane(),
            "stack": StackPane(),
            "code": CodePane(),
            "flow": FlowPane(),
            "threads": ThreadsPane(),
        }

    def render(
        self,
        snapshot: ContextSnapshot,
        reader: object | None,
        resolver: object | None,
        target: object | None,
        process: object | None,
    ) -> list[str]:
        term_width, term_height = get_terminal_size()
        ctx = PaneContext(
            snapshot=snapshot,
            settings=self.settings,
            theme=self.theme,
            last_regs=self.last_regs,
            reader=reader,
            resolver=resolver,
            target=target,
            process=process,
            term_width=term_width,
            term_height=term_height,
        )
        lines: list[str] = []
        for pane_name in self.settings.layout:
            pane = self.panes.get(pane_name)
            if not pane:
                continue
            if lines:
                lines.append("")
            lines.extend(pane.render(ctx))
        self.last_regs = dict(snapshot.regs)
        return lines

    def show(
        self,
        snapshot: ContextSnapshot,
        reader: object | None,
        resolver: object | None,
        target: object | None,
        process: object | None,
    ) -> None:
        for line in self.render(snapshot, reader, resolver, target, process):
            print(line)
