"""Scoring prompts for Samfkurator."""

import json

from samfkurator.models import DisciplineScore, ScoringResult

# ─── Shared curriculum context ────────────────────────────────────────────────

_CURRICULUM = """\
Samfundsfag A (stx) er opdelt i fem discipliner med følgende centrale teorier og begreber:

POLITIK:
Lipset-Rokkan, fordelings- og værdipolitik, postmaterialisme, Molins model, Kaare Strøm,
medianvælgerteorien, partityper, Sjøbloms partistrategier, marginalvælgere, kernevælgere,
issuevoting, Columbia-skolen, Michigan-skolen, rational choice-model, liberalisme, socialisme,
konservatisme, deltagelsesdemokrati, konkurrencedemokrati, deliberativt demokrati, meritokrati,
medborgerskab, parlamentarisk styringskæde, valgmåder, lovgivningsproces, magtformer (ressource,
relation, strukturel, direkte, indirekte, institutionel), magtdeling, regeringstyper,
medialisering, priming, framing, nyhedskriterier, gatekeeper-funktion, RAS-model, kanyleteori,
forstærkelses- og mobiliseringshypotese, køn (formel og reel lighed)

SOCIOLOGI:
Socialisering, dobbeltsocialisering, normer (formelle/uformelle), sanktioner, social kontrol,
sociale roller, rollekonflikt, identitet (jeg, personlig, social, kollektiv), sociale grupper,
social arv, mønsterbrydere, chanceulighed, social mobilitet,
Giddens (senmodernitet, strukturation, adskillelse af tid og rum, udlejring, aftraditionalisering),
Bourdieu (kapitaler, habitus), Honneth (anerkendelse, sfærer),
Habermas (kommunikativ handlen, kolonisering af livsverden, herredømmefri dialog),
Reckwitz (singularitetens tid), Beck (risikosamfund, valgbiografi, institutionaliseret individualisering),
Ziehe (kulturel frisættelse, formbarhed, subjektivisering, ontologisering, potensering),
køn som biologi, Parsons (instrumentel/ekspressiv), doing gender,
Connell (hegemonisk maskulinitet, medvirkende/underordnede/undertrykte maskuliniteter),
patriarkat, mental load, Hofstede (magtdistance, individualisme/kollektivisme,
feminin/maskulin, usikkerhedsundvigelse, langtids-/korttidsorientering),
struktur/aktør, majoritet, minoritet, segregation, Huntingtons civilisationsteori

ØKONOMI:
Gini-koefficient, BNP, fuld beskæftigelse, inflation, betalingsbalance,
økonomisk kredsløb, høj-/lavkonjunktur, rente, konkurrenceevne, eksport, multiplikator,
monetarisme, keynesianisme, Adam Smith (udbud/efterspørgsel, markedsmekanismen),
finanspolitik (automatiske stabilisatorer, crowding out), pengepolitik, strukturpolitik,
valutapolitik (revaluering, devaluering, ERM2), flexicurity, arbejdsmarkedspolitik,
ledighed (skifte/hjemsendelse/sæson/konjunktur/strukturel), lønspredning, indkomstpolitik,
priselasticitet, udbud og efterspørgsel, afgifter, regulering,
økonomiske systemer (planøkonomi, markedsøkonomi, blandingsøkonomi),
velfærdsmodeller (skandinavisk, centraleuropæisk, liberal), civilsamfund, marked, stat

INTERNATIONAL POLITIK:
EU-organer (Kommissionen, Det Europæiske Råd, EU-Parlamentet, EU-Domstolen, Ministerrådet),
mellemstatsligt/overstatsligt, føderation, konføderation,
integrationsteorier (føderalisme, neofunktionalisme, liberal intergovernmentalisme, multilevel governance),
direktiv, forordning, politisk/kulturel/økonomisk globalisering,
amerikanisering, monokultur, WTO, NATO, velfærdsstatens udfordringer (globalisering, social dumping),
Huntingtons civilisationsteori

METODE:
Kvalitativ og kvantitativ metode, hypoteser, operationalisering, validitet,
komparativ metode, casestudier\
"""

# ─── Skim prompt (batch headline filtering) ───────────────────────────────────

SKIM_SYSTEM_PROMPT = (
    "Du er en erfaren samfundsfagslærer (stx) der hurtigt skimmer nyhedsoverskrifter for at finde "
    "artikler der kan bruges som undervisningsmateriale.\n\n"
    "Du leder efter artikler der kan bruges som GENSTANDSFELT for analyse med fagets teorier og begreber:\n"
    + _CURRICULUM
    + "\n\nVær SELEKTIV. Vælg kun overskrifter der umiddelbart signalerer at artiklen kan analyseres med "
    "konkrete faglige begreber. Afvis artikler om sport, underholdning, vejr, kriminalitet uden "
    "samfundsmæssig dimension, og lokalnyheder uden overordnet relevans.\n\n"
    "Du svarer KUN med valid JSON. Ingen anden tekst."
)


def build_skim_prompt(headlines: list[dict]) -> str:
    """Build prompt for quick headline filtering."""
    lines = []
    for i, h in enumerate(headlines):
        teaser = f" — {h['teaser']}" if h.get("teaser") else ""
        lines.append(f"{i}: {h['title']}{teaser}")

    return (
        f"Her er {len(headlines)} nyhedsoverskrifter fra en dansk/international nyhedsside.\n"
        "Vælg de overskrifter der sandsynligvis kan bruges som genstandsfelt i Samfundsfag A.\n\n"
        + "\n".join(lines)
        + '\n\nSvar med JSON:\n{"relevant_indices": [<liste af indeksnumre der er værd at læse>]}'
    )


# ─── Deep-read prompt (full article scoring) ──────────────────────────────────

DEEP_READ_SYSTEM_PROMPT = (
    "Du er en erfaren samfundsfagslærer (stx) der vurderer om en nyhedsartikel kan bruges som "
    "GENSTANDSFELT for analyse i undervisningen.\n\n"
    + _CURRICULUM
    + "\n\nDIN OPGAVE:\n"
    "Læs artiklen grundigt og vurder om elever kan bruge den som udgangspunkt for en faglig analyse. "
    "En god artikel er en hvor eleverne kan ANVENDE konkrete teorier og begreber – ikke bare nævne dem.\n\n"
    "STRENGE KRITERIER:\n"
    "- En artikel om en virksomheds overskud er IKKE økonomi-relevant, medmindre den kan analyseres "
    "med f.eks. markedsmekanismen, priselasticitet eller monetarisme.\n"
    "- En artikel om krig er IKKE automatisk international politik – den skal give mulighed for at "
    "anvende f.eks. integrationsteorier, NATO-analyse eller globaliseringsbegrebet analytisk.\n"
    "- En artikel om ulighed er IKKE sociologi, medmindre den giver grundlag for at anvende f.eks. "
    "Bourdieu, social mobilitet eller Gini-koefficienten konkret.\n"
    "- Vær KRITISK. De fleste nyheder er IKKE gode undervisningsartikler (score 1-4).\n"
    "- Score 7+ kræver at du kan beskrive en KONKRET analyse-opgave eleven kan lave.\n\n"
    "SCORINGSSKALA:\n"
    "- 9-10: Oplagt undervisningsartikel. Klar kobling til 2+ teorier. Kan bruges direkte som eksamenscase.\n"
    "- 7-8: God artikel. Tydelig kobling til mindst 1 teori med konkret analytisk potentiale.\n"
    "- 5-6: Mulig artikel. Kræver fortolkning. Begrænset analytisk dybde.\n"
    "- 3-4: Svag kobling. Kun overfladisk relation til fagets begreber.\n"
    "- 1-2: Ikke brugbar som undervisningsmateriale i Samfundsfag A.\n\n"
    "I 'explanation' SKAL du:\n"
    "1. Nævne 1-3 SPECIFIKKE teorier/begreber der kan APPLICERES (ikke blot nævnes)\n"
    "2. Beskrive HVAD eleverne konkret kan analysere med disse begreber\n"
    "3. Hvis score < 5: forklare HVORFOR artiklen ikke er god nok\n\n"
    "Du svarer KUN med valid JSON. Ingen anden tekst."
)


def build_deep_read_prompt(
    title: str, text: str, source: str, language: str
) -> str:
    """Build prompt for deep article scoring."""
    lang_note = ""
    if language == "en":
        lang_note = (
            " (Artiklen er på engelsk – vurder relevans for dansk "
            "Samfundsfag A, herunder komparativt perspektiv.)"
        )

    return (
        f"Vurder denne artikel fra {source}{lang_note} som potentielt undervisningsmateriale:\n\n"
        f"Titel: {title}\n\n"
        f"Artikeltekst:\n{text[:5000]}\n\n"
        "Svar med dette JSON-format:\n"
        "{\n"
        '  "overall_score": <1-10>,\n'
        '  "disciplines": {\n'
        '    "sociologi": <0-10>,\n'
        '    "politik": <0-10>,\n'
        '    "okonomi": <0-10>,\n'
        '    "international_politik": <0-10>,\n'
        '    "metode": <0-10>\n'
        "  },\n"
        '  "primary_discipline": "<sociologi|politik|okonomi|international_politik|metode>",\n'
        '  "explanation": "<Hvilke konkrete teorier kan eleverne anvende, og hvad kan de analysere?>"\n'
        "}"
    )


# ─── Backwards-compat aliases (used by ollama/claude backends) ────────────────

SYSTEM_PROMPT = DEEP_READ_SYSTEM_PROMPT


def build_scoring_prompt(
    title: str, text: str, source: str, language: str
) -> str:
    return build_deep_read_prompt(title, text, source, language)


# ─── Response parser ──────────────────────────────────────────────────────────

def parse_scoring_response(
    raw: str, article_url: str, backend: str = "ollama"
) -> ScoringResult | None:
    """Parse JSON response from LLM into a ScoringResult."""
    try:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        data = json.loads(text)
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
