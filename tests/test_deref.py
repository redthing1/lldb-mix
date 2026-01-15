import unittest

from lldb_mix.core.memory import MemoryRegion
from lldb_mix.core.settings import Settings
from lldb_mix.core.symbols import SymbolInfo
from lldb_mix.deref import deref_chain


class FakeReader:
    def __init__(self, segments):
        self.segments = segments

    def read(self, addr, size):
        for start, data in self.segments:
            end = start + len(data)
            if addr >= start and addr + size <= end:
                offset = addr - start
                return data[offset : offset + size]
        return None

    def read_pointer(self, addr, ptr_size):
        data = self.read(addr, ptr_size)
        if not data or len(data) < ptr_size:
            return None
        return int.from_bytes(data, byteorder="little")


class FakeResolver:
    def __init__(self, mapping):
        self.mapping = mapping

    def resolve(self, addr):
        return self.mapping.get(addr)


class TestDerefChain(unittest.TestCase):
    def test_deref_chain_string(self):
        reader = FakeReader(
            [
                (0x1000, (0x2000).to_bytes(8, "little")),
                (0x2000, b"hello\x00" + (b"\x00" * 64)),
            ]
        )
        regions = [MemoryRegion(0x1000, 0x3000, True, True, False, None)]
        chain = deref_chain(0x1000, reader, regions, None, Settings(), 8)
        self.assertEqual(
            chain,
            [
                "0x0000000000001000",
                "0x0000000000002000",
                '"hello"',
            ],
        )

    def test_deref_chain_symbol(self):
        reader = FakeReader([(0x1000, (0x2000).to_bytes(8, "little"))])
        regions = [MemoryRegion(0x1000, 0x3000, True, True, False, None)]
        resolver = FakeResolver({0x2000: SymbolInfo("func", "mod", 0x10)})
        chain = deref_chain(0x1000, reader, regions, resolver, Settings(), 8)
        self.assertEqual(
            chain,
            [
                "0x0000000000001000",
                "0x0000000000002000",
                "mod!func+0x10",
            ],
        )

    def test_deref_chain_loop(self):
        reader = FakeReader([(0x1000, (0x1000).to_bytes(8, "little"))])
        regions = [MemoryRegion(0x1000, 0x2000, True, True, False, None)]
        chain = deref_chain(0x1000, reader, regions, None, Settings(), 8)
        self.assertEqual(
            chain,
            [
                "0x0000000000001000",
                "0x0000000000001000",
                "[loop]",
            ],
        )


if __name__ == "__main__":
    unittest.main()
