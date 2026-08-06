# Detection And Estimates

This prototype uses simple rules so the result is easy to explain in a demo.

## Rework Signals

A source/follow-up pair must first pass two hard checks:

- Same repo.
- Follow-up PR closed after the source PR.

Then it is treated as rework when either:

- The follow-up title or body contains `#rework`.
- Or the PRs share at least one changed file and at least two of these signals
  match:
  - Source PR is AI-generated and follow-up PR is not AI-generated within 14
    days.
  - Source and follow-up PRs changed at least one same file path.
  - Follow-up title/body contains rework language like `fix`, `patch`, or
    `restore`.

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
