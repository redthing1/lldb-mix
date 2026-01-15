from __future__ import annotations

from dataclasses import dataclass

from lldb_mix.core.settings import Settings
from lldb_mix.core.snapshot import ContextSnapshot
from lldb_mix.core.watchlist import WatchList
from lldb_mix.ui.theme import Theme


@dataclass
class PaneContext:
    snapshot: ContextSnapshot
    settings: Settings
    theme: Theme
    last_regs: dict[str, int]
    reader: object | None
    resolver: object | None
    target: object | None
    process: object | None
    watchlist: WatchList
    term_width: int
    term_height: int
