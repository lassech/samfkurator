import time

import trafilatura

from samfkurator.models import Article


def extract_full_text(
    article: Article, delay: float = 2.0, timeout: float = 15.0
) -> Article:
    """Attempt to extract full article text. Modifies article in place."""
    try:
        downloaded = trafilatura.fetch_url(article.url)
        if downloaded:
            text = trafilatura.extract(
                downloaded,
                include_comments=False,
                include_tables=False,
                favor_precision=True,
            )
            if text:
                article.full_text = text

        time.sleep(delay)
    except Exception:
        pass  # Graceful degradation -- score on summary alone

    return article
