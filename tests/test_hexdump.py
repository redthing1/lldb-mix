import unittest

from lldb_mix.ui.hexdump import hexdump


class TestHexdump(unittest.TestCase):
    def test_hexdump_basic(self):
        lines = hexdump(b"AB\x00C", 0x1000, bytes_per_line=4)
        self.assertEqual(
            lines[0],
            "0x0000000000001000: 41 42 00 43  AB.C",
        )


if __name__ == "__main__":
    unittest.main()
