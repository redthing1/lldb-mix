import unittest

from lldb_mix.arch.arm64 import ARM64_ARCH
from lldb_mix.arch.riscv import RISCV64_ABI_ARCH
from lldb_mix.arch.x64 import X64_ARCH
from lldb_mix.core.flow import is_branch_like, resolve_flow_target
from tests.arch_test_utils import make_arch_view


class TestFlowTargets(unittest.TestCase):
    def test_branch_like_arm64_cond(self):
        arch = make_arch_view(ARM64_ARCH, gpr_names=("x0", "sp", "pc"), ptr_size=8)
        self.assertTrue(is_branch_like("b.eq", arch))

    def test_branch_like_x86_loop(self):
        arch = make_arch_view(X64_ARCH, gpr_names=("rax", "rip", "rsp"), ptr_size=8)
        self.assertTrue(is_branch_like("loop", arch))
        self.assertTrue(is_branch_like("jrcxz", arch))

    def test_riscv_jal_target(self):
        self.assertEqual(
            resolve_flow_target(
                "jal",
                "ra, 0x1000",
                {},
                make_arch_view(RISCV64_ABI_ARCH, gpr_names=("ra",), ptr_size=8),
            ),
            0x1000,
        )

    def test_riscv_jalr_base_offset(self):
        regs = {"sp": 0x1000}
        self.assertEqual(
            resolve_flow_target(
                "jalr",
                "ra, 0(sp)",
                regs,
                make_arch_view(RISCV64_ABI_ARCH, gpr_names=("sp",), ptr_size=8),
            ),
            0x1000,
        )
        self.assertEqual(
            resolve_flow_target(
                "jalr",
                "ra, 8(sp)",
                regs,
                make_arch_view(RISCV64_ABI_ARCH, gpr_names=("sp",), ptr_size=8),
            ),
            0x1008,
        )

    def test_riscv_beq_target(self):
        regs = {"a0": 1, "a1": 2}
        self.assertEqual(
            resolve_flow_target(
                "beq",
                "a0, a1, 0x20",
                regs,
                make_arch_view(RISCV64_ABI_ARCH, gpr_names=("a0", "a1"), ptr_size=8),
            ),
            0x20,
        )

    def test_arm64_cond_target(self):
        self.assertEqual(
            resolve_flow_target(
                "b.eq",
                "0x2000",
                {},
                make_arch_view(ARM64_ARCH, gpr_names=(), ptr_size=8),
            ),
            0x2000,
        )

    def test_arm64_ret_target(self):
        regs = {"lr": 0x1234}
        self.assertEqual(
            resolve_flow_target(
                "ret",
                "",
                regs,
                make_arch_view(ARM64_ARCH, gpr_names=("lr",), ptr_size=8),
            ),
            0x1234,
        )

    def test_riscv_ret_target(self):
        regs = {"ra": 0x2000}
        self.assertEqual(
            resolve_flow_target(
                "ret",
                "",
                regs,
                make_arch_view(RISCV64_ABI_ARCH, gpr_names=("ra",), ptr_size=8),
            ),
            0x2000,
        )

    def test_x64_ret_target(self):
        regs = {"rsp": 0x1000}

        def read_pointer(addr: int, size: int) -> int | None:
            if addr == 0x1000 and size == 8:
                return 0xdeadbeef
            return None

        self.assertEqual(
            resolve_flow_target(
                "ret",
                "",
                regs,
                make_arch_view(X64_ARCH, gpr_names=("rsp",), ptr_size=8),
                read_pointer=read_pointer,
                ptr_size=8,
            ),
            0xdeadbeef,
        )


if __name__ == "__main__":
    unittest.main()
