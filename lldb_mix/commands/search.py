from __future__ import annotations

import argparse
import shlex

from lldb_mix.commands.utils import emit_result, module_fullpath
from lldb_mix.core.addressing import parse_int
from lldb_mix.core.memory import (
    ProcessMemoryReader,
    read_memory_regions,
    regions_unavailable_message,
)
from lldb_mix.core.session import Session
from lldb_mix.deref import format_addr


def cmd_findmem(debugger, command, result, internal_dict) -> None:
    try:
        import lldb
    except Exception:
        print("[lldb-mix] findmem not available outside LLDB")
        return

    args = shlex.split(command)
    if args and args[0] in ("-h", "--help", "help"):
        emit_result(result, _usage(), lldb)
        return

    parsed, error = _parse_args(args)
    if error == "help":
        emit_result(result, _usage(), lldb)
        return
    if error:
        emit_result(result, f"[lldb-mix] {error}\n{_usage()}", lldb)
        return

    session = Session(debugger)
    process = session.process()
    target = session.target()
    if not process or not target:
        emit_result(result, "[lldb-mix] process unavailable", lldb)
        return

    regions = read_memory_regions(process)
    if not regions:
        emit_result(result, regions_unavailable_message(process), lldb)
        return

    reader = ProcessMemoryReader(process)
    ptr_size = target.GetAddressByteSize() or 8
    header = f"[findmem] {parsed.kind} len={len(parsed.pattern)}"
    if parsed.count > 0:
        header += f" count={parsed.count}"

    lines = [header]
    hits = 0
    chunk_size = _chunk_size(len(parsed.pattern))
    for region in regions:
        if not region.read:
            continue
        if parsed.verbose:
            start = format_addr(region.start, ptr_size)
            end = format_addr(region.end, ptr_size)
            lines.append(f"[findmem] scanning {start}-{end}")
        carry = b""
        addr = region.start
        while addr < region.end:
            size = min(chunk_size, region.end - addr)
            data = reader.read(addr, size)
            if not data:
                break
            haystack = carry + data
            base = addr - len(carry)
            idx = haystack.find(parsed.pattern)
            while idx != -1:
                hit_addr = base + idx
                if region.start <= hit_addr < region.end:
                    hits += 1
                    lines.append(_format_hit(target, region, hit_addr, ptr_size, lldb))
                    if parsed.count > 0 and hits >= parsed.count:
                        emit_result(result, "\n".join(lines), lldb)
                        return
                idx = haystack.find(parsed.pattern, idx + 1)
            if len(parsed.pattern) > 1:
                carry = haystack[-(len(parsed.pattern) - 1) :]
            else:
                carry = b""
            addr += size

    if hits == 0:
        lines.append("(no matches)")
    emit_result(result, "\n".join(lines), lldb)


class _FindArgs:
    def __init__(
        self,
        pattern: bytes,
        kind: str,
        count: int,
        verbose: bool,
    ) -> None:
        self.pattern = pattern
        self.kind = kind
        self.count = count
        self.verbose = verbose


def _parse_args(args: list[str]) -> tuple[_FindArgs | None, str | None]:
    parser = argparse.ArgumentParser(add_help=False, prog="findmem")
    parser.add_argument("-s", "--string")
    parser.add_argument("-b", "--binary")
    parser.add_argument("-d", "--dword")
    parser.add_argument("-q", "--qword")
    parser.add_argument("-f", "--file")
    parser.add_argument("-c", "--count")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-h", "--help", action="store_true")

    try:
        opts = parser.parse_args(args)
    except SystemExit:
        return None, "invalid arguments"

    if opts.help:
        return None, "help"

    pattern, kind, err = _pattern_from_opts(opts)
    if err:
        return None, err

    count = -1
    if opts.count:
        parsed = parse_int(opts.count)
        if parsed is None or parsed <= 0:
            return None, "invalid count"
        count = parsed

    return (
        _FindArgs(pattern=pattern, kind=kind, count=count, verbose=opts.verbose),
        None,
    )


def _pattern_from_opts(opts) -> tuple[bytes | None, str, str | None]:
    chosen = [
        opts.string is not None,
        opts.binary is not None,
        opts.dword is not None,
        opts.qword is not None,
        opts.file is not None,
    ]
    if sum(chosen) != 1:
        return None, "", "select exactly one of -s/-b/-d/-q/-f"

    if opts.string is not None:
        pattern = opts.string.encode("utf-8")
        if not pattern:
            return None, "", "pattern is empty"
        return pattern, "string", None
    if opts.binary is not None:
        raw = opts.binary.strip().lower()
        if raw.startswith("0x"):
            raw = raw[2:]
        raw = raw.replace(" ", "")
        try:
            pattern = bytes.fromhex(raw)
            if not pattern:
                return None, "", "pattern is empty"
            return pattern, "binary", None
        except ValueError:
            return None, "", "invalid hex string"
    if opts.dword is not None:
        value = parse_int(opts.dword)
        if value is None:
            return None, "", "invalid dword"
        return (value & 0xFFFFFFFF).to_bytes(4, "little"), "dword", None
    if opts.qword is not None:
        value = parse_int(opts.qword)
        if value is None:
            return None, "", "invalid qword"
        return (value & 0xFFFFFFFFFFFFFFFF).to_bytes(8, "little"), "qword", None
    if opts.file is not None:
        try:
            with open(opts.file, "rb") as handle:
                pattern = handle.read()
                if not pattern:
                    return None, "", "pattern is empty"
                return pattern, "file", None
        except OSError:
            return None, "", f"failed to read file: {opts.file}"
    return None, "", "invalid pattern"


def _format_hit(target, region, addr: int, ptr_size: int, lldb_module) -> str:
    base = format_addr(region.start, ptr_size)
    offset = format_addr(addr - region.start, ptr_size)
    addr_text = format_addr(addr, ptr_size)
    prot = "".join(
        [
            "r" if region.read else "-",
            "w" if region.write else "-",
            "x" if region.execute else "-",
        ]
    )
    name = (region.name or "").strip()
    module_path = _module_path(target, addr, lldb_module)
    detail = f"base={base} off={offset} {prot}"
    if name:
        detail += f" {name}"
    if module_path:
        detail += f" {module_path}"
    return f"{addr_text} {detail}".rstrip()


def _module_path(target, addr: int, lldb_module) -> str:
    try:
        sbaddr = lldb_module.SBAddress(addr, target)
        module = sbaddr.GetModule()
        if module and module.IsValid():
            return module_fullpath(module)
    except Exception:
        return ""
    return ""


def _chunk_size(pattern_len: int) -> int:
    if pattern_len <= 0:
        return 0x10000
    return max(0x10000, pattern_len * 4)


def _usage() -> str:
    return (
        "[lldb-mix] usage: findmem -s <text> | -b <hex> | -d <dword> | -q <qword> | -f <path> "
        "[-c count] [-v]"
    )
