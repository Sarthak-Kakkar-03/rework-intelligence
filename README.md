# Rework Autopsy

I built Rework Autopsy as a small Faros-style product loop for AI-assisted
engineering work.

The idea came from Faros's context-engineering direction: AI coding agents are
faster when they are given the institutional knowledge that experienced
engineers already carry. Without that context, agents can increase throughput
while also creating review churn, bugs, and follow-up cleanup.

This prototype detects where AI-generated pull requests are followed by likely
human rework, then helps teams manage the context artifacts that should be
injected into AI coding agents before similar future changes.

The product question is:

> Where is AI-assisted work creating rework, why is it happening, and what
> context should an AI coding agent have before generating this kind of PR
> again?

Context artifacts are not auto-generated fixes. They are human-curated inputs
such as runbooks, schema contracts, repo conventions, deployment notes, and
domain constraints.

## Who It Is For

- Engineering managers who want to see where AI-assisted work creates follow-up
  human cost.
- Platform and DevEx teams managing agent context packs.
- Engineers reviewing why an AI-generated PR needed later cleanup.

## Product Loop

```text
PR activity
  -> rule-based rework detection
  -> dashboard and detail page
  -> human labels root cause
  -> human adds or manages context artifacts
  -> future AI coding agents can use those artifacts as context
```

## Structure

```text
backend/                 FastAPI backend, SQLite queries, and rework detection
data/seed/               Local synthetic seed data
docs/                    Notes on mock data and detector assumptions
frontend-rework-autopsy/ Next.js dashboard
scripts/                 Local helper scripts
```

## Run Locally

Demo-ready Docker Compose:

```bash
docker compose up --build
```

Open http://localhost:3000.

The backend container reseeds SQLite on startup so every demo starts from the
same data.

Manual backend/frontend setup:

Start the backend:

```bash
./scripts/reset_db.sh
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Start the frontend in another terminal:

```bash
cd frontend-rework-autopsy
npm install
npm run dev
```

Open http://localhost:3000.

Useful frontend scripts:

```bash
npm run lint
npm run format
npm run format:check
npm run build
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
and editable file paths. Shared file paths are not required, so the demo can
also show negative examples. After clicking Compute Rework, qualifying pairs
produce new rework events.

## What Is Real, Mocked, Or Assumed

- Mocked: PRs, repos, teams, changed files, rework events, and context
  artifacts are seeded from local JSON.
- Real implementation shape: FastAPI routes, SQLite persistence, typed frontend
  calls, a recompute endpoint, and a dashboard/detail workflow.
- Assumed: `ai_generated` is already known on each PR. In a production system
  that could come from GitHub labels, commit metadata, Faros ingestion, or the
  agentic PR workflow itself.
- Assumed: root cause labels are human-editable because this prototype should
  not pretend to infer every causal explanation perfectly.

## What The Prototype Shows

- Summary metrics for total PRs, AI-generated PRs, rework events, estimated
  human hours lost, and context artifacts.
- A rework events table showing source PR, follow-up PR, severity, root cause,
  days after merge, and estimated human hours.
- A detail page where a user can inspect one rework event, edit the root cause,
  and add context artifacts.
- A demo Add PR Pair flow for creating positive or negative examples, then
  recomputing rework.
- Context artifact management for future agent input context, not
  auto-generated recommendations.

## Tradeoffs

- The detector is rule-based and intentionally explainable instead of using an
  opaque model.
- SQLite and seed JSON keep the prototype runnable and inspectable, but they are
  not meant to represent production ingestion scale.
- Human-hour estimates are simple heuristics, useful for ranking and demo
  storytelling rather than precise accounting.
- Context artifacts are created by humans. The system detects where context may
  be missing, but does not invent the artifact content.
- Pairing is conservative: closest valid source and follow-up PRs are selected
  to avoid duplicate demo events.

## What I Would Do With One More Week

- Replace JSON seed data with GitHub API or Faros-style normalized work data.
- Add evidence panels showing exactly which files and language signals matched.
- Add a context-pack view showing which artifacts would be injected for a repo
  or team.
- Add tests around detection edge cases and recompute behavior.
- Add Docker Compose for one-command review.

## How AI Was Used

AI was used as a coding assistant for scaffolding, implementation, review, and
debugging. I still kept the detection rules explicit and inspectable so the
logic can be explained during review.

AI was less helpful when it suggested over-general abstractions, generated
stale wording that implied automatic recommendations, or missed product
constraints like keeping demo examples easy to explain.

## Deliberately Not Built

- Auth, permissions, or multi-tenant concerns.
- Charts.
- Automated context artifact generation.
- A real agentic PR workflow integration.
- Large-scale matching or deduplication beyond the demo rules.

See [Mock Data Notes](docs/mock-data.md) for the synthetic data shape and classification taxonomy.
