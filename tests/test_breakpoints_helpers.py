import unittest

from lldb_mix.core.modules import find_module, module_base


class _FakeFileSpec:
    def __init__(self, filename: str, directory: str):
        self._filename = filename
        self._directory = directory

    def GetFilename(self):
        return self._filename

    def GetDirectory(self):
        return self._directory


class _FakeAddress:
    def __init__(self, load_addr: int, valid: bool = True):
        self._load_addr = load_addr
        self._valid = valid

    def IsValid(self):
        return self._valid

    def GetLoadAddress(self, target):
        _ = target
        return self._load_addr


class _FakeSection(_FakeAddress):
    pass


class _FakeModule:
    def __init__(
        self,
        filename: str,
        directory: str,
        header: _FakeAddress | None = None,
        section: _FakeSection | None = None,
    ):
        self._spec = _FakeFileSpec(filename, directory)
        self._header = header
        self._section = section

    def GetFileSpec(self):
        return self._spec

    def GetObjectFileHeaderAddress(self):
        return self._header

    def GetSectionAtIndex(self, idx: int):
        _ = idx
        return self._section


class _FakeTarget:
    def __init__(self, modules):
        self._modules = list(modules)

    def module_iter(self):
        return iter(self._modules)


class _FakeLLDB:
    LLDB_INVALID_ADDRESS = 0xFFFFFFFFFFFFFFFF


class TestBreakpointsHelpers(unittest.TestCase):
    def test_find_module_by_filename(self):
        modules = [
            _FakeModule("libfoo.dylib", "/tmp"),
            _FakeModule("libbar.dylib", "/opt"),
        ]
        target = _FakeTarget(modules)
        self.assertIs(find_module(target, "libbar.dylib"), modules[1])

    def test_find_module_by_path(self):
        modules = [
            _FakeModule("libfoo.dylib", "/tmp"),
            _FakeModule("libbar.dylib", "/opt"),
        ]
        target = _FakeTarget(modules)
        self.assertIs(find_module(target, "/tmp/libfoo.dylib"), modules[0])

    def test_find_module_no_match(self):
        modules = [_FakeModule("libfoo.dylib", "/tmp")]
        target = _FakeTarget(modules)
        self.assertIsNone(find_module(target, "missing.dylib"))

    def test_module_base_prefers_header(self):
        header = _FakeAddress(0x1234, valid=True)
        section = _FakeSection(0x9999, valid=True)
        module = _FakeModule("libfoo.dylib", "/tmp", header=header, section=section)
        base = module_base(_FakeTarget([]), module, _FakeLLDB)
        self.assertEqual(base, 0x1234)

    def test_module_base_falls_back_to_section(self):
        header = _FakeAddress(_FakeLLDB.LLDB_INVALID_ADDRESS, valid=True)
        section = _FakeSection(0x2000, valid=True)
        module = _FakeModule("libfoo.dylib", "/tmp", header=header, section=section)
        base = module_base(_FakeTarget([]), module, _FakeLLDB)
        self.assertEqual(base, 0x2000)


if __name__ == "__main__":
    unittest.main()
