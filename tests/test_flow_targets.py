import unittest

from lldb_mix.core.flow import is_branch_like, resolve_flow_target


class TestFlowTargets(unittest.TestCase):
    def test_branch_like_arm64_cond(self):
        self.assertTrue(is_branch_like("b.eq"))

    def test_branch_like_x86_loop(self):
        self.assertTrue(is_branch_like("loop"))
        self.assertTrue(is_branch_like("jrcxz"))

    def test_riscv_jal_target(self):
        self.assertEqual(resolve_flow_target("jal", "ra, 0x1000", {}), 0x1000)

    def test_riscv_jalr_base_offset(self):
        regs = {"sp": 0x1000}
        self.assertEqual(resolve_flow_target("jalr", "ra, 0(sp)", regs), 0x1000)
        self.assertEqual(resolve_flow_target("jalr", "ra, 8(sp)", regs), 0x1008)

    def test_riscv_beq_target(self):
        regs = {"a0": 1, "a1": 2}
        self.assertEqual(resolve_flow_target("beq", "a0, a1, 0x20", regs), 0x20)

    def test_arm64_cond_target(self):
        self.assertEqual(resolve_flow_target("b.eq", "0x2000", {}), 0x2000)


if __name__ == "__main__":
    unittest.main()
