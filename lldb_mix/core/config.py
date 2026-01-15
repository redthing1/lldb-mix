from __future__ import annotations

import json
import os
import tempfile

from lldb_mix.core.settings import Settings

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".lldb-mix")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")


def load_settings(settings: Settings) -> bool:
    if not os.path.isfile(CONFIG_PATH):
        return False

    try:
        with open(CONFIG_PATH, "r") as handle:
            data = json.load(handle)
    except Exception:
        return False

    _apply_settings(settings, data)
    return True


def save_settings(settings: Settings) -> bool:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    data = _settings_dict(settings)
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            dir=CONFIG_DIR,
            delete=False,
        ) as handle:
            json.dump(data, handle, indent=2)
            tmp_name = handle.name
        os.replace(tmp_name, CONFIG_PATH)
    except Exception:
        return False
    return True


def _settings_dict(settings: Settings) -> dict[str, object]:
    return {
        "enable_color": settings.enable_color,
        "theme": settings.theme,
        "layout": list(settings.layout),
        "aggressive_deref": settings.aggressive_deref,
        "max_deref_depth": settings.max_deref_depth,
        "max_string_length": settings.max_string_length,
        "auto_context": settings.auto_context,
        "stack_lines": settings.stack_lines,
        "memory_window_bytes": settings.memory_window_bytes,
        "memory_bytes_per_line": settings.memory_bytes_per_line,
        "code_lines_before": settings.code_lines_before,
        "code_lines_after": settings.code_lines_after,
        "show_opcodes": settings.show_opcodes,
    }


def _apply_settings(settings: Settings, data: dict[str, object]) -> None:
    if isinstance(data.get("layout"), list):
        settings.layout = [str(x) for x in data["layout"]]
    if isinstance(data.get("enable_color"), bool):
        settings.enable_color = data["enable_color"]
    if isinstance(data.get("theme"), str):
        settings.theme = data["theme"]
    if isinstance(data.get("aggressive_deref"), bool):
        settings.aggressive_deref = data["aggressive_deref"]
    if isinstance(data.get("max_deref_depth"), int):
        settings.max_deref_depth = data["max_deref_depth"]
    if isinstance(data.get("max_string_length"), int):
        settings.max_string_length = data["max_string_length"]
    if isinstance(data.get("auto_context"), bool):
        settings.auto_context = data["auto_context"]
    if isinstance(data.get("stack_lines"), int):
        settings.stack_lines = data["stack_lines"]
    if isinstance(data.get("memory_window_bytes"), int):
        settings.memory_window_bytes = data["memory_window_bytes"]
    if isinstance(data.get("memory_bytes_per_line"), int):
        settings.memory_bytes_per_line = data["memory_bytes_per_line"]
    if isinstance(data.get("code_lines_before"), int):
        settings.code_lines_before = data["code_lines_before"]
    if isinstance(data.get("code_lines_after"), int):
        settings.code_lines_after = data["code_lines_after"]
    if isinstance(data.get("show_opcodes"), bool):
        settings.show_opcodes = data["show_opcodes"]
