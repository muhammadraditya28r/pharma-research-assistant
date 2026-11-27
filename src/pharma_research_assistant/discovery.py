from datetime import date, timedelta
import re
import time

import requests

from .models import Paper

OPENALEX = "https://api.openalex.org/works"

# OpenAlex search is full-text relevance search, not a Boolean query parser.
# Keep each query as natural-language terms and use the API filters separately.
SEARCH_TERMS = [
    "HPLC troubleshooting peak tailing baseline drift carryover robustness",
    "UHPLC method robustness validation peak shape pharmaceutical",
    "gas chromatography residual solvents troubleshooting column bleed carryover",
    "pharmaceutical UV Vis spectrophotometry FTIR analytical method validation",
    "ICP-MS ICP-OES elemental impurities pharmaceutical matrix interference",
    "pharmaceutical dissolution testing variability troubleshooting analytical method",
    "Raman near infrared spectroscopy pharmaceutical process analytical technology calibration",
    "pharmaceutical analytical method out of specification investigation robustness",
    "pharmaceutical sample preparation extraction recovery matrix effects analytical chemistry",
    "chromatographic analytical method transfer reproducibility system suitability",
    "pharmaceutical stability indicating assay degradation products method development",
]


def _abstract_from_inverted_index(index: dict | None) -> str:
    if not index:
        return ""
    positioned = [
        (position, word)
        for word, positions in index.items()
        for position in positions
    ]
    positioned.sort(key=lambda pair: pair[0])
    return " ".join(word for _, word in positioned)


def _doi_value(value: str | None) -> str | None:
    if not value:
        return None
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", value.strip(), flags=re.I).lower() or None


def discover_papers(
    lookback_days: int,
    per_query: int,
    mailto: str,
    max_total: int = 250,
) -> list[Paper]:
    cutoff = (date.today() - timedelta(days=lookback_days)).isoformat()
    session = requests.Session()
    session.headers.update({"User-Agent": f"PharmaResearchAssistant/0.1 (mailto:{mailto})"})
    found: dict[str, Paper] = {}

    for query in SEARCH_TERMS:
        params = {
            "search": query,
            "filter": f"from_publication_date:{cutoff},type:article|review,has_abstract:true,language:en",
            "sort": "publication_date:desc",
            "per-page": per_query,
            "mailto": mailto,
        }
        response = session.get(OPENALEX, params=params, timeout=40)
        response.raise_for_status()
        payload = response.json()

        for item in payload.get("results", []):
            abstract = _abstract_from_inverted_index(item.get("abstract_inverted_index"))
            title = (item.get("title") or "").strip()
            publication_date = item.get("publication_date") or ""
            if len(abstract) < 180 or len(title) < 12 or not publication_date:
                continue

            doi = _doi_value(item.get("doi"))
            work_id = item.get("id") or ""
            paper_id = f"doi:{doi}" if doi else work_id
            if not paper_id:
                continue

            primary = item.get("primary_location") or {}
            source = primary.get("source") or {}
            landing_page = primary.get("landing_page_url")
            url = f"https://doi.org/{doi}" if doi else (landing_page or work_id)
            found.setdefault(
                paper_id,
                Paper(
                    paper_id=paper_id,
                    doi=doi,
                    title=title,
                    publication_date=publication_date,
                    journal=source.get("display_name") or "Journal not provided",
                    url=url,
                    abstract=abstract[:5000],
                ),
            )
        # Avoid hammering the public API across a batch of queries.
        time.sleep(0.15)

    papers = sorted(found.values(), key=lambda paper: paper.publication_date, reverse=True)
    return papers[:max_total]
