import unittest

from lldb_mix.commands.run import _build_launch_cmd


class TestRRCommand(unittest.TestCase):
    def test_build_launch_cmd_no_args(self):
        self.assertEqual(_build_launch_cmd(""), "process launch -s -X true --")

    def test_build_launch_cmd_with_args(self):
        self.assertEqual(
            _build_launch_cmd("arg1 arg2"),
            "process launch -s -X true -- arg1 arg2",
        )

    def test_build_launch_cmd_strips_args(self):
        self.assertEqual(
            _build_launch_cmd("  arg1  "),
            "process launch -s -X true -- arg1",
        )


if __name__ == "__main__":
    unittest.main()
