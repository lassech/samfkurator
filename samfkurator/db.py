import sqlite3
from datetime import datetime

from samfkurator.models import Article, DisciplineScore, ScoringResult

CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS articles (
    url TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source_name TEXT NOT NULL,
    summary TEXT,
    full_text TEXT,
    published TEXT,
    language TEXT DEFAULT 'da',
    has_paywall INTEGER DEFAULT 0,
    fetched_at TEXT
);

CREATE TABLE IF NOT EXISTS scores (
    article_url TEXT PRIMARY KEY REFERENCES articles(url),
    overall_score INTEGER NOT NULL,
    sociologi INTEGER DEFAULT 0,
    politik INTEGER DEFAULT 0,
    okonomi INTEGER DEFAULT 0,
    international_politik INTEGER DEFAULT 0,
    metode INTEGER DEFAULT 0,
    primary_discipline TEXT,
    explanation TEXT,
    backend_used TEXT,
    scored_at TEXT
);
"""


class Database:
    def __init__(self, path: str = "./samfkurator.db"):
        self.db = sqlite3.connect(path)
        self.db.executescript(CREATE_TABLES)

    def has_article(self, url: str) -> bool:
        cur = self.db.execute("SELECT 1 FROM articles WHERE url = ?", (url,))
        return cur.fetchone() is not None

    def has_score(self, url: str) -> bool:
        cur = self.db.execute(
            "SELECT 1 FROM scores WHERE article_url = ?", (url,)
        )
        return cur.fetchone() is not None

    def save_article(self, article: Article) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO articles VALUES (?,?,?,?,?,?,?,?,?)",
            (
                article.url,
                article.title,
                article.source_name,
                article.summary,
                article.full_text,
                article.published.isoformat() if article.published else None,
                article.language,
                int(article.has_paywall),
                datetime.now().isoformat(),
            ),
        )
        self.db.commit()

    def save_score(self, result: ScoringResult) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO scores VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                result.article_url,
                result.overall_score,
                result.disciplines.sociologi,
                result.disciplines.politik,
                result.disciplines.okonomi,
                result.disciplines.international_politik,
                result.disciplines.metode,
                result.primary_discipline,
                result.explanation,
                result.backend_used,
                datetime.now().isoformat(),
            ),
        )
        self.db.commit()

    def get_scored_articles(
        self, min_score: int = 1, limit: int = 50
    ) -> list[tuple]:
        """Return articles with scores, sorted by overall_score DESC."""
        return self.db.execute(
            """
            SELECT a.title, a.source_name, a.url, a.published, a.language,
                   s.overall_score, s.primary_discipline, s.explanation,
                   s.sociologi, s.politik, s.okonomi,
                   s.international_politik, s.metode
            FROM articles a JOIN scores s ON a.url = s.article_url
            WHERE s.overall_score >= ?
            ORDER BY s.overall_score DESC, a.published DESC
            LIMIT ?
            """,
            (min_score, limit),
        ).fetchall()

    def get_todays_scored_articles(self, min_score: int = 1) -> list[tuple]:
        """Return today's scored articles."""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.db.execute(
            """
            SELECT a.title, a.source_name, a.url, a.published, a.language,
                   s.overall_score, s.primary_discipline, s.explanation,
                   s.sociologi, s.politik, s.okonomi,
                   s.international_politik, s.metode
            FROM articles a JOIN scores s ON a.url = s.article_url
            WHERE s.overall_score >= ?
              AND s.scored_at LIKE ?
            ORDER BY s.overall_score DESC, a.published DESC
            """,
            (min_score, f"{today}%"),
        ).fetchall()

    def close(self):
        self.db.close()
