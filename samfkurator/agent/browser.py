"""Playwright-based browser with bypass-paywalls extension for full article access."""

import random
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, Page, BrowserContext

try:
    from playwright_stealth import Stealth
    _STEALTH = Stealth()
except ImportError:
    _STEALTH = None


def _extension_path() -> str:
    """Find the bypass-paywalls extension directory."""
    candidates = [
        Path(__file__).parent.parent.parent / "extensions" / "bypass-paywalls",
        Path("extensions") / "bypass-paywalls",
    ]
    for p in candidates:
        if p.exists():
            return str(p.resolve())
    raise FileNotFoundError(
        "bypass-paywalls extension not found. "
        "Expected at: extensions/bypass-paywalls/"
    )


class ArticleBrowser:
    """Headless browser with bypass-paywalls extension loaded."""

    def __init__(self, headless: bool = True):
        self._playwright = sync_playwright().start()
        ext = _extension_path()
        # Chrome extensions require persistent context
        self._context: BrowserContext = (
            self._playwright.chromium.launch_persistent_context(
                user_data_dir="/tmp/samfkurator-browser-profile",
                headless=headless,
                args=[
                    f"--disable-extensions-except={ext}",
                    f"--load-extension={ext}",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                ],
                viewport={"width": 1280, "height": 900},
            )
        )
        self._page: Page = self._context.new_page()
        if _STEALTH:
            _STEALTH.apply_stealth_sync(self._page)

    def _accept_cookies(self):
        """Try to click through cookie consent dialogs."""
        selectors = [
            "button:has-text('Tillad alle')",
            "button:has-text('Accepter alle')",
            "button:has-text('Accepter')",
            "button:has-text('Accept all')",
            "button:has-text('Godkend alle')",
            "button:has-text('Kun nødvendige')",
            "button:has-text('OK')",
        ]
        for selector in selectors:
            try:
                btn = self._page.locator(selector).first
                if btn.is_visible(timeout=1500):
                    btn.click()
                    time.sleep(2.5)
                    return
            except Exception:
                continue

    def get_headlines(self, url: str, wait_ms: int = 3000) -> list[dict]:
        """
        Open a news site and extract visible headlines with teasers.
        Returns list of {title, teaser, url} dicts.
        """
        self._page.goto(url, wait_until="load", timeout=30000)
        time.sleep(wait_ms / 1000 + random.uniform(0.5, 2.0))
        self._accept_cookies()

        headlines = self._page.evaluate("""() => {
            const seen = new Set();
            const results = [];
            const base = window.location.origin;

            // Collect all <a> tags with meaningful text
            for (const a of document.querySelectorAll('a[href]')) {
                const title = a.innerText.trim().replace(/\\s+/g, ' ');
                if (title.length < 20) continue;

                let href = a.getAttribute('href');
                if (!href) continue;
                if (href.startsWith('/')) href = base + href;
                if (!href.startsWith('http')) continue;
                if (seen.has(href)) continue;

                // Skip obvious non-articles
                const skipWords = ['abonnement', 'log ind', 'tilmeld', 'cookie',
                                   'podcast', 'video', 'galleri', 'nyhedsbrev',
                                   'udbyder', 'kun 1 kr', 'fuld adgang'];
                const titleLower = title.toLowerCase();
                if (skipWords.some(w => titleLower.includes(w))) continue;

                // Look for a teaser in nearby sibling/parent elements
                let teaser = '';
                const parent = a.closest('article') || a.closest('[class*="card"]')
                             || a.closest('[class*="item"]') || a.parentElement;
                if (parent) {
                    for (const el of parent.querySelectorAll('p, [class*="teaser"], [class*="summary"], [class*="lead"]')) {
                        const t = el.innerText.trim().replace(/\\s+/g, ' ');
                        if (t.length > 30 && t !== title) {
                            teaser = t.substring(0, 200);
                            break;
                        }
                    }
                }

                seen.add(href);
                results.push({ title: title.substring(0, 200), teaser, url: href });
                if (results.length >= 60) break;
            }
            return results;
        }""")
        return headlines or []

    def read_article(self, url: str, wait_ms: int = 4000) -> str:
        """
        Navigate to an article and extract its full text.
        bypass-paywalls extension handles paywall removal automatically.
        Returns the article text.
        """
        self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(wait_ms / 1000 + random.uniform(0.5, 2.5))
        self._accept_cookies()

        text = self._page.evaluate("""() => {
            // Remove clutter
            for (const sel of ['header', 'footer', 'nav', 'aside',
                                '[class*="cookie"]', '[class*="paywall"]',
                                '[class*="subscribe"]', '[class*="ad-"]',
                                '[class*="related"]', '[class*="recommend"]']) {
                document.querySelectorAll(sel).forEach(el => el.remove());
            }

            // Try article-specific containers first
            const containers = [
                'article',
                '[class*="article-body"]',
                '[class*="article__body"]',
                '[class*="story-body"]',
                '[class*="article-content"]',
                'main',
            ];
            for (const sel of containers) {
                const el = document.querySelector(sel);
                if (el && el.innerText.trim().length > 300) {
                    return el.innerText.trim().replace(/\\s+/g, ' ');
                }
            }
            // Fallback: body text
            return document.body.innerText.trim().replace(/\\s+/g, ' ');
        }""")
        return (text or "")[:6000]

    def close(self):
        self._context.close()
        self._playwright.stop()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
