import os
import sys


def _ensure_repo_on_path() -> None:
    repo_root = os.path.dirname(os.path.abspath(__file__))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    package_dir = os.path.join(repo_root, "lldb_mix")
    existing_path = globals().get("__path__")
    if existing_path is None:
        globals()["__path__"] = [package_dir]
    elif package_dir not in existing_path:
        existing_path.append(package_dir)


def __lldb_init_module(debugger, internal_dict) -> None:
    _ensure_repo_on_path()
    try:
        from lldb_mix import bootstrap
    except Exception as exc:
        print(f"[lldb-mix] load failed: {exc}")
        return
    bootstrap.init(debugger, internal_dict)
