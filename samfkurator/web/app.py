from datetime import datetime

from flask import Flask, render_template, request

from samfkurator.config import load_config
from samfkurator.db import Database
from samfkurator.output.daily import select_daily

app = Flask(__name__)

DISCIPLINE_NAMES = {
    "sociologi": "Sociologi",
    "politik": "Politik",
    "okonomi": "Økonomi",
    "international_politik": "Int. Politik",
    "metode": "Metode",
}


@app.route("/")
def index():
    config = load_config()
    db = Database(config.database.path)

    min_score = request.args.get("min_score", 1, type=int)
    discipline = request.args.get("discipline", "")
    source = request.args.get("source", "")
    date_from = request.args.get("date_from", "")
    date_to = request.args.get("date_to", "")

    rows = db.get_scored_articles(min_score=min_score, limit=500)

    # Must-reads: top 10 fra i dag (eller seneste hvis ingen i dag)
    today_rows = db.get_todays_scored_articles(min_score=5)
    if not today_rows:
        today_rows = db.get_scored_articles(min_score=5, limit=100)
    must_reads_raw = select_daily(today_rows, config.daily)

    db.close()

    must_reads = []
    for row in must_reads_raw:
        title, source_name, url, published, language, score, disc, explanation, soc, pol, oko, ip, met = row
        must_reads.append({
            "title": title, "source": source_name, "url": url,
            "published_date": (published or "")[:10],
            "language": language, "score": score,
            "discipline": disc,
            "discipline_label": DISCIPLINE_NAMES.get(disc, disc or "?"),
            "explanation": explanation or "",
        })

    articles = []
    sources_set = set()
    for row in rows:
        (
            title, source_name, url, published, language,
            score, disc, explanation,
            soc, pol, oko, ip, met,
        ) = row

        sources_set.add(source_name)

        if discipline and disc != discipline:
            continue
        if source and source_name != source:
            continue

        # Date filtering
        pub_date = (published or "")[:10]
        if date_from and pub_date and pub_date < date_from:
            continue
        if date_to and pub_date and pub_date > date_to:
            continue

        articles.append({
            "title": title,
            "source": source_name,
            "url": url,
            "published": published or "",
            "published_date": pub_date,
            "language": language,
            "score": score,
            "discipline": disc,
            "discipline_label": DISCIPLINE_NAMES.get(disc, disc or "?"),
            "explanation": explanation or "",
            "soc": soc, "pol": pol, "oko": oko, "ip": ip, "met": met,
        })

    today = datetime.now().strftime("%Y-%m-%d")

    return render_template(
        "index.html",
        articles=articles,
        must_reads=must_reads,
        sources=sorted(sources_set),
        disciplines=DISCIPLINE_NAMES,
        current_min_score=min_score,
        current_discipline=discipline,
        current_source=source,
        current_date_from=date_from,
        current_date_to=date_to,
        today=today,
    )


def run_server(host: str = "0.0.0.0", port: int = 5000, debug: bool = False):
    app.run(host=host, port=port, debug=debug)
