from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, fields
from typing import Callable

from lldb_mix.arch.abi import ABI_BY_NAME
from lldb_mix.core.paths import config_dir, config_path
from lldb_mix.core.settings import Settings
from lldb_mix.ui.theme import THEMES


@dataclass(frozen=True)
class SettingSpec:
    key: str
    attr: str
    type_name: str
    parse: Callable[[list[str]], object]
    format: Callable[[object], str]
    validate: Callable[[object], bool] | None = None


def load_settings(settings: Settings) -> bool:
    path = config_path()
    if not path:
        return False
    if not os.path.isfile(path):
        return False

    try:
        with open(path, "r") as handle:
            data = json.load(handle)
    except Exception:
        return False

    if not isinstance(data, dict):
        return False

    _apply_settings(settings, data)
    return True


def save_settings(settings: Settings) -> bool:
    path = config_path()
    if not path:
        return False
    os.makedirs(config_dir(), exist_ok=True)
    data = _settings_dict(settings)
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            dir=config_dir(),
            delete=False,
        ) as handle:
            json.dump(data, handle, indent=2)
            tmp_name = handle.name
        os.replace(tmp_name, path)
    except Exception:
        return False
    return True


def list_specs() -> list[SettingSpec]:
    return list(_SPECS)


def get_setting(settings: Settings, key: str) -> object | None:
    spec = _spec_by_key().get(key)
    if not spec:
        return None
    return getattr(settings, spec.attr)


def set_setting(settings: Settings, key: str, tokens: list[str]) -> tuple[bool, str]:
    spec = _spec_by_key().get(key)
    if not spec:
        return False, f"unknown setting: {key}"
    try:
        value = spec.parse(tokens)
    except ValueError as exc:
        return False, str(exc) or "invalid value"
    if spec.validate and not spec.validate(value):
        return False, "invalid value"
    setattr(settings, spec.attr, value)
    return True, spec.format(value)


def format_setting(settings: Settings, key: str) -> str | None:
    spec = _spec_by_key().get(key)
    if not spec:
        return None
    value = getattr(settings, spec.attr)
    return spec.format(value)


def reset_settings(settings: Settings) -> None:
    defaults = Settings()
    for field in fields(Settings):
        setattr(settings, field.name, getattr(defaults, field.name))


def _settings_dict(settings: Settings) -> dict[str, object]:
    data: dict[str, object] = {}
    for spec in _SPECS:
        data[spec.key] = getattr(settings, spec.attr)
    return data


def _apply_settings(settings: Settings, data: dict[str, object]) -> None:
    for spec in _SPECS:
        if spec.key not in data:
            continue
        value = data[spec.key]
        if spec.key == "layout":
            value = _normalize_layout(value)
            if not value:
                continue
            setattr(settings, spec.attr, value)
            continue
        if spec.validate and not spec.validate(value):
            continue
        setattr(settings, spec.attr, value)


def _spec_by_key() -> dict[str, SettingSpec]:
    return {spec.key: spec for spec in _SPECS}


def _normalize_layout(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            item = str(item)
        token = item.strip().lower()
        if not token or token in seen:
            continue
        seen.add(token)
        normalized.append(token)
    return normalized


def _parse_bool(tokens: list[str]) -> bool:
    if len(tokens) != 1:
        raise ValueError("expected one value")
    value = tokens[0].strip().lower()
    if value in ("1", "true", "on", "yes"):
        return True
    if value in ("0", "false", "off", "no"):
        return False
    raise ValueError("invalid boolean (use on/off)")


def _parse_int(tokens: list[str]) -> int:
    if len(tokens) != 1:
        raise ValueError("expected one value")
    try:
        return int(tokens[0], 0)
    except ValueError as exc:
        raise ValueError("invalid integer") from exc


def _parse_str(tokens: list[str]) -> str:
    if len(tokens) != 1:
        raise ValueError("expected one value")
    return tokens[0]


def _parse_layout(tokens: list[str]) -> list[str]:
    if not tokens:
        raise ValueError("layout requires at least one pane")
    return _normalize_layout(tokens)


def _parse_theme(tokens: list[str]) -> str:
    if len(tokens) != 1:
        raise ValueError("expected one value")
    name = tokens[0]
    if name not in THEMES:
        choices = ", ".join(sorted(THEMES.keys()))
        raise ValueError(f"unknown theme (choices: {choices})")
    return name


def _parse_abi(tokens: list[str]) -> str:
    if len(tokens) != 1:
        raise ValueError("expected one value")
    name = tokens[0].strip().lower()
    if name == "auto":
        return name
    if name not in ABI_BY_NAME:
        choices = ", ".join(["auto"] + sorted(ABI_BY_NAME.keys()))
        raise ValueError(f"unknown abi (choices: {choices})")
    return name


def _fmt_bool(value: object) -> str:
    return "on" if bool(value) else "off"


def _fmt_list(value: object) -> str:
    if not isinstance(value, list):
        return ""
    return " ".join(value)


def _fmt_value(value: object) -> str:
    return str(value)


def _is_bool(value: object) -> bool:
    return isinstance(value, bool)


def _is_str(value: object) -> bool:
    return isinstance(value, str)


def _is_int(value: object, min_value: int | None = None) -> bool:
    if not isinstance(value, int):
        return False
    if min_value is None:
        return True
    return value >= min_value


def _is_int_positive(value: object) -> bool:
    return _is_int(value, min_value=1)


def _is_int_nonneg(value: object) -> bool:
    return _is_int(value, min_value=0)


def _is_layout(value: object) -> bool:
    if not isinstance(value, list):
        return False
    if not value:
        return False
    return all(isinstance(item, str) and item.strip() for item in value)


def _is_theme(value: object) -> bool:
    return isinstance(value, str) and value in THEMES


def _is_abi(value: object) -> bool:
    return isinstance(value, str) and (value == "auto" or value in ABI_BY_NAME)


_SPECS: list[SettingSpec] = [
    SettingSpec(
        key="enable_color",
        attr="enable_color",
        type_name="bool",
        parse=_parse_bool,
        format=_fmt_bool,
        validate=_is_bool,
    ),
    SettingSpec(
        key="theme",
        attr="theme",
        type_name="theme",
        parse=_parse_theme,
        format=_fmt_value,
        validate=_is_theme,
    ),
    SettingSpec(
        key="layout",
        attr="layout",
        type_name="list",
        parse=_parse_layout,
        format=_fmt_list,
        validate=_is_layout,
    ),
    SettingSpec(
        key="abi",
        attr="abi",
        type_name="abi",
        parse=_parse_abi,
        format=_fmt_value,
        validate=_is_abi,
    ),
    SettingSpec(
        key="aggressive_deref",
        attr="aggressive_deref",
        type_name="bool",
        parse=_parse_bool,
        format=_fmt_bool,
        validate=_is_bool,
    ),
    SettingSpec(
        key="max_deref_depth",
        attr="max_deref_depth",
        type_name="int",
        parse=_parse_int,
        format=_fmt_value,
        validate=_is_int_nonneg,
    ),
    SettingSpec(
        key="max_string_length",
        attr="max_string_length",
        type_name="int",
        parse=_parse_int,
        format=_fmt_value,
        validate=_is_int_positive,
    ),
    SettingSpec(
        key="auto_context",
        attr="auto_context",
        type_name="bool",
        parse=_parse_bool,
        format=_fmt_bool,
        validate=_is_bool,
    ),
    SettingSpec(
        key="clear_screen",
        attr="clear_screen",
        type_name="bool",
        parse=_parse_bool,
        format=_fmt_bool,
        validate=_is_bool,
    ),
    SettingSpec(
        key="stack_lines",
        attr="stack_lines",
        type_name="int",
        parse=_parse_int,
        format=_fmt_value,
        validate=_is_int_nonneg,
    ),
    SettingSpec(
        key="stack_frame_lines",
        attr="stack_frame_lines",
        type_name="int",
        parse=_parse_int,
        format=_fmt_value,
        validate=_is_int_nonneg,
    ),
    SettingSpec(
        key="memory_window_bytes",
        attr="memory_window_bytes",
        type_name="int",
        parse=_parse_int,
        format=_fmt_value,
        validate=_is_int_positive,
    ),
    SettingSpec(
        key="memory_bytes_per_line",
        attr="memory_bytes_per_line",
        type_name="int",
        parse=_parse_int,
        format=_fmt_value,
        validate=_is_int_positive,
    ),
    SettingSpec(
        key="code_lines_before",
        attr="code_lines_before",
        type_name="int",
        parse=_parse_int,
        format=_fmt_value,
        validate=_is_int_nonneg,
    ),
    SettingSpec(
        key="code_lines_after",
        attr="code_lines_after",
        type_name="int",
        parse=_parse_int,
        format=_fmt_value,
        validate=_is_int_nonneg,
    ),
    SettingSpec(
        key="show_opcodes",
        attr="show_opcodes",
        type_name="bool",
        parse=_parse_bool,
        format=_fmt_bool,
        validate=_is_bool,
    ),
]
