import re
from datetime import datetime
from typing import Generator

import feedparser

from samfkurator.config import SourceConfig
from samfkurator.models import Article


def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    return re.sub(r"<[^>]+>", "", text).strip()


def fetch_feed(
    feed_url: str, source: SourceConfig, max_items: int = 20
) -> Generator[Article, None, None]:
    """Parse an RSS feed and yield Article objects."""
    feed = feedparser.parse(feed_url)

    for entry in feed.entries[:max_items]:
        summary = ""
        if hasattr(entry, "summary"):
            summary = entry.summary
        elif hasattr(entry, "description"):
            summary = entry.description

        published = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                published = datetime(*entry.published_parsed[:6])
            except (TypeError, ValueError):
                pass

        link = entry.get("link", "")
        if not link:
            continue

        yield Article(
            url=link,
            title=entry.get("title", ""),
            source_name=source.name,
            summary=_strip_html(summary),
            published=published,
            language=source.language,
            has_paywall=source.paywall,
        )


def fetch_all_sources(
    sources: list[SourceConfig], max_per_feed: int = 20
) -> list[Article]:
    """Fetch articles from all configured sources, deduplicating by URL."""
    seen_urls: set[str] = set()
    articles: list[Article] = []

    for source in sources:
        for feed_url in source.feeds:
            try:
                for article in fetch_feed(feed_url, source, max_per_feed):
                    if article.url not in seen_urls:
                        seen_urls.add(article.url)
                        articles.append(article)
            except Exception:
                # Log warning but continue with other feeds
                pass

    return articles
