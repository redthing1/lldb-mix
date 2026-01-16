import hashlib
import unittest
from unittest.mock import patch

from lldb_mix.core import paths


class TestPaths(unittest.TestCase):
    def test_session_path_hash(self):
        path = "/opt/bin/sample_basic"
        digest = hashlib.sha256(path.encode("utf-8", errors="ignore")).hexdigest()[:8]
        with patch("lldb_mix.core.paths.sessions_dir", return_value="/tmp/sessions"):
            result = paths.session_path(path)
        self.assertEqual(
            result,
            f"/tmp/sessions/sample_basic-{digest}.json",
        )

    def test_session_path_sanitizes(self):
        path = "/opt/bin/my sample@bin"
        digest = hashlib.sha256(path.encode("utf-8", errors="ignore")).hexdigest()[:8]
        with patch("lldb_mix.core.paths.sessions_dir", return_value="/tmp/sessions"):
            result = paths.session_path(path)
        self.assertEqual(
            result,
            f"/tmp/sessions/my_sample_bin-{digest}.json",
        )


if __name__ == "__main__":
    unittest.main()
