import unittest

from lldb_mix.commands.disasm import _format_instructions
from lldb_mix.core.disasm import Instruction


class TestDisasmFormat(unittest.TestCase):
    def test_u_spacing(self):
        insts = [
            Instruction(address=0x1000, bytes=b"\x90", mnemonic="nop", operands=""),
            Instruction(
                address=0x1001,
                bytes=b"\x90\x90\x90",
                mnemonic="mov",
                operands="eax, ebx",
            ),
        ]
        lines = _format_instructions(
            insts,
            ptr_size=8,
            show_opcodes=True,
            style=lambda text, role: text,
        )
        self.assertEqual(
            lines[0],
            "=> 0x0000000000001000 90       nop",
        )
        self.assertEqual(
            lines[1],
            "   0x0000000000001001 90 90 90 mov eax, ebx",
        )

    def test_u_no_opcodes(self):
        insts = [
            Instruction(address=0x1000, bytes=b"\x90", mnemonic="nop", operands=""),
            Instruction(
                address=0x1001,
                bytes=b"\x90\x90\x90",
                mnemonic="mov",
                operands="eax, ebx",
            ),
        ]
        lines = _format_instructions(
            insts,
            ptr_size=8,
            show_opcodes=False,
            style=lambda text, role: text,
        )
        self.assertEqual(lines[0], "=> 0x0000000000001000 nop")
        self.assertEqual(lines[1], "   0x0000000000001001 mov eax, ebx")


if __name__ == "__main__":
    unittest.main()
