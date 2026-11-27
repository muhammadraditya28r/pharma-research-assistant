import json

from google import genai
from google.genai import types

from .history import normalize_title
from .models import Paper, Topic

SYSTEM_INSTRUCTION = """
You are an evidence-focused pharmaceutical analytical chemistry literature analyst.
Choose exactly seven distinct and genuinely relevant research papers from the candidates.
Prioritize practical instrument troubleshooting and failure mechanisms. Also include method reliability,
method development/validation, sample preparation, and laboratory optimization when supported by the papers.
Do not force a paper into a troubleshooting category. Cover different analytical techniques where the
candidate evidence permits. Select original research or review papers with clear pharmaceutical analytical,
QC, or R&D relevance. Do not select papers based only on keyword overlap.

Use only supplied metadata and abstracts. Never invent experimental results, numerical values, causes,
journal details, dates, or conclusions. Distinguish a paper's actual findings from practical implications.
If a specific detail is not in the abstract, state that the abstract does not provide it.

Return exactly seven distinct topics. Each paper_id must be copied exactly from the input.
"""

OUTPUT_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "topics": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "paper_id": {"type": "STRING"},
                    "title": {"type": "STRING"},
                    "instrument": {"type": "STRING"},
                    "category": {
                        "type": "STRING",
                        "enum": [
                            "Troubleshooting", "Method reliability", "Method development",
                            "Validation", "Sample preparation", "Optimization",
                        ],
                    },
                    "research_summary": {"type": "STRING"},
                    "practical_relevance": {"type": "STRING"},
                    "linkedin_angle": {"type": "STRING"},
                },
                "required": [
                    "paper_id", "title", "instrument", "category",
                    "research_summary", "practical_relevance", "linkedin_angle",
                ],
            },
        }
    },
    "required": ["topics"],
}


def _parse_topics(output_text: str, papers: list[Paper]) -> list[Topic]:
    try:
        payload = json.loads(output_text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise RuntimeError("Gemini response was not valid JSON.") from exc

    if not isinstance(payload, dict) or not isinstance(payload.get("topics"), list):
        raise RuntimeError("Gemini response is missing the topics array.")

    by_id = {paper.paper_id: paper for paper in papers}
    topics: list[Topic] = []
    seen_ids: set[str] = set()
    seen_titles: set[str] = set()
    required = (
        "title", "instrument", "category", "research_summary",
        "practical_relevance", "linkedin_angle",
    )

    for item in payload["topics"]:
        if not isinstance(item, dict):
            continue
        paper_id = item.get("paper_id")
        paper = by_id.get(paper_id) if isinstance(paper_id, str) else None
        if not paper or paper_id in seen_ids:
            continue
        if any(not isinstance(item.get(field), str) or not item[field].strip() for field in required):
            continue
        headline_key = normalize_title(item["title"])
        if not headline_key or headline_key in seen_titles:
            continue

        topics.append(Topic(
            paper_id=paper.paper_id,
            title=item["title"].strip(),
            instrument=item["instrument"].strip(),
            category=item["category"].strip(),
            research_summary=item["research_summary"].strip(),
            practical_relevance=item["practical_relevance"].strip(),
            linkedin_angle=item["linkedin_angle"].strip(),
            paper_title=paper.title,
            journal=paper.journal,
            publication_date=paper.publication_date,
            url=paper.url,
            doi=paper.doi,
        ))
        seen_ids.add(paper_id)
        seen_titles.add(headline_key)

    if len(topics) != 7:
        raise RuntimeError(
            f"Gemini returned {len(topics)} valid, unique topics; exactly 7 are required. "
            "No email or history update was performed."
        )
    return topics


def select_topics(
    papers: list[Paper],
    api_key: str,
    model: str,
    fallback_models: tuple[str, ...] = (),
) -> list[Topic]:
    client = genai.Client(api_key=api_key)
    candidates = [
        {
            "paper_id": paper.paper_id,
            "title": paper.title,
            "date": paper.publication_date,
            "journal": paper.journal,
            "url": paper.url,
            "abstract": paper.abstract[:3500],
        }
        for paper in papers
    ]
    prompt = (
        SYSTEM_INSTRUCTION
        + "\n\nSelect and analyze seven topics from these candidate papers. "
        "Use only their supplied metadata and abstracts.\n"
        + json.dumps(candidates, ensure_ascii=False)
    )

    models = tuple(dict.fromkeys((model, *fallback_models)))
    failures: list[str] = []

    for candidate_model in models:
        try:
            response = client.models.generate_content(
                model=candidate_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=OUTPUT_SCHEMA,
                    temperature=0.2,
                ),
            )
            output_text = response.text
            if not output_text:
                raise RuntimeError("Gemini returned an empty response.")
            topics = _parse_topics(output_text, papers)
            print(f"Research analysis completed using model: {candidate_model}")
            return topics
        except Exception as exc:
            failures.append(f"{candidate_model}: {type(exc).__name__}: {exc}")
            print(f"Model {candidate_model} failed; trying the next fallback if available.")

    details = "\n".join(f"- {failure}" for failure in failures)
    raise RuntimeError(
        "All configured Gemini models failed. No email or history update was performed.\n"
        + details
    )
