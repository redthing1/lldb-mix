from __future__ import annotations

from typing import Any, Iterable


def run_command(debugger: Any, command: str) -> str:
    try:
        import lldb
    except Exception:
        return ""

    res = lldb.SBCommandReturnObject()
    debugger.GetCommandInterpreter().HandleCommand(command, res)
    return (res.GetOutput() or "") + (res.GetError() or "")


def parse_setting_value(output: str) -> str | None:
    collecting = False
    quote_char = ""
    parts: list[str] = []
    for line in output.splitlines():
        if "=" not in line:
            if collecting:
                if line.endswith(quote_char):
                    parts.append(line[:-1])
                    return "\n".join(parts)
                parts.append(line)
            continue
        value = line.split("=", 1)[1].strip()
        if not value:
            return value
        if value[0] not in ("'", '"'):
            return value
        quote_char = value[0]
        if len(value) >= 2 and value[-1] == quote_char:
            return value[1:-1]
        collecting = True
        parts.append(value[1:])
    if collecting:
        return "\n".join(parts)
    return None


def read_settings(debugger: Any, names: Iterable[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for name in names:
        value = parse_setting_value(run_command(debugger, f"settings show {name}"))
        if value is not None:
            values[name] = value
    return values


def set_settings(debugger: Any, values: dict[str, str], quoted: bool) -> None:
    for name, value in values.items():
        if quoted:
            escaped = value.replace('"', '\\"')
            run_command(debugger, f'settings set {name} "{escaped}"')
        else:
            run_command(debugger, f"settings set -- {name} {value}")
