from __future__ import annotations

import re
from typing import List, Optional

from playwright.sync_api import Page

from src.models.item import BookItem


def extract_category_links(page: Page, base_url: str) -> List[str]:
    side_categories = page.locator(".side_categories ul li ul li a")
    count = side_categories.count()
    links: List[str] = []
    for index in range(count):
        relative = side_categories.nth(index).get_attribute("href") or ""
        links.append(f"{base_url}{relative}")
    return links


def find_category_link(page: Page, category_name: str, base_url: str) -> Optional[str]:
    side_categories = page.locator(".side_categories ul li ul li a")
    count = side_categories.count()
    for index in range(count):
        text = side_categories.nth(index).inner_text().strip()
        if text.lower() == category_name.lower():
            relative = side_categories.nth(index).get_attribute("href") or ""
            return f"{base_url}{relative}"
    return None


def extract_list_items(page: Page, category_url: str, category_name: str, crawled_at: str) -> List[BookItem]:
    items: List[BookItem] = []
    rows = page.locator("article.product_pod")
    count = rows.count()
    for index in range(count):
        row = rows.nth(index)
        title = _safe_inner_text(row, "h3 a", attr="title")
        price = _safe_inner_text(row, ".price_color")
        availability = _safe_inner_text(row, ".instock.availability")
        rating = _safe_rating(row)
        relative = _safe_attr(row, "h3 a", "href")
        product_url = relative if relative.startswith("http") else f"{category_url.rsplit('/', 1)[0]}/{relative.lstrip('/')}"
        items.append(
            BookItem(
                title=title,
                price=price,
                availability=availability,
                rating=rating,
                product_url=product_url,
                source_category=category_name,
                source_url=category_url,
                crawled_at=crawled_at,
            )
        )
    return items


def extract_detail(page: Page, item: BookItem) -> BookItem:
    item.upc = _table_value(page, "UPC")
    item.product_type = _table_value(page, "Product Type")
    item.tax = _table_value(page, "Tax")
    item.number_of_reviews = _table_value(page, "Number of reviews")
    item.description = _description(page)
    return item


def _safe_inner_text(parent, selector: str, attr: Optional[str] = None) -> str:
    locator = parent.locator(selector).first
    if attr:
        return (locator.get_attribute(attr) or "").strip()
    return locator.inner_text().strip()


def _safe_rating(parent) -> str:
    rating_class = parent.locator("p.star-rating").get_attribute("class") or ""
    match = re.search(r"star-rating\s+(\w+)", rating_class)
    return match.group(1) if match else ""


def _safe_attr(parent, selector: str, attr: str) -> str:
    return parent.locator(selector).first.get_attribute(attr) or ""


def _table_value(page: Page, header_text: str) -> Optional[str]:
    rows = page.locator("table.table-striped tr")
    count = rows.count()
    for index in range(count):
        row = rows.nth(index)
        header = row.locator("th").inner_text().strip()
        if header == header_text:
            return row.locator("td").inner_text().strip()
    return None


def _description(page: Page) -> Optional[str]:
    paragraph = page.locator("#product_description + p")
    if paragraph.count() == 0:
        return None
    return paragraph.first.inner_text().strip()


def next_page_exists(page: Page) -> Optional[str]:
    next_button = page.locator("li.next > a")
    if next_button.count() == 0:
        return None
    href = next_button.first.get_attribute("href")
    if not href:
        return None
    return href
