"""Web scraper for Danish news sites without RSS feeds."""

import time
from datetime import datetime
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from samfkurator.config import ScrapeSourceConfig
from samfkurator.models import Article

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
}

# URL path patterns that indicate news articles for each site
ARTICLE_PATTERNS = {
    "politiken.dk": [
        "/danmark/", "/international/", "/debat/", "/kultur/",
        "/oekonomi/", "/samfund/", "/politik/",
    ],
    "berlingske.dk": [
        "/politik/", "/oekonomi/", "/indland/", "/internationalt/",
        "/samfund/", "/kultur/", "/kommentarer/",
    ],
    "jyllands-posten.dk": [
        "/politik/", "/indland/", "/international/", "/oekonomi/",
        "/debat/",
    ],
}


def _is_article_link(href: str, domain: str) -> bool:
    """Check if a link looks like a news article."""
    patterns = ARTICLE_PATTERNS.get(domain, [])
    return any(p in href for p in patterns)


def _clean_title(text: str) -> str:
    """Clean up scraped title text."""
    return " ".join(text.split()).strip()


def _parse_datetime(text: str) -> datetime | None:
    """Parse an ISO datetime string."""
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(text.strip(), fmt)
        except ValueError:
            continue
    return None


def _fetch_article_meta(url: str) -> tuple[str, datetime | None]:
    """Fetch description and published date from an article page."""
    summary = ""
    published = None
    try:
        r = httpx.get(url, headers=HEADERS, follow_redirects=True, timeout=10)
        if r.status_code != 200:
            return summary, published
        soup = BeautifulSoup(r.text, "lxml")

        # Extract description
        og = soup.find("meta", property="og:description")
        if og and og.get("content"):
            summary = og["content"].strip()
        else:
            meta = soup.find("meta", attrs={"name": "description"})
            if meta and meta.get("content"):
                summary = meta["content"].strip()

        # Extract published date
        pub_tag = soup.find("meta", property="article:published_time")
        if pub_tag and pub_tag.get("content"):
            published = _parse_datetime(pub_tag["content"])
        if not published:
            time_tag = soup.find("time", datetime=True)
            if time_tag:
                published = _parse_datetime(time_tag["datetime"])
    except Exception:
        pass
    return summary, published


def scrape_site(
    source: ScrapeSourceConfig, max_articles: int = 20, delay: float = 1.0
) -> list[Article]:
    """Scrape articles from a news site's front page."""
    articles = []
    seen_urls: set[str] = set()

    for url in source.urls:
        try:
            r = httpx.get(
                url, headers=HEADERS, follow_redirects=True, timeout=15
            )
            if r.status_code != 200:
                continue

            soup = BeautifulSoup(r.text, "lxml")
            domain = url.split("//")[1].split("/")[0].replace("www.", "")

            for a_tag in soup.find_all("a", href=True):
                if len(articles) >= max_articles:
                    break

                href = a_tag["href"]
                title = _clean_title(a_tag.get_text())

                # Skip short titles (navigation links, etc.)
                if len(title) < 20:
                    continue

                if not _is_article_link(href, domain):
                    continue

                # Make absolute URL
                full_url = urljoin(url, href)

                # Deduplicate
                if full_url in seen_urls:
                    continue
                seen_urls.add(full_url)

                # Fetch meta description and date
                if delay > 0:
                    time.sleep(delay)
                summary, published = _fetch_article_meta(full_url)

                articles.append(
                    Article(
                        url=full_url,
                        title=title[:200],
                        source_name=source.name,
                        summary=summary[:500],
                        language=source.language,
                        has_paywall=source.paywall,
                        published=published,
                    )
                )

        except Exception:
            continue

    return articles[:max_articles]


def scrape_all_sources(
    sources: list[ScrapeSourceConfig], max_per_site: int = 20, delay: float = 2.0
) -> list[Article]:
    """Scrape articles from all configured scrape sources."""
    all_articles: list[Article] = []

    for source in sources:
        articles = scrape_site(source, max_per_site, delay=delay)
        all_articles.extend(articles)
        if delay > 0:
            time.sleep(delay)

    return all_articles
