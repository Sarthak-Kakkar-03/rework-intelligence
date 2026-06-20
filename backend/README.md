# Rework Autopsy Backend

FastAPI backend for the Rework Autopsy prototype.

It stores synthetic engineering data in SQLite, exposes dashboard APIs, and runs
the rule-based rework detector.

## Run

From the repo root:

```bash
./scripts/reset_db.sh
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Main Responsibilities

- Load local seed data into SQLite.
- Reuse `scripts/reset_db.sh` for demo startup in Docker.
- Serve pull requests, repos, rework events, context artifacts, and summary
  metrics.
- Recompute likely rework events from PR metadata and changed files.
- Accept demo PR pairs and their changed files.
- Store human-managed context artifacts that can later be used as AI agent input
  context.

## Product Boundary

The backend detects likely rework and stores human-curated context artifacts. It
does not auto-generate fixes or artifact content.
