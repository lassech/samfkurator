"""DeepSeek API backend (OpenAI-compatible) for article scoring."""

import json
import os

from openai import OpenAI

from samfkurator.models import Article, ScoringResult
from samfkurator.scoring.prompt import DEEP_READ_SYSTEM_PROMPT, build_deep_read_prompt, parse_scoring_response


class DeepSeekBackend:
    def __init__(self, model: str = "deepseek-chat"):
        self.model = model
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable not set")
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
        )

    def score_article(self, article: Article) -> ScoringResult | None:
        prompt = build_deep_read_prompt(
            article.title,
            article.scoring_text,
            article.source_name,
            article.language,
        )
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": DEEP_READ_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=500,
            )
            raw = response.choices[0].message.content
            return parse_scoring_response(raw, article.url, "deepseek")
        except Exception:
            return None

    def skim(self, headlines: list[dict]) -> list[int]:
        from samfkurator.scoring.prompt import SKIM_SYSTEM_PROMPT, build_skim_prompt
        prompt = build_skim_prompt(headlines)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SKIM_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=200,
            )
            data = json.loads(response.choices[0].message.content)
            return [int(i) for i in data.get("relevant_indices", [])]
        except Exception:
            return list(range(len(headlines)))

    def is_available(self) -> bool:
        return bool(os.environ.get("DEEPSEEK_API_KEY"))
