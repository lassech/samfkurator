"""
Agent-based news curator for Samfundsfag A.

Two-pass approach:
  1. Skim: LLM looks at all headlines and picks promising ones
  2. Deep-read: Browser opens each candidate; LLM reads full text and scores
"""

import os
import random
import time
from datetime import datetime
from pathlib import Path

from rich.console import Console

from samfkurator.agent.browser import ArticleBrowser
from samfkurator.db import Database
from samfkurator.models import Article
from samfkurator.scoring.prompt import parse_scoring_response

LOG_PATH = Path(os.environ.get("SCRAPING_LOG_PATH", "./scraping.log"))


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
    jitter_minutes: int = 20,
    headless: bool = True,
    executable_path: str | None = None,
    user_data_dir: str = "/tmp/samfkurator-browser-profile",
) -> int:
    """
    Run the agent on a list of news sites.

    Each site dict: {"name": str, "url": str, "language": str}

    headless=False + executable_path → lokal Brave/Chrome (omgår Cloudflare IP-blokering)

    Returns number of articles saved.
    """
    if console is None:
        console = Console()

    # Random startup delay so scraping never happens at exactly the same time
    if jitter_minutes > 0:
        delay = random.uniform(0, jitter_minutes * 60)
        console.print(
            f"[dim]Starter om {delay/60:.1f} min (jitter)...[/dim]"
        )
        time.sleep(delay)

    backend = _create_backend(backend_name)
    saved = 0
    run_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    log_lines: list[str] = []

    with ArticleBrowser(
        headless=headless,
        executable_path=executable_path,
        user_data_dir=user_data_dir,
    ) as browser:
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
                log_lines.append(
                    f"{run_date} | {name} {url} | FEJL: {e}"
                )
                continue

            if not headlines:
                console.print(f"  [dim]Ingen overskrifter fundet på {name}[/dim]")
                log_lines.append(
                    f"{run_date} | {name} {url} | 0 overskrifter | 0 kandidater | 0 gemt"
                )
                continue

            console.print(f"  Fandt {len(headlines)} overskrifter. Filtrerer med LLM...")

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
                log_lines.append(
                    f"{run_date} | {name} {url} | {len(headlines)} overskrifter | 0 kandidater | 0 gemt"
                )
                continue

            # ── Pass 2: Deep-read each candidate ─────────────────────────────
            site_saved = 0
            for i, candidate in enumerate(candidates):
                art_url = candidate["url"]
                title = candidate["title"]

                # Random delay between articles (skip before first)
                if i > 0:
                    delay = random.uniform(4.0, 10.0)
                    console.print(f"  [dim]Venter {delay:.1f}s...[/dim]")
                    time.sleep(delay)

                console.print(f"  [dim]Læser:[/dim] {title[:70]}...")

                try:
                    full_text = browser.read_article(art_url)
                except Exception as e:
                    console.print(f"    [yellow]Kunne ikke læse: {e}[/yellow]")
                    continue

                if len(full_text) < 200:
                    console.print("    [dim]For lidt tekst - springer over[/dim]")
                    continue

                now = datetime.now()
                article = Article(
                    url=art_url,
                    title=title,
                    source_name=name,
                    summary=candidate.get("teaser", ""),
                    full_text=full_text,
                    language=language,
                    has_paywall=False,  # bypass-paywalls handles it
                    published=now,
                    fetched_at=now,
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
                    site_saved += 1
                    console.print(
                        f"    [green]✓ Score {score}/10 [{discipline}][/green] — gemmes"
                    )
                else:
                    console.print(
                        f"    [dim]✗ Score {score}/10 — ikke relevant nok[/dim]"
                    )

            log_lines.append(
                f"{run_date} | {name} {url} | {len(headlines)} overskrifter | {len(candidates)} kandidater | {site_saved} gemt"
            )

            # Pause between sites
            site_delay = random.uniform(15.0, 30.0)
            console.print(f"  [dim]Pause mellem sites: {site_delay:.0f}s[/dim]")
            time.sleep(site_delay)

    # Write log
    log_lines.append(
        f"{run_date} | TOTAL | {saved} artikler gemt i alt"
    )
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            for line in log_lines:
                f.write(line + "\n")
    except Exception as e:
        console.print(f"[yellow]Advarsel: Kunne ikke skrive logfil: {e}[/yellow]")

    console.print(
        f"\n[bold green]Agent færdig. {saved} artikler gemt.[/bold green]"
    )
    return saved
