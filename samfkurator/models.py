from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Article:
    url: str
    title: str
    source_name: str
    summary: str = ""
    full_text: Optional[str] = None
    published: Optional[datetime] = None
    language: str = "da"
    has_paywall: bool = False
    fetched_at: Optional[datetime] = None

    @property
    def scoring_text(self) -> str:
        """Best available text for scoring."""
        if self.full_text and len(self.full_text) > 200:
            return f"{self.title}\n\n{self.full_text[:2000]}"
        return f"{self.title}\n\n{self.summary}"


@dataclass
class DisciplineScore:
    sociologi: int = 0
    politik: int = 0
    okonomi: int = 0
    international_politik: int = 0
    metode: int = 0


@dataclass
class ScoringResult:
    article_url: str
    overall_score: int
    disciplines: DisciplineScore
    primary_discipline: str
    explanation: str
    scored_at: Optional[datetime] = None
    backend_used: str = "ollama"
