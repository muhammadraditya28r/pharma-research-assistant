from datetime import date
import html

from .models import Topic


def render_digest(topics: list[Topic], lookback_days: int) -> str:
    lines = [
        "# Pharmaceutical Research Radar",
        f"**Weekly issue · {date.today().isoformat()} · Literature window: {lookback_days} days**",
        "",
        "Seven recent research topics for pharmaceutical QC, analytical development, and R&D.",
        "",
    ]
    for index, topic in enumerate(topics, 1):
        lines.extend([
            "---",
            f"## {index:02d}. {topic.title}",
            "",
            f"**Instrument:** {topic.instrument}  ",
            f"**Category:** {topic.category}  ",
            f"**Published:** {topic.publication_date}  ",
            f"**Journal:** {topic.journal}",
            "",
            f"**Research finding:** {topic.research_summary}",
            "",
            f"**Practical relevance:** {topic.practical_relevance}",
            "",
            f"**LinkedIn discussion angle:** {topic.linkedin_angle}",
            "",
            f"**Reference:** [{topic.paper_title}]({topic.url})",
            "",
        ])
    lines.extend([
        "---",
        "## Your next step",
        "",
        "Select one topic for a deeper evidence review and LinkedIn draft. "
        "Nothing is published automatically.",
        "",
    ])
    return "\n".join(lines)


def email_html(markdown: str) -> str:
    escaped = html.escape(markdown)
    return (
        "<html><body><pre style='white-space:pre-wrap;"
        "font-family:Arial,sans-serif;font-size:14px'>"
        + escaped
        + "</pre></body></html>"
    )
