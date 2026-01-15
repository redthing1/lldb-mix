import unittest

from lldb_mix.core.config import format_setting, set_setting
from lldb_mix.core.settings import Settings


class TestConfConfig(unittest.TestCase):
    def test_set_bool(self):
        settings = Settings()
        ok, value = set_setting(settings, "enable_color", ["off"])
        self.assertTrue(ok)
        self.assertEqual(value, "off")
        self.assertFalse(settings.enable_color)

    def test_set_layout_dedup(self):
        settings = Settings()
        ok, value = set_setting(
            settings, "layout", ["regs", "stack", "regs", "code"]
        )
        self.assertTrue(ok)
        self.assertEqual(value, "regs stack code")
        self.assertEqual(settings.layout, ["regs", "stack", "code"])

    def test_set_theme_unknown(self):
        settings = Settings()
        ok, message = set_setting(settings, "theme", ["nope"])
        self.assertFalse(ok)
        self.assertIn("unknown theme", message)

    def test_format_setting(self):
        settings = Settings()
        settings.auto_context = False
        value = format_setting(settings, "auto_context")
        self.assertEqual(value, "off")


if __name__ == "__main__":
    unittest.main()
