# Mock Data Notes

This prototype uses local JSON seed data instead of live GitHub, Jira, or Faros
data. The goal is not to make the data look large. The goal is to make the
product loop easy to inspect:

```text
AI-assisted PR
  -> possible follow-up rework
  -> dashboard evidence
  -> human-reviewed root cause
  -> context artifact for future AI coding work
```

## Seed Files

The seed data lives in `data/seed/`.

- `teams.json`: small set of engineering teams.
- `repos.json`: repositories owned by those teams.
- `pull_requests.json`: mocked merged PRs with author, repo, timestamps, review
  counts, changed-file counts, and `ai_generated`.
- `pull_request_files.json`: file paths changed by each PR.
- `rework_events.json`: initial demo rework events that match what recompute
  should produce from the seeded PRs.
- `context_artifacts.json`: human-managed context assets linked to rework
  events.

## What Is Mocked

The PRs, repos, teams, changed files, rework events, and context artifacts are
all synthetic. They are written to resemble fields that could come from real
engineering systems:

- version-control PR metadata
- changed file paths
- review/comment counts
- repo and team ownership
- merged/closed timestamps
- context docs such as runbooks or schema contracts

The data does not contain real source code, real people, or real company
activity.

## What Is Assumed

The prototype assumes a few fields are already available:

- Whether a PR was AI-generated.
- Which repo a PR belongs to.
- When the PR closed or merged.
- Which files changed.
- Whether a follow-up PR title/body contains explicit rework language.

In a production version, those fields could come from GitHub/GitLab, issue
trackers, agentic coding workflow metadata, or a Faros-style normalized data
model.

## Rework Examples

The seeded PRs are intentionally small but cover the important detector cases.

Positive cases include:

- Same repo, AI-generated source PR, non-AI follow-up PR within 14 days,
  overlapping files, and fix language.
- Same repo follow-up with `#rework`, which acts as an explicit override.
- Same repo follow-up outside 14 days that still has overlapping files and
  rework language.

Negative cases include:

- Different repos, even when titles or file names look related.
- Same repo pairs with only one weak signal.
- Non-`#rework` pairs that do not share changed files.

For demo predictability, the detector currently keeps pairing conservative: one
source PR and one follow-up PR should not create repeated duplicate rework
events.

## Context Artifacts

Context artifacts are not generated fixes. They are human-curated knowledge
assets that could help future AI coding agents avoid the same mistake.

Examples:

- Runbooks
- Schema contracts
- Repo conventions
- Deployment notes
- Domain constraints
- Known edge-case documentation

The artifact link does not prove causality by itself. It means a human reviewed
the rework event and decided that this context would be useful before similar
future work.

## What Not To Read Into The Data

- The human-hour estimate is a simple demo heuristic, not time tracking.
- Root cause labels are starting points and can be edited by a human.
- The detector is intentionally rule-based so it is explainable.
- The seed data is small by design; it exists to show the loop, not to benchmark
  model quality.
