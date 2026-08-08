# Rework Intelligence — Project Reference

Single consolidated reference for slides/presentation — everything about the
detection pipeline, the ML classifier, the dataset, and the results in one
place. For deeper narrative detail, see:
- [`detection-and-estimates.md`](detection-and-estimates.md) — the rule engine, in full
- [`../ml-classifier/README.md`](../ml-classifier/README.md) — dataset construction, limitations, wiring instructions
- [`ml-classifier/README.md`](ml-classifier/README.md) — this doc's source figures + raw numbers

## The pipeline, in one picture

```
AI-assisted PR merges
        ↓
Rule-based candidate filter  (cheap, explainable, high recall)
        ↓
ML classifier scores each candidate  (P(rework), 0–1)
        ↓
Human reviewer confirms/rejects via disposition
        ↓
That review becomes training data for the next model refresh
```

## Why rule-based *and* ML, not just one

1. **Scale.** Comparing every PR against every other PR in a repo is expensive, and most pairs are obviously irrelevant (wrong repo, wrong order, months apart). The rule filter is cheap and throws those out before any real computation happens.
2. **Class distribution.** If every pair got passed to the model, the "not rework" class would be dominated by trivially-obvious non-matches that teach the model nothing. Filtering first keeps training data concentrated on the genuinely ambiguous cases where the model's judgment actually matters.
3. **Bootstrapping.** A model needs labeled examples to learn from. The rule-based detector is what generates the *first* candidates for a human to review (via the disposition feature) — those reviews are what eventually train and improve the model. Skip the rules and there's nothing to train on yet.
4. **Explainability.** Every flagged pair shows the human-readable reason it was flagged ("Detected Overlapping files," "Followup references source PR") before a probability score ever enters the picture — a reviewer can sanity-check *why* something surfaced, not just trust a number.

## Stage 1 — Rule-Based Candidate Filter

A pair must pass a hard filter (same repo, follow-up closed after the original), then either carry a manual `#rework` tag or match **at least 2** of the signals below.

| Feature | Description | How we extract it (now / future) | Possible values |
|---|---|---|---|
| Same repo + correct order | Both PRs belong to the same repository, and the follow-up closed after the original | **Now:** direct comparison of `repo_id` and `closed_at` timestamps, both already stored per PR | True/False *(hard filter — if it fails, the pair is discarded immediately)* |
| AI → human within 2 weeks | Original PR was AI-assisted, follow-up wasn't, and they're ≤14 days apart | **Now:** compares each PR's `ai_generated` flag + the time gap between `closed_at` timestamps | True/False |
| File overlap | Both PRs changed at least one of the same file paths | **Now:** exact string match on the list of changed file paths per PR (already stored) | True/False |
| Corrective language | Follow-up's title/body contains words like fix, bug, regression, cleanup, correct, hotfix, adjust, broken, patch | **Now:** regex keyword match over the raw title+body text. **Future:** could move to a trained text classifier instead of a fixed keyword list, to catch phrasing the list misses | True/False |
| Revert language | Follow-up looks like it's undoing the original (contains "revert", or GitHub's `Revert "..."` title format) | **Now:** regex match over title+body | True/False |
| Explicit PR reference | Follow-up literally says something like "Fixes #41" pointing at the original PR's number | **Now:** regex extracts all `#N` references from the text, checks if the original's PR number is among them | True/False |
| Same issue reference | Both PRs reference some *other* shared ticket/issue number (not each other) | **Now:** same `#N` extraction, checks for overlap between the two PRs' reference sets, excluding their own numbers | True/False |
| Test file overlap | Both PRs touched the same test file | **Now:** path-pattern match (`tests/`, `test_*.py`, `*_test.py`) applied to the shared-file set | True/False |
| High-risk file overlap | Both PRs touched the same "risky" file — API route, DB migration, config, data model, or core service | **Now:** path-pattern heuristic (folder/filename conventions like `api/`, `migrations/`, `config/`, `models/`, `services/`). **Future:** could be replaced by a repo-configured explicit list of critical files instead of guessing from naming conventions | True/False |
| Manual `#rework` tag | Someone explicitly tagged the follow-up PR as rework | **Now:** literal `#rework` text match, overrides everything else and auto-qualifies the pair | True/False |

## Stage 2 — ML Model Features

Pairs that pass Stage 1 get scored by the trained classifier on exactly these 13 numbers — nothing else.

| # | Feature | Description | How we extract it (now / future) | Possible values |
|---|---|---|---|---|
| 1 | `shared_file_count` | How many files both PRs touched in common | **Now:** count of exact file-path matches between the two PRs | Integer, 0+ |
| 2 | `source_file_overlap_ratio` | What % of the original PR's files got touched again | **Now:** shared ÷ total files in the original PR | Float, 0.0–1.0 |
| 3 | `followup_file_overlap_ratio` | What % of the follow-up's files were already touched by the original | **Now:** shared ÷ total files in the follow-up PR | Float, 0.0–1.0 |
| 4 | `semantic_similarity` | How similar the two PRs' titles/descriptions sound | **Now:** bag-of-words word-overlap score (no real language understanding). **Future:** swap in real text embeddings for actual semantic meaning, not just shared vocabulary | Float, 0.0–1.0 |
| 5 | `has_revert_signal` | Same as the rule-based revert check above | **Now:** same regex match, reused as a numeric input | True/False |
| 6 | `has_test_file_overlap` | Same as the rule-based test-file check above | **Now:** same path-pattern match, reused | True/False |
| 7 | `has_high_risk_file_overlap` | Same as the rule-based high-risk-file check above | **Now:** same path heuristic, reused | True/False |
| 8 | `has_explicit_pr_reference` | Same as the rule-based explicit-reference check above | **Now:** same `#N` extraction, reused | True/False |
| 9 | `references_same_issue` | Same as the rule-based shared-issue check above | **Now:** same `#N` extraction, reused | True/False |
| 10 | `hours_between_merges` | How much time passed between the two PRs closing | **Now:** direct timestamp subtraction | Float, hours (0+) |
| 11 | `same_author` | Whether the same person wrote both PRs | **Now:** direct string comparison of `author_login` | True/False |
| 12 | `source_ai_generated` | Whether the original PR was AI-assisted | **Now:** direct read of the `ai_generated` flag | True/False |
| 13 | `author_historical_rework_rate` | This author's track record: of their past AI-assisted PRs, what fraction were human-confirmed as real rework | **Now:** computed live, time-ordered (see formula below). **Future:** gets more accurate purely as the team reviews more pairs — no code change needed, just more usage | Float, 0.0–1.0 |

### `author_historical_rework_rate` formula

```
author_historical_rework_rate(author, before_time) =
    confirmed_AI_PRs_by_author_before(before_time)
    ──────────────────────────────────────────────
      total_AI_PRs_by_author_before(before_time)
```

Where:
- `total_AI_PRs_by_author_before(before_time)` = count of this author's PRs where `ai_generated = true` AND `closed_at < before_time` — strictly before, so nothing "in the future" relative to this pair ever leaks in.
- `confirmed_AI_PRs_by_author_before(before_time)` = count of those same PRs that are also the `source_pr_id` of at least one `rework_events` row with `disposition IN (confirmed_rework, partial_rework)`.

**Two-level fallback**, not one: an author with no history yet falls back to the **team-wide rate** (the same ratio computed across every author); the team-wide rate itself only falls back to a hardcoded **`0.1`** in the extreme case where the system has zero AI-generated PRs at all.

## Dataset

| | |
|---|---|
| Pull requests | 484, across 8 repos, 4 teams, 32 synthetic authors |
| AI-generated PRs | 225 |
| Genuine rework pairs (ground truth) | 53 (~23.6% of AI-generated PRs) |
| Candidate pairs considered by the model | 13,952 (same repo, right order, within 90 days) |
| — of those, genuinely real | 53 (0.38%) |
| Train / test split | 9,871 pairs (44 real) / 4,081 pairs (9 real), grouped by source PR |

Built from a causal generation process (not random labels) using the app's *real* `PullRequest`/`PullRequestFile` models — every file path was validated against the real detector logic, not a parallel simulation. Full methodology and honest limitations (templated text, invented author-skill trait, shared vocabulary across repos, no line/diff data) in [`../ml-classifier/README.md`](../ml-classifier/README.md).

## Models trained and results

| Model | ROC-AUC | PR-AUC | Caught in top 100? | Precision | Recall |
|---|---|---|---|---|---|
| Logistic Regression | 0.995 | 0.802 | 8/9 | 0.222 | 0.889 |
| Random Forest | 0.9985 | 0.760 | 9/9 | 0.800 | 0.889 |
| **Gradient Boosting** ✅ deployed | 0.998 | **0.879** | 9/9 | 0.800 | 0.889 |
| MLP (small neural net) | 0.994 | 0.796 | 8/9 | 0.500 | 0.778 |

Gradient Boosting and Random Forest are nearly tied on ROC-AUC; Gradient Boosting wins on **PR-AUC**, the metric that actually matters at this level of class imbalance (ROC-AUC looks deceptively good for all 4 models because the negative class is 99.6% of the data).

![ROC Curve](ml-classifier/roc_curve.png)

![Precision-Recall Curve](ml-classifier/pr_curve.png)

![Confusion Matrix](ml-classifier/confusion_matrix.png)

- True Positives: 8 · False Positives: 2
- False Negatives: 1 · True Negatives: 4,070
- Precision: 0.800 · Recall: 0.889

![Feature Importances](ml-classifier/feature_importance.png)

```
hours_between_merges             0.4158
has_explicit_pr_reference        0.3230
references_same_issue            0.1178
semantic_similarity              0.0606
followup_file_overlap_ratio      0.0421
source_ai_generated              0.0183
source_file_overlap_ratio        0.0136
author_historical_rework_rate    0.0040
shared_file_count                0.0024
has_test_file_overlap            0.0017
has_high_risk_file_overlap       0.0007
has_revert_signal                0.0000
same_author                      0.0000
```

## A real bug fix found along the way

While testing the expanded signal set at realistic repo density, the original candidate-matching algorithm (greedy: assign each PR to the *nearest chronological* match) was found to silently steal genuine pairs — verified on this 484-PR corpus that recall was suppressed to **30%** (16/53 real pairs caught). Replaced with global greedy-by-best-match assignment (find every valid candidate first, sort by override → matched-signal count → smallest time gap, assign greedily) — recall on the same corpus rose to **98%** (52/53). This is a real, independently-verified product improvement, not just classifier work.

## Status: what's shipped vs. what's left

| Piece | Status |
|---|---|
| Reviewer disposition (ground-truth labeling) | Shipped — `feature/reviewer-disposition` |
| Expanded rule signals + feature vector + matching bug fix | Shipped — `feature/rework-feature-extraction` |
| Dataset generation, model training, evaluation, this report | Done — `ml-classifier/` + this doc |
| Classifier wired into the live app (`classifier.py`, `ml_rework_probability`, frontend badge) | **Reference implementation exists, not yet its own clean PR** — see "Wiring it in" in [`../ml-classifier/README.md`](../ml-classifier/README.md) for exactly what's already built and where |
| Root-cause taxonomy (fixed categories instead of free text) | Not started |

## Known limitations (say these out loud, don't let a question catch you off guard)

- PR text is template-generated — believable, not indistinguishable from real engineer writing.
- All 8 synthetic repos share the same made-up vocabulary.
- The author "skill" trait driving rework outcomes is invented; the *mechanism* for learning from it (live historical rate from real disposition reviews) is genuine and would work identically on real data.
- `semantic_similarity` is a stdlib bag-of-words placeholder, not real embeddings.
- No line/diff-level data exists anywhere — deliberately scoped out (see `detection-and-estimates.md`).
- Model was evaluated on 9 held-out positive examples — a small test set, appropriate caution warranted on how tightly to trust the exact decimal precision of these numbers versus the overall pattern they show.
