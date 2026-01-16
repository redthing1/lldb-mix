import unittest

from lldb_mix.core.config import format_setting, reset_settings, set_setting
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

    def test_set_abi(self):
        settings = Settings()
        ok, value = set_setting(settings, "abi", ["sysv"])
        self.assertTrue(ok)
        self.assertEqual(value, "sysv")
        self.assertEqual(settings.abi, "sysv")

    def test_set_abi_invalid(self):
        settings = Settings()
        ok, message = set_setting(settings, "abi", ["nope"])
        self.assertFalse(ok)
        self.assertIn("unknown abi", message)

    def test_reset_settings(self):
        settings = Settings()
        settings.enable_color = False
        settings.layout = ["code"]
        settings.abi = "sysv"
        reset_settings(settings)
        defaults = Settings()
        self.assertEqual(settings.enable_color, defaults.enable_color)
        self.assertEqual(settings.layout, defaults.layout)
        self.assertEqual(settings.abi, defaults.abi)


if __name__ == "__main__":
    unittest.main()
