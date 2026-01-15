from __future__ import annotations

import hashlib
import os
import string
import sys


_SAFE_CHARS = set(string.ascii_letters + string.digits + "._-")


def config_dir() -> str:
    kind = _platform_kind()
    if kind == "darwin":
        base = os.path.join(
            os.path.expanduser("~"),
            "Library",
            "Application Support",
        )
        return os.path.join(base, "lldb-mix")
    if kind == "windows":
        base = os.environ.get("APPDATA") or os.environ.get("LOCALAPPDATA")
        if not base:
            base = os.path.expanduser("~")
        return os.path.join(base, "lldb-mix")
    root = os.environ.get("XDG_CONFIG_HOME")
    if not root:
        root = os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(root, "lldb-mix")


def config_path() -> str:
    return os.path.join(config_dir(), "config.json")


def state_dir() -> str:
    kind = _platform_kind()
    if kind == "darwin":
        return config_dir()
    if kind == "windows":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if not base:
            base = os.path.expanduser("~")
        return os.path.join(base, "lldb-mix")
    root = os.environ.get("XDG_STATE_HOME")
    if not root:
        root = os.path.join(os.path.expanduser("~"), ".local", "state")
    return os.path.join(root, "lldb-mix")


def sessions_dir() -> str:
    return os.path.join(state_dir(), "sessions")


def session_path(target) -> str:
    name = _session_filename(target_path(target))
    return os.path.join(sessions_dir(), name)


def _platform_kind() -> str:
    if sys.platform == "darwin":
        return "darwin"
    if os.name == "nt":
        return "windows"
    if sys.platform.startswith("linux"):
        return "linux"
    if os.name == "posix":
        return "posix"
    return "other"


def target_path(target) -> str:
    if isinstance(target, str):
        return target
    if target is None:
        return ""
    try:
        spec = target.GetExecutable()
    except Exception:
        spec = None
    if spec:
        path = _filespec_path(spec)
        if path:
            return path
    return ""


def _filespec_path(spec) -> str:
    if not spec:
        return ""
    try:
        path = spec.GetPath() or ""
    except Exception:
        path = ""
    if path:
        return path
    try:
        filename = spec.GetFilename() or ""
    except Exception:
        filename = ""
    try:
        directory = spec.GetDirectory() or ""
    except Exception:
        directory = ""
    if directory and filename:
        return f"{directory}/{filename}"
    return filename


def _session_filename(path: str) -> str:
    text = path or "unknown"
    base = os.path.basename(text) or "target"
    safe_base = _sanitize_filename(base)
    digest = hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:8]
    return f"{safe_base}-{digest}.json"


def _sanitize_filename(name: str) -> str:
    out = []
    for ch in name:
        out.append(ch if ch in _SAFE_CHARS else "_")
    cleaned = "".join(out).strip("._")
    return cleaned or "target"
