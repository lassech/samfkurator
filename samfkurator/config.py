import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class SourceConfig:
    name: str
    feeds: list[str]
    paywall: bool = False
    language: str = "da"


@dataclass
class OllamaConfig:
    model: str = "llama3:8b"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.3


@dataclass
class ClaudeConfig:
    model: str = "claude-haiku-4-5-20251001"


@dataclass
class GeminiConfig:
    model: str = "gemini-2.0-flash"


@dataclass
class DeepSeekConfig:
    model: str = "deepseek-chat"


@dataclass
class AIConfig:
    backend: str = "gemini"
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    claude: ClaudeConfig = field(default_factory=ClaudeConfig)
    gemini: GeminiConfig = field(default_factory=GeminiConfig)
    deepseek: DeepSeekConfig = field(default_factory=DeepSeekConfig)


@dataclass
class ScrapingConfig:
    max_articles_per_feed: int = 20
    request_delay_seconds: float = 2.0
    user_agent: str = "Samfkurator/0.1 (educational news aggregator)"
    fetch_full_text: bool = True
    timeout_seconds: int = 15


@dataclass
class ScoringConfig:
    min_score_to_display: int = 4


@dataclass
class DailyConfig:
    count: int = 10
    max_per_discipline: int = 3
    min_danish: int = 2
    min_international: int = 2


@dataclass
class OutputConfig:
    format: str = "terminal"
    max_results: int = 50
    export_path: str = "./output"


@dataclass
class DatabaseConfig:
    path: str = "./samfkurator.db"


@dataclass
class AgentSourceConfig:
    name: str
    url: str
    language: str = "da"


@dataclass
class ScrapeSourceConfig:
    name: str
    urls: list[str]
    paywall: bool = True
    language: str = "da"
    sections: list[str] = field(default_factory=list)


@dataclass
class Config:
    ai: AIConfig = field(default_factory=AIConfig)
    sources_danish: list[SourceConfig] = field(default_factory=list)
    sources_international: list[SourceConfig] = field(default_factory=list)
    scrape_sources: list[ScrapeSourceConfig] = field(default_factory=list)
    agent_sources: list[AgentSourceConfig] = field(default_factory=list)
    scraping: ScrapingConfig = field(default_factory=ScrapingConfig)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    daily: DailyConfig = field(default_factory=DailyConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)

    def get_all_sources(self) -> list[SourceConfig]:
        return self.sources_danish + self.sources_international


def load_config(path: str | None = None) -> Config:
    """Load configuration from config.yaml."""
    if path is None:
        # Look for config.yaml in the current directory, then project root
        candidates = [
            Path("config.yaml"),
            Path(__file__).parent.parent / "config.yaml",
        ]
        for candidate in candidates:
            if candidate.exists():
                path = str(candidate)
                break

    if path is None or not Path(path).exists():
        return Config()

    with open(path) as f:
        raw = yaml.safe_load(f)

    if not raw:
        return Config()

    # Parse AI config
    ai_raw = raw.get("ai", {})
    ai = AIConfig(
        backend=ai_raw.get("backend", "gemini"),
        ollama=OllamaConfig(**ai_raw.get("ollama", {})),
        claude=ClaudeConfig(**ai_raw.get("claude", {})),
        gemini=GeminiConfig(**ai_raw.get("gemini", {})),
        deepseek=DeepSeekConfig(**ai_raw.get("deepseek", {})),
    )

    # Parse sources
    sources_raw = raw.get("sources", {})
    danish = [
        SourceConfig(**s) for s in sources_raw.get("danish", [])
    ]
    international = [
        SourceConfig(**s) for s in sources_raw.get("international", [])
    ]

    # Parse scrape sources
    scrape_sources = [
        ScrapeSourceConfig(**s) for s in raw.get("scrape_sources", [])
    ]

    # Parse agent sources
    agent_sources = [
        AgentSourceConfig(**s) for s in raw.get("agent_sources", [])
    ]

    # Parse simple configs
    scraping = ScrapingConfig(**raw.get("scraping", {}))
    scoring = ScoringConfig(**raw.get("scoring", {}))
    daily = DailyConfig(**raw.get("daily", {}))
    output = OutputConfig(**raw.get("output", {}))
    database = DatabaseConfig(**raw.get("database", {}))
    if os.environ.get("DATABASE_PATH"):
        database.path = os.environ["DATABASE_PATH"]

    return Config(
        ai=ai,
        sources_danish=danish,
        sources_international=international,
        scrape_sources=scrape_sources,
        agent_sources=agent_sources,
        scraping=scraping,
        scoring=scoring,
        daily=daily,
        output=output,
        database=database,
    )
