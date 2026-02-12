from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from samfkurator.config import DailyConfig

DISCIPLINE_NAMES = {
    "sociologi": "Sociologi",
    "politik": "Politik",
    "okonomi": "Økonomi",
    "international_politik": "International politik",
    "metode": "Metode",
}

DISCIPLINE_COLORS = {
    "sociologi": "magenta",
    "politik": "red",
    "okonomi": "green",
    "international_politik": "blue",
    "metode": "yellow",
}

# Danish sources for diversity checking
DANISH_SOURCES = {"DR Nyheder", "TV2 Nyheder", "Politiken", "Berlingske", "Jyllands-Posten"}


def select_daily(
    rows: list[tuple], config: DailyConfig | None = None
) -> list[tuple]:
    """Select diverse top articles for daily must-reads.

    Diversity logic:
    - Max `max_per_discipline` articles from same discipline
    - At least `min_danish` Danish sources
    - At least `min_international` international sources
    - Sorted by score within constraints
    """
    if config is None:
        config = DailyConfig()

    count = config.count
    max_per_disc = config.max_per_discipline
    min_danish = config.min_danish
    min_int = config.min_international

    # rows are already sorted by score DESC from the DB query
    selected: list[tuple] = []
    disc_counts: dict[str, int] = {}
    danish_count = 0
    int_count = 0

    # First pass: ensure minimum Danish articles
    remaining = list(rows)
    for row in remaining[:]:
        if len(selected) >= count:
            break
        source = row[1]
        discipline = row[6]
        if source in DANISH_SOURCES and danish_count < min_danish:
            if disc_counts.get(discipline, 0) < max_per_disc:
                selected.append(row)
                disc_counts[discipline] = disc_counts.get(discipline, 0) + 1
                danish_count += 1
                remaining.remove(row)

    # Second pass: ensure minimum international articles
    for row in remaining[:]:
        if len(selected) >= count:
            break
        source = row[1]
        discipline = row[6]
        if source not in DANISH_SOURCES and int_count < min_int:
            if disc_counts.get(discipline, 0) < max_per_disc:
                selected.append(row)
                disc_counts[discipline] = disc_counts.get(discipline, 0) + 1
                int_count += 1
                remaining.remove(row)

    # Third pass: fill remaining slots with highest-scored articles
    for row in remaining:
        if len(selected) >= count:
            break
        discipline = row[6]
        if disc_counts.get(discipline, 0) < max_per_disc:
            selected.append(row)
            disc_counts[discipline] = disc_counts.get(discipline, 0) + 1

    # Sort final selection by score descending
    selected.sort(key=lambda r: r[5], reverse=True)
    return selected


def display_daily(rows: list[tuple], console: Console | None = None):
    """Display daily must-reads in a rich formatted view."""
    console = console or Console()

    if not rows:
        console.print("[dim]Ingen artikler fundet i dag.[/dim]")
        return

    console.print()
    console.rule(
        f"[bold]Dagens {len(rows)} Must-Reads til Samfundsfag A[/bold]",
        style="cyan",
    )
    console.print()

    for i, row in enumerate(rows, 1):
        (
            title, source, url, published, language,
            score, discipline, explanation,
            soc, pol, oko, ip, met,
        ) = row

        disc_name = DISCIPLINE_NAMES.get(discipline, discipline or "?")
        disc_color = DISCIPLINE_COLORS.get(discipline, "white")
        lang_tag = "" if language == "da" else " (EN)"

        score_bar = "█" * score + "░" * (10 - score)
        score_color = "green" if score >= 8 else ("yellow" if score >= 6 else "red")

        content = (
            f"[{score_color}]{score_bar} {score}/10[/{score_color}]  "
            f"[{disc_color}]■ {disc_name}[/{disc_color}]\n"
            f"[dim]{source}{lang_tag}[/dim]\n"
        )
        if explanation:
            content += f"\n{explanation}\n"
        content += f"\n[link={url}]{url}[/link]"

        panel = Panel(
            content,
            title=f"[bold]#{i}[/bold]  {title[:70]}",
            title_align="left",
            border_style=disc_color,
            padding=(0, 1),
        )
        console.print(panel)
