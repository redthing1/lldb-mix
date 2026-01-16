from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Settings:
    enable_color: bool = True
    theme: str = "base"
    layout: list[str] = field(default_factory=lambda: ["regs", "args", "stack", "code"])
    abi: str = "auto"
    aggressive_deref: bool = True
    pointer_mode: str = "smart"
    max_deref_depth: int = 6
    max_string_length: int = 64
    auto_context: bool = True
    clear_screen: bool = False
    stack_lines: int = 8
    stack_frame_lines: int = 2
    memory_window_bytes: int = 64
    memory_bytes_per_line: int = 16
    code_lines_before: int = 3
    code_lines_after: int = 6
    show_opcodes: bool = True
