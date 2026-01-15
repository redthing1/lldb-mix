from __future__ import annotations

import shutil
import sys


def get_terminal_size(default_cols: int = 120, default_rows: int = 40) -> tuple[int, int]:
    size = shutil.get_terminal_size(fallback=(default_cols, default_rows))
    return size.columns, size.lines


def clear_screen_code() -> str:
    return "\x1b[2J\x1b[H"


def clear_screen() -> None:
    sys.stdout.write(clear_screen_code())
    sys.stdout.flush()
