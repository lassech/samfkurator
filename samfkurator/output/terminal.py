from rich.console import Console
from rich.table import Table
from rich.text import Text

DISCIPLINE_COLORS = {
    "sociologi": "magenta",
    "politik": "red",
    "okonomi": "green",
    "international_politik": "blue",
    "metode": "yellow",
}

DISCIPLINE_LABELS = {
    "sociologi": "Socio",
    "politik": "Pol",
    "okonomi": "Økon",
    "international_politik": "IP",
    "metode": "Met",
}


def _score_style(score: int) -> str:
    if score >= 8:
        return "bold green"
    if score >= 6:
        return "yellow"
    return "dim"


def display_results(rows: list[tuple], console: Console | None = None):
    """Display scored articles in a rich table."""
    console = console or Console()

    if not rows:
        console.print("[dim]Ingen artikler at vise.[/dim]")
        return

    table = Table(
        title="Samfkurator - Nyhedsrelevans for Samfundsfag A",
        show_lines=True,
    )

    table.add_column("Score", justify="center", style="bold", width=5)
    table.add_column("Kilde", width=14)
    table.add_column("Titel", width=50)
    table.add_column("Disciplin", width=8)
    table.add_column("So/Po/Øk/IP/Me", width=14, justify="center")
    table.add_column("Begrundelse", width=40)

    for row in rows:
        (
            title, source, url, published, language,
            score, discipline, explanation,
            soc, pol, oko, ip, met,
        ) = row

        disc_color = DISCIPLINE_COLORS.get(discipline, "white")
        disc_label = DISCIPLINE_LABELS.get(discipline, discipline or "?")

        lang_flag = "" if language == "da" else " [dim](EN)[/dim]"

        table.add_row(
            Text(str(score), style=_score_style(score)),
            source[:14],
            f"[link={url}]{title[:50]}[/link]{lang_flag}",
            Text(disc_label, style=disc_color),
            f"{soc}/{pol}/{oko}/{ip}/{met}",
            (explanation[:40] + "...") if explanation and len(explanation) > 40 else (explanation or ""),
        )

    console.print(table)
