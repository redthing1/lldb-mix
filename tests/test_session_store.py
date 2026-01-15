import json
import os
import tempfile
import unittest
from unittest.mock import patch

from lldb_mix.core.session_store import (
    build_session_data,
    list_sessions,
    load_session,
    save_session,
)
from lldb_mix.core.watchlist import WatchList


class TestSessionStore(unittest.TestCase):
    def test_build_session_data(self):
        watches = WatchList()
        watches.add("$sp")
        data = build_session_data(None, watches)
        self.assertIn("version", data)
        self.assertIn("breakpoints", data)
        self.assertEqual(len(data["watches"]), 1)

    def test_save_load_session(self):
        watches = WatchList()
        watches.add("$sp")
        data = build_session_data(None, watches)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "session.json")
            self.assertTrue(save_session(path, data))
            loaded = load_session(path)
            self.assertIsInstance(loaded, dict)
            self.assertEqual(loaded.get("version"), 1)

    def test_list_sessions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            session_path = os.path.join(tmpdir, "demo.json")
            with open(session_path, "w") as handle:
                json.dump({"version": 1}, handle)
            with patch("lldb_mix.core.session_store.sessions_dir", return_value=tmpdir):
                items = list_sessions()
            self.assertEqual(items, ["demo.json"])


if __name__ == "__main__":
    unittest.main()
