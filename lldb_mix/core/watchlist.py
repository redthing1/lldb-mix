from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WatchEntry:
    wid: int
    expr: str
    label: str | None = None


class WatchList:
    def __init__(self) -> None:
        self._next_id = 1
        self._entries: list[WatchEntry] = []

    def add(self, expr: str, label: str | None = None) -> WatchEntry:
        entry = WatchEntry(wid=self._next_id, expr=expr, label=label)
        self._next_id += 1
        self._entries.append(entry)
        return entry

    def remove(self, wid: int) -> bool:
        for idx, entry in enumerate(self._entries):
            if entry.wid == wid:
                self._entries.pop(idx)
                return True
        return False

    def clear(self) -> None:
        self._entries.clear()
        self._next_id = 1

    def items(self) -> list[WatchEntry]:
        return list(self._entries)

    def serialize(self) -> list[dict[str, object]]:
        return [
            {
                "id": entry.wid,
                "expr": entry.expr,
                "label": entry.label,
            }
            for entry in self._entries
        ]

    def load(self, entries: list[dict[str, object]]) -> None:
        self._entries.clear()
        self._next_id = 1
        max_id = 0
        for raw in entries:
            expr = raw.get("expr")
            if not isinstance(expr, str) or not expr.strip():
                continue
            wid = raw.get("id")
            if isinstance(wid, int) and wid > 0:
                entry_id = wid
            else:
                entry_id = self._next_id
            label = raw.get("label")
            if not isinstance(label, str):
                label = None
            self._entries.append(WatchEntry(wid=entry_id, expr=expr, label=label))
            max_id = max(max_id, entry_id)
            self._next_id = max_id + 1
