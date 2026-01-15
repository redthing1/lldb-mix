import unittest

from lldb_mix.arch.arm64 import ARM64_ARCH
from lldb_mix.arch.x64 import X64_ARCH


class TestArchFlags(unittest.TestCase):
    def test_x64_format_flags(self):
        zf = 1 << 6
        cf = 1 << 0
        flags = zf | cf
        self.assertEqual(X64_ARCH.format_flags(flags), "o d i t s Z a p C")

    def test_arm64_format_flags(self):
        n = 1 << 31
        c = 1 << 29
        flags = n | c
        self.assertEqual(ARM64_ARCH.format_flags(flags), "N z C v a i f")

    def test_x64_branch_taken(self):
        zf = 1 << 6
        taken, reason = X64_ARCH.branch_taken("je", zf)
        self.assertTrue(taken)
        self.assertEqual(reason, "zf=1")

    def test_arm64_branch_taken(self):
        z = 1 << 30
        taken, reason = ARM64_ARCH.branch_taken("b.eq", z)
        self.assertTrue(taken)
        self.assertEqual(reason, "z=1")


if __name__ == "__main__":
    unittest.main()
