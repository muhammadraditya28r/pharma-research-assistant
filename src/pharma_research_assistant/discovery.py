from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import re
import time

import requests

from .models import Paper

OPENALEX = "https://api.openalex.org/works"
MAX_RETRIES = 6
MIN_REQUEST_INTERVAL_SECONDS = 1.1

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
    return re.sub(r"^https?://(dx\\.)?doi\\.org/", "", value.strip(), flags=re.I).lower() or None


def _retry_after_seconds(response: requests.Response, attempt: int) -> float:
    value = response.headers.get("Retry-After")
    if value:
        try:
            return max(1.0, float(value))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(value)
                return max(1.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                pass

    try:
        body = response.json()
        detail = body.get("message", "")
        match = re.search(r"retry after ([0-9.]+)s?", detail, flags=re.I)
        if match:
            return max(1.0, float(match.group(1)))
        retry_after = body.get("retryAfter")
        if retry_after is not None:
            return max(1.0, float(retry_after))
    except (ValueError, AttributeError, TypeError):
        pass

    return min(2 ** attempt, 60)


def _get_with_retries(
    session: requests.Session,
    params: dict,
    last_request_at: float | None,
) -> tuple[requests.Response, float]:
    if last_request_at is not None:
        elapsed = time.monotonic() - last_request_at
        if elapsed < MIN_REQUEST_INTERVAL_SECONDS:
            time.sleep(MIN_REQUEST_INTERVAL_SECONDS - elapsed)

    for attempt in range(MAX_RETRIES):
        try:
            response = session.get(OPENALEX, params=params, timeout=40)
        except (requests.Timeout, requests.ConnectionError):
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(min(2 ** attempt, 60))
            continue

        if response.status_code == 429:
            try:
                error = response.json()
            except ValueError:
                error = {}
            reason = error.get("reason")
            if reason == "daily_budget":
                reset = error.get("resets_at") or "the next UTC daily reset"
                raise RuntimeError(
                    f"OpenAlex daily API budget is exhausted (HTTP 429). "
                    f"Budget resets at {reset}. Check your OpenAlex API key usage."
                )
            if attempt == MAX_RETRIES - 1:
                response.raise_for_status()
            wait = _retry_after_seconds(response, attempt)
            print(f"OpenAlex rate limited this request; retrying in {wait:.1f}s "
                  f"(attempt {attempt + 1}/{MAX_RETRIES}).")
            time.sleep(wait)
            continue

        if response.status_code in (500, 502, 503, 504):
            if attempt == MAX_RETRIES - 1:
                response.raise_for_status()
            wait = min(2 ** attempt, 60)
            print(f"OpenAlex temporary server error {response.status_code}; "
                  f"retrying in {wait}s.")
            time.sleep(wait)
            continue

        response.raise_for_status()
        return response, time.monotonic()

    raise RuntimeError("OpenAlex request failed after all retry attempts.")


def discover_papers(
    lookback_days: int,
    per_query: int,
    api_key: str,
    max_total: int = 250,
) -> list[Paper]:
    cutoff = (date.today() - timedelta(days=lookback_days)).isoformat()
    session = requests.Session()
    session.headers.update({"User-Agent": "PharmaResearchAssistant/0.2"})
    found: dict[str, Paper] = {}
    last_request_at = None

    for query in SEARCH_TERMS:
        params = {
            "search": query,
            "filter": f"from_publication_date:{cutoff},type:article|review,has_abstract:true,language:en",
            "sort": "publication_date:desc",
            "per-page": min(per_query, 100),
            "api_key": api_key,
        }
        response, last_request_at = _get_with_retries(session, params, last_request_at)
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

    papers = sorted(found.values(), key=lambda paper: paper.publication_date, reverse=True)
    return papers[:max_total]
