import unittest

from lldb_mix.arch.info import ArchInfo
from lldb_mix.arch.reginfo import RegInfo
from lldb_mix.arch.view import ArchView


class TestArchInfo(unittest.TestCase):
    def test_selects_general_purpose_set(self):
        info = ArchInfo.from_register_sets(
            triple="",
            arch_name="",
            ptr_size=8,
            reg_sets={
                "General Purpose Registers": [RegInfo("r0", 8), RegInfo("r1", 8)],
                "Floating Point Registers": [RegInfo("f0", 8)],
            },
        )
        self.assertEqual(info.gpr_names, ("r0", "r1"))

    def test_selects_largest_set_when_no_gpr(self):
        info = ArchInfo.from_register_sets(
            triple="",
            arch_name="",
            ptr_size=8,
            reg_sets={
                "A": [RegInfo("r0", 8)],
                "B": [RegInfo("r0", 4), RegInfo("r1", 4), RegInfo("r2", 4)],
            },
        )
        self.assertEqual(info.gpr_names, ("r0",))

    def test_prefers_ptr_sized_set(self):
        info = ArchInfo.from_register_sets(
            triple="",
            arch_name="",
            ptr_size=8,
            reg_sets={
                "A": [RegInfo("r0", 8), RegInfo("r1", 8)],
                "B": [RegInfo("f0", 4), RegInfo("f1", 4), RegInfo("f2", 4)],
            },
        )
        self.assertEqual(info.gpr_names, ("r0", "r1"))

    def test_pc_sp_from_value(self):
        info = ArchInfo.from_register_sets(
            triple="",
            arch_name="",
            ptr_size=8,
            reg_sets={
                "regs": [RegInfo("r0", 8), RegInfo("r1", 8), RegInfo("r2", 8)]
            },
            pc_value=0x1111,
            sp_value=0x2222,
            reg_values={"r1": 0x1111, "r2": 0x2222, "r0": 0},
        )
        self.assertEqual(info.pc_reg_name, "r1")
        self.assertEqual(info.sp_reg_name, "r2")

    def test_arch_view_fallbacks(self):
        info = ArchInfo.from_register_sets(
            triple="custom-unknown",
            arch_name="custom",
            ptr_size=4,
            reg_sets={
                "General Purpose Registers": [
                    RegInfo("r0", 4),
                    RegInfo("r1", 4),
                    RegInfo("sp", 4),
                    RegInfo("pc", 4),
                ]
            },
            pc_value=0x1000,
            sp_value=0x2000,
        )
        arch = ArchView(info=info, profile=None)
        self.assertEqual(arch.name, "custom")
        self.assertEqual(arch.ptr_size, 4)
        self.assertEqual(arch.gpr_names, ("r0", "r1", "sp", "pc"))
        self.assertEqual(arch.pc_value, 0x1000)
        self.assertEqual(arch.sp_value, 0x2000)


if __name__ == "__main__":
    unittest.main()
