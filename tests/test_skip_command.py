import unittest

from lldb_mix.commands import skip
from lldb_mix.core.disasm import Instruction


class TestSkipCommand(unittest.TestCase):
    def test_parse_count_default(self):
        count, error = skip._parse_count([])
        self.assertEqual(count, 1)
        self.assertIsNone(error)

    def test_parse_count_value(self):
        count, error = skip._parse_count(["3"])
        self.assertEqual(count, 3)
        self.assertIsNone(error)

    def test_parse_count_invalid(self):
        count, error = skip._parse_count(["0"])
        self.assertEqual(count, 0)
        self.assertEqual(error, "invalid count")

    def test_parse_count_too_many(self):
        count, error = skip._parse_count(["1", "2"])
        self.assertEqual(count, 0)
        self.assertEqual(error, "too many arguments")

    def test_compute_target(self):
        insts = [
            Instruction(address=0x1000, bytes=b"\x90", mnemonic="nop", operands=""),
            Instruction(address=0x1001, bytes=b"\x90\x90", mnemonic="nop", operands=""),
        ]
        target = skip._compute_target(0x1000, insts, 2)
        self.assertEqual(target, 0x1003)

    def test_compute_target_missing_bytes(self):
        insts = [
            Instruction(address=0x1000, bytes=b"", mnemonic="nop", operands=""),
        ]
        target = skip._compute_target(0x1000, insts, 1)
        self.assertIsNone(target)


if __name__ == "__main__":
    unittest.main()
