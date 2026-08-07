"""
Train and evaluate a rework classifier on the large synthetic corpus, using
the app's REAL PullRequest/PullRequestFile models and REAL
compute_rework_features — not a parallel simulation.

Candidate universe: every (source, followup) pair in the same repo, followup
closed after source, within a 90-day window (a "configurable time window",
per the proposal's Stage 1 description) — broader than the rule-based
detector's own >=2-signal threshold, so the classifier has real hard
negatives to learn from, not just the pairs the rules already flagged.

Ground truth: data/training/ground_truth_pairs.json, written by
generate_large_seed.py at generation time — these are pairs that were
*intentionally* generated as rework, independent of whatever the rule-based
detector does or doesn't catch.

Author historical rework rate is computed properly here (unlike the earlier
sandbox version): only from that author's AI-generated PRs closed STRICTLY
BEFORE the candidate's source PR, so there's no leakage from the future.

WIRING INTO THE APP — this script IS the spec for what the live app must
have before the trained model is usable:
    - `from app.services.rework_detection.features import
      compute_rework_features` — the app needs this exact function, with
      this exact 13-field ReworkFeatures output, or the model's
      `feature_order` (see train_final_model.py) won't line up.
    - `get_author_historical_rework_rate` / `get_global_rework_rate` here
      are hand-rolled, time-ordered versions of the same queries that must
      exist in `app/queries.py` for live scoring (they read from
      `disposition`, so that column must exist too).
    - Output (`data/training/real_candidate_features.csv`) feeds directly
      into `evaluate_classifier.py` and `train_final_model.py` — run this
      first, always.

Usage:
    cd ml-classifier
    ../backend/.venv/bin/python train_classifier.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.api.models import PullRequest, PullRequestFile  # noqa: E402
from app.services.rework_detection.features import compute_rework_features  # noqa: E402
from app.services.rework_detection.signals import (  # noqa: E402
    get_overlapping_files,
    has_same_repo,
    is_followup_after_source,
)

SEED_DIR = REPO_ROOT / "data" / "seed"
TRAINING_DIR = REPO_ROOT / "data" / "training"
CANDIDATE_WINDOW_DAYS = 90


def load_pull_requests() -> tuple[list[PullRequest], dict[int, list[PullRequestFile]]]:
    pr_rows = json.loads((SEED_DIR / "pull_requests.json").read_text())
    file_rows = json.loads((SEED_DIR / "pull_request_files.json").read_text())

    prs = [PullRequest(**row) for row in pr_rows]
    files_by_pr_id: dict[int, list[PullRequestFile]] = defaultdict(list)
    for row in file_rows:
        files_by_pr_id[row["pull_request_id"]].append(PullRequestFile(**row))

    return prs, files_by_pr_id


def build_author_history_index(prs: list[PullRequest]) -> dict[str, list[tuple]]:
    """
    For each author, a chronological list of (closed_at, was_confirmed_rework)
    for their AI-generated PRs. `was_confirmed_rework` is filled in by the
    caller once ground truth is known — see main().
    """
    by_author: dict[str, list[dict]] = defaultdict(list)
    for pr in prs:
        if pr.ai_generated:
            by_author[pr.author_login].append({"pr_id": pr.id, "closed_at": pr.closed_at, "is_rework": False})
    for entries in by_author.values():
        entries.sort(key=lambda e: e["closed_at"])
    return by_author


def historical_rework_rate(
    author_history: list[dict], before_time, prior: float
) -> float:
    past = [e for e in author_history if e["closed_at"] < before_time]
    if not past:
        return prior
    return sum(1 for e in past if e["is_rework"]) / len(past)


def main() -> None:
    prs, files_by_pr_id = load_pull_requests()
    ground_truth = json.loads((TRAINING_DIR / "ground_truth_pairs.json").read_text())
    ground_truth_set = {(p["source_pr_id"], p["followup_pr_id"]) for p in ground_truth}
    rework_source_ids = {p["source_pr_id"] for p in ground_truth}

    prs_by_repo: dict[str, list[PullRequest]] = defaultdict(list)
    for pr in prs:
        prs_by_repo[pr.repo_id].append(pr)
    for repo_prs in prs_by_repo.values():
        repo_prs.sort(key=lambda p: p.closed_at)

    author_history = build_author_history_index(prs)
    for entries in author_history.values():
        for entry in entries:
            entry["is_rework"] = entry["pr_id"] in rework_source_ids
    overall_prior = len(rework_source_ids) / max(sum(1 for pr in prs if pr.ai_generated), 1)

    rows = []
    window = timedelta(days=CANDIDATE_WINDOW_DAYS)

    for repo_id, repo_prs in prs_by_repo.items():
        n = len(repo_prs)
        for followup_idx in range(n):
            followup_pr = repo_prs[followup_idx]
            for source_idx in range(followup_idx - 1, -1, -1):
                source_pr = repo_prs[source_idx]
                if followup_pr.closed_at - source_pr.closed_at > window:
                    break  # repo_prs is time-sorted, so nothing earlier will be closer
                if not (
                    has_same_repo(source_pr=source_pr, followup_pr=followup_pr)
                    and is_followup_after_source(source_pr=source_pr, followup_pr=followup_pr)
                ):
                    continue

                source_files = files_by_pr_id.get(source_pr.id, [])
                followup_files = files_by_pr_id.get(followup_pr.id, [])
                overlapping_files = get_overlapping_files(
                    source_files=source_files, followup_files=followup_files
                )
                author_hist_rate = historical_rework_rate(
                    author_history.get(source_pr.author_login, []),
                    before_time=source_pr.closed_at,
                    prior=overall_prior,
                )
                features = compute_rework_features(
                    source_pr=source_pr,
                    followup_pr=followup_pr,
                    source_files=source_files,
                    followup_files=followup_files,
                    overlapping_files=overlapping_files,
                    author_historical_rework_rate=author_hist_rate,
                )

                row = features.model_dump()
                row["source_pr_id"] = source_pr.id
                row["followup_pr_id"] = followup_pr.id
                row["is_rework"] = int((source_pr.id, followup_pr.id) in ground_truth_set)
                rows.append(row)

    df = pd.DataFrame(rows)
    out_path = TRAINING_DIR / "real_candidate_features.csv"
    df.to_csv(out_path, index=False)

    print(f"Candidate pairs (within {CANDIDATE_WINDOW_DAYS}-day window): {len(df)}")
    print(f"Positives (genuine rework): {df['is_rework'].sum()}")
    print(f"Negatives: {(df['is_rework'] == 0).sum()}")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
