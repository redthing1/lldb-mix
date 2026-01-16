import unittest
from unittest.mock import patch

from lldb_mix.arch.base import ArchSpec
from lldb_mix.context.panes.code import CodePane
from lldb_mix.context.types import PaneContext
from lldb_mix.core.disasm import Instruction
from lldb_mix.core.symbols import SymbolInfo
from lldb_mix.core.settings import Settings
from lldb_mix.core.snapshot import ContextSnapshot
from lldb_mix.core.watchlist import WatchList
from lldb_mix.ui.theme import BASE_THEME


class TestCodePaneFormat(unittest.TestCase):
    def test_opcode_spacing(self):
        arch = ArchSpec(
            name="test",
            ptr_size=8,
            gpr_names=(),
            pc_reg="pc",
            sp_reg="sp",
        )
        snapshot = ContextSnapshot(
            arch=arch,
            pc=0x1000,
            sp=0,
            regs={},
            maps=[],
            timestamp=0.0,
        )
        settings = Settings()
        settings.enable_color = False
        settings.show_opcodes = True
        ctx = PaneContext(
            snapshot=snapshot,
            settings=settings,
            theme=BASE_THEME,
            last_regs={},
            reader=None,
            resolver=None,
            target=object(),
            process=None,
            watchlist=WatchList(),
            term_width=120,
            term_height=40,
        )
        insts = [
            Instruction(address=0x1000, bytes=b"\x90", mnemonic="nop", operands=""),
            Instruction(
                address=0x1001,
                bytes=b"\x90\x90\x90",
                mnemonic="mov",
                operands="eax, ebx",
            ),
        ]

        with patch(
            "lldb_mix.context.panes.code.read_instructions_around",
            return_value=insts,
        ):
            lines = CodePane().render(ctx)

        self.assertEqual(lines[0], "[code]")
        self.assertEqual(lines[1], "=> 0x0000000000001000 90       nop")
        self.assertEqual(lines[2], "   0x0000000000001001 90 90 90 mov eax, ebx")

    def test_branch_comment(self):
        arch = ArchSpec(
            name="test",
            ptr_size=8,
            gpr_names=(),
            pc_reg="pc",
            sp_reg="sp",
        )
        snapshot = ContextSnapshot(
            arch=arch,
            pc=0x1000,
            sp=0,
            regs={"x0": 0},
            maps=[],
            timestamp=0.0,
        )
        settings = Settings()
        settings.enable_color = False
        settings.show_opcodes = False
        ctx = PaneContext(
            snapshot=snapshot,
            settings=settings,
            theme=BASE_THEME,
            last_regs={},
            reader=None,
            resolver=None,
            target=object(),
            process=None,
            watchlist=WatchList(),
            term_width=120,
            term_height=40,
        )
        insts = [
            Instruction(
                address=0x1000,
                bytes=b"\x00",
                mnemonic="cbz",
                operands="x0, 0x2000",
            )
        ]

        with patch(
            "lldb_mix.context.panes.code.read_instructions_around",
            return_value=insts,
        ):
            lines = CodePane().render(ctx)

        self.assertEqual(
            lines[1],
            "=> 0x0000000000001000 cbz x0, 0x2000 ; "
            "taken (x0=0) | x0=0x0000000000000000 | target=0x0000000000002000",
        )

    def test_branch_symbol_target(self):
        arch = ArchSpec(
            name="test",
            ptr_size=8,
            gpr_names=(),
            pc_reg="pc",
            sp_reg="sp",
        )
        snapshot = ContextSnapshot(
            arch=arch,
            pc=0x1000,
            sp=0,
            regs={},
            maps=[],
            timestamp=0.0,
        )
        settings = Settings()
        settings.enable_color = False
        settings.show_opcodes = False

        class _Resolver:
            def resolve(self, addr: int):
                if addr == 0x2000:
                    return SymbolInfo(name="target", module="mod", offset=4)
                return None

        ctx = PaneContext(
            snapshot=snapshot,
            settings=settings,
            theme=BASE_THEME,
            last_regs={},
            reader=None,
            resolver=_Resolver(),
            target=object(),
            process=None,
            watchlist=WatchList(),
            term_width=120,
            term_height=40,
        )
        insts = [
            Instruction(
                address=0x1000,
                bytes=b"\x00",
                mnemonic="b",
                operands="0x2000",
            )
        ]

        with patch(
            "lldb_mix.context.panes.code.read_instructions_around",
            return_value=insts,
        ):
            lines = CodePane().render(ctx)

        self.assertEqual(
            lines[1],
            "=> 0x0000000000001000 b 0x2000 ; "
            "target=0x0000000000002000 mod!target+0x4",
        )

if __name__ == "__main__":
    unittest.main()
