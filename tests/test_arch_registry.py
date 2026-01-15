import unittest

from lldb_mix.arch.arm64 import ARM64_ARCH
from lldb_mix.arch.registry import detect_arch
from lldb_mix.arch.x64 import X64_ARCH


class TestArchRegistry(unittest.TestCase):
    def test_detect_x64_from_triple(self):
        arch = detect_arch("x86_64-apple-darwin", [])
        self.assertIs(arch, X64_ARCH)

    def test_detect_arm64_from_triple(self):
        arch = detect_arch("arm64-apple-darwin", [])
        self.assertIs(arch, ARM64_ARCH)

    def test_detect_x64_from_regs(self):
        arch = detect_arch("", ["rax", "rip", "rsp"])
        self.assertIs(arch, X64_ARCH)

    def test_detect_arm64_from_regs(self):
        arch = detect_arch("", ["x0", "x1", "sp", "pc"])
        self.assertIs(arch, ARM64_ARCH)


if __name__ == "__main__":
    unittest.main()
