import os
import shutil
import subprocess
import tempfile
import unittest

from lldb_mix.ui.ansi import strip_ansi


class TestLldbIntegration(unittest.TestCase):
    def _run_lldb(self, commands):
        lldb_path = shutil.which("lldb")
        cmake_path = shutil.which("cmake")
        if not lldb_path or not cmake_path:
            raise unittest.SkipTest("lldb or cmake not available")

        repo_root = os.path.dirname(os.path.dirname(__file__))
        samples_dir = os.path.join(repo_root, "samples")
        loader = os.path.join(repo_root, "lldb_mix_loader.py")

        with tempfile.TemporaryDirectory() as tmpdir:
            build_dir = os.path.join(tmpdir, "build")
            session_path = os.path.join(tmpdir, "session.json")
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

            expanded = [cmd.replace("{session}", session_path) for cmd in commands]
            full_commands = [f"command script import {loader}"] + expanded
            if not any(cmd.strip() == "quit" for cmd in full_commands):
                full_commands.append("quit")

            lldb_cmd = [lldb_path, "-b", binary]
            for cmd in full_commands:
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

            return output

    def test_context_command_emits_panes(self):
        commands = [
            "breakpoint set -n main",
            "run",
            "context",
            "deref $sp",
            "watch add $sp stack",
            "sess save {session}",
            "dump sp 64",
            "u",
            "skip",
            "patch nop $pc 1",
            "patch list",
            "patch restore $pc",
            "db pc 64",
            "dw pc 64",
            "dd pc 64",
            "dq pc 128",
            "bpm sample_basic 0",
            "regions",
            "bpt main",
            "bpn",
            "findmem -s hello -c 1",
            "antidebug",
            "bp clear all",
            "sess load {session}",
            "ret 0",
        ]
        output = self._run_lldb(commands)

        self.assertIn("[regs]", output)
        self.assertIn("[code]", output)
        self.assertIn("[deref]", output)
        self.assertIn("[lldb-mix] watch", output)
        self.assertIn("[lldb-mix] session saved", output)
        self.assertIn("[dump]", output)
        self.assertIn("[u]", output)
        self.assertIn("[lldb-mix] skip", output)
        self.assertIn("[lldb-mix] patch", output)
        self.assertIn("[lldb-mix] patches:", output)
        self.assertIn("[db]", output)
        self.assertIn("[dw]", output)
        self.assertIn("[dd]", output)
        self.assertIn("[dq]", output)
        self.assertIn("[lldb-mix] bpm", output)
        self.assertIn("START", output)
        self.assertIn("[lldb-mix] bpt", output)
        self.assertIn("[lldb-mix] bpn", output)
        self.assertIn("[findmem]", output)
        self.assertIn("[lldb-mix] antidebug", output)
        self.assertIn("[lldb-mix] session loaded", output)
        self.assertIn("[lldb-mix] ret", output)

    def test_rr_command(self):
        output = self._run_lldb(["rr"])
        self.assertNotIn("[lldb-mix] rr failed", output)


if __name__ == "__main__":
    unittest.main()
