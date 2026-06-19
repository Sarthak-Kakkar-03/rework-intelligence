# Rework Autopsy

Prototype for analyzing AI-assisted PRs and the downstream rework they create.

The goal is to show where agent-written work is causing human follow-up, classify the likely reason, and point to the context source that may need review.

## Structure

```text
backend/                 FastAPI backend, SQLite queries, and rework detection
data/seed/               Local synthetic seed data
frontend-rework-autopsy/ Next.js dashboard
scripts/                 Local helper scripts
```

## Frontend

```bash
cd frontend-rework-autopsy
npm install
npm run dev
```

Useful scripts:

```bash
npm run lint
npm run format
npm run format:check
npm run build
```

## Backend

```bash
./scripts/reset_db.sh
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Rework Detection Rules

The detector compares closed pull requests in each repo and creates at most one
rework event per source PR and at most one rework event per follow-up PR.

A pair must first pass the hard gates:

- Same repo.
- Follow-up PR closed after the source PR.

Then the follow-up is classified as rework when either:

- The follow-up title or body contains `#rework`.
- Or the PRs share at least one changed file and at least two signals match:
  - Source PR is AI-generated and follow-up PR is not AI-generated within 14 days.
  - The PRs have overlapping changed files.
  - Follow-up title or body contains rework language such as `fix`, `patch`, or `restore`.

Negative cases:

- Different repos never match, even if titles or files look related.
- Same-repo PRs with only one weak signal do not match.
- Non-`#rework` pairs without file overlap do not match.

The Add PR Pair demo creates an AI-generated source PR, a non-AI follow-up PR,
and shared file paths. After clicking Compute Rework, that pair should produce a
new rework event.

## MVP Direction

- Local synthetic PR/review/rework data
- Rule-based detection of rework candidates
- Dashboard for top context gaps and estimated rework hours
- Detail view with evidence and suggested context source to review

See [Mock Data Notes](docs/mock-data.md) for the synthetic data shape and classification taxonomy.
