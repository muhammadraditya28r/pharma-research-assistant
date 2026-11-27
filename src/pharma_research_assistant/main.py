from datetime import date

from .analyzer import select_topics
from .config import load_settings
from .digest import render_digest
from .discovery import discover_papers
from .history import load_history, record_digest, unseen_papers
from .mailer import send_digest


def main() -> None:
    settings = load_settings()
    digest_id = date.today().isoformat()
    output = settings.briefs_dir / f"weekly_digest_{digest_id}.md"

    if output.exists():
        raise RuntimeError(
            f"A digest archive already exists for {digest_id}. "
            "Delete/rename it only if you intentionally want to regenerate this issue."
        )

    history = load_history(settings.history_path)
    papers = discover_papers(
        lookback_days=settings.lookback_days,
        per_query=settings.max_results_per_query,
        api_key=settings.openalex_api_key,
        max_total=settings.max_total_candidates,
    )
    fresh = unseen_papers(papers, history)
    if len(fresh) < 7:
        raise RuntimeError(
            f"Only {len(fresh)} unseen papers with usable abstracts were found; "
            "at least 7 are required. Increase LOOKBACK_DAYS or improve search coverage. "
            "No email/history update performed."
        )

    topics = select_topics(
        fresh,
        settings.gemini_api_key,
        settings.gemini_model,
        settings.gemini_fallback_models,
    )
    digest = render_digest(topics, settings.lookback_days)

    settings.briefs_dir.mkdir(parents=True, exist_ok=True)
    output.write_text(digest + "\n", encoding="utf-8")
    try:
        send_digest(
            settings.smtp_user,
            settings.smtp_app_password,
            settings.recipient_email,
            f"[Pharma Research Radar] Weekly Digest — {digest_id}",
            digest,
        )
    except Exception:
        output.unlink(missing_ok=True)
        raise

    record_digest(settings.history_path, topics, digest_id)
    print(
        f"Digest sent to {settings.recipient_email}; saved {output}; "
        f"recorded {len(topics)} topics."
    )


if __name__ == "__main__":
    main()
