from __future__ import annotations

from lldb_mix.core.patches import PatchStore
from lldb_mix.core.settings import Settings
from lldb_mix.core.watchlist import WatchList
from lldb_mix.ui.theme import get_theme

SETTINGS = Settings()
THEME = get_theme(SETTINGS.theme)
WATCHLIST = WatchList()
PATCHES = PatchStore()
