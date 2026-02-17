"""Google Gemini API backend for article scoring."""

import json
import os

from google import genai
from google.genai import types

from samfkurator.models import Article, ScoringResult
from samfkurator.scoring.prompt import DEEP_READ_SYSTEM_PROMPT, build_deep_read_prompt, parse_scoring_response


class GeminiBackend:
    def __init__(self, model: str = "gemini-2.0-flash"):
        self.model = model
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        self.client = genai.Client(api_key=api_key)

    def score_article(self, article: Article) -> ScoringResult | None:
        prompt = build_deep_read_prompt(
            article.title,
            article.scoring_text,
            article.source_name,
            article.language,
        )
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=DEEP_READ_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.2,
                    max_output_tokens=500,
                ),
            )
            raw = response.text
            return parse_scoring_response(raw, article.url, "gemini")
        except Exception:
            return None

    def skim(self, headlines: list[dict]) -> list[int]:
        """
        Given a list of {title, teaser, url} dicts, return indices of
        headlines worth reading in full (0-indexed).
        """
        from samfkurator.scoring.prompt import SKIM_SYSTEM_PROMPT, build_skim_prompt
        prompt = build_skim_prompt(headlines)
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SKIM_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.1,
                    max_output_tokens=200,
                ),
            )
            data = json.loads(response.text)
            return [int(i) for i in data.get("relevant_indices", [])]
        except Exception:
            return list(range(len(headlines)))

    def is_available(self) -> bool:
        return bool(os.environ.get("GEMINI_API_KEY"))
