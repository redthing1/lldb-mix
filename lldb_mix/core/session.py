from __future__ import annotations

from typing import Any

from lldb_mix.arch.registry import detect_arch
from lldb_mix.core.state import SETTINGS


class Session:
    def __init__(self, debugger: Any):
        self.debugger = debugger

    def target(self) -> Any | None:
        if not self.debugger:
            return None
        target = self.debugger.GetSelectedTarget()
        if target and target.IsValid():
            return target
        return None

    def process(self) -> Any | None:
        target = self.target()
        if not target:
            return None
        process = target.GetProcess()
        if process and process.IsValid():
            return process
        return None

    def thread(self) -> Any | None:
        process = self.process()
        if not process:
            return None
        thread = process.GetSelectedThread()
        if thread and thread.IsValid():
            return thread
        return None

    def frame(self) -> Any | None:
        thread = self.thread()
        if not thread:
            return None
        frame = thread.GetSelectedFrame()
        if frame and frame.IsValid():
            return frame
        return None

    def arch(self):
        target = self.target()
        triple = target.GetTriple() if target else ""
        reg_names = set()
        frame = self.frame()
        if frame:
            reg_names = {r.GetName() for r in self._iter_registers(frame)}
        return detect_arch(triple, reg_names, SETTINGS.abi)

    def read_registers(self) -> dict[str, int]:
        frame = self.frame()
        if not frame:
            return {}
        regs: dict[str, int] = {}
        for reg in self._iter_registers(frame):
            name = reg.GetName() or ""
            if not name:
                continue
            try:
                value = int(reg.GetValueAsUnsigned())
            except Exception:
                continue
            regs[name.lower()] = value
        return regs

    def read_gprs(self) -> dict[str, int]:
        arch = self.arch()
        regs = self.read_registers()
        if not arch.gpr_names:
            return {}
        return {name: regs[name] for name in arch.gpr_names if name in regs}

    @staticmethod
    def _iter_registers(frame: Any):
        regs = frame.GetRegisters()
        for reg_set in regs:
            for reg in reg_set:
                yield reg
