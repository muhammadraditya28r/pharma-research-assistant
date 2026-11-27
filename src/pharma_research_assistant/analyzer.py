import json

from openai import OpenAI

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


def select_topics(papers: list[Paper], api_key: str, model: str) -> list[Topic]:
    client = OpenAI(api_key=api_key)
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
    schema = {
        "type": "object",
        "properties": {
            "topics": {
                "type": "array",
                "minItems": 7,
                "maxItems": 7,
                "items": {
                    "type": "object",
                    "properties": {
                        "paper_id": {"type": "string"},
                        "title": {"type": "string"},
                        "instrument": {"type": "string"},
                        "category": {
                            "type": "string",
                            "enum": [
                                "Troubleshooting", "Method reliability", "Method development",
                                "Validation", "Sample preparation", "Optimization",
                            ],
                        },
                        "research_summary": {"type": "string"},
                        "practical_relevance": {"type": "string"},
                        "linkedin_angle": {"type": "string"},
                    },
                    "required": [
                        "paper_id", "title", "instrument", "category",
                        "research_summary", "practical_relevance", "linkedin_angle",
                    ],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["topics"],
        "additionalProperties": False,
    }
    response = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {
                "role": "user",
                "content": "Select and analyze seven topics from these candidate papers. "
                "Use only their supplied metadata and abstracts.\n"
                + json.dumps(candidates, ensure_ascii=False),
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "pharmaceutical_research_topics",
                "strict": True,
                "schema": schema,
            }
        },
    )
    output_text = response.output_text
    if not output_text:
        raise RuntimeError("OpenAI returned an empty response or no text output.")
    try:
        payload = json.loads(output_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("OpenAI response was not valid JSON.") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("topics"), list):
        raise RuntimeError("OpenAI response is missing the topics array.")

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
            f"OpenAI returned {len(topics)} valid, unique topics; exactly 7 are required. "
            "No email or history update was performed."
        )
    return topics
