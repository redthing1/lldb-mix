import os
import tempfile
import unittest

from lldb_mix.commands.search import _parse_args


class TestFindmemParse(unittest.TestCase):
    def test_string_pattern(self):
        args, error = _parse_args(["-s", "hello"])
        self.assertIsNone(error)
        self.assertEqual(args.kind, "string")
        self.assertEqual(args.pattern, b"hello")
        self.assertEqual(args.count, -1)

    def test_binary_pattern(self):
        args, error = _parse_args(["-b", "0x414243"])
        self.assertIsNone(error)
        self.assertEqual(args.kind, "binary")
        self.assertEqual(args.pattern, b"ABC")

    def test_binary_pattern_with_spaces(self):
        args, error = _parse_args(["-b", "41 42 43"])
        self.assertIsNone(error)
        self.assertEqual(args.pattern, b"ABC")

    def test_dword_pattern(self):
        args, error = _parse_args(["-d", "0x41414141"])
        self.assertIsNone(error)
        self.assertEqual(args.kind, "dword")
        self.assertEqual(args.pattern, b"AAAA")

    def test_qword_pattern(self):
        args, error = _parse_args(["-q", "0x4141414141414141"])
        self.assertIsNone(error)
        self.assertEqual(args.kind, "qword")
        self.assertEqual(args.pattern, b"AAAAAAAA")

    def test_file_pattern(self):
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            handle.write(b"xyz")
            path = handle.name
        try:
            args, error = _parse_args(["-f", path])
            self.assertIsNone(error)
            self.assertEqual(args.kind, "file")
            self.assertEqual(args.pattern, b"xyz")
        finally:
            os.unlink(path)

    def test_count(self):
        args, error = _parse_args(["-s", "hello", "-c", "2"])
        self.assertIsNone(error)
        self.assertEqual(args.count, 2)

    def test_invalid_count(self):
        args, error = _parse_args(["-s", "hello", "-c", "0"])
        self.assertIsNotNone(error)
        self.assertEqual(error, "invalid count")

    def test_multiple_patterns(self):
        args, error = _parse_args(["-s", "hello", "-b", "41"])
        self.assertIsNotNone(error)
        self.assertEqual(error, "select exactly one of -s/-b/-d/-q/-f")

    def test_empty_string_pattern(self):
        args, error = _parse_args(["-s", ""])
        self.assertIsNotNone(error)
        self.assertEqual(error, "pattern is empty")


if __name__ == "__main__":
    unittest.main()
