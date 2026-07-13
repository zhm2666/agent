"""
Selenium demo for books.toscrape.com
Extracts Travel category books (list + detail) into JSONL.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "https://books.toscrape.com/"
START_CATEGORY = "Travel"
MAX_PAGES = 2
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    )
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    wait = WebDriverWait(driver, 30)
    items = []

    try:
        driver.get(BASE_URL)
        wait = WebDriverWait(driver, 30)

        # open category
        cat = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, START_CATEGORY)))
        cat.click()

        for _ in range(MAX_PAGES):
            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article.product_pod")))
            rows = driver.find_elements(By.CSS_SELECTOR, "article.product_pod")
            for row in rows:
                title = row.find_element(By.CSS_SELECTOR, "h3 a").get_attribute("title") or row.find_element(By.CSS_SELECTOR, "h3 a").text.strip()
                price = row.find_element(By.CSS_SELECTOR, ".price_color").text.strip()
                availability = row.find_element(By.CSS_SELECTOR, ".instock.availability").text.strip()
                rating = row.find_element(By.CSS_SELECTOR, "p.star-rating").get_attribute("class") or ""
                rating = rating.replace("star-rating", "").strip()
                rel = row.find_element(By.CSS_SELECTOR, "h3 a").get_attribute("href") or ""
                product_url = rel if rel.startswith("http") else f"{BASE_URL.rstrip('/')}/{rel.lstrip('/')}"

                item = {
                    "title": title,
                    "price": price,
                    "availability": availability,
                    "rating": rating,
                    "product_url": product_url,
                    "source_category": START_CATEGORY,
                    "source_url": driver.current_url,
                    "crawled_at": iso_now(),
                }

                # detail in new window/tab to avoid losing list page state
                driver.execute_script("window.open(arguments[0]);", product_url)
                driver.switch_to.window(driver.window_handles[-1])
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.table-striped")))
                rows_table = driver.find_elements(By.CSS_SELECTOR, "table.table-striped tr")
                for r in rows_table:
                    th = r.find_element(By.CSS_SELECTOR, "th").text.strip()
                    td = r.find_element(By.CSS_SELECTOR, "td").text.strip()
                    if th == "UPC":
                        item["upc"] = td
                    elif th == "Product Type":
                        item["product_type"] = td
                    elif th == "Tax":
                        item["tax"] = td
                    elif th == "Number of reviews":
                        item["number_of_reviews"] = td

                desc_els = driver.find_elements(By.CSS_SELECTOR, "#product_description + p")
                if desc_els:
                    item["description"] = desc_els[0].text.strip()

                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                items.append(item)

            next_btns = driver.find_elements(By.CSS_SELECTOR, "li.next > a")
            if not next_btns:
                break
            next_btns[0].click()
    finally:
        driver.quit()

    out_path = OUTPUT_DIR / "selenium_demo.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it, ensure_ascii=False) + "\n")
    print(f"[selenium_demo] saved {len(items)} items -> {out_path}")


if __name__ == "__main__":
    main()
