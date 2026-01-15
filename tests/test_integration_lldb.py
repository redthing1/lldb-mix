import os
import shutil
import subprocess
import tempfile
import unittest

from lldb_mix.ui.ansi import strip_ansi


class TestLldbIntegration(unittest.TestCase):
    def test_context_command_emits_panes(self):
        lldb_path = shutil.which("lldb")
        cmake_path = shutil.which("cmake")
        if not lldb_path or not cmake_path:
            raise unittest.SkipTest("lldb or cmake not available")

        repo_root = os.path.dirname(os.path.dirname(__file__))
        samples_dir = os.path.join(repo_root, "samples")
        loader = os.path.join(repo_root, "lldb_mix_loader.py")

        with tempfile.TemporaryDirectory() as tmpdir:
            build_dir = os.path.join(tmpdir, "build")
            configure = subprocess.run(
                [cmake_path, "-S", samples_dir, "-B", build_dir],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            if configure.returncode != 0:
                raise unittest.SkipTest(f"cmake configure failed: {configure.stdout}")

            build = subprocess.run(
                [cmake_path, "--build", build_dir, "--target", "sample_basic"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            if build.returncode != 0:
                raise unittest.SkipTest(f"cmake build failed: {build.stdout}")

            binary = os.path.join(build_dir, "sample_basic")
            if not os.path.isfile(binary):
                raise unittest.SkipTest("sample binary not produced")

            commands = [
                f"command script import {loader}",
                "breakpoint set -n main",
                "run",
                "context",
                "dump sp 64",
                "quit",
            ]
            lldb_cmd = [lldb_path, "-b", binary]
            for cmd in commands:
                lldb_cmd.extend(["-o", cmd])

            proc = subprocess.run(
                lldb_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            output = strip_ansi(proc.stdout)

            if "attach failed" in output or "Not allowed to attach" in output:
                raise unittest.SkipTest("debugger attach not permitted")

            self.assertIn("[regs]", output)
            self.assertIn("[code]", output)
            self.assertIn("[dump]", output)


if __name__ == "__main__":
    unittest.main()
