# AI Content Pipeline Demo

## Overview
This repository is a **minimal but realistic backend architecture demo** of a scalable content generation and multi-platform publishing pipeline.

The core idea is simple:

- One campaign input (entered by a team in Airtable) can generate **hundreds of localized posts**
- Posts are generated per **website (city + language + domain)** and per **platform**
- Each generated post becomes a **job in a queue**
- A worker processes jobs with **rate limits, retries, and logs**

This is meant to be a **portfolio/demo project** that demonstrates system design thinking (data modeling, orchestration, queue/worker separation), not a production posting system.

## Demo Flow
1. Team enters one campaign in Airtable (simulated by `sample_campaign.json`)
2. Airtable syncs campaign into Supabase (simulated by inserting into SQLite via `sync_airtable.py`)
3. System finds matching websites by service (e.g. *roofing* sites)
4. Content generator creates localized posts per website/platform (3 variations each)
5. Job queue is created (one `post_job` per generated post)
6. Worker processes publishing jobs with retries and logs (simulated publishing)

## Why this architecture works
- **Supabase/Postgres as source of truth**: normalized tables, traceability, and reliable querying for “what happened when”.
- **Airtable as lightweight team input layer**: operations-friendly UI for campaigns; the backend doesn’t depend on Airtable views/automation logic.
- **Worker/queue separation for scalability**: generation and publishing are separate phases; publishing can scale horizontally.
- **Retries + logging for reliability**: transient failures are expected; retries and logs make the system debuggable.
- **Publishing layer is swappable**: later you can replace the simulated publisher with platform APIs or browser automation.

## Airtable -> Supabase sync strategy
- **Airtable is for operations/team input** (campaign briefs, approvals, scheduling fields, checklists).
- **Supabase/Postgres is the source of truth** where you store normalized, queryable records.
- Sync can run via **webhooks or polling**, commonly orchestrated by **n8n** (or a lightweight serverless function).
- Input should be **normalized before insert** (service name normalization, platform normalization, URL validation).
- A single inserted campaign record becomes the **trigger** for content generation (and downstream job creation).

## Localized content generation strategy
- Each website carries context: **service + city + language + domain**
- Generation uses structured “prompt variables” (implemented here as deterministic templates + variation knobs)
- Output must be **unique per city/site/platform**, not “spin” or copy-paste
- Content should feel local: city mentions, tone adjustments, platform style differences
- In production, you’d call an LLM with strict templates, guardrails, and uniqueness controls (plus QA rules)

## Queue + worker system
- Generated posts become `post_jobs`
- Worker processes `pending` jobs, transitions to `processing` and then `success` / `failed`
- Supports:
  - **retries** (up to 3 attempts)
  - **rate limiting** delay between jobs
  - **logs** for success/failure and debugging
  - **failure recovery** (retryable failures return to `pending`)
- Can evolve to:
  - API publishing when platforms support it
  - Playwright/Puppeteer automation when APIs are missing

## Proxy/browser automation note
In real publishing systems:
- **Mobile proxy rotation** can be triggered per batch or per session to reduce platform risk.
- **GoLogin / session persistence** (or similar) can store stable browser profiles per account.

This demo **does not** implement any of those components; it simulates the pipeline so the architecture is clear and reviewable.

## Example input
`sample_campaign.json`:

```json
{
  "service": "roofing",
  "content_idea": "Spring roof inspection",
  "platforms": ["facebook", "instagram", "linkedin"],
  "cta": "Book your spring inspection today",
  "link": "https://example.com/spring-roof-inspection"
}
```

## Example output
Example generated post (German, Berlin, roofing; one variation):

> Hallo Berlin! Jetzt im Frühling ist ein guter Zeitpunkt für eine kurze Dach-Inspektion.  
> Wir schauen uns Dachrinne und typische Schwachstellen an – so lassen sich Folgekosten vermeiden.  
> Kurz anfragen: https://example.com/spring-roof-inspection

Example generated post (Dutch, Amsterdam, roofing; one variation):

> Hoi Amsterdam! Dit voorjaar is perfect voor een snelle dak-check.  
> We kijken o.a. naar dakpannen en bekende zwakke plekken — voorkom onverwachte kosten.  
> Plan je check: https://example.com/spring-roof-inspection

## Run locally
From the repo root:

```bash
python seed_data.py
python sync_airtable.py
python generator.py
python create_jobs.py
python worker.py
```

Worker tuning knobs (optional environment variables):
- `PIPELINE_FAIL_RATE` (default `0.20`)
- `PIPELINE_RATE_DELAY_SEC` (default `0.50`)
- `PIPELINE_MAX_JOBS` (default `0`, no limit)

## Project structure
```text
ai-content-pipeline-demo/
  schema.sql
  sample_campaign.json
  db.py
  utils.py
  seed_data.py
  sync_airtable.py
  generator.py
  create_jobs.py
  worker.py
  requirements.txt
  .gitignore
  README.md
```

## How this maps to a real production build
This demo is intentionally local + lightweight. In a production build you would typically:

- Replace **SQLite** with **Supabase Postgres**
- Replace JSON-based “sync” with **Airtable API + webhooks** (or n8n workflows)
- Replace the simulated generator with **real LLM calls** (OpenAI or similar) + templating + QA validation
- Replace simulated posting with:
  - **platform APIs** where available, and/or
  - **Playwright workers** where APIs do not exist
- Add a **distributed queue** (e.g. Redis/RQ, Celery, SQS) and job monitoring (dashboards, alerts)

## Important note
This repository is an **architecture demo**, not a production publishing system.
It demonstrates the data model and orchestration flow you’d use for **Supabase + Airtable + n8n + worker + publishing** pipelines, while keeping the code minimal and easy to review.

