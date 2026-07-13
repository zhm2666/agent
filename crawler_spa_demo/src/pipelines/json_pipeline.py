from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable

from src.models.item import BookItem


class JsonlPipeline:
    def __init__(self, output_dir: str, filename: str = "books.jsonl") -> None:
        self._output_path = Path(output_dir) / filename
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_handle = open(self._output_path, "w", encoding="utf-8")

    def open(self) -> None:
        if self._file_handle.closed:
            self._file_handle = open(self._output_path, "w", encoding="utf-8")

    def process_items(self, items: Iterable[BookItem]) -> None:
        for item in items:
            self._file_handle.write(json.dumps(item.__dict__, ensure_ascii=False) + "\n")

    def close(self) -> None:
        if self._file_handle and not self._file_handle.closed:
            self._file_handle.close()
