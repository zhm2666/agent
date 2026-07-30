"""
Use Playwright to render https://huohuo90.com/home and capture:
  - rendered HTML
  - full-page screenshot
  - all CSS stylesheets content
  - all <img> / inline SVG references
Goal: understand the page structure so we can reproduce it as static HTML.
"""
from pathlib import Path
from urllib.parse import urljoin, urlparse
import json
import re

from playwright.sync_api import sync_playwright

OUT = Path("F:/GOMaster/agent/huohuo90_capture")
OUT.mkdir(exist_ok=True)
BASE = "https://huohuo90.com/home"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        page.set_default_timeout(45000)

        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(2500)

        # try to scroll to bottom to trigger lazy load
        for y in range(0, 8000, 600):
            page.evaluate(f"window.scrollTo(0, {y})")
            page.wait_for_timeout(250)
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(500)

        # 1) rendered HTML
        html = page.content()
        (OUT / "rendered.html").write_text(html, encoding="utf-8")

        # 2) full-page screenshot
        page.screenshot(path=str(OUT / "home_full.png"), full_page=True)
        page.screenshot(path=str(OUT / "home_above_fold.png"), full_page=False)

        # 3) external CSS
        css_links = page.eval_on_selector_all(
            "link[rel='stylesheet']", "els => els.map(e => e.href)"
        )
        (OUT / "css_links.json").write_text(json.dumps(css_links, indent=2, ensure_ascii=False))

        # 4) collect inline <style> blocks
        inline_styles = page.eval_on_selector_all(
            "style", "els => els.map(e => e.textContent)"
        )
        (OUT / "inline_styles.txt").write_text("\n\n---STYLE BLOCK---\n\n".join(inline_styles), encoding="utf-8")

        # 5) collect img src + alt + role for hero/illustration
        imgs = page.evaluate(
            """
            () => Array.from(document.querySelectorAll('img')).map(i => ({
                src: i.currentSrc || i.src,
                alt: i.alt || '',
                width: i.naturalWidth,
                height: i.naturalHeight,
                cls: i.className,
                parent: (i.closest('section,header,footer,main,div')||{}).className || ''
            }))
            """
        )
        (OUT / "imgs.json").write_text(json.dumps(imgs, indent=2, ensure_ascii=False))

        # 6) collect all text content per top-level section for layout analysis
        structure = page.evaluate(
            """
            () => {
              const root = document.getElementById('app');
              if (!root) return null;
              const walk = (el, depth=0) => {
                if (depth > 4) return null;
                if (!el || el.nodeType !== 1) return null;
                const tag = el.tagName.toLowerCase();
                if (['script','style','noscript'].includes(tag)) return null;
                const text = (el.children.length === 0 ? (el.innerText || '').trim() : '');
                const cs = getComputedStyle(el);
                const self = {
                  tag,
                  cls: el.className && el.className.toString ? el.className.toString().slice(0,80) : '',
                  id: el.id || '',
                  rect: (() => { const r = el.getBoundingClientRect(); return {x:Math.round(r.x),y:Math.round(r.y),w:Math.round(r.width),h:Math.round(r.height)}; })(),
                  bg: cs.backgroundColor,
                  color: cs.color,
                  font: cs.fontSize + ' / ' + cs.fontWeight + ' / ' + cs.fontFamily.slice(0,60),
                  text: text.slice(0, 200),
                  children: []
                };
                for (const c of el.children) {
                  const sub = walk(c, depth+1);
                  if (sub) self.children.push(sub);
                }
                return self;
              };
              return walk(root);
            }
            """
        )
        (OUT / "structure.json").write_text(json.dumps(structure, indent=2, ensure_ascii=False))

        # 7) outer HTML of the app
        app_outer = page.eval_on_selector("#app", "el => el.outerHTML")
        (OUT / "app_outer.html").write_text(app_outer, encoding="utf-8")

        browser.close()
        print("done. outputs in", OUT)


if __name__ == "__main__":
    main()