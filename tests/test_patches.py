import unittest

from lldb_mix.core.patches import PatchStore, parse_hex_bytes


class TestPatches(unittest.TestCase):
    def test_parse_hex_bytes(self):
        self.assertEqual(parse_hex_bytes("90 90"), b"\x90\x90")
        self.assertEqual(parse_hex_bytes("0x90,0x90"), b"\x90\x90")
        self.assertEqual(parse_hex_bytes("9090"), b"\x90\x90")
        self.assertIsNone(parse_hex_bytes(""))
        self.assertIsNone(parse_hex_bytes("9"))
        self.assertIsNone(parse_hex_bytes("zz"))

    def test_patch_store_overlap(self):
        store = PatchStore()
        ok, err = store.add(0x1000, b"\x00\x00", b"\x90\x90")
        self.assertTrue(ok)
        self.assertIsNone(err)

        ok, err = store.add(0x1001, b"\x00", b"\x90")
        self.assertFalse(ok)
        self.assertIn("overlaps", err or "")

        ok, err = store.add(0x1002, b"\x00", b"\x90")
        self.assertTrue(ok)
        self.assertIsNone(err)


if __name__ == "__main__":
    unittest.main()
