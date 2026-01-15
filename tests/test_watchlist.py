import unittest

from lldb_mix.core.watchlist import WatchList


class TestWatchList(unittest.TestCase):
    def test_add_remove(self):
        watches = WatchList()
        entry = watches.add("$sp", "stack")
        self.assertEqual(entry.wid, 1)
        self.assertTrue(watches.remove(1))
        self.assertFalse(watches.remove(1))

    def test_serialize_load(self):
        watches = WatchList()
        watches.add("$sp", "stack")
        watches.add("0x1234")
        data = watches.serialize()
        self.assertEqual(len(data), 2)

        restored = WatchList()
        restored.load(data)
        items = restored.items()
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].expr, "$sp")
        self.assertEqual(items[0].label, "stack")


if __name__ == "__main__":
    unittest.main()
