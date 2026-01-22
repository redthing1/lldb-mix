import unittest

from lldb_mix.core.lldb_settings import parse_setting_value


class TestLldbSettings(unittest.TestCase):
    def test_parse_unquoted(self):
        output = "stop-line-count (unsigned) = 0\n"
        self.assertEqual(parse_setting_value(output), "0")

    def test_parse_quoted(self):
        output = 'prompt (string) = "(lldb) "\n'
        self.assertEqual(parse_setting_value(output), "(lldb) ")

    def test_parse_multiline_quoted(self):
        output = "\n".join(
            [
                'thread-format (format-string) = "line1',
                "line2",
                "line3",
                '"',
                "",
            ]
        )
        self.assertEqual(parse_setting_value(output), "line1\nline2\nline3\n")


if __name__ == "__main__":
    unittest.main()
