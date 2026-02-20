import argparse

from rich.console import Console
from rich.progress import Progress

from samfkurator.config import load_config
from samfkurator.db import Database
from samfkurator.output.daily import display_daily, select_daily
from samfkurator.output.export import export_csv, export_json
from samfkurator.output.terminal import display_results
from samfkurator.sources.extractors import extract_full_text
from samfkurator.sources.rss import fetch_all_sources


def _create_backend(config, backend_name: str):
    """Create the appropriate AI scoring backend."""
    if backend_name == "claude":
        from samfkurator.scoring.claude_backend import ClaudeBackend

        return ClaudeBackend(config.ai.claude.model)
    else:
        from samfkurator.scoring.ollama_backend import OllamaBackend

        return OllamaBackend(
            config.ai.ollama.base_url,
            config.ai.ollama.model,
            config.ai.ollama.temperature,
        )


def _fetch_and_score(args, config, db, console):
    """Fetch new articles and score them."""
    # 1. Fetch RSS feeds
    console.print("[bold]Henter nyheder fra RSS feeds...[/bold]")
    all_sources = config.get_all_sources()
    articles = fetch_all_sources(all_sources, config.scraping.max_articles_per_feed)

    # 1b. Old BeautifulSoup scraper (fallback if scrape_sources configured)
    if config.scrape_sources:
        from samfkurator.sources.scraper import scrape_all_sources

        console.print("[bold]Scraper med BeautifulSoup...[/bold]")
        scraped = scrape_all_sources(
            config.scrape_sources,
            max_per_site=config.scraping.max_articles_per_feed,
            delay=config.scraping.request_delay_seconds,
        )
        articles.extend(scraped)

    # 1c. Agent browser (to-trins: skim + deep-read med bypass-paywalls)
    if config.agent_sources:
        from samfkurator.agent.curator import run_agent
        backend_name = getattr(args, "backend", None) or config.ai.backend
        console.print(
            f"[bold]Agent browser starter ({backend_name})...[/bold]"
        )
        no_jitter = getattr(args, "no_jitter", False)
        run_agent(
            [{"name": s.name, "url": s.url, "language": s.language}
             for s in config.agent_sources],
            db=db,
            backend_name=backend_name,
            console=console,
            min_score=config.scoring.min_score_to_display,
            jitter_minutes=0 if no_jitter else 20,
        )

    # 2. Filter already-scored articles
    new_articles = [a for a in articles if not db.has_score(a.url)]
    console.print(
        f"Fandt [bold]{len(articles)}[/bold] artikler, "
        f"[bold]{len(new_articles)}[/bold] nye."
    )

    if not new_articles:
        console.print("[dim]Ingen nye artikler at score.[/dim]")
        return

    # 3. Extract full text (optional)
    if not args.no_fetch and config.scraping.fetch_full_text:
        with Progress(console=console) as progress:
            task = progress.add_task(
                "Henter artikeltekst...", total=len(new_articles)
            )
            for article in new_articles:
                if not article.has_paywall:
                    extract_full_text(
                        article, config.scraping.request_delay_seconds
                    )
                progress.update(task, advance=1)

    # 4. Score with LLM
    backend_name = args.backend or config.ai.backend
    backend = _create_backend(config, backend_name)

    if backend_name == "ollama" and not backend.is_available():
        console.print(
            "[red bold]Ollama er ikke tilgængelig![/red bold]\n"
            "[dim]Start Ollama med: ollama serve\n"
            "Eller brug: samfkurator daily --backend claude[/dim]"
        )
        return

    console.print(
        f"Scorer artikler med [bold]{backend_name}[/bold]..."
    )

    scored = 0
    failed = 0
    with Progress(console=console) as progress:
        task = progress.add_task(
            "Scorer artikler...", total=len(new_articles)
        )
        for article in new_articles:
            db.save_article(article)
            result = backend.score_article(article)
            if result:
                db.save_score(result)
                scored += 1
            else:
                failed += 1
            progress.update(task, advance=1)

    console.print(
        f"[green]Scoret {scored} artikler.[/green]"
        + (f" [yellow]({failed} fejlede)[/yellow]" if failed else "")
    )


def main():
    parser = argparse.ArgumentParser(
        description="Samfkurator - Nyhedskurator til Samfundsfag A",
    )
    subparsers = parser.add_subparsers(dest="command")

    # Daily command (default/main feature)
    daily_parser = subparsers.add_parser(
        "daily", help="Dagens must-read artikler"
    )
    daily_parser.add_argument(
        "--count", type=int, help="Antal artikler (default: 10)"
    )
    daily_parser.add_argument(
        "--backend", choices=["ollama", "claude", "gemini", "deepseek"],
        help="AI backend (overrides config)",
    )
    daily_parser.add_argument(
        "--no-fetch", action="store_true",
        help="Spring fuld tekst-ekstraktion over",
    )
    daily_parser.add_argument(
        "--cached", action="store_true",
        help="Vis kun tidligere scorede artikler (ingen ny hentning)",
    )
    daily_parser.add_argument(
        "--no-jitter", action="store_true",
        help="Spring startup-forsinkelse over (til manuel kørsel)",
    )

    # All command - show all scored articles
    all_parser = subparsers.add_parser(
        "all", help="Vis alle scorede artikler"
    )
    all_parser.add_argument(
        "--min-score", type=int, help="Minimum score at vise"
    )
    all_parser.add_argument(
        "--limit", type=int, default=50, help="Max antal resultater"
    )
    all_parser.add_argument(
        "--backend", choices=["ollama", "claude"],
        help="AI backend (overrides config)",
    )
    all_parser.add_argument(
        "--no-fetch", action="store_true",
        help="Spring fuld tekst-ekstraktion over",
    )
    all_parser.add_argument(
        "--format", choices=["terminal", "json", "csv"],
        default="terminal", help="Output-format",
    )
    all_parser.add_argument(
        "--cached", action="store_true",
        help="Vis kun tidligere scorede artikler",
    )

    # Local command - lokal Brave-agent til Cloudflare-beskyttede sider
    local_parser = subparsers.add_parser(
        "local",
        help="Lokal Brave-agent til sider blokeret på serveren (Berlingske, Weekendavisen...)",
    )
    local_parser.add_argument(
        "--backend", choices=["ollama", "claude", "gemini", "deepseek"],
        help="AI backend (overrides config)",
    )
    local_parser.add_argument(
        "--no-fetch", action="store_true",
        help="Spring fuld tekst-ekstraktion over",
    )
    local_parser.add_argument(
        "--sync", action="store_true",
        help="Træk serverens DB ned inden kørsel og push tilbage bagefter",
    )

    # Web command
    web_parser = subparsers.add_parser(
        "web", help="Start webserver med sortérbar tabel"
    )
    web_parser.add_argument(
        "--port", type=int, default=5000, help="Port (default: 5000)"
    )
    web_parser.add_argument(
        "--host", default="127.0.0.1", help="Host (default: 127.0.0.1)"
    )

    args = parser.parse_args()
    config = load_config()

    # Handle web command before database
    if args.command == "web":
        from samfkurator.web.app import run_server

        console = Console()
        console.print(
            f"[bold cyan]Samfkurator web[/bold cyan] starter på "
            f"[link=http://{args.host}:{args.port}]"
            f"http://{args.host}:{args.port}[/link]"
        )
        run_server(host=args.host, port=args.port, debug=True)
        return

    db = Database(config.database.path)
    console = Console()

    # Default to daily command
    if args.command is None:
        args.command = "daily"
        args.count = None
        args.backend = None
        args.no_fetch = False
        args.cached = False

    try:
        if args.command == "local":
            if not config.local_sources:
                console.print(
                    "[yellow]Ingen local_sources konfigureret i config.yaml[/yellow]"
                )
                return

            import os
            from samfkurator.agent.curator import run_agent

            backend_name = getattr(args, "backend", None) or config.ai.backend
            exe = config.local_browser.executable_path or None
            udir = os.path.expanduser(config.local_browser.user_data_dir)

            console.print(
                f"[bold cyan]Lokal browser-agent starter ({backend_name})...[/bold cyan]"
            )
            if exe:
                console.print(f"[dim]Browser: {exe}[/dim]")
            console.print(f"[dim]Profil: {udir}[/dim]")
            console.print(
                f"[dim]{len(config.local_sources)} kilder: "
                + ", ".join(s.name for s in config.local_sources)
                + "[/dim]"
            )

            # Sync: træk serverens DB ned inden kørsel
            sync_cfg = config.sync
            do_sync = getattr(args, "sync", False) and sync_cfg.host
            local_db_path = config.database.path
            if do_sync:
                import subprocess
                remote = f"{sync_cfg.host}:{sync_cfg.remote_db_path}"
                console.print(f"[dim]Trækker DB fra {remote}...[/dim]")
                result = subprocess.run(
                    ["scp", remote, local_db_path],
                    capture_output=True, text=True,
                )
                if result.returncode != 0:
                    console.print(
                        f"[yellow]Advarsel: Kunne ikke trække DB: {result.stderr.strip()}[/yellow]"
                    )
                else:
                    console.print("[dim]DB hentet — fortsætter med serverens data.[/dim]")
                    # Genåbn DB med de nye data
                    db.close()
                    db = Database(local_db_path)

            run_agent(
                [{"name": s.name, "url": s.url, "language": s.language}
                 for s in config.local_sources],
                db=db,
                backend_name=backend_name,
                console=console,
                min_score=config.scoring.min_score_to_display,
                jitter_minutes=0,          # aldrig jitter ved lokal kørsel
                headless=False,            # synligt browservindue
                executable_path=exe,
                user_data_dir=udir,
            )

            # Sync: push den opdaterede DB tilbage til serveren
            if do_sync:
                remote = f"{sync_cfg.host}:{sync_cfg.remote_db_path}"
                console.print(f"[dim]Pusher DB til {remote}...[/dim]")
                result = subprocess.run(
                    ["scp", local_db_path, remote],
                    capture_output=True, text=True,
                )
                if result.returncode != 0:
                    console.print(
                        f"[yellow]Advarsel: Kunne ikke pushe DB: {result.stderr.strip()}[/yellow]"
                    )
                else:
                    console.print("[green]DB synkroniseret til server.[/green]")

            # Vis dagens resultater inkl. det der lige er hentet
            rows = db.get_todays_scored_articles(config.scoring.min_score_to_display)
            if rows:
                daily_rows = select_daily(rows, config.daily)
                display_daily(daily_rows, console)

        elif args.command == "daily":
            if not args.cached:
                _fetch_and_score(args, config, db, console)

            # Get today's articles and select diverse top N
            min_score = config.scoring.min_score_to_display
            rows = db.get_todays_scored_articles(min_score)

            if not rows:
                # Fall back to all scored articles if none today
                rows = db.get_scored_articles(min_score, 100)

            if args.count:
                config.daily.count = args.count

            daily_rows = select_daily(rows, config.daily)
            display_daily(daily_rows, console)

        elif args.command == "all":
            if not args.cached:
                _fetch_and_score(args, config, db, console)

            min_score = args.min_score or config.scoring.min_score_to_display
            rows = db.get_scored_articles(min_score, args.limit)

            fmt = args.format
            if fmt == "terminal":
                display_results(rows, console)
            elif fmt == "json":
                filepath = export_json(rows, config.output.export_path)
                console.print(f"Eksporteret til [bold]{filepath}[/bold]")
            elif fmt == "csv":
                filepath = export_csv(rows, config.output.export_path)
                console.print(f"Eksporteret til [bold]{filepath}[/bold]")

    finally:
        db.close()
