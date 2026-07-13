from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Optional

from src.models.item import BookItem


class CsvPipeline:
    def __init__(self, output_dir: str, filename: str = "books.csv") -> None:
        self._output_path = Path(output_dir) / filename
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_handle = open(self._output_path, "w", newline="", encoding="utf-8-sig")
        self._writer: Optional[csv.DictWriter] = None

    def open(self) -> None:
        fieldnames = [
            "title",
            "price",
            "availability",
            "rating",
            "product_url",
            "source_category",
            "source_url",
            "crawled_at",
            "description",
            "upc",
            "product_type",
            "tax",
            "number_of_reviews",
        ]
        self._writer = csv.DictWriter(self._file_handle, fieldnames=fieldnames)
        self._writer.writeheader()

    def process_items(self, items: Iterable[BookItem]) -> None:
        if not self._writer:
            raise RuntimeError("Pipeline not opened")
        for item in items:
            self._writer.writerow(item.__dict__)

    def close(self) -> None:
        if self._file_handle and not self._file_handle.closed:
            self._file_handle.close()
