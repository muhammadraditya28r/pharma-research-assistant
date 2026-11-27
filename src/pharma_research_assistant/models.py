from dataclasses import dataclass


@dataclass(frozen=True)
class Paper:
    paper_id: str
    doi: str | None
    title: str
    publication_date: str
    journal: str
    url: str
    abstract: str
    source: str = "OpenAlex"


@dataclass(frozen=True)
class Topic:
    paper_id: str
    title: str
    instrument: str
    category: str
    research_summary: str
    practical_relevance: str
    linkedin_angle: str
    paper_title: str
    journal: str
    publication_date: str
    url: str
    doi: str | None = None
