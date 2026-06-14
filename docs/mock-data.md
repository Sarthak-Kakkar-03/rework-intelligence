# Mock Data Notes

The prototype uses local synthetic JSON data, but the shape should stay close to fields that could come from version-control and work-tracking systems.

## Include

- AI-assisted PR metadata
- Follow-up or rework PR metadata
- PR titles and descriptions
- Labels
- Authors and teams
- Created and merged timestamps
- Changed file paths
- Diff summaries, not full source code
- Review comments
- Linked tickets
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

## Productization Note

The JSON source is only for the local prototype. The field choices should make it obvious how the data could later be replaced by GitHub, GitLab, Jira, or Faros-style integrations.
