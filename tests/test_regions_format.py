import unittest
from unittest.mock import patch

from lldb_mix.commands.regions import format_regions_table
from lldb_mix.core.memory import MemoryRegion


class TestRegionsFormat(unittest.TestCase):
    def test_regions_table_basic(self):
        regions = [
            MemoryRegion(
                start=0x1000,
                end=0x2000,
                read=True,
                write=False,
                execute=True,
                name="text",
            ),
            MemoryRegion(
                start=0x2000,
                end=0x2400,
                read=True,
                write=True,
                execute=False,
                name="data",
            ),
        ]
        with patch(
            "lldb_mix.commands.regions._module_path",
            side_effect=lambda target, addr, lldb_module: (
                "" if addr == 0x1000 else "/bin/test"
            ),
        ):
            lines = format_regions_table(
                regions,
                ptr_size=8,
                target=object(),
                lldb_module=None,
                term_width=120,
                style=lambda text, role: text,
            )

        self.assertEqual(
            lines[0].split()[:6], ["START", "END", "SIZE", "PROT", "NAME", "PATH"]
        )
        self.assertEqual(lines[1], "-" * len(lines[0]))
        self.assertIn("r-x", lines[2])
        self.assertIn("rw-", lines[3])
        self.assertIn("/bin/test", lines[3])


if __name__ == "__main__":
    unittest.main()
