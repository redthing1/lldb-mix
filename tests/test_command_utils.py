import unittest

from lldb_mix.commands.utils import default_addr, parse_int, resolve_addr


class TestCommandUtils(unittest.TestCase):
    def test_parse_int(self):
        self.assertEqual(parse_int("0x10"), 16)
        self.assertEqual(parse_int("20"), 20)
        self.assertIsNone(parse_int("nope"))

    def test_default_addr_prefers_sp(self):
        regs = {"sp": 0x1000, "pc": 0x2000}
        self.assertEqual(default_addr(regs), 0x1000)

    def test_default_addr_falls_back_to_pc(self):
        regs = {"sp": 0, "pc": 0x2000}
        self.assertEqual(default_addr(regs), 0x2000)

    def test_resolve_addr_sp_alias(self):
        regs = {"rsp": 0x1111}
        self.assertEqual(resolve_addr("sp", regs), 0x1111)
        self.assertEqual(resolve_addr("$sp", regs), 0x1111)

    def test_resolve_addr_pc_alias(self):
        regs = {"rip": 0x2222}
        self.assertEqual(resolve_addr("pc", regs), 0x2222)

    def test_resolve_addr_reg_value(self):
        regs = {"rax": 0x3333}
        self.assertEqual(resolve_addr("rax", regs), 0x3333)

    def test_resolve_addr_literal(self):
        regs = {}
        self.assertEqual(resolve_addr("0x1234", regs), 0x1234)
        self.assertEqual(resolve_addr("4660", regs), 4660)

    def test_resolve_addr_invalid(self):
        regs = {}
        self.assertIsNone(resolve_addr("nope", regs))


if __name__ == "__main__":
    unittest.main()
