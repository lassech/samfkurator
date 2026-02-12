import json

from samfkurator.models import DisciplineScore, ScoringResult

SYSTEM_PROMPT = """\
Du er en ekspert i Samfundsfag A (stx) og hjælper en gymnasielærer med at \
vurdere nyhedsartiklers relevans for undervisningen.

Du scorer artikler på en skala fra 1-10 baseret på deres relevans for \
fagets kernestof og faglige mål.

Kernestoffet er opdelt i fem discipliner:

**Sociologi:**
- Identitetsdannelse og socialisering samt social differentiering og \
kulturelle mønstre i forskellige lande, herunder Danmark
- Politisk meningsdannelse og medier, herunder adfærd på de sociale medier
- Samfundsforandringer og forholdet mellem aktør og struktur

**Politik:**
- Politiske ideologier, skillelinjer, partiadfærd og vælgeradfærd
- Magt- og demokratiopfattelser samt rettigheder og pligter i et \
demokratisk samfund, herunder ligestilling mellem kønnene
- Politiske beslutningsprocesser i Danmark i en global sammenhæng, \
herunder de politiske systemer i Danmark og EU

**Økonomi:**
- Velfærdsprincipper og forholdet mellem stat, civilsamfund og marked, \
herunder markedsmekanismen og politisk påvirkning heraf
- Globaliseringens og EU's betydning for den økonomiske udvikling i \
Danmark, herunder konkurrenceevne og arbejdsmarkedsforhold
- Makroøkonomiske sammenhænge, bæredygtig udvikling, målkonflikter og \
styring nationalt, regionalt og globalt

**International politik:**
- Aktører, magt, sikkerhed, konflikter og integration i Europa og \
internationalt
- Mål og muligheder i Danmarks udenrigspolitik
- Globalisering og samfundsudvikling i lande på forskellige udviklingstrin

**Metode:**
- Kvalitativ og kvantitativ metode, herunder tilrettelæggelse og \
gennemførelse af undersøgelser samt systematisk behandling af \
forskellige typer data
- Komparativ metode og casestudier
- Statistiske mål, herunder lineær regression og statistisk usikkerhed

Scoring-kriterier:
- 9-10: Direkte relevant for kernestof. Kan bruges som supplerende stof \
i undervisningen. Behandler centrale begreber eller teorier fra faget.
- 7-8: Klart relevant. Illustrerer vigtige samfundsmæssige \
problemstillinger der kan kobles til fagets discipliner.
- 5-6: Moderat relevant. Berører emner der tangerer fagets kernestof.
- 3-4: Svagt relevant. Perifert forbundet til fagets emneområder.
- 1-2: Ikke relevant for Samfundsfag A.

Du svarer KUN med valid JSON. Ingen anden tekst."""


def build_scoring_prompt(
    title: str, text: str, source: str, language: str
) -> str:
    """Build the user prompt for scoring a single article."""
    lang_note = ""
    if language == "en":
        lang_note = (
            " (Artiklen er på engelsk -- vurder relevans for dansk "
            "Samfundsfag A-undervisning, herunder komparativt perspektiv.)"
        )

    return f"""Vurder denne nyhedsartikel fra {source}{lang_note}:

Titel: {title}

Indhold:
{text[:2000]}

Svar med dette JSON-format:
{{
  "overall_score": <1-10>,
  "disciplines": {{
    "sociologi": <0-10>,
    "politik": <0-10>,
    "okonomi": <0-10>,
    "international_politik": <0-10>,
    "metode": <0-10>
  }},
  "primary_discipline": "<sociologi|politik|okonomi|international_politik|metode>",
  "explanation": "<1-2 sætninger på dansk om hvorfor denne score>"
}}"""


def parse_scoring_response(
    raw: str, article_url: str, backend: str = "ollama"
) -> ScoringResult | None:
    """Parse JSON response from LLM into a ScoringResult."""
    try:
        data = json.loads(raw)
        return ScoringResult(
            article_url=article_url,
            overall_score=int(data["overall_score"]),
            disciplines=DisciplineScore(
                sociologi=int(data["disciplines"].get("sociologi", 0)),
                politik=int(data["disciplines"].get("politik", 0)),
                okonomi=int(data["disciplines"].get("okonomi", 0)),
                international_politik=int(
                    data["disciplines"].get("international_politik", 0)
                ),
                metode=int(data["disciplines"].get("metode", 0)),
            ),
            primary_discipline=data.get("primary_discipline", ""),
            explanation=data.get("explanation", ""),
            backend_used=backend,
        )
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        return None
