import unittest

from lldb_mix.arch.arm32 import ARM32_ARCH
from lldb_mix.arch.arm64 import ARM64_ARCH
from lldb_mix.arch.info import ArchInfo
from lldb_mix.arch.registry import detect_arch_info
from lldb_mix.arch.x64 import X64_ARCH
from lldb_mix.arch.x86 import X86_ARCH


class TestArchRegistry(unittest.TestCase):
    def test_detect_x64_from_triple(self):
        info = ArchInfo.from_register_sets(
            triple="x86_64-apple-darwin",
            arch_name="x86_64",
            ptr_size=8,
            reg_sets={"General Purpose Registers": ["rax", "rip", "rsp"]},
        )
        arch = detect_arch_info(info)
        self.assertEqual(arch.name, X64_ARCH.name)
        self.assertIsNotNone(arch.abi)
        self.assertEqual(arch.abi.name, "sysv")

    def test_detect_x64_win64(self):
        info = ArchInfo.from_register_sets(
            triple="x86_64-pc-windows-msvc",
            arch_name="x86_64",
            ptr_size=8,
            reg_sets={"General Purpose Registers": ["rax", "rip", "rsp"]},
        )
        arch = detect_arch_info(info)
        self.assertEqual(arch.name, X64_ARCH.name)
        self.assertIsNotNone(arch.abi)
        self.assertEqual(arch.abi.name, "win64")

    def test_detect_x64_override(self):
        info = ArchInfo.from_register_sets(
            triple="x86_64-apple-darwin",
            arch_name="x86_64",
            ptr_size=8,
            reg_sets={"General Purpose Registers": ["rax", "rip", "rsp"]},
        )
        arch = detect_arch_info(info, abi_override="win64")
        self.assertEqual(arch.name, X64_ARCH.name)
        self.assertIsNotNone(arch.abi)
        self.assertEqual(arch.abi.name, "win64")

    def test_detect_arm64_from_triple(self):
        info = ArchInfo.from_register_sets(
            triple="arm64-apple-darwin",
            arch_name="arm64",
            ptr_size=8,
            reg_sets={"General Purpose Registers": ["x0", "x1", "sp", "pc"]},
        )
        arch = detect_arch_info(info)
        self.assertEqual(arch.name, ARM64_ARCH.name)
        self.assertIsNotNone(arch.abi)
        self.assertEqual(arch.abi.name, "aapcs64")

    def test_detect_arm32_from_triple(self):
        info = ArchInfo.from_register_sets(
            triple="armv4t-unknown-elf",
            arch_name="arm",
            ptr_size=4,
            reg_sets={"General Purpose Registers": ["r0", "r1", "sp", "pc", "cpsr"]},
        )
        arch = detect_arch_info(info)
        self.assertEqual(arch.name, ARM32_ARCH.name)
        self.assertIsNotNone(arch.abi)
        self.assertEqual(arch.abi.name, "aapcs32")

    def test_detect_x86_sysv32(self):
        info = ArchInfo.from_register_sets(
            triple="i386-pc-linux-gnu",
            arch_name="i386",
            ptr_size=4,
            reg_sets={"General Purpose Registers": ["eax", "eip", "esp"]},
        )
        arch = detect_arch_info(info)
        self.assertEqual(arch.name, X86_ARCH.name)
        self.assertIsNotNone(arch.abi)
        self.assertEqual(arch.abi.name, "sysv32")

    def test_detect_x86_win32(self):
        info = ArchInfo.from_register_sets(
            triple="i686-pc-windows-msvc",
            arch_name="i686",
            ptr_size=4,
            reg_sets={"General Purpose Registers": ["eax", "eip", "esp"]},
        )
        arch = detect_arch_info(info)
        self.assertEqual(arch.name, X86_ARCH.name)
        self.assertIsNotNone(arch.abi)
        self.assertEqual(arch.abi.name, "win32")

    def test_detect_x86_override_fastcall(self):
        info = ArchInfo.from_register_sets(
            triple="i686-pc-windows-msvc",
            arch_name="i686",
            ptr_size=4,
            reg_sets={"General Purpose Registers": ["eax", "eip", "esp"]},
        )
        arch = detect_arch_info(info, abi_override="win32-fastcall")
        self.assertEqual(arch.name, X86_ARCH.name)
        self.assertIsNotNone(arch.abi)
        self.assertEqual(arch.abi.name, "win32-fastcall")

    def test_detect_x64_from_regs(self):
        info = ArchInfo.from_register_sets(
            triple="",
            arch_name="",
            ptr_size=8,
            reg_sets={"General Purpose Registers": ["rax", "rip", "rsp"]},
        )
        arch = detect_arch_info(info)
        self.assertEqual(arch.name, X64_ARCH.name)
        self.assertIsNotNone(arch.abi)
        self.assertEqual(arch.abi.name, "sysv")

    def test_detect_arm64_from_regs(self):
        info = ArchInfo.from_register_sets(
            triple="",
            arch_name="",
            ptr_size=8,
            reg_sets={"General Purpose Registers": ["x0", "x1", "sp", "pc"]},
        )
        arch = detect_arch_info(info)
        self.assertEqual(arch.name, ARM64_ARCH.name)
        self.assertIsNotNone(arch.abi)
        self.assertEqual(arch.abi.name, "aapcs64")

    def test_triple_gates_other_profiles(self):
        info = ArchInfo.from_register_sets(
            triple="armv7-unknown-elf",
            arch_name="riscv32",
            ptr_size=4,
            reg_sets={"General Purpose Registers": ["sp", "pc"]},
        )
        arch = detect_arch_info(info)
        self.assertEqual(arch.name, ARM32_ARCH.name)


if __name__ == "__main__":
    unittest.main()
