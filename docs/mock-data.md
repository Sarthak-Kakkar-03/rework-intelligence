# Mock Data Notes

The prototype uses local synthetic JSON data, but the shape should stay close to
fields that could come from version-control systems, work-tracking systems, or
Faros-style normalized engineering data.

The seed data exists to support one product loop:

```text
AI-generated PR
  -> likely human follow-up rework
  -> root cause review
  -> human-managed context artifact
  -> future AI coding agent context injection
```

## Include

- AI-generated PR metadata
- Follow-up or rework PR metadata
- PR titles and descriptions
- Labels
- Authors and teams
- Created and merged timestamps
- Changed file paths
- Diff summaries, not full source code
- Review comments
- Rework estimate
- Mock context artifacts that represent future agent input context

## Avoid

Do not encode the answer directly in fake fields:

```json
{
  "ai_failed_because": "missing context"
}
```

The system should infer classifications from realistic fields like PR metadata,
titles, summaries, timestamps, changed files, and explicit tags such as
`#rework`.

Context artifacts should not be written as generated fixes. They should look
like knowledge a team would maintain and inject into AI coding agents later:

- Runbooks
- Schema contracts
- Repo conventions
- Deployment notes
- Domain constraints
- Known edge-case documentation

## Rework Taxonomy

Classify rework into:

1. Missed existing pattern or utility
2. Violated architecture decision
3. Missed known edge case
4. Wrong API or dependency assumption
5. Incomplete test or validation path

The current app keeps root cause labels editable because human review is part of
the product loop.

## Detection Rule Coverage

Seed data should cover both positive and negative detector cases.

Positive examples:

- Same repo, AI-generated source PR, non-AI follow-up within 14 days, overlapping files, and fix language.
- Same repo follow-up with `#rework`, which overrides the normal signal threshold.
- Same repo follow-up outside 14 days that still has overlapping files and rework language.

Negative examples:

- Different repo pairs should not produce rework, even with overlapping file names or fix language.
- Same repo pairs with only one weak signal should not produce rework.
- Non-`#rework` pairs without overlapping files should not produce rework.

For demo predictability, the detector currently emits at most one rework event
per source PR and at most one rework event per follow-up PR.

## Context Artifact Meaning

Context artifacts are managed by humans after inspecting rework. They answer:

> What context should an AI coding agent have before attempting this kind of PR
> again?

They are not automatic recommendations, generated patches, or guaranteed root
causes. A context artifact can be useful even when the detector only provides a
probable rework signal.

## Productization Note

The JSON source is only for the local prototype. The field choices should make
it obvious how the data could later be replaced by GitHub, GitLab, Jira,
agentic PR workflow data, or Faros-style integrations.
