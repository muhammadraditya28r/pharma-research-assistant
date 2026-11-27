import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str
    smtp_user: str
    smtp_app_password: str
    recipient_email: str
    openalex_mailto: str
    lookback_days: int
    max_results_per_query: int
    max_total_candidates: int
    history_path: Path = Path("data/research_history.json")
    briefs_dir: Path = Path("briefs")


def load_settings() -> Settings:
    required = ["GEMINI_API_KEY", "SMTP_USER", "SMTP_APP_PASSWORD", "RECIPIENT_EMAIL"]
    missing = [key for key in required if not os.getenv(key, "").strip()]
    if missing:
        raise RuntimeError("Missing required environment variables: " + ", ".join(missing))

    try:
        lookback = int(os.getenv("LOOKBACK_DAYS", "45"))
        per_query = int(os.getenv("MAX_RESULTS_PER_QUERY", "50"))
        total = int(os.getenv("MAX_TOTAL_CANDIDATES", "250"))
    except ValueError as exc:
        raise RuntimeError("LOOKBACK_DAYS and candidate limits must be integers.") from exc
    if min(lookback, per_query, total) < 1:
        raise RuntimeError("LOOKBACK_DAYS and candidate limits must be positive integers.")

    sender = os.environ["SMTP_USER"].strip()
    return Settings(
        gemini_api_key=os.environ["GEMINI_API_KEY"].strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip(),
        smtp_user=sender,
        smtp_app_password=os.environ["SMTP_APP_PASSWORD"].replace(" ", "").strip(),
        recipient_email=os.environ["RECIPIENT_EMAIL"].strip(),
        openalex_mailto=(os.getenv("OPENALEX_MAILTO") or sender).strip(),
        lookback_days=lookback,
        max_results_per_query=per_query,
        max_total_candidates=total,
    )
