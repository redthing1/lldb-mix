import unittest
from unittest.mock import patch

from lldb_mix.commands import conf
from lldb_mix.core.settings import Settings


class TestConfCommand(unittest.TestCase):
    def setUp(self):
        self._orig_settings = conf.SETTINGS
        conf.SETTINGS = Settings()

    def tearDown(self):
        conf.SETTINGS = self._orig_settings

    def test_list_includes_keys(self):
        msg = conf._handle_list()
        self.assertIn("enable_color", msg)
        self.assertIn("layout", msg)

    def test_get_setting(self):
        conf.SETTINGS.theme = "base"
        msg = conf._handle_get(["theme"])
        self.assertEqual(msg, "[lldb-mix] theme = base")

    def test_get_unknown(self):
        msg = conf._handle_get(["nope"])
        self.assertEqual(msg, "[lldb-mix] unknown setting: nope")

    def test_set_auto_context_on(self):
        conf.SETTINGS.auto_context = False
        with patch("lldb_mix.commands.conf.ensure_stop_hook") as hook:
            msg = conf._handle_set(object(), ["auto_context", "on"])
            self.assertTrue(conf.SETTINGS.auto_context)
            self.assertIn("auto_context = on", msg)
            hook.assert_called_once()

    def test_set_auto_context_off(self):
        conf.SETTINGS.auto_context = True
        with patch("lldb_mix.commands.conf.remove_stop_hook") as hook:
            msg = conf._handle_set(object(), ["auto_context", "off"])
            self.assertFalse(conf.SETTINGS.auto_context)
            self.assertIn("auto_context = off", msg)
            hook.assert_called_once()


if __name__ == "__main__":
    unittest.main()
