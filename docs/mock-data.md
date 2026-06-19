# Mock Data Notes

The prototype uses local synthetic JSON data, but the shape should stay close to fields that could come from version-control and work-tracking systems.

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
- Mock context artifacts

## Avoid

Do not encode the answer directly in fake fields:

```json
{
  "ai_failed_because": "missing context"
}
```

The system should infer classifications from realistic fields like review comments, labels, summaries, changed files, linked PRs, and context artifacts.

## Rework Taxonomy

Classify rework into:

1. Missed existing pattern or utility
2. Violated architecture decision
3. Missed known edge case
4. Wrong API or dependency assumption
5. Incomplete test or validation path

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

## Productization Note

The JSON source is only for the local prototype. The field choices should make it obvious how the data could later be replaced by GitHub, GitLab, Jira, or Faros-style integrations.
