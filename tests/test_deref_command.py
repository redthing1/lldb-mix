import unittest

from lldb_mix.commands.deref import _parse_args


class TestDerefCommand(unittest.TestCase):
    def test_parse_args_default(self):
        parsed, error = _parse_args([])
        self.assertIsNone(error)
        self.assertIsNone(parsed.token)
        self.assertIsNone(parsed.depth)

    def test_parse_args_depth(self):
        parsed, error = _parse_args(["-d", "3", "$sp"])
        self.assertIsNone(error)
        self.assertEqual(parsed.depth, 3)
        self.assertEqual(parsed.token, "$sp")

    def test_parse_args_invalid(self):
        parsed, error = _parse_args(["-d"])
        self.assertIsNotNone(error)
        self.assertIsNotNone(parsed)

        parsed, error = _parse_args(["a", "b"])
        self.assertIsNotNone(error)
        self.assertIsNotNone(parsed)


if __name__ == "__main__":
    unittest.main()
