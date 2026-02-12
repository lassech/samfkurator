import httpx

from samfkurator.models import Article, ScoringResult
from samfkurator.scoring.prompt import (
    SYSTEM_PROMPT,
    build_scoring_prompt,
    parse_scoring_response,
)


class OllamaBackend:
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3:8b",
        temperature: float = 0.3,
    ):
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.client = httpx.Client(timeout=120.0)

    def score_article(self, article: Article) -> ScoringResult | None:
        prompt = build_scoring_prompt(
            article.title,
            article.scoring_text,
            article.source_name,
            article.language,
        )

        try:
            response = self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "system": SYSTEM_PROMPT,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": 300,
                    },
                },
            )
            response.raise_for_status()
            raw = response.json()["response"]
            return parse_scoring_response(raw, article.url, "ollama")
        except (httpx.HTTPError, KeyError):
            return None

    def is_available(self) -> bool:
        try:
            r = self.client.get(f"{self.base_url}/api/tags")
            return r.status_code == 200
        except httpx.ConnectError:
            return False
