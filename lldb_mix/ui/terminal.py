from __future__ import annotations

import shutil


def get_terminal_size(default_cols: int = 120, default_rows: int = 40) -> tuple[int, int]:
    size = shutil.get_terminal_size(fallback=(default_cols, default_rows))
    return size.columns, size.lines
