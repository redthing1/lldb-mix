#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


_MARK_BEGIN = "# lldb-mix begin"
_MARK_END = "# lldb-mix end"


def _lldbinit_path() -> Path:
    return Path.home() / ".lldbinit"


def _render_block(loader_path: Path) -> list[str]:
    return [
        _MARK_BEGIN,
        f'command script import "{loader_path}"',
        _MARK_END,
    ]


def _install_block(path: Path, block: list[str]) -> None:
    existing: list[str] = []
    if path.exists():
        existing = path.read_text().splitlines()

    out: list[str] = []
    in_block = False
    for line in existing:
        if line.strip() == _MARK_BEGIN:
            in_block = True
            continue
        if line.strip() == _MARK_END:
            in_block = False
            continue
        if not in_block:
            out.append(line)

    if out and out[-1].strip():
        out.append("")
    out.extend(block)
    path.write_text("\n".join(out) + "\n")


def _remove_block(path: Path) -> bool:
    if not path.exists():
        return False
    existing = path.read_text().splitlines()
    out: list[str] = []
    in_block = False
    removed = False
    for line in existing:
        if line.strip() == _MARK_BEGIN:
            in_block = True
            removed = True
            continue
        if line.strip() == _MARK_END:
            in_block = False
            continue
        if not in_block:
            out.append(line)
    if removed:
        path.write_text("\n".join(out) + ("\n" if out else ""))
    return removed


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Register lldb-mix in ~/.lldbinit."
    )
    parser.add_argument(
        "--print",
        action="store_true",
        help="Print the block instead of writing ~/.lldbinit.",
    )
    parser.add_argument(
        "--remove",
        action="store_true",
        help="Remove the lldb-mix block from ~/.lldbinit.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    loader = repo_root / "lldb_mix_loader.py"
    if not loader.is_file():
        raise SystemExit(f"missing loader: {loader}")

    block = _render_block(loader)
    if args.print:
        print("\n".join(block))
        return

    path = _lldbinit_path()
    if args.remove:
        removed = _remove_block(path)
        if removed:
            print(f"[lldb-mix] removed from {path}")
        else:
            print(f"[lldb-mix] no block found in {path}")
        return

    _install_block(path, block)
    print(f"[lldb-mix] registered in {path}")
    print("If you move the repo, rerun this script.")


if __name__ == "__main__":
    main()
