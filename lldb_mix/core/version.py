from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class LldbVersion:
    variant: str
    major: int
    minor: int
    raw: str


def parse_lldb_version(version_string: str) -> LldbVersion:
    apple_pattern = r"lldb-(\d+)(?:\.(\d+))?(?:\.(\d+))?"
    clang_pattern = r"lldb version (\d+)(?:\.(\d+))?(?:\.(\d+))?"

    apple_match = re.search(apple_pattern, version_string, re.IGNORECASE)
    if apple_match:
        major = int(apple_match.group(1))
        minor = int(apple_match.group(2) or 0)
        return LldbVersion("apple", major, minor, version_string)

    clang_match = re.search(clang_pattern, version_string, re.IGNORECASE)
    if clang_match:
        major = int(clang_match.group(1))
        minor = int(clang_match.group(2) or 0)
        return LldbVersion("clang", major, minor, version_string)

    return LldbVersion("unknown", 0, 0, version_string)
