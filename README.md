# Pharma Research Assistant

A weekly literature radar for pharmaceutical analytical chemistry and QC/R&D. It prioritizes instrument troubleshooting, then method reliability, development/validation, sample preparation, and laboratory optimization.

## What it does

1. Runs every Friday at 20:00 WIB through GitHub Actions (also supports manual runs).
2. Searches recent English-language journal articles and reviews in OpenAlex.
3. Deduplicates candidates against the committed research history.
4. Uses the Google Gemini API to select and summarize exactly seven evidence-backed topics using structured JSON output.
5. Emails the digest through Gmail SMTP using an App Password.
6. Archives the digest and updates history only after successful email delivery.

It does **not** publish to LinkedIn. Each topic includes its source, publication date, findings, practical relevance, and a LinkedIn discussion angle.

## Gemini model selection and fallback

The workflow tries models in this order:

1. `gemini-4-carbon` — latest frontier model; requires paid Gemini API access.
2. `gemini-3.8-flash` — free-tier compatible fallback.
3. `gemini-3.1-flash-lite` — additional free-tier compatible fallback.

On a free API account, Carbon is expected to be unavailable, so the workflow should fall back to Flash. If a model returns an API error, an empty response, invalid JSON, or fewer than seven valid unique topics, the next configured model is attempted. If every model fails, the run stops without emailing or updating research history.

Free-tier model availability and quotas can change and are subject to Google's account-specific limits. Google may use free-tier submitted content to improve its products; do not send confidential or proprietary laboratory data.

## One-time setup

### 1. Get API credentials

- Create a Gemini API key in [Google AI Studio](https://aistudio.google.com/app/apikey). Start with the free tier; the fallback models are selected for free-tier availability.
- Create a free OpenAlex account and copy its API key from OpenAlex Settings → API key.
- For the Gmail **sender** account, enable 2-Step Verification and create a Google App Password. Use the App Password, not the normal Gmail password.
- The sender and recipient can be different Gmail addresses.

### 2. Add GitHub repository secrets

Open **Settings → Secrets and variables → Actions → New repository secret** and add:

| Secret | Value |
|---|---|
| `GEMINI_API_KEY` | Your Google AI Studio API key |
| `OPENALEX_API_KEY` | Your OpenAlex API key |
| `SMTP_USER` | Gmail sender address |
| `SMTP_APP_PASSWORD` | Gmail App Password |
| `RECIPIENT_EMAIL` | Destination email address |

The old `OPENAI_API_KEY` secret is no longer used and can be deleted. Never commit API keys, App Passwords, or a real `.env` file.

### 3. Run

The workflow is scheduled for Friday 20:00 WIB. To test it, open **Actions → Weekly Pharmaceutical Research Digest → Run workflow**.

A run will fail clearly if credentials are missing, fewer than seven eligible unseen papers are found, or all configured Gemini models fail. It will not pad the digest with fabricated topics.

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

See `.env.example`. The primary model and ordered fallback models can be changed using `GEMINI_MODEL` and `GEMINI_FALLBACK_MODELS`. The default literature window is 45 days and discovery retrieves up to 50 records per search query before global deduplication and candidate limiting.
