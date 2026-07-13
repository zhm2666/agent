from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Any


def load_settings() -> Any:
    package_root = Path(__file__).resolve().parent.parent
    src_path = str(package_root)
    if src_path not in __import__("sys").path:
        __import__("sys").path.insert(0, src_path)
    settings = import_module("settings")
    return settings
