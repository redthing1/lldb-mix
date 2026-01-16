from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lldb_mix.arch.view import ArchView


@dataclass(frozen=True)
class AddressResolver:
    regs: dict[str, int]
    arch: ArchView | None = None
    frame: Any | None = None

    def resolve(self, token: str | None, allow_expression: bool = True) -> int | None:
        if token:
            addr = resolve_addr(token, self.regs, self.arch)
            if addr is not None:
                return addr
            if allow_expression and self.frame:
                return eval_expression(self.frame, token)
            return None
        return default_addr(self.regs, self.arch)

    def default(self) -> int | None:
        return default_addr(self.regs, self.arch)


def parse_int(text: str) -> int | None:
    try:
        return int(text, 0)
    except ValueError:
        return None


def eval_expression(frame, expr: str) -> int | None:
    if not frame or not expr:
        return None
    try:
        value = frame.EvaluateExpression(expr)
    except Exception:
        return None
    if not value or not value.IsValid():
        return None
    try:
        error = value.GetError()
        if error and not error.Success():
            return None
    except Exception:
        pass
    try:
        return int(value.GetValueAsUnsigned())
    except Exception:
        try:
            raw = value.GetValue()
            return int(raw, 0) if raw else None
        except Exception:
            return None


def default_addr(regs: dict[str, int], arch: ArchView | None = None) -> int | None:
    sp = _pick_special("sp", regs, arch, require_nonzero=True)
    if sp is not None:
        return sp
    pc = _pick_special("pc", regs, arch, require_nonzero=True)
    if pc is not None:
        return pc
    sp = _pick_special("sp", regs, arch, require_nonzero=False)
    if sp is not None:
        return sp
    return _pick_special("pc", regs, arch, require_nonzero=False)


def resolve_addr(token: str, regs: dict[str, int], arch: ArchView | None = None) -> int | None:
    cleaned = token.strip()
    if cleaned.startswith("$"):
        cleaned = cleaned[1:]
    key = cleaned.lower()
    if key == "sp":
        return _pick_special("sp", regs, arch, require_nonzero=False)
    if key == "pc":
        return _pick_special("pc", regs, arch, require_nonzero=False)
    reg_key = _resolve_reg(key, regs, arch)
    if reg_key is not None:
        return regs[reg_key]
    parsed = parse_int(cleaned)
    if parsed is not None:
        return parsed
    return None


def _resolve_reg(name: str, regs: dict[str, int], arch: ArchView | None) -> str | None:
    key = name.lower()
    if key in regs:
        return key
    if arch is not None:
        try:
            aliases = arch.register_aliases(regs)
        except Exception:
            aliases = {}
        alias = aliases.get(key)
        if alias and alias in regs:
            return alias
    return None


def _pick_special(
    kind: str, regs: dict[str, int], arch: ArchView | None, require_nonzero: bool
) -> int | None:
    if arch is not None:
        if kind == "sp":
            if arch.sp_value is not None and (not require_nonzero or arch.sp_value != 0):
                return arch.sp_value
            key = arch.sp_reg
            if key:
                reg_key = _resolve_reg(key, regs, arch)
                if reg_key is not None:
                    value = regs[reg_key]
                    if not require_nonzero or value != 0:
                        return value
        if kind == "pc":
            if arch.pc_value is not None and (not require_nonzero or arch.pc_value != 0):
                return arch.pc_value
            key = arch.pc_reg
            if key:
                reg_key = _resolve_reg(key, regs, arch)
                if reg_key is not None:
                    value = regs[reg_key]
                    if not require_nonzero or value != 0:
                        return value
    if kind == "sp":
        return _pick_reg(("sp", "rsp", "esp"), regs, require_nonzero=require_nonzero)
    return _pick_reg(("pc", "rip", "eip"), regs, require_nonzero=require_nonzero)


def _pick_reg(
    candidates: tuple[str, ...],
    regs: dict[str, int],
    require_nonzero: bool,
) -> int | None:
    for name in candidates:
        if name not in regs:
            continue
        value = regs[name]
        if require_nonzero and value == 0:
            continue
        return value
    return None
