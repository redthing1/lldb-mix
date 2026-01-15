from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass

from lldb_mix.core.breakpoints import apply_breakpoints, serialize_breakpoints
from lldb_mix.core.paths import session_path, sessions_dir, target_path
from lldb_mix.core.watchlist import WatchList


@dataclass(frozen=True)
class SessionData:
    target_path: str
    breakpoints: list[dict[str, object]]
    watches: list[dict[str, object]]


def build_session_data(target, watchlist: WatchList) -> dict[str, object]:
    return {
        "version": 1,
        "target": {"path": target_path(target)},
        "breakpoints": serialize_breakpoints(target),
        "watches": watchlist.serialize(),
    }


def save_session(path: str, data: dict[str, object]) -> bool:
    if not path:
        return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            dir=os.path.dirname(path),
            delete=False,
        ) as handle:
            json.dump(data, handle, indent=2)
            tmp_name = handle.name
        os.replace(tmp_name, path)
    except Exception:
        return False
    return True


def load_session(path: str) -> dict[str, object] | None:
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, "r") as handle:
            data = json.load(handle)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return data


def apply_session(target, watchlist: WatchList, data: dict[str, object]) -> tuple[int, int]:
    if not data:
        return 0, 0
    raw_bps = data.get("breakpoints")
    raw_watches = data.get("watches")
    bps = raw_bps if isinstance(raw_bps, list) else []
    watches = raw_watches if isinstance(raw_watches, list) else []
    count = apply_breakpoints(target, bps)
    watchlist.load(watches)
    return count, len(watchlist.items())


def default_session_path(target) -> str:
    if not target:
        return ""
    return session_path(target)


def list_sessions() -> list[str]:
    root = sessions_dir()
    if not os.path.isdir(root):
        return []
    return sorted(
        name for name in os.listdir(root) if name.endswith(".json")
    )
