# Detection And Estimates

This prototype uses simple rules so the result is easy to explain in a demo.

## Rework Signals

A source/follow-up pair must first pass two hard checks:

- Same repo.
- Follow-up PR closed after the source PR.

Then it is treated as rework when either:

- The follow-up title or body contains `#rework`.
- Or at least two of these qualifying signals match. File overlap is
  intentionally just one signal among several, not a mandatory prerequisite —
  a pair can qualify on structural/textual evidence alone with zero file
  overlap:
  - Source PR is AI-generated and follow-up PR is not AI-generated within 14
    days.
  - Source and follow-up PRs changed at least one same file path.
  - Follow-up title/body contains rework language like `fix`, `bug`,
    `regression`, `patch`, `cleanup`, `correct`, `restore`, `hotfix`,
    `adjust`, or `broken`.
  - Follow-up title/body contains revert language (`revert`, or GitHub's
    `Revert "..."` title convention).
  - Follow-up title/body explicitly references the source PR's number
    (e.g. `Fixes #41`).
  - Source and follow-up both reference the same other issue/PR number.
  - Source and follow-up PRs both changed a test file at the same path.
  - Source and follow-up PRs both changed a "high-value" file at the same
    path — an API route, a DB migration, a config file, a model/schema
    definition, or a service module (see `classify_file_risk` in
    `features.py`). Overlap here is treated as stronger evidence than
    overlap on an arbitrary utility file, per the proposal.

Candidate matching is a global greedy-by-best-match assignment, not
first-match-in-chronological-order: every valid candidate pair is found
first, then sorted by (override > matched-signal count > smallest time gap)
and assigned greedily. A PR that's a plausible match for several others goes
to its strongest match, not whichever candidate happened to be scanned
first — this matters once a repo has enough PRs that coincidental overlaps
are common.

## Feature Vector

Each generated `ReworkCandidate` also carries a `features` object
(`ReworkFeatures`, see `backend/app/services/rework_detection/features.py`) —
a set of continuous/explainable signals meant to feed an ML classifier,
computed but not persisted to `rework_events`:

- `shared_file_count`, `source_file_overlap_ratio`,
  `followup_file_overlap_ratio` — how much of each PR's changed-file surface
  overlaps with the other.
- `semantic_similarity` — a stdlib-only bag-of-words cosine similarity over
  PR title+body text (0–1). This is an explainable placeholder pending real
  embeddings; no ML/NLP dependency has been added.
- `has_revert_signal`, `has_test_file_overlap`, `has_high_risk_file_overlap`,
  `has_explicit_pr_reference`, `references_same_issue` — the boolean signals
  above, exposed individually.
- `hours_between_merges`, `same_author`, `source_ai_generated` — basic
  temporal/authorship context, computed directly from the two PRs.
- `author_historical_rework_rate` — the source PR's author's track record:
  of their past AI-generated PRs (closed strictly before this one, so no
  looking into the future), what fraction were human-confirmed via
  `disposition` as real rework. Falls back to the team-wide average when the
  author has no reviewed history yet. This is a live, request-time
  computation (`get_author_historical_rework_rate` / `get_global_rework_rate`
  in `queries.py`), not a stored value — it gets more accurate purely from
  accumulated disposition reviews, no code change needed.

This vector can be recomputed on demand for any existing rework event via
`GET /api/rework-events/{id}/features`, without any schema change.

## Deliberately Out Of Scope

Two feature categories from the proposal are intentionally not built, because
neither can be computed from data that exists anywhere in this schema or seed
set today — adding either is a real data-model change, not a rule tweak:

- **Line/diff-level overlap** (e.g. "PR B directly edited 64% of the lines
  PR A introduced"). `pull_request_files` only stores `file_path` plus
  additions/deletions counts — no diff text, no line ranges, no git-blame
  data. This is the strongest signal the proposal describes, and the one
  most worth adding first if the project continues past this scope.
- **CI-failure-after-merge.** There is no CI/pipeline status data anywhere
  in the schema — this would need a new table from scratch, not a column.

Both are scoped out for now rather than half-built, the same way the rest of
this prototype's tradeoffs are already documented in the root `README.md`.

## Demo Defaults

For PRs created through the Add PR Pair modal:

- Source PR is always AI-generated.
- Follow-up PR is always non-AI.
- Source closes at the next safe demo timestamp.
- Follow-up closes exactly one day after the source.
- For each demo PR, `changed_files` is the number of cleaned file paths submitted for that PR.
- In the human-hours estimate, `followup_changed_files` means the follow-up PR's `changed_files`.
- `review_comments` defaults to `6`.
- `commits` defaults to `3`.
- `comments` defaults to `6`.
- `additions` defaults to `240`.
- `deletions` defaults to `60`.

File paths are trimmed, deduped, converted to `/`, and stripped of leading
`./`.

## Human Hours Formula

```text
human_hours =
  1.0
  + followup_changed_files * 0.5
  + overlapping_files * 0.5
  + min(followup_review_comments, 10) * 0.1
```

Example:

```text
follow-up changed files = 3
overlapping files = 2
review comments = 6

1.0 + (3 * 0.5) + (2 * 0.5) + (6 * 0.1) = 4.1 hours
```

## Severity

```text
high:   human_hours >= 6
medium: human_hours >= 3
low:    human_hours < 3
```

## Confidence

```text
high:   #rework override, or at least 3 matched signals
medium: otherwise
```

This is a ranking heuristic, not time tracking or causal proof.

## Reviewer Disposition

Every rework event carries a human-set `disposition`, independent of the
detector's own `severity`/`confidence` output:

- `unreviewed` (default) — no human has looked at it yet.
- `confirmed_rework` — a reviewer agrees this is genuine rework.
- `partial_rework` — some of the follow-up is rework, some is unrelated.
- `related_expected` — a legitimate, expected follow-up (not rework).
- `unrelated` — false positive; the pair should not have been flagged.

Set via `POST /api/ingest/{rework_id}/disposition`. A `disposition` is
preserved across `POST /api/ingest/rework-events/recompute` the same way
`root_cause_label` is — recompute never overwrites a human's review. This is
the ground-truth label a future ML classifier would train against.
