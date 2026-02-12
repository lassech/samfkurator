from anthropic import Anthropic

from samfkurator.models import Article, ScoringResult
from samfkurator.scoring.prompt import (
    SYSTEM_PROMPT,
    build_scoring_prompt,
    parse_scoring_response,
)


class ClaudeBackend:
    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.model = model
        self.client = Anthropic()

    def score_article(self, article: Article) -> ScoringResult | None:
        prompt = build_scoring_prompt(
            article.title,
            article.scoring_text,
            article.source_name,
            article.language,
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=400,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text
            return parse_scoring_response(raw, article.url, "claude")
        except Exception:
            return None
