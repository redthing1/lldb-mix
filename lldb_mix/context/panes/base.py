from __future__ import annotations

from lldb_mix.context.types import PaneContext
from lldb_mix.ui.style import colorize


class Pane:
    name = ""
    full_width = False

    def title(self, ctx: PaneContext | None = None) -> str:
        text = f"[{self.name}]"
        if ctx is None:
            return text
        return colorize(text, "title", ctx.theme, ctx.settings.enable_color)

    def style(self, ctx: PaneContext, text: str, role: str) -> str:
        return colorize(text, role, ctx.theme, ctx.settings.enable_color)

    def render(self, ctx: PaneContext) -> list[str]:
        return [self.title(ctx), "(not implemented)"]
