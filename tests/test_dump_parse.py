import unittest

from lldb_mix.commands.dump import _parse_args, _parse_simple_args
from lldb_mix.core.settings import Settings


class TestDumpParse(unittest.TestCase):
    def test_dump_defaults_to_sp(self):
        regs = {"sp": 0x1000, "pc": 0x2000}
        args, error = _parse_args([], regs)
        self.assertIsNone(error)
        self.assertEqual(args.addr, 0x1000)

    def test_dump_defaults_to_pc(self):
        regs = {"sp": 0, "pc": 0x2000}
        args, error = _parse_args([], regs)
        self.assertIsNone(error)
        self.assertEqual(args.addr, 0x2000)

    def test_dump_addr_and_len(self):
        regs = {}
        args, error = _parse_args(["0x3000", "32"], regs)
        self.assertIsNone(error)
        self.assertEqual(args.addr, 0x3000)
        self.assertEqual(args.length, 32)

    def test_dump_flags(self):
        regs = {"sp": 0x1000}
        args, error = _parse_args(["-l", "128", "-w", "8"], regs)
        self.assertIsNone(error)
        self.assertEqual(args.addr, 0x1000)
        self.assertEqual(args.length, 128)
        self.assertEqual(args.width, 8)

    def test_dump_invalid_width(self):
        regs = {"sp": 0x1000}
        _, error = _parse_args(["-w", "0"], regs)
        self.assertEqual(error, "invalid width value")

    def test_dump_invalid_length(self):
        regs = {"sp": 0x1000}
        _, error = _parse_args(["-l", "0"], regs)
        self.assertEqual(error, "invalid length value")

    def test_word_dump_defaults(self):
        regs = {"sp": 0x1000}
        args, error = _parse_simple_args([], regs)
        self.assertIsNone(error)
        self.assertEqual(args.addr, 0x1000)

    def test_word_dump_len(self):
        regs = {"sp": 0x1000}
        args, error = _parse_simple_args(["0x2000", "64"], regs)
        self.assertIsNone(error)
        self.assertEqual(args.addr, 0x2000)
        self.assertEqual(args.length, 64)


if __name__ == "__main__":
    unittest.main()
