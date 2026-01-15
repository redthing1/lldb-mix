from __future__ import annotations

PREFIX = "[lldb-mix]"


def _emit(level: str, msg: str) -> None:
    if level:
        print(f"{PREFIX} {level}: {msg}")
    else:
        print(f"{PREFIX} {msg}")


def banner(msg: str) -> None:
    _emit("", msg)


def info(msg: str) -> None:
    _emit("info", msg)


def warn(msg: str) -> None:
    _emit("warn", msg)


def err(msg: str) -> None:
    _emit("error", msg)
