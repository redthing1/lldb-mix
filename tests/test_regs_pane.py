import unittest

from lldb_mix.arch.base import ArchSpec
from lldb_mix.context.panes.regs import RegsPane
from lldb_mix.context.types import PaneContext
from lldb_mix.core.settings import Settings
from lldb_mix.core.snapshot import ContextSnapshot
from lldb_mix.ui.theme import BASE_THEME


class TestRegsPane(unittest.TestCase):
    def test_regs_multicolumn_layout(self):
        arch = ArchSpec(
            name="test",
            ptr_size=8,
            gpr_names=("r0", "r1", "r2", "r3"),
            pc_reg="pc",
            sp_reg="sp",
            flags_reg=None,
        )
        regs = {"r0": 1, "r1": 2, "r2": 3, "r3": 4}
        snapshot = ContextSnapshot(
            arch=arch,
            pc=0,
            sp=0,
            regs=regs,
            maps=[],
            timestamp=0.0,
        )
        settings = Settings()
        settings.enable_color = False
        ctx = PaneContext(
            snapshot=snapshot,
            settings=settings,
            theme=BASE_THEME,
            last_regs={},
            reader=None,
            resolver=None,
            target=None,
            process=None,
            term_width=80,
            term_height=24,
        )
        lines = RegsPane().render(ctx)
        self.assertEqual(lines[0], "[regs]")
        self.assertEqual(
            lines[1],
            "r0: 0x0000000000000001  r1: 0x0000000000000002  r2: 0x0000000000000003",
        )
        self.assertEqual(lines[2], "r3: 0x0000000000000004")


if __name__ == "__main__":
    unittest.main()
