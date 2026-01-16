import unittest

from lldb_mix.arch.info import ArchInfo
from lldb_mix.arch.view import ArchView


class TestArchInfo(unittest.TestCase):
    def test_selects_general_purpose_set(self):
        info = ArchInfo.from_register_sets(
            triple="",
            arch_name="",
            ptr_size=8,
            reg_sets={
                "General Purpose Registers": ["r0", "r1"],
                "Floating Point Registers": ["f0"],
            },
        )
        self.assertEqual(info.gpr_names, ("r0", "r1"))

    def test_selects_largest_set_when_no_gpr(self):
        info = ArchInfo.from_register_sets(
            triple="",
            arch_name="",
            ptr_size=8,
            reg_sets={
                "A": ["r0"],
                "B": ["r0", "r1", "r2"],
            },
        )
        self.assertEqual(info.gpr_names, ("r0", "r1", "r2"))

    def test_arch_view_fallbacks(self):
        info = ArchInfo.from_register_sets(
            triple="custom-unknown",
            arch_name="custom",
            ptr_size=4,
            reg_sets={"General Purpose Registers": ["r0", "r1", "sp", "pc"]},
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
