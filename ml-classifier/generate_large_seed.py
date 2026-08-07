"""
Generate a larger, realistic synthetic PR corpus for rework-autopsy.

Replaces the old hand-authored 10-PR seed data with a generated corpus sized
so that real statistical patterns (author history, file-overlap volume) can
actually show up. Every correlation baked in here is grounded in the
"Tier 1 / Tier 2" realism review — no fabricated per-agent or confidence
metadata (that was explicitly dropped as ungrounded).

Unlike the old seed data, rework_events are NOT hand-authored here. This
script only writes teams/repos/pull_requests/pull_request_files. The real
detector (via POST /api/ingest/rework-events/recompute) discovers rework
events from this data using the app's actual code — same as it would for a
real repository. That's the point: nothing about detection is faked, only
the underlying PR history is synthetic.

Ground truth (which follow-ups were *actually* generated as intentional
rework, as opposed to coincidental overlap) is written separately to
data/training/ground_truth_pairs.json — this is NOT app seed data, it exists
purely so a classifier can be trained and evaluated against real labels
later. The app itself never reads this file.

WIRING INTO THE APP — this script writes directly to the app's own seed
files, no adapter needed:
    - Overwrites data/seed/teams.json, repos.json, pull_requests.json,
      pull_request_files.json (the exact files backend/db/seed.py loads).
    - Clears data/seed/rework_events.json and context_artifacts.json to []
      — rework events get discovered fresh by the real detector, not faked.
    - After running this, `backend/db/seed.py` (reset_database) picks up
      the new corpus on the next `./scripts/reset_db.sh` or reseed.

Usage:
    cd ml-classifier
    ../backend/.venv/bin/python generate_large_seed.py --seed 7
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.services.rework_detection.features import classify_file_risk, is_test_file  # noqa: E402

SEED_DIR = REPO_ROOT / "data" / "seed"
TRAINING_DIR = REPO_ROOT / "data" / "training"

# ---------------------------------------------------------------------------
# Vocabulary pools (generic, shared across repos — see realism review: this
# keeps authoring tractable without pretending to bespoke domain expertise
# per repo).
# ---------------------------------------------------------------------------

COMPONENTS = [
    "the checkout flow", "the webhook handler", "the retry worker",
    "the auth middleware", "the notification dispatcher", "the rate limiter",
    "the pagination logic", "the currency conversion step", "the cache layer",
    "the search indexer", "the session store", "the export pipeline",
    "the audit logger", "the feature flag resolver", "the queue consumer",
]

FEATURES = [
    "retry handling", "idempotency keys", "pagination", "rate limiting",
    "webhook signature verification", "currency rounding", "cache invalidation",
    "session expiry", "audit logging", "feature flag rollout", "batch export",
    "queue backpressure", "duplicate detection", "timeout handling",
]

FAILURE_DESCRIPTIONS = [
    "fail silently on malformed input",
    "return stale data after a cache write",
    "throw an unhandled exception under load",
    "drop duplicate events instead of deduping them",
    "time out under concurrent requests",
    "leak a connection on the error path",
    "double-charge on retry",
    "skip validation for an edge case",
    "miss a null check on an optional field",
    "use the wrong timezone when comparing timestamps",
]

REWORK_KEYWORD_TEMPLATES = {
    "fix": ["Fix {failure} in {component}", "Fixes an issue where {component} would {failure}"],
    "bug": ["Bug: {component} would {failure}", "Fix a bug in {component}"],
    "regression": ["Fix regression in {component}", "Address a regression where {component} would {failure}"],
    "cleanup": ["Cleanup pass on {component}", "Cleanup {component} after the earlier change"],
    "correct": ["Correct {component} behavior after the prior update", "Correct handling in {component}"],
    "hotfix": ["Hotfix for {component}", "Hotfix: {component} would {failure}"],
    "adjust": ["Adjust {component} after the earlier change", "Adjust timeout handling in {component}"],
    "broken": ["{component} was broken after the earlier change", "Restore {component} after it broke"],
    "revert": ['Revert "{original_title}"', "Revert problematic change to {component}"],
    "patch": ["Patch {component} for {failure}", "Small patch to {component}"],
    "refactor": ["Refactor {component} to fix {failure}", "Refactor cleanup in {component}"],
    "security": ["Security fix for {component}", "Security patch: {component} would {failure}"],
}

TEAMS = [
    {"id": "team-platform", "name": "Platform Engineering"},
    {"id": "team-payments", "name": "Payments"},
    {"id": "team-data", "name": "Data Infrastructure"},
    {"id": "team-growth", "name": "Growth"},
]

REPOS = [
    {"id": "repo-checkout-service", "name": "checkout-service", "team_id": "team-payments"},
    {"id": "repo-billing-api", "name": "billing-api", "team_id": "team-payments"},
    {"id": "repo-auth-gateway", "name": "auth-gateway", "team_id": "team-platform"},
    {"id": "repo-notification-worker", "name": "notification-worker", "team_id": "team-platform"},
    {"id": "repo-search-indexer", "name": "search-indexer", "team_id": "team-data"},
    {"id": "repo-analytics-pipeline", "name": "analytics-pipeline", "team_id": "team-data"},
    {"id": "repo-user-profile-service", "name": "user-profile-service", "team_id": "team-growth"},
    {"id": "repo-referral-api", "name": "referral-api", "team_id": "team-growth"},
]

FIRST_NAMES = [
    "maya", "alex", "samir", "nina", "lena", "jordan", "priya", "omar",
    "casey", "ravi", "elena", "marcus", "yuki", "diego", "hana", "leo",
    "sofia", "tariq", "ines", "kwame",
]
LAST_NAMES = [
    "chen", "rivera", "patel", "kapoor", "wu", "kim", "singh", "hassan",
    "nakamura", "silva", "novak", "reyes", "okafor", "lindqvist", "tanaka",
]

N_AUTHORS = 32
FILE_CATEGORIES_PER_REPO = {
    "migration": 3,
    "api": 4,
    "config": 2,
    "model": 3,
    "service": 4,
    "generic": 6,
}
FILE_CATEGORY_PATH_TEMPLATES = {
    "migration": "db/migrations/{seq:03d}_{feature_slug}.sql",
    "api": "app/api/routes/{feature_slug}.py",
    "config": "app/config/{feature_slug}.py",
    "model": "app/models/{feature_slug}.py",
    "service": "app/services/{feature_slug}.py",
    "generic": "app/utils/{feature_slug}.py",
}


def slugify(text: str) -> str:
    return text.lower().replace(" ", "_").replace("-", "_")


def build_author_pool(rng: np.random.Generator) -> list[dict]:
    logins = set()
    authors = []
    while len(authors) < N_AUTHORS:
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        login = f"{first}-{last}"
        if login in logins:
            continue
        logins.add(login)
        # Latent, never exposed directly: how likely this author's
        # AI-assisted PRs are to need real rework. Drives generation, not a
        # feature a model would see directly (mirrors the historical-rate
        # design from the sandbox experiment).
        rework_proneness = float(np.clip(rng.normal(0.0, 1.0), -2.5, 2.5))
        authors.append({"login": login, "rework_proneness": rework_proneness})
    return authors


def build_file_pool(rng: np.random.Generator, repo_id: str) -> list[dict]:
    """Each file entry: {path, category, feature_slug}. `category` lets us
    later verify our generated paths actually trip the real classify_file_risk
    / is_test_file functions the way we intend."""
    files = []
    seq = 1
    for category, count in FILE_CATEGORIES_PER_REPO.items():
        for _ in range(count):
            feature = rng.choice(FEATURES)
            feature_slug = slugify(feature) + f"_{seq}"
            path = FILE_CATEGORY_PATH_TEMPLATES[category].format(
                seq=seq, feature_slug=feature_slug
            )
            files.append({"path": path, "category": category, "feature_slug": feature_slug})
            # Give roughly half of non-migration files a paired test file.
            if category != "migration" and rng.random() < 0.6:
                files.append(
                    {
                        "path": f"tests/test_{feature_slug}.py",
                        "category": "test",
                        "feature_slug": feature_slug,
                    }
                )
            seq += 1
    return files


def verify_file_pool(files: list[dict]) -> None:
    """Sanity-check our generated paths against the REAL app functions, so
    the corpus actually exercises the detector the way we intend."""
    for f in files:
        risk = classify_file_risk(f["path"])
        is_test = is_test_file(f["path"])
        if f["category"] == "test":
            assert is_test, f"Expected test path to be classified as test: {f['path']}"
        elif f["category"] == "generic":
            assert risk is None, f"Expected generic path to be non-high-risk: {f['path']}"
        else:
            assert risk == f["category"], (
                f"Path {f['path']} expected risk category {f['category']!r}, got {risk!r}"
            )


def choose_rework_title_body(
    rng: np.random.Generator,
    component: str,
    failure: str,
    original_title: str,
    n_keywords: int = 1,
) -> tuple[str, str, list[str]]:
    primary = str(rng.choice(list(REWORK_KEYWORD_TEMPLATES.keys())))
    # "revert" describes undoing a whole change — semantically incompatible
    # with also describing an unrelated partial fix in the same PR, so it
    # never gets combined with a second keyword.
    if n_keywords > 1 and primary != "revert":
        secondary_pool = [k for k in REWORK_KEYWORD_TEMPLATES if k not in (primary, "revert")]
        extra = rng.choice(secondary_pool, size=n_keywords - 1, replace=False)
        keywords = [primary] + list(extra)
    else:
        keywords = [primary]
    template = rng.choice(REWORK_KEYWORD_TEMPLATES[primary])
    title = template.format(component=component, failure=failure, original_title=original_title)
    title = title[0].upper() + title[1:]

    body_sentences = [
        f"Fixes an issue where {component} would {failure}."
        if primary not in ("revert",)
        else f"Reverts the change to {component} that caused problems in production."
    ]
    for extra_keyword in keywords[1:]:
        body_sentences.append(
            REWORK_KEYWORD_TEMPLATES[extra_keyword][0].format(
                component=component, failure=failure, original_title=original_title
            )
            + "."
        )
    body = " ".join(body_sentences)
    return title, body, keywords


# ---------------------------------------------------------------------------
# Per-repo PR stream generation
# ---------------------------------------------------------------------------

N_PRS_PER_REPO_RANGE = (45, 70)
BASE_REWORK_PROBABILITY = 0.15
HIGH_RISK_TOUCH_BOOST = 0.12
AUTHOR_PRONENESS_SCALE = 0.06


def _new_pr_draft(
    temp_id: str,
    repo_id: str,
    title: str,
    body: str,
    author: str,
    merged_by: str,
    ai_generated: bool,
    created_at: datetime,
    review_hours: float,
    touched_files: list[dict],
) -> dict:
    closed_at = created_at + timedelta(hours=review_hours)
    return {
        "temp_id": temp_id,
        "repo_id": repo_id,
        "title": title,
        "body": body,
        "author_login": author,
        "merged_by_login": merged_by,
        "created_at": created_at,
        "closed_at": closed_at,
        "ai_generated": ai_generated,
        "touched_files": touched_files,
    }


def generate_repo_prs(
    rng: np.random.Generator,
    repo: dict,
    authors: list[dict],
    start_date: datetime,
    ground_truth_pairs: list[dict],
) -> list[dict]:
    file_pool = build_file_pool(rng, repo["id"])
    verify_file_pool(file_pool)
    non_test_files = [f for f in file_pool if f["category"] != "test"]

    n_prs = int(rng.integers(*N_PRS_PER_REPO_RANGE))
    author_by_login = {a["login"]: a for a in authors}
    login_pool = [a["login"] for a in authors]

    drafts: list[dict] = []
    current_time = start_date

    def pick_touched_files(topic_file: dict) -> list[dict]:
        touched = [topic_file]
        # Same-topic test file, often.
        paired_test = next(
            (
                f
                for f in file_pool
                if f["category"] == "test" and f["feature_slug"] == topic_file["feature_slug"]
            ),
            None,
        )
        if paired_test is not None and rng.random() < 0.55:
            touched.append(paired_test)
        # 0-2 extra, mostly unrelated files (multi-file PRs happen).
        n_extra = rng.choice([0, 1, 2], p=[0.55, 0.30, 0.15])
        extras = rng.choice(non_test_files, size=min(n_extra, len(non_test_files)), replace=False)
        for extra in extras:
            if extra["path"] not in {t["path"] for t in touched}:
                touched.append(extra)
        return touched

    for _ in range(n_prs):
        gap_days = float(np.clip(rng.exponential(scale=1.8), 0.1, 20))
        current_time = current_time + timedelta(days=gap_days)

        ai_generated = bool(rng.random() < 0.5)
        author_login = str(rng.choice(login_pool))
        merged_by = str(rng.choice(login_pool))
        topic_file = non_test_files[int(rng.integers(0, len(non_test_files)))]
        touched_files = pick_touched_files(topic_file)

        feature = rng.choice(FEATURES)
        component = rng.choice(COMPONENTS)
        title = f"Add {feature} support to {component}"
        title = title[0].upper() + title[1:]
        body = f"Implements {feature} for {component}."

        review_hours = float(np.clip(rng.gamma(shape=2.0, scale=4.0), 1, 72))
        source_draft = _new_pr_draft(
            temp_id=f"{repo['id']}-{len(drafts)}",
            repo_id=repo["id"],
            title=title,
            body=body,
            author=author_login,
            merged_by=merged_by,
            ai_generated=ai_generated,
            created_at=current_time,
            review_hours=review_hours,
            touched_files=touched_files,
        )
        drafts.append(source_draft)

        if not ai_generated:
            continue

        author = author_by_login[author_login]
        touched_categories = {classify_file_risk(f["path"]) for f in touched_files} - {None}
        rework_p = BASE_REWORK_PROBABILITY
        if touched_categories:
            rework_p += HIGH_RISK_TOUCH_BOOST
        rework_p += AUTHOR_PRONENESS_SCALE * author["rework_proneness"]
        rework_p = float(np.clip(rework_p, 0.02, 0.85))

        if rng.random() >= rework_p:
            continue

        # Genuine rework follow-up.
        gap_followup_days = float(np.clip(rng.exponential(scale=3.0), 0.2, 20))
        followup_created_at = source_draft["closed_at"] + timedelta(days=gap_followup_days)

        followup_author = str(rng.choice([l for l in login_pool if l != author_login] or login_pool))
        failure = rng.choice(FAILURE_DESCRIPTIONS)
        n_keywords = int(rng.choice([1, 2], p=[0.7, 0.3]))
        followup_title, followup_body, _keywords = choose_rework_title_body(
            rng, component=component, failure=failure, original_title=title, n_keywords=n_keywords
        )

        # Follow-up files: overlap with source (favor the high-risk one if present).
        high_risk_touched = [f for f in touched_files if classify_file_risk(f["path"]) is not None]
        overlap_pool = high_risk_touched if high_risk_touched else touched_files
        n_overlap = min(len(overlap_pool), int(rng.integers(1, len(overlap_pool) + 1)))
        followup_files = list(rng.choice(overlap_pool, size=n_overlap, replace=False))
        if rng.random() < 0.3:
            extra = non_test_files[int(rng.integers(0, len(non_test_files)))]
            if extra["path"] not in {f["path"] for f in followup_files}:
                followup_files.append(extra)

        followup_draft = _new_pr_draft(
            temp_id=f"{repo['id']}-{len(drafts)}",
            repo_id=repo["id"],
            title=followup_title,
            body=followup_body,
            author=followup_author,
            merged_by=str(rng.choice(login_pool)),
            ai_generated=False,
            created_at=followup_created_at,
            review_hours=float(np.clip(rng.gamma(shape=1.5, scale=3.0), 1, 48)),
            touched_files=followup_files,
        )

        # Explicit reference and same-issue reference are mutually exclusive
        # per pair, so the two signals stay individually distinguishable.
        reference_roll = rng.random()
        if reference_roll < 0.45:
            followup_draft["explicit_ref_source"] = source_draft["temp_id"]
        elif reference_roll < 0.60:
            shared_issue_number = int(rng.integers(1000, 9999))
            source_draft["body"] += f" Related to #{shared_issue_number}."
            followup_draft["body"] += f" Related to #{shared_issue_number}."

        drafts.append(followup_draft)
        ground_truth_pairs.append(
            {"source_temp_id": source_draft["temp_id"], "followup_temp_id": followup_draft["temp_id"]}
        )

    return drafts


# ---------------------------------------------------------------------------
# Finalization: assign per-repo sequential numbers (sorted by creation time),
# resolve deferred explicit-PR-reference text, assign global integer ids, and
# emit rows matching the app's exact schema/column order.
# ---------------------------------------------------------------------------


def finalize_repo(drafts: list[dict], id_counter_start: int) -> tuple[list[dict], list[dict], int]:
    drafts_sorted = sorted(drafts, key=lambda d: d["created_at"])
    number_by_temp_id = {d["temp_id"]: idx + 1 for idx, d in enumerate(drafts_sorted)}

    for draft in drafts_sorted:
        ref_source_temp_id = draft.pop("explicit_ref_source", None)
        if ref_source_temp_id is not None:
            source_number = number_by_temp_id[ref_source_temp_id]
            draft["body"] += f" Fixes #{source_number}."

    pull_requests: list[dict] = []
    pull_request_files: list[dict] = []
    next_id = id_counter_start

    for draft in drafts_sorted:
        pr_id = next_id
        next_id += 1
        number = number_by_temp_id[draft["temp_id"]]
        additions = int(np.clip(np.random.default_rng(pr_id).gamma(2.0, 60.0), 5, 900))
        deletions = int(additions * np.random.default_rng(pr_id + 1).uniform(0.15, 0.6))

        pull_requests.append(
            {
                "id": pr_id,
                "number": number,
                "repo_id": draft["repo_id"],
                "title": draft["title"],
                "body": draft["body"],
                "state": "closed",
                "draft": 0,
                "created_at": draft["created_at"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                "updated_at": draft["closed_at"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                "closed_at": draft["closed_at"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                "merged_at": draft["closed_at"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                "merged": 1,
                "author_login": draft["author_login"],
                "merged_by_login": draft["merged_by_login"],
                "base_branch": "main",
                "head_branch": f"{draft['author_login']}/pr-{number}",
                "additions": additions,
                "deletions": deletions,
                "changed_files": len(draft["touched_files"]),
                "commits": int(np.clip(np.random.default_rng(pr_id + 2).poisson(3), 1, 15)),
                "comments": int(np.random.default_rng(pr_id + 3).poisson(4)),
                "review_comments": int(np.random.default_rng(pr_id + 4).poisson(5)),
                "ai_generated": 1 if draft["ai_generated"] else 0,
            }
        )
        for file_idx, f in enumerate(draft["touched_files"], start=1):
            pull_request_files.append(
                {
                    "id": f"PRF-{pr_id}-{file_idx:03d}",
                    "pull_request_id": pr_id,
                    "file_path": f["path"],
                    "additions": int(np.random.default_rng(pr_id * 10 + file_idx).integers(2, 80)),
                    "deletions": int(np.random.default_rng(pr_id * 10 + file_idx + 1).integers(0, 40)),
                }
            )

    return pull_requests, pull_request_files, next_id


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    authors = build_author_pool(rng)
    author_by_login = {a["login"]: a for a in authors}

    all_pull_requests: list[dict] = []
    all_pull_request_files: list[dict] = []
    ground_truth_output: list[dict] = []
    next_id = 1
    start_date = datetime(2026, 1, 1)

    for repo in REPOS:
        ground_truth_pairs: list[dict] = []
        drafts = generate_repo_prs(rng, repo, authors, start_date, ground_truth_pairs)
        pull_requests, pull_request_files, next_id = finalize_repo(drafts, next_id)
        all_pull_requests.extend(pull_requests)
        all_pull_request_files.extend(pull_request_files)

        pr_by_temp_id_number = {}
        drafts_sorted = sorted(drafts, key=lambda d: d["created_at"])
        for idx, draft in enumerate(drafts_sorted):
            pr_by_temp_id_number[draft["temp_id"]] = pull_requests[idx]["id"]

        for pair in ground_truth_pairs:
            ground_truth_output.append(
                {
                    "source_pr_id": pr_by_temp_id_number[pair["source_temp_id"]],
                    "followup_pr_id": pr_by_temp_id_number[pair["followup_temp_id"]],
                    "repo_id": repo["id"],
                    "label": 1,
                }
            )

    SEED_DIR.mkdir(parents=True, exist_ok=True)
    TRAINING_DIR.mkdir(parents=True, exist_ok=True)

    (SEED_DIR / "teams.json").write_text(json.dumps(TEAMS, indent=2))
    (SEED_DIR / "repos.json").write_text(json.dumps(REPOS, indent=2))
    (SEED_DIR / "pull_requests.json").write_text(json.dumps(all_pull_requests, indent=2))
    (SEED_DIR / "pull_request_files.json").write_text(json.dumps(all_pull_request_files, indent=2))
    (SEED_DIR / "rework_events.json").write_text(json.dumps([], indent=2))
    (SEED_DIR / "context_artifacts.json").write_text(json.dumps([], indent=2))
    (TRAINING_DIR / "ground_truth_pairs.json").write_text(json.dumps(ground_truth_output, indent=2))
    (TRAINING_DIR / "authors.json").write_text(
        json.dumps([{"login": a["login"]} for a in authors], indent=2)
    )

    print(f"Generated {len(all_pull_requests)} pull requests across {len(REPOS)} repos")
    print(f"Generated {len(all_pull_request_files)} pull_request_files rows")
    print(f"Genuine (ground-truth) rework pairs: {len(ground_truth_output)}")
    print(f"Authors: {len(authors)}")


if __name__ == "__main__":
    main()
