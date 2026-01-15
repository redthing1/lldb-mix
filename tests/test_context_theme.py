import unittest
from unittest.mock import patch

from lldb_mix.commands import context
from lldb_mix.core.settings import Settings
from lldb_mix.ui.theme import THEMES


class TestContextTheme(unittest.TestCase):
    def setUp(self):
        self._orig_settings = context.SETTINGS
        context.SETTINGS = Settings()

    def tearDown(self):
        context.SETTINGS = self._orig_settings

    def test_theme_status(self):
        context.SETTINGS.theme = "base"
        msg = context._handle_theme([])
        self.assertEqual(msg, "[lldb-mix] theme: base")

    def test_theme_list(self):
        msg = context._handle_theme(["list"])
        for name in THEMES.keys():
            self.assertIn(name, msg)

    def test_theme_unknown(self):
        msg = context._handle_theme(["nope"])
        self.assertEqual(msg, "[lldb-mix] unknown theme: nope")

    def test_theme_set(self):
        context.SETTINGS.theme = "base"
        msg = context._handle_theme(["lrt-dark"])
        self.assertEqual(msg, "[lldb-mix] theme set: lrt-dark")
        self.assertEqual(context.SETTINGS.theme, "lrt-dark")

    def test_layout_set(self):
        msg = context._handle_layout(["regs", "stack", "code"])
        self.assertEqual(msg, "[lldb-mix] layout set: regs stack code")
        self.assertEqual(context.SETTINGS.layout, ["regs", "stack", "code"])

    def test_layout_status(self):
        context.SETTINGS.layout = ["regs", "code"]
        msg = context._handle_layout([])
        self.assertEqual(msg, "[lldb-mix] layout: regs code")

    def test_auto_status(self):
        context.SETTINGS.auto_context = True
        msg = context._handle_auto(object(), ["status"])
        self.assertEqual(msg, "[lldb-mix] auto context is on")

    def test_auto_on(self):
        context.SETTINGS.auto_context = False
        with patch("lldb_mix.commands.context.ensure_stop_hook") as hook:
            msg = context._handle_auto(object(), ["on"])
            self.assertEqual(msg, "[lldb-mix] auto context enabled")
            self.assertTrue(context.SETTINGS.auto_context)
            hook.assert_called_once()

    def test_auto_off(self):
        context.SETTINGS.auto_context = True
        with patch("lldb_mix.commands.context.remove_stop_hook") as hook:
            msg = context._handle_auto(object(), ["off"])
            self.assertEqual(msg, "[lldb-mix] auto context disabled")
            self.assertFalse(context.SETTINGS.auto_context)
            hook.assert_called_once()


if __name__ == "__main__":
    unittest.main()
