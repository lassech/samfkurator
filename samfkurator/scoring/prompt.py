import json

from samfkurator.models import DisciplineScore, ScoringResult

SYSTEM_PROMPT = """\
Du er en ekspert i Samfundsfag A (stx) og hjælper en gymnasielærer med at \
vurdere nyhedsartiklers relevans for undervisningen.

Din opgave er at vurdere om en artikel kan bruges som GENSTANDSFELT for \
analyse med fagets teorier og begreber. En god artikel er en som eleverne \
kan analysere med konkrete faglige redskaber -- ikke blot en artikel der \
"handler om" et emne.

Fagets discipliner med tilhørende teorier og begreber:

**Politik:**
Lipset-Rokkan, fordelings- og værdipolitik, postmaterialisme, \
Molins model, Kaare Strøm, medianvælgerteorien, partityper, \
Sjøbloms partistrategier, marginalvælgere, kernevælgere, issuevoting, \
Columbia-skolen, Michigan-skolen, rational choice-model, \
liberalisme, socialisme, konservatisme, \
deltagelsesdemokrati, konkurrencedemokrati, deliberativt demokrati, \
meritokrati, medborgerskab, medborgerskabstyper, \
køn (formel og reel lighed), parlamentarisk styringskæde, valgmåder, \
lovgivningsproces, magtformer (ressource, relation, strukturel, direkte, \
indirekte, institutionel), magtdeling, regeringstyper, \
medialisering, priming, framing, nyhedskriterier, gatekeeper-funktion, \
RAS-model, kanyleteori, referencemodel, \
forstærkelses- og mobiliseringshypotese

**Sociologi:**
Socialisering, dobbeltsocialisering, normer (formelle/uformelle), \
sanktioner, social kontrol, sociale roller, rollekonflikt, \
identitet (jeg, personlig, social, kollektiv), sociale grupper, \
social arv, mønsterbrydere, chanceulighed, social mobilitet, \
Giddens (senmodernitet, strukturation, adskillelse af tid og rum, \
udlejring af sociale relationer, aftraditionalisering), \
Bourdieu (kapitaler, habitus), Honneth (anerkendelse, sfærer), \
Habermas (kommunikativ handlen, kolonisering af livsverden, \
herredømmefri dialog), Reckwitz (singularitetens tid), \
Beck (risikosamfund, valgbiografi, institutionaliseret individualisering), \
Ziehe (kulturel frisættelse, formbarhed, subjektivisering, \
ontologisering, potensering), \
køn som biologi, Parsons (instrumentel/ekspressiv), doing gender, \
Connell (hegemonisk maskulinitet, medvirkende/underordnede/undertrykte \
maskuliniteter), patriarkat, mental load, \
Hofstede (magtdistance, individualistisk/kollektivistisk, \
feminin/maskulin, usikkerhedsundvigelse, langtids-/korttidsorientering, \
eftergivenhed/begrænsning), \
struktur/aktør, majoritet, minoritet, segregation, \
Huntingtons civilisationsteori

**Økonomi:**
Økonomiske mål (udligning af sociale forskelle, Gini-koefficient, \
vækst/BNP, fuld beskæftigelse, lav inflation, \
betalingsbalance, klima og miljø), \
økonomisk kredsløb, høj-/lavkonjunktur, rente, konkurrenceevne, \
eksport, multiplikator, \
monetarisme, keynesianisme, Adam Smith, \
finanspolitik (automatiske stabilisatorer, crowding out), \
pengepolitik, strukturpolitik, \
valutapolitik (revaluering, devaluering, flydende/fast kurs, ERM2), \
flexicurity, arbejdsmarkedspolitik, arbejdsstyrken, \
ledighed (register/AKU, skifte/hjemsendelse/sæson/konjunktur/struktur), \
lønspredning, indkomstpolitik, \
udbud, efterspørgsel, afgifter, regulering, priselasticitet, \
økonomiske systemer (plan-/markeds-/blandingsøkonomi), \
velfærdsmodeller (skandinavisk, centraleuropæisk, liberal), \
civilsamfund, marked, stat

**International politik:**
EU-organer (Kommissionen, Det Europæiske Råd, EU-Parlamentet, \
EU-Domstolen, Ministerrådet), mellemstatsligt/overstatsligt, \
føderation, konføderation, \
integrationsteorier (føderalisme, neofunktionalisme, \
liberal intergovernmentalisme, multilevel governance), \
direktiv, forordning, lovgivningsproces i EU, \
politisk/kulturel/økonomisk globalisering, \
amerikanisering, monokultur, WTO, NATO, \
velfærdsstatens udfordringer (ældrebyrde, forventningspres, \
globalisering, outsourcing, social dumping), \
velfærdsstrategier (udvidelse/nedskæring), \
Huntingtons civilisationsteori

**Metode:**
Kvalitativ og kvantitativ metode, spørgsmålsformulering, \
hypoteser, operationalisering, validitet, \
komparativ metode, casestudier

Scoring-kriterier (baseret på analytisk brugbarhed som genstandsfelt):
- 9-10: Oplagt genstandsfelt. Artiklen kan direkte analyseres med \
mindst 2-3 konkrete teorier/begreber. Ideel som eksamenscase eller \
undervisningseksempel.
- 7-8: Godt genstandsfelt. Artiklen kan analyseres med mindst 1-2 \
teorier/begreber og illustrerer tydelige faglige problemstillinger.
- 5-6: Muligt genstandsfelt. Artiklen berører faglige emner men \
kræver en del fortolkning for at koble til konkrete begreber.
- 3-4: Svagt genstandsfelt. Kun overfladisk kobling til fagets \
begreber. Begrænset analytisk potentiale.
- 1-2: Ikke brugbart som genstandsfelt for Samfundsfag A.

I din forklaring SKAL du nævne 1-3 konkrete teorier eller begreber \
fra listen ovenfor som artiklen kan analyseres med.

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
  "explanation": "<1-2 sætninger: hvilke konkrete teorier/begreber kan artiklen analyseres med?>"
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
