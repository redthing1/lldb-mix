import unittest

from lldb_mix.arch.match import (
    declared_family,
    family_from_token,
    is_explicitly_unsupported_arch,
    profile_family,
)


class TestArchMatch(unittest.TestCase):
    def test_family_from_token_known_arches(self):
        self.assertEqual(family_from_token("x86_64h"), "x86_64")
        self.assertEqual(family_from_token("i686"), "x86")
        self.assertEqual(family_from_token("arm64e"), "arm64")
        self.assertEqual(family_from_token("armv7"), "arm32")
        self.assertEqual(family_from_token("riscv64"), "riscv")
        self.assertEqual(family_from_token("mips64el"), "mips")

    def test_family_from_token_unknown_arch(self):
        self.assertIsNone(family_from_token("loongarch64"))
        self.assertIsNone(family_from_token("unknown"))

    def test_declared_family_prefers_triple_over_arch_name(self):
        self.assertEqual(declared_family("armv7-unknown-elf", "riscv64"), "arm32")

    def test_declared_family_falls_back_to_arch_name(self):
        self.assertEqual(declared_family("unknown-unknown-unknown", "riscv64"), "riscv")

    def test_declared_family_none_for_unsupported_triple(self):
        self.assertIsNone(declared_family("loongarch64-unknown-linux-gnu", "riscv64"))

    def test_is_explicitly_unsupported_arch(self):
        self.assertTrue(
            is_explicitly_unsupported_arch("loongarch64-unknown-linux-gnu", "riscv64")
        )
        self.assertTrue(is_explicitly_unsupported_arch("", "loongarch64"))
        self.assertFalse(is_explicitly_unsupported_arch("riscv64-unknown-elf", ""))
        self.assertFalse(is_explicitly_unsupported_arch("", ""))

    def test_profile_family_mapping(self):
        self.assertEqual(profile_family("x86_64"), "x86_64")
        self.assertEqual(profile_family("i386"), "x86")
        self.assertEqual(profile_family("arm64"), "arm64")
        self.assertEqual(profile_family("arm32"), "arm32")
        self.assertEqual(profile_family("riscv64"), "riscv")
        self.assertEqual(profile_family("mips64el"), "mips")
        self.assertIsNone(profile_family("custom-arch"))


if __name__ == "__main__":
    unittest.main()
