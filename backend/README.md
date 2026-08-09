# Rework Autopsy Backend

FastAPI backend for the Rework Autopsy prototype.

It stores synthetic engineering data in SQLite, exposes dashboard APIs, and runs
the Gradient Boosting rework detector with rule-based fallback.

## Run

From the repo root:

```bash
cd backend
uv sync
cd ..
PYTHON_CMD="uv run python" UVICORN_CMD="uv run uvicorn" ./scripts/start_backend.sh
```

The startup script resets SQLite, rebuilds
`data/training/real_candidate_features.csv`, regenerates
`app/services/rework_detection/artifacts/rework_classifier.joblib`, and then
starts Uvicorn.

## Main Responsibilities

- Load local seed data into SQLite.
- Reuse `scripts/start_backend.sh` for demo startup in Docker and local dev.
- Serve pull requests, repos, rework events, context artifacts, and summary
  metrics.
- Recompute likely rework events from PR metadata and changed files.
- Accept demo PR pairs and their changed files.
- Store human-managed context artifacts that can later be used as AI agent input
  context.

## Product Boundary

The backend detects likely rework and stores human-curated context artifacts. It
does not auto-generate fixes or artifact content.
