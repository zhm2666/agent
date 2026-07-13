"""
Playwright demo for books.toscrape.com
Extracts Travel category books (list + detail) into JSONL.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_URL = "https://books.toscrape.com/"
START_CATEGORY = "Travel"
MAX_PAGES = 2
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main():
    items = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        ))
        page = context.new_page()
        page.set_default_timeout(30000)

        # Open category page
        page.goto(BASE_URL, wait_until="domcontentloaded")
        page.click(f"text={START_CATEGORY}")
        page.wait_for_load_state("domcontentloaded")

        for _ in range(MAX_PAGES):
            page.wait_for_selector("article.product_pod")
            rows = page.locator("article.product_pod")
            count = rows.count()
            for i in range(count):
                row = rows.nth(i)
                title = row.locator("h3 a").get_attribute("title") or row.locator("h3 a").inner_text().strip()
                price = row.locator(".price_color").inner_text().strip()
                availability = row.locator(".instock.availability").inner_text().strip()
                rating = row.locator("p.star-rating").get_attribute("class") or ""
                rating = rating.replace("star-rating", "").strip()
                rel = row.locator("h3 a").get_attribute("href") or ""
                if rel.startswith("http"):
                    product_url = rel
                else:
                    product_url = f"{BASE_URL.rstrip('/')}/{rel.lstrip('/')}"

                item = {
                    "title": title,
                    "price": price,
                    "availability": availability,
                    "rating": rating,
                    "product_url": product_url,
                    "source_category": START_CATEGORY,
                    "source_url": page.url,
                    "crawled_at": iso_now(),
                }

                # detail page
                detail = context.new_page()
                detail.goto(product_url, wait_until="domcontentloaded")
                detail.wait_for_selector("table.table-striped")
                rows_table = detail.locator("table.table-striped tr")
                for r in range(rows_table.count()):
                    th = rows_table.nth(r).locator("th").inner_text().strip()
                    td = rows_table.nth(r).locator("td").inner_text().strip()
                    if th == "UPC":
                        item["upc"] = td
                    elif th == "Product Type":
                        item["product_type"] = td
                    elif th == "Tax":
                        item["tax"] = td
                    elif th == "Number of reviews":
                        item["number_of_reviews"] = td

                desc = detail.locator("#product_description + p")
                if desc.count():
                    item["description"] = desc.first.inner_text().strip()
                detail.close()
                items.append(item)

            next_btn = page.locator("li.next > a")
            if next_btn.count() == 0:
                break
            next_btn.first.click()
            page.wait_for_load_state("domcontentloaded")
            time.sleep(1.0)

        browser.close()

    out_path = OUTPUT_DIR / "playwright_demo.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    print(f"[playwright_demo] saved {len(items)} items -> {out_path}")


if __name__ == "__main__":
    main()
