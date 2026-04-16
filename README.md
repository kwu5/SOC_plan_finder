# SOC Plan Finder

Streamlit app for finding combinations of insurance plans whose total premium falls in a target range.

## Stack

- Streamlit (UI + server)
- Neon or Supabase Postgres (persistence)
- SQLAlchemy 2.x + psycopg

## Local setup

```bash
python -m venv .venv
. .venv/Scripts/activate       # Windows bash
pip install -r requirements.txt

cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edit DATABASE_URL

# apply schema (once)
psql "$DATABASE_URL" -f migrations/001_init.sql

streamlit run app.py
```

## Tests

```bash
pytest
```

## Deploy (Streamlit Community Cloud)

1. Push the repo to GitHub.
2. In Streamlit Cloud, create a new app pointing at `app.py`.
3. In the app's Settings → Secrets, paste the `DATABASE_URL` line.
4. Deploy.

## Search semantics

Given a minimum premium `y` and optional ceiling extension `x` (default 0), the search returns combinations of enabled plans where `y < total_premium <= y + x`, subject to:

- Each provider contributes at most one plan, unless the provider is marked `allow_multiple = true`.
- No pair of plans appears together when an enabled mutual-exclusion rule exists between them.
