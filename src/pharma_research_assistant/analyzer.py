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
If a specific detail is not in the abstract, do not claim it.

Return JSON only, using this exact shape:
{"topics":[{"paper_id":"exact supplied id","title":"concise descriptive headline",
"instrument":"instrument or technique","category":"Troubleshooting | Method reliability | Method development | Validation | Sample preparation | Optimization",
"research_summary":"two concise evidence-based sentences",
"practical_relevance":"one or two sentences for pharmaceutical QC/R&D analysts",
"linkedin_angle":"one focused question or discussion angle"}]}
Each paper_id must be copied exactly from the input. Do not repeat a paper.
"""


def select_topics(papers: list[Paper], api_key: str, model: str) -> list[Topic]:
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
    response = client.models.generate_content(
        model=model,
        contents="Candidate research papers:\n" + json.dumps(candidates, ensure_ascii=False),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            temperature=0.1,
        ),
    )
    if not response or not response.text:
        raise RuntimeError("Gemini returned an empty response.")
    try:
        payload = json.loads(response.text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Gemini response was not valid JSON.") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("topics"), list):
        raise RuntimeError("Gemini response is missing the topics array.")

    by_id = {paper.paper_id: paper for paper in papers}
    topics: list[Topic] = []
    seen_ids: set[str] = set()
    seen_titles: set[str] = set()
    required = ("title", "instrument", "category", "research_summary", "practical_relevance", "linkedin_angle")

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
        category = item["category"].strip()
        allowed_categories = {
            "Troubleshooting", "Method reliability", "Method development",
            "Validation", "Sample preparation", "Optimization",
        }
        if category not in allowed_categories:
            continue

        topics.append(Topic(
            paper_id=paper.paper_id,
            title=item["title"].strip(),
            instrument=item["instrument"].strip(),
            category=category,
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
