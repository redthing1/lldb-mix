import unittest
from unittest.mock import patch

from lldb_mix.arch.abi import AbiSpec
from lldb_mix.arch.base import ArchSpec
from lldb_mix.context.panes.args import ArgsPane
from lldb_mix.context.types import PaneContext
from lldb_mix.core.disasm import Instruction
from lldb_mix.core.settings import Settings
from lldb_mix.core.snapshot import ContextSnapshot
from lldb_mix.core.watchlist import WatchList
from lldb_mix.ui.theme import BASE_THEME


class TestArgsPaneFormat(unittest.TestCase):
    def _make_ctx(self, arch, regs, pc=0x1000, target=None):
        snapshot = ContextSnapshot(
            arch=arch,
            pc=pc,
            sp=0,
            regs=regs,
            maps=[],
            timestamp=0.0,
        )
        settings = Settings()
        settings.enable_color = False
        return PaneContext(
            snapshot=snapshot,
            settings=settings,
            theme=BASE_THEME,
            last_regs={},
            reader=None,
            resolver=None,
            target=target,
            process=None,
            watchlist=WatchList(),
            term_width=120,
            term_height=40,
        )

    def test_arg_regs_header(self):
        abi = AbiSpec(name="testabi", int_arg_regs=("r0", "r1"))
        arch = ArchSpec(
            name="test",
            ptr_size=8,
            gpr_names=("r0", "r1"),
            pc_reg="pc",
            sp_reg="sp",
            abi=abi,
        )
        ctx = self._make_ctx(arch, {"r0": 0x1111, "r1": 0x2222})

        lines = ArgsPane().render(ctx)

        self.assertEqual(lines[0], "[args:testabi]")
        self.assertEqual(lines[1], "arg regs")
        self.assertEqual(lines[2], "r0: 0x0000000000001111")
        self.assertEqual(lines[3], "r1: 0x0000000000002222")

    def test_call_args_header(self):
        abi = AbiSpec(name="testabi", int_arg_regs=("r0", "r1"))
        arch = ArchSpec(
            name="test",
            ptr_size=8,
            gpr_names=("r0", "r1"),
            pc_reg="pc",
            sp_reg="sp",
            call_mnemonics=("call",),
            abi=abi,
        )
        ctx = self._make_ctx(
            arch,
            {"r0": 0x1111, "r1": 0x2222},
            target=object(),
        )
        insts = [
            Instruction(
                address=0x1000,
                bytes=b"\x00",
                mnemonic="call",
                operands="0x2000",
            )
        ]

        with patch("lldb_mix.context.panes.args.read_instructions", return_value=insts):
            lines = ArgsPane().render(ctx)

        self.assertEqual(lines[1], "call args -> 0x0000000000002000")
        self.assertEqual(lines[2], "r0: 0x0000000000001111")
        self.assertEqual(lines[3], "r1: 0x0000000000002222")


if __name__ == "__main__":
    unittest.main()
