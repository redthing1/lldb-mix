from __future__ import annotations

from dataclasses import dataclass

from lldb_mix.core.modules import (
    find_module,
    module_base,
    module_for_address,
    module_fullpath,
)
from lldb_mix.deref import format_addr


@dataclass(frozen=True)
class BreakpointSpec:
    kind: str
    address: str | None = None
    module: str | None = None
    offset: str | None = None
    name: str | None = None
    enabled: bool = True


def serialize_breakpoints(target) -> list[dict[str, object]]:
    specs: list[dict[str, object]] = []
    if not target or not target.IsValid():
        return specs
    for bp in target.breakpoint_iter():
        if not bp or not bp.IsValid():
            continue
        enabled = bool(bp.IsEnabled())
        count = bp.GetNumLocations()
        for idx in range(count):
            loc = bp.GetLocationAtIndex(idx)
            if not loc or not loc.IsValid():
                continue
            addr = _location_address(target, loc)
            if addr is None:
                continue
            spec = _spec_for_address(target, addr, enabled)
            specs.append(_spec_dict(spec))
    return specs


def apply_breakpoints(target, specs: list[dict[str, object]]) -> int:
    if not target or not target.IsValid():
        return 0
    created = 0
    for raw in specs:
        spec = _spec_from_dict(raw)
        bp = _apply_spec(target, spec)
        if bp and bp.IsValid():
            bp.SetEnabled(spec.enabled)
            created += 1
    return created


def clear_breakpoints(target) -> int:
    if not target or not target.IsValid():
        return 0
    removed = 0
    ids = [bp.GetID() for bp in target.breakpoint_iter()]
    for bp_id in ids:
        if target.BreakpointDelete(bp_id):
            removed += 1
    return removed


def format_breakpoint_list(target) -> list[str]:
    if not target or not target.IsValid():
        return ["[lldb-mix] target unavailable"]
    ptr_size = target.GetAddressByteSize() or 8
    lines = ["[lldb-mix] breakpoints:"]
    bps = list(target.breakpoint_iter())
    if not bps:
        lines.append("(none)")
        return lines
    for bp in bps:
        if not bp or not bp.IsValid():
            continue
        status = "enabled" if bp.IsEnabled() else "disabled"
        locs = bp.GetNumLocations()
        line = f"#{bp.GetID()} {status} locs={locs}"
        if locs > 0:
            loc = bp.GetLocationAtIndex(0)
            addr = _location_address(target, loc)
            if addr is not None:
                line += f" addr={format_addr(addr, ptr_size)}"
        lines.append(line)
    return lines


def _apply_spec(target, spec: BreakpointSpec):
    kind = spec.kind
    if kind == "name" and spec.name:
        return target.BreakpointCreateByName(spec.name)
    if kind == "module_offset" and spec.module and spec.offset:
        module = find_module(target, spec.module)
        if module:
            base = module_base(target, module)
            offset = _parse_int(spec.offset)
            if base is not None and offset is not None:
                return target.BreakpointCreateByAddress(base + offset)
    addr = _parse_int(spec.address) if spec.address else None
    if addr is not None:
        return target.BreakpointCreateByAddress(addr)
    return None


def _spec_for_address(target, addr: int, enabled: bool) -> BreakpointSpec:
    module = module_for_address(target, addr)
    if module:
        base = module_base(target, module)
        if base is not None and addr >= base:
            offset = addr - base
            module_path = module_fullpath(module)
            if module_path:
                return BreakpointSpec(
                    kind="module_offset",
                    address=_format_hex(addr),
                    module=module_path,
                    offset=_format_hex(offset),
                    enabled=enabled,
                )
    return BreakpointSpec(
        kind="address",
        address=_format_hex(addr),
        enabled=enabled,
    )


def _spec_dict(spec: BreakpointSpec) -> dict[str, object]:
    return {
        "kind": spec.kind,
        "address": spec.address,
        "module": spec.module,
        "offset": spec.offset,
        "name": spec.name,
        "enabled": spec.enabled,
    }


def _spec_from_dict(raw: dict[str, object]) -> BreakpointSpec:
    kind = raw.get("kind")
    if not isinstance(kind, str):
        kind = "address"
    address = raw.get("address")
    module = raw.get("module")
    offset = raw.get("offset")
    name = raw.get("name")
    enabled = raw.get("enabled")
    return BreakpointSpec(
        kind=kind,
        address=address if isinstance(address, str) else None,
        module=module if isinstance(module, str) else None,
        offset=offset if isinstance(offset, str) else None,
        name=name if isinstance(name, str) else None,
        enabled=bool(enabled) if isinstance(enabled, bool) else True,
    )


def _location_address(target, location) -> int | None:
    try:
        sbaddr = location.GetAddress()
    except Exception:
        return None
    if not sbaddr or not sbaddr.IsValid():
        return None
    try:
        addr = sbaddr.GetLoadAddress(target)
    except Exception:
        return None
    invalid = 0xFFFFFFFFFFFFFFFF
    try:
        import lldb

        invalid = getattr(lldb, "LLDB_INVALID_ADDRESS", invalid)
    except Exception:
        pass
    if addr in (invalid, 0xFFFFFFFFFFFFFFFF):
        return None
    return addr


def _format_hex(value: int) -> str:
    return f"0x{value:x}"


def _parse_int(text: str) -> int | None:
    try:
        return int(text, 0)
    except (TypeError, ValueError):
        return None
