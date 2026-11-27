from pathlib import Path

from pharma_research_assistant.history import (
    load_history,
    normalize_doi,
    normalize_title,
    record_digest,
    unseen_papers,
)
from pharma_research_assistant.models import Paper, Topic


def test_normalize_title():
    assert normalize_title("HPLC: Peak-Tailing!") == "hplc peak tailing"


def test_normalize_doi():
    assert normalize_doi("https://doi.org/10.1000/ABC") == "10.1000/abc"
    assert normalize_doi("doi:10.1000/ABC") == "10.1000/abc"


def test_unseen_deduplicates_by_id_doi_and_title(tmp_path: Path):
    path = tmp_path / "history.json"
    path.write_text(
        '{"papers":[{"paper_id":"doi:10.1/a","doi":"https://doi.org/10.1/a",'
        '"title":"Known Paper"}],"digests":[]}',
        encoding="utf-8",
    )
    history = load_history(path)
    papers = [
        Paper("doi:10.1/a", "10.1/a", "Another title", "2026-01-01", "J", "https://doi.org/10.1/a", "x" * 200),
        Paper("id2", None, "Known Paper", "2026-01-02", "J", "https://example.org/2", "x" * 200),
        Paper("id3", None, "New Paper", "2026-01-03", "J", "https://example.org/3", "x" * 200),
    ]
    assert [paper.paper_id for paper in unseen_papers(papers, history)] == ["id3"]


def test_record_digest_is_idempotent(tmp_path: Path):
    path = tmp_path / "history.json"
    topic = Topic(
        paper_id="doi:10.1/x", title="Headline", instrument="HPLC",
        category="Troubleshooting", research_summary="Finding.",
        practical_relevance="Useful.", linkedin_angle="Question?",
        paper_title="Paper title", journal="Journal", publication_date="2026-01-01",
        url="https://doi.org/10.1/x", doi="10.1/x",
    )
    record_digest(path, [topic], "2026-01-01")
    record_digest(path, [topic], "2026-01-01")
    history = load_history(path)
    assert len(history["papers"]) == 1
    assert len(history["digests"]) == 1
    assert history["papers"][0]["doi"] == "10.1/x"
