from __future__ import annotations

PROMPT_TEXT = "mix> "
PROMPT_COMMANDS = (
    f'settings set prompt "{PROMPT_TEXT}"',
    "settings set use-color false",
    'settings set -f -- prompt-ansi-prefix ""',
    'settings set -f -- prompt-ansi-suffix ""',
    "settings set show-statusline false",
)
