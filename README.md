# Pharma Research Assistant

A weekly literature radar for pharmaceutical analytical chemistry and QC/R&D. It prioritizes instrument troubleshooting, then method reliability, development/validation, sample preparation, and laboratory optimization.

## What it does

1. Runs every Friday at 20:00 WIB through GitHub Actions (also supports manual runs).
2. Searches recent English-language journal articles and reviews in OpenAlex.
3. Deduplicates candidates against the committed research history.
4. Uses the OpenAI Responses API to select and summarize exactly seven evidence-backed topics using structured JSON output.
5. Emails the digest through Gmail SMTP using an App Password.
6. Archives the digest and updates history only after successful email delivery.

It does **not** publish to LinkedIn. Each topic includes its source, publication date, findings, practical relevance, and a LinkedIn discussion angle.

## One-time setup

### 1. Get API credentials

- Create an OpenAI API key from the OpenAI developer platform. API usage is billed separately from a ChatGPT subscription.
- Create a free OpenAlex account and copy its API key from OpenAlex Settings → API key. OpenAlex replaced its old polite-pool `mailto` mechanism with API keys in 2026.
- For the Gmail **sender** account, enable 2-Step Verification and create a Google App Password. Use the App Password, not the normal Gmail password.
- The sender and recipient can be different Gmail addresses.

### 2. Add GitHub repository secrets

Open **Settings → Secrets and variables → Actions → New repository secret** and add:

| Secret | Value |
|---|---|
| `OPENAI_API_KEY` | Your OpenAI API key |
| `OPENALEX_API_KEY` | Your OpenAlex API key |
| `SMTP_USER` | Gmail sender address |
| `SMTP_APP_PASSWORD` | Gmail App Password |
| `RECIPIENT_EMAIL` | Destination email address |

Never commit API keys, App Passwords, or a real `.env` file.

### 3. Run

The workflow is scheduled for Friday 20:00 WIB. To test it, open **Actions → Weekly Pharmaceutical Research Digest → Run workflow**.

A run will fail clearly if credentials are missing, fewer than seven eligible unseen papers are found, or the model cannot return seven valid topics. It will not pad the digest with fabricated topics.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e ".[dev]"
cp .env.example .env
# Fill .env with your own credentials
python -m pharma_research_assistant.main
pytest
```

## Research scope and limitations

- OpenAlex is the initial discovery provider; PubMed and Crossref are not yet integrated.
- Search results are candidates, not proof of a finding. Summaries are constrained to the retrieved title, journal, date, URL, and abstract.
- Abstract-only evidence may not expose detailed experimental conditions or troubleshooting mechanisms; the digest flags unavailable details rather than inventing them.
- The 45-day lookback is configurable. Some weeks may not contain seven sufficiently relevant, unseen papers. In that case, the run stops instead of repeating old topics or inventing research.
- OpenAlex requests use a per-request delay, retry temporary errors with backoff, respect `Retry-After`, and stop with an explicit message if the daily API budget is exhausted.
- History tracks DOI, work ID, and normalized title to reduce repeats. History is committed to this repository after successful delivery.

## Configuration

See `.env.example`. The default literature window is 45 days and discovery retrieves up to 50 records per search query before global deduplication and candidate limiting.
