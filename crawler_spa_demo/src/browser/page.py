from __future__ import annotations

from pathlib import Path
from typing import Optional

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from src.utils.throttle import Throttle


class BrowserPage:
    def __init__(self, headless: bool = True, throttle: Optional[Throttle] = None) -> None:
        self._headless = headless
        self._throttle = throttle
        self._playwright = sync_playwright().start()
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    def start(self) -> Page:
        self._browser = self._playwright.chromium.launch(headless=self._headless)
        self._context = self._browser.new_context(
            user_agent="Mozilla/5.0 (compatible; CrawlerDemo/1.0)",
            locale="en-US",
        )
        self._page = self._context.new_page()
        return self._page

    def stop(self) -> None:
        if self._page:
            self._page.close()
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        self._playwright.stop()

    def goto(self, page: Page, url: str) -> None:
        if self._throttle:
            self._throttle.wait()
        page.goto(url, wait_until="networkidle")

    @staticmethod
    def capture_requests(page: Page, url_pattern: str):
        captured = []

        def _handler(route):
            request = route.request
            if url_pattern in request.url:
                captured.append(request.url)
            route.continue_()

        page.route("**/*", _handler)
        return captured
