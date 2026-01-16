from __future__ import annotations

from lldb_mix.context.panes.base import Pane
from lldb_mix.context.types import PaneContext


def _stop_reason_name(reason: int) -> str:
    try:
        import lldb
    except Exception:
        return str(reason)

    mapping = {
        lldb.eStopReasonInvalid: "invalid",
        lldb.eStopReasonNone: "none",
        lldb.eStopReasonTrace: "trace",
        lldb.eStopReasonBreakpoint: "breakpoint",
        lldb.eStopReasonWatchpoint: "watchpoint",
        lldb.eStopReasonSignal: "signal",
        lldb.eStopReasonException: "exception",
        lldb.eStopReasonExec: "exec",
        lldb.eStopReasonPlanComplete: "plan-complete",
        lldb.eStopReasonThreadExiting: "thread-exiting",
        lldb.eStopReasonInstrumentation: "instrumentation",
    }
    return mapping.get(reason, str(reason))


class ThreadsPane(Pane):
    name = "threads"
    column = 0

    def render(self, ctx: PaneContext) -> list[str]:
        lines = [self.title(ctx)]
        process = ctx.process
        if not process:
            lines.append("(process unavailable)")
            return lines

        num_threads = process.GetNumThreads()
        if num_threads == 0:
            lines.append("(no threads)")
            return lines

        for idx in range(num_threads):
            thread = process.GetThreadAtIndex(idx)
            tid = thread.GetThreadID() if thread else 0
            reason = _stop_reason_name(thread.GetStopReason()) if thread else "unknown"
            name = thread.GetName() if thread and thread.GetName() else ""
            name_suffix = f" ({name})" if name else ""
            idx_text = self.style(ctx, str(idx), "label")
            tid_text = self.style(ctx, f"0x{tid:x}", "addr")
            reason_text = self.style(ctx, reason, "muted")
            lines.append(
                f"{idx_text}: tid={tid_text} reason={reason_text}{name_suffix}"
            )

        return lines
