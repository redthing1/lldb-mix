import unittest

from lldb_mix.ui.hexdump import hexdump_words


class TestHexdumpWords(unittest.TestCase):
    def test_word_dump_16_bytes(self):
        data = bytes(range(1, 17))
        lines = hexdump_words(data, 0x1000, word_size=2, bytes_per_line=16)
        self.assertEqual(
            lines[0],
            "0x0000000000001000: 0201 0403 0605 0807 0a09 0c0b 0e0d 100f  ................",
        )


if __name__ == "__main__":
    unittest.main()
