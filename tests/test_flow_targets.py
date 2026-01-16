import unittest

from lldb_mix.arch.arm64 import ARM64_ARCH
from lldb_mix.arch.riscv import RISCV64_ABI_ARCH
from lldb_mix.arch.x64 import X64_ARCH
from lldb_mix.core.flow import is_branch_like, resolve_flow_target


class TestFlowTargets(unittest.TestCase):
    def test_branch_like_arm64_cond(self):
        self.assertTrue(is_branch_like("b.eq", ARM64_ARCH))

    def test_branch_like_x86_loop(self):
        self.assertTrue(is_branch_like("loop", X64_ARCH))
        self.assertTrue(is_branch_like("jrcxz", X64_ARCH))

    def test_riscv_jal_target(self):
        self.assertEqual(
            resolve_flow_target("jal", "ra, 0x1000", {}, RISCV64_ABI_ARCH), 0x1000
        )

    def test_riscv_jalr_base_offset(self):
        regs = {"sp": 0x1000}
        self.assertEqual(
            resolve_flow_target("jalr", "ra, 0(sp)", regs, RISCV64_ABI_ARCH), 0x1000
        )
        self.assertEqual(
            resolve_flow_target("jalr", "ra, 8(sp)", regs, RISCV64_ABI_ARCH), 0x1008
        )

    def test_riscv_beq_target(self):
        regs = {"a0": 1, "a1": 2}
        self.assertEqual(
            resolve_flow_target("beq", "a0, a1, 0x20", regs, RISCV64_ABI_ARCH), 0x20
        )

    def test_arm64_cond_target(self):
        self.assertEqual(
            resolve_flow_target("b.eq", "0x2000", {}, ARM64_ARCH), 0x2000
        )


if __name__ == "__main__":
    unittest.main()
