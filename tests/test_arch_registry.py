import unittest

from lldb_mix.arch.arm64 import ARM64_ARCH
from lldb_mix.arch.registry import detect_arch
from lldb_mix.arch.x64 import X64_ARCH


class TestArchRegistry(unittest.TestCase):
    def test_detect_x64_from_triple(self):
        arch = detect_arch("x86_64-apple-darwin", [])
        self.assertEqual(arch.name, X64_ARCH.name)
        self.assertIsNotNone(arch.abi)
        self.assertEqual(arch.abi.name, "sysv")

    def test_detect_x64_win64(self):
        arch = detect_arch("x86_64-pc-windows-msvc", [])
        self.assertEqual(arch.name, X64_ARCH.name)
        self.assertIsNotNone(arch.abi)
        self.assertEqual(arch.abi.name, "win64")

    def test_detect_x64_override(self):
        arch = detect_arch("x86_64-apple-darwin", [], abi_override="win64")
        self.assertEqual(arch.name, X64_ARCH.name)
        self.assertIsNotNone(arch.abi)
        self.assertEqual(arch.abi.name, "win64")

    def test_detect_arm64_from_triple(self):
        arch = detect_arch("arm64-apple-darwin", [])
        self.assertEqual(arch.name, ARM64_ARCH.name)
        self.assertIsNotNone(arch.abi)
        self.assertEqual(arch.abi.name, "aapcs64")

    def test_detect_x64_from_regs(self):
        arch = detect_arch("", ["rax", "rip", "rsp"])
        self.assertEqual(arch.name, X64_ARCH.name)
        self.assertIsNotNone(arch.abi)
        self.assertEqual(arch.abi.name, "sysv")

    def test_detect_arm64_from_regs(self):
        arch = detect_arch("", ["x0", "x1", "sp", "pc"])
        self.assertEqual(arch.name, ARM64_ARCH.name)
        self.assertIsNotNone(arch.abi)
        self.assertEqual(arch.abi.name, "aapcs64")


if __name__ == "__main__":
    unittest.main()
