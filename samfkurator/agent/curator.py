"""
Agent-based news curator for Samfundsfag A.

Two-pass approach:
  1. Skim: LLM looks at all headlines and picks promising ones
  2. Deep-read: Browser opens each candidate; LLM reads full text and scores
"""

from datetime import datetime

from rich.console import Console

from samfkurator.agent.browser import ArticleBrowser
from samfkurator.db import Database
from samfkurator.models import Article
from samfkurator.scoring.prompt import parse_scoring_response


def _create_backend(backend_name: str):
    """Instantiate the chosen AI backend."""
    if backend_name == "gemini":
        from samfkurator.scoring.gemini_backend import GeminiBackend
        return GeminiBackend()
    elif backend_name == "deepseek":
        from samfkurator.scoring.deepseek_backend import DeepSeekBackend
        return DeepSeekBackend()
    elif backend_name == "claude":
        from samfkurator.scoring.claude_backend import ClaudeBackend
        return ClaudeBackend()
    else:
        from samfkurator.scoring.ollama_backend import OllamaBackend
        return OllamaBackend()


def run_agent(
    agent_sites: list[dict],
    db: Database,
    backend_name: str = "gemini",
    console: Console | None = None,
    min_score: int = 5,
) -> int:
    """
    Run the agent on a list of news sites.

    Each site dict: {"name": str, "url": str, "language": str}

    Returns number of articles saved.
    """
    if console is None:
        console = Console()

    backend = _create_backend(backend_name)
    saved = 0

    with ArticleBrowser(headless=True) as browser:
        for site in agent_sites:
            name = site["name"]
            url = site["url"]
            language = site.get("language", "da")

            console.print(f"\n[bold cyan]Skimmer {name}...[/bold cyan]")

            # ── Pass 1: Skim headlines ────────────────────────────────────────
            try:
                headlines = browser.get_headlines(url)
            except Exception as e:
                console.print(f"  [red]Kunne ikke hente {url}: {e}[/red]")
                continue

            if not headlines:
                console.print(f"  [dim]Ingen overskrifter fundet på {name}[/dim]")
                continue

            console.print(f"  Fandt {len(headlines)} overskrifter. Filtrerer...")

            # LLM picks which headlines are worth reading
            if hasattr(backend, "skim"):
                try:
                    indices = backend.skim(headlines)
                except Exception:
                    indices = list(range(len(headlines)))
            else:
                indices = list(range(len(headlines)))

            candidates = [headlines[i] for i in indices if i < len(headlines)]
            # Filter already-scored
            candidates = [c for c in candidates if not db.has_score(c["url"])]

            console.print(
                f"  [green]{len(candidates)} kandidater valgt[/green] "
                f"(af {len(headlines)} overskrifter)"
            )

            if not candidates:
                continue

            # ── Pass 2: Deep-read each candidate ─────────────────────────────
            for candidate in candidates:
                art_url = candidate["url"]
                title = candidate["title"]

                console.print(f"  [dim]Læser:[/dim] {title[:70]}...")

                try:
                    full_text = browser.read_article(art_url)
                except Exception as e:
                    console.print(f"    [yellow]Kunne ikke læse: {e}[/yellow]")
                    continue

                if len(full_text) < 200:
                    console.print("    [dim]For lidt tekst - springer over[/dim]")
                    continue

                article = Article(
                    url=art_url,
                    title=title,
                    source_name=name,
                    summary=candidate.get("teaser", ""),
                    full_text=full_text,
                    language=language,
                    has_paywall=False,  # bypass-paywalls handles it
                    fetched_at=datetime.now(),
                )

                result = backend.score_article(article)

                if result is None:
                    console.print("    [yellow]Scoring fejlede[/yellow]")
                    continue

                score = result.overall_score
                discipline = result.primary_discipline

                if score >= min_score:
                    db.save_article(article)
                    db.save_score(result)
                    saved += 1
                    console.print(
                        f"    [green]✓ Score {score}/10 [{discipline}][/green] — gemmes"
                    )
                else:
                    console.print(
                        f"    [dim]✗ Score {score}/10 — ikke relevant nok[/dim]"
                    )

    console.print(
        f"\n[bold green]Agent færdig. {saved} artikler gemt.[/bold green]"
    )
    return saved
