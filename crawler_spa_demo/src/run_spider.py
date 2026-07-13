from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List

from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from src.browser.page import BrowserPage
from src.extractors.schema import extract_detail, extract_list_items, find_category_link, next_page_exists
from src.models.item import BookItem
from src.pipelines.csv_pipeline import CsvPipeline
from src.pipelines.json_pipeline import JsonlPipeline
from src.settings import BASE_URL, MAX_PAGES, OUTPUT_DIR, POLITENESS_DELAY_SECONDS, START_CATEGORY
from src.utils.load_config import load_settings
from src.utils.throttle import Throttle


def _is_retryable(exception: BaseException) -> bool:
    message = str(exception).lower()
    return "timeout" in message or "navigation" in message


class CategorySpider:
    def __init__(self) -> None:
        settings = load_settings()
        self._base_url = getattr(settings, "BASE_URL", BASE_URL)
        self._start_category = getattr(settings, "START_CATEGORY", START_CATEGORY)
        self._max_pages = getattr(settings, "MAX_PAGES", MAX_PAGES)
        self._output_dir = getattr(settings, "OUTPUT_DIR", OUTPUT_DIR)
        self._delay = getattr(settings, "POLITENESS_DELAY_SECONDS", POLITENESS_DELAY_SECONDS)
        self._throttle = Throttle(self._delay)
        self._browser = BrowserPage(headless=True, throttle=self._throttle)
        self._csv_pipeline = CsvPipeline(self._output_dir)
        self._jsonl_pipeline = JsonlPipeline(self._output_dir)
        self._logger = logging.getLogger("crawler.category")

    def run(self) -> None:
        page = self._browser.start()
        try:
            self._csv_pipeline.open()
            self._jsonl_pipeline.open()
            self._crawl_category(page)
        finally:
            self._csv_pipeline.close()
            self._jsonl_pipeline.close()
            self._browser.stop()

    @retry(retry=retry_if_exception(_is_retryable), wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
    def _crawl_category(self, page) -> None:
        category_url = self._resolve_category_url(page)
        self._browser.goto(page, category_url)
        crawled_at = datetime.now(timezone.utc).isoformat()
        page_number = 1
        collected: List[BookItem] = []
        while page_number <= self._max_pages:
            self._logger.info("Crawling page %s", page.url)
            items = extract_list_items(page, category_url, self._start_category, crawled_at)
            self._logger.info("Found %s items", len(items))
            for item in items:
                detail_item = self._visit_detail(page, item)
                collected.append(detail_item)
            next_href = next_page_exists(page)
            if not next_href:
                break
            next_url = next_href if next_href.startswith("http") else f"{category_url.rsplit('/', 1)[0]}/{next_href.lstrip('/')}"
            self._browser.goto(page, next_url)
            page_number += 1
        if collected:
            self._csv_pipeline.process_items(collected)
            self._jsonl_pipeline.process_items(collected)

    def _resolve_category_url(self, page) -> str:
        self._browser.goto(page, self._base_url)
        found = find_category_link(page, self._start_category, self._base_url)
        if not found:
            raise ValueError(f"Category '{self._start_category}' not found")
        return found

    @retry(retry=retry_if_exception(_is_retryable), wait=wait_exponential(multiplier=1, min=2, max=10), stop=stop_after_attempt(3))
    def _visit_detail(self, page, item: BookItem) -> BookItem:
        self._browser.goto(page, item.product_url)
        return extract_detail(page, item)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    spider = CategorySpider()
    spider.run()


if __name__ == "__main__":
    main()
