import json
import re
from pathlib import Path

from .models import Paper, Topic


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def normalize_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    value = doi.strip().lower()
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value)
    value = re.sub(r"^doi:\s*", "", value)
    return value or None


def load_history(path: Path) -> dict:
    if not path.exists():
        return {"papers": [], "digests": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"History file has invalid structure: {path}")
    data.setdefault("papers", [])
    data.setdefault("digests", [])
    return data


def unseen_papers(papers: list[Paper], history: dict) -> list[Paper]:
    records = history.get("papers", [])
    ids = {record.get("paper_id") for record in records}
    dois = {normalize_doi(record.get("doi")) for record in records}
    titles = {normalize_title(record.get("title", "")) for record in records}
    result = []
    for paper in papers:
        doi = normalize_doi(paper.doi)
        if paper.paper_id in ids:
            continue
        if doi and doi in dois:
            continue
        if normalize_title(paper.title) in titles:
            continue
        result.append(paper)
    return result


def record_digest(path: Path, topics: list[Topic], digest_id: str) -> None:
    history = load_history(path)
    existing_ids = {record.get("paper_id") for record in history["papers"]}
    for topic in topics:
        if topic.paper_id not in existing_ids:
            history["papers"].append({
                "paper_id": topic.paper_id,
                "title": topic.paper_title,
                "doi": normalize_doi(topic.doi),
                "topic_title": topic.title,
                "instrument": topic.instrument,
                "first_seen_digest": digest_id,
            })
            existing_ids.add(topic.paper_id)
    if not any(item.get("digest_id") == digest_id for item in history["digests"]):
        history["digests"].append({"digest_id": digest_id, "topic_count": len(topics)})
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(history, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)
