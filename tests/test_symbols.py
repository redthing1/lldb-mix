import unittest

from lldb_mix.core.symbols import is_placeholder_symbol


class TestSymbols(unittest.TestCase):
    def test_placeholder_detection(self):
        self.assertTrue(is_placeholder_symbol(""))
        self.assertTrue(is_placeholder_symbol("___lldb_unnamed_symbol4"))
        self.assertTrue(is_placeholder_symbol("___LLDB_UNNAMED_SYMBOL123"))
        self.assertFalse(is_placeholder_symbol("main"))


if __name__ == "__main__":
    unittest.main()
