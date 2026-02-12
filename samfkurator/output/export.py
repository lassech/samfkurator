import csv
import json
from datetime import datetime
from pathlib import Path


def export_json(rows: list[tuple], export_path: str = "./output") -> str:
    """Export scored articles to JSON file."""
    Path(export_path).mkdir(parents=True, exist_ok=True)
    filename = f"samfkurator_{datetime.now().strftime('%Y-%m-%d_%H%M')}.json"
    filepath = Path(export_path) / filename

    articles = []
    for row in rows:
        (
            title, source, url, published, language,
            score, discipline, explanation,
            soc, pol, oko, ip, met,
        ) = row
        articles.append({
            "title": title,
            "source": source,
            "url": url,
            "published": published,
            "language": language,
            "overall_score": score,
            "primary_discipline": discipline,
            "explanation": explanation,
            "scores": {
                "sociologi": soc,
                "politik": pol,
                "okonomi": oko,
                "international_politik": ip,
                "metode": met,
            },
        })

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    return str(filepath)


def export_csv(rows: list[tuple], export_path: str = "./output") -> str:
    """Export scored articles to CSV file."""
    Path(export_path).mkdir(parents=True, exist_ok=True)
    filename = f"samfkurator_{datetime.now().strftime('%Y-%m-%d_%H%M')}.csv"
    filepath = Path(export_path) / filename

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Titel", "Kilde", "URL", "Publiceret", "Sprog",
            "Score", "Disciplin", "Begrundelse",
            "Sociologi", "Politik", "Økonomi", "Int. Politik", "Metode",
        ])
        for row in rows:
            writer.writerow(row)

    return str(filepath)
