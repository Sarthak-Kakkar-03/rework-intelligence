import json
from datetime import timedelta
from pathlib import Path

import joblib

from app.api.models import PullRequest, PullRequestFile, ReworkFeatures
from app.services.rework_detection.models import ReworkCandidate
from app.services.rework_detection.estimates import (
    build_summary,
    estimate_confidence,
    estimate_days_after_merge,
    estimate_human_hours_spent,
    estimate_severity,
)
from app.services.rework_detection.features import (
    compute_rework_features,
    has_explicit_pr_reference,
    has_revert_signal,
    high_risk_file_overlap,
    references_same_issue,
    test_file_overlap,
)
from app.services.rework_detection.signals import (
    get_overlapping_files,
    has_followup_rework_language,
    has_rework_override,
    has_same_repo,
    is_ai_to_non_ai_within_14_days,
    is_followup_after_source,
)
from app.queries import (
    get_author_historical_rework_rate,
    get_global_rework_rate,
    get_rework_events,
    get_pull_requests_ordered_by_closed_at,
    get_pull_request_files_by_pr_id,
)

MODEL_REWORK_THRESHOLD = 0.5
MODEL_SOURCE_LOOKBACK_DAYS = 15
DEDUPLICATE_MODEL_CANDIDATES_BY_SOURCE = True


class ReworkDetector:
    def __init__(self):
        artifact_dir = Path(__file__).resolve().parent / "artifacts"
        self.model_path = artifact_dir / "rework_classifier.joblib"
        self.metadata_path = artifact_dir / "metadata.json"
        self.backup_model = "rule_classifier"
        self.model_name = self.backup_model
        self.model = None
        self.feature_order: list[str] = []
        self._load_gradient_boosting_model()

    def _load_gradient_boosting_model(self) -> None:
        if not (self.model_path.exists() and self.metadata_path.exists()):
            return

        try:
            metadata = json.loads(self.metadata_path.read_text())
            feature_order = metadata["feature_order"]
            schema_order = list(ReworkFeatures.model_fields)
            if feature_order != schema_order:
                raise ValueError(
                    "Model feature order does not match ReworkFeatures schema"
                )

            self.model = joblib.load(self.model_path)
            self.feature_order = feature_order
            self.model_name = metadata.get("model_type", "GradientBoostingClassifier")
        except Exception as exc:
            print(
                "Could not load Gradient Boosting classifier, defaulting to "
                f"rule-based classifier: {exc}"
            )
            self.model_name = self.backup_model

    def predict_rework_probability(self, features: ReworkFeatures) -> float:
        if self.model is None:
            return 0.0

        values = features.model_dump()
        row = [[values[feature_name] for feature_name in self.feature_order]]
        return round(float(self.model.predict_proba(row)[0][1]), 4)

    def predict_rework_probabilities(
        self, features: list[ReworkFeatures]
    ) -> list[float]:
        if self.model is None or not features:
            return []

        rows = []
        for feature_row in features:
            values = feature_row.model_dump()
            rows.append([values[feature_name] for feature_name in self.feature_order])

        return [
            round(float(probability), 4)
            for probability in self.model.predict_proba(rows)[:, 1]
        ]

    def is_possible_rework_candidate(
        self, source_pr: PullRequest, followup_pr: PullRequest
    ) -> bool:
        if not (
            has_same_repo(source_pr=source_pr, followup_pr=followup_pr)
            and is_followup_after_source(source_pr=source_pr, followup_pr=followup_pr)
        ):
            return False
        return True

    def is_model_candidate_pair(
        self,
        source_pr: PullRequest,
        followup_pr: PullRequest,
    ) -> bool:
        return has_same_repo(
            source_pr=source_pr, followup_pr=followup_pr
        ) and is_followup_after_source(source_pr=source_pr, followup_pr=followup_pr)

    def is_rework_candidate(
        self,
        source_pr: PullRequest,
        followup_pr: PullRequest,
        source_files: list[PullRequestFile],
        followup_files: list[PullRequestFile],
    ) -> bool:
        if not self.is_possible_rework_candidate(
            source_pr=source_pr, followup_pr=followup_pr
        ):
            return False
        if has_rework_override(followup_pr=followup_pr):
            return True

        # File overlap is intentionally just one of several qualifying signals
        # below (alongside revert language, PR/issue references, and test-file
        # overlap), not a mandatory prerequisite — a pair can still be a rework
        # candidate purely on structural/textual evidence with zero file overlap.
        return (
            len(
                self.get_rework_signals(
                    source_pr=source_pr,
                    followup_pr=followup_pr,
                    source_files=source_files,
                    followup_files=followup_files,
                )
            )
            >= 2
        )

    def get_rework_signals(
        self,
        source_pr: PullRequest,
        followup_pr: PullRequest,
        source_files: list[PullRequestFile],
        followup_files: list[PullRequestFile],
    ) -> list[str]:
        if not self.is_possible_rework_candidate(
            source_pr=source_pr, followup_pr=followup_pr
        ):
            return []
        if has_rework_override(followup_pr=followup_pr):
            return ["Rework Override Indicated"]

        signals = []

        if is_ai_to_non_ai_within_14_days(source_pr=source_pr, followup_pr=followup_pr):
            signals.append("Non AI PR within 2 weeks")
        if get_overlapping_files(
            source_files=source_files, followup_files=followup_files
        ):
            signals.append("Detected Overlapping files")
        if has_followup_rework_language(followup_pr=followup_pr):
            signals.append("Followup has rework language")
        if has_revert_signal(followup_pr):
            signals.append("Followup contains revert language")
        if has_explicit_pr_reference(source_pr=source_pr, followup_pr=followup_pr):
            signals.append("Followup references source PR")
        if references_same_issue(source_pr=source_pr, followup_pr=followup_pr):
            signals.append("Source and followup reference the same issue")
        if test_file_overlap(source_files=source_files, followup_files=followup_files):
            signals.append("Detected overlapping test files")
        if high_risk_file_overlap(
            source_files=source_files, followup_files=followup_files
        ):
            signals.append(
                "Overlapping high-risk file (api/migration/config/model/service)"
            )
        return signals

    def _find_all_candidate_pairs(
        self,
        pr_list: list[PullRequest],
        already_used_pr_ids: set[int],
    ) -> list[dict]:
        """
        Finds every (source, followup) pair that qualifies as a rework
        candidate, without assigning/consuming PRs yet. A PR can appear in
        multiple candidate pairs here — deduplication happens in a separate
        pass so the best match wins, not just the chronologically nearest one.
        """
        files_by_pr_id: dict[int, list[PullRequestFile]] = {}

        def get_files(pr_id: int) -> list[PullRequestFile]:
            if pr_id not in files_by_pr_id:
                files_by_pr_id[pr_id] = get_pull_request_files_by_pr_id(pr_id)
            return files_by_pr_id[pr_id]

        candidates: list[dict] = []
        for followup_idx, followup_pr in enumerate(pr_list):
            if followup_pr.id in already_used_pr_ids:
                continue

            for source_idx in range(followup_idx - 1, -1, -1):
                source_pr = pr_list[source_idx]
                if source_pr.id in already_used_pr_ids:
                    continue
                if not self.is_possible_rework_candidate(
                    source_pr=source_pr, followup_pr=followup_pr
                ):
                    continue

                source_files = get_files(source_pr.id)
                followup_files = get_files(followup_pr.id)
                matched_signals = self.get_rework_signals(
                    source_pr=source_pr,
                    followup_pr=followup_pr,
                    followup_files=followup_files,
                    source_files=source_files,
                )
                if not self.is_rework_candidate(
                    source_pr=source_pr,
                    followup_pr=followup_pr,
                    followup_files=followup_files,
                    source_files=source_files,
                ):
                    continue

                candidates.append(
                    {
                        "source_pr": source_pr,
                        "followup_pr": followup_pr,
                        "source_files": source_files,
                        "followup_files": followup_files,
                        "matched_signals": matched_signals,
                        "is_override": has_rework_override(followup_pr=followup_pr),
                    }
                )

        return candidates

    def _find_all_model_candidate_pairs(
        self,
        pr_list: list[PullRequest],
    ) -> list[dict]:
        """
        Finds ordered same-repo PR pairs for model scoring. The rule detector
        is not used as a gate here; the model decides which pairs become rework.
        """
        files_by_pr_id: dict[int, list[PullRequestFile]] = {}
        source_lookback = timedelta(days=MODEL_SOURCE_LOOKBACK_DAYS)

        def get_files(pr_id: int) -> list[PullRequestFile]:
            if pr_id not in files_by_pr_id:
                files_by_pr_id[pr_id] = get_pull_request_files_by_pr_id(pr_id)
            return files_by_pr_id[pr_id]

        candidates: list[dict] = []
        for followup_idx, followup_pr in enumerate(pr_list):
            for source_idx in range(followup_idx - 1, -1, -1):
                source_pr = pr_list[source_idx]
                if followup_pr.closed_at - source_pr.closed_at > source_lookback:
                    break
                if not self.is_model_candidate_pair(
                    source_pr=source_pr, followup_pr=followup_pr
                ):
                    continue

                source_files = get_files(source_pr.id)
                followup_files = get_files(followup_pr.id)
                candidates.append(
                    {
                        "source_pr": source_pr,
                        "followup_pr": followup_pr,
                        "source_files": source_files,
                        "followup_files": followup_files,
                    }
                )

        return candidates

    @staticmethod
    def _candidate_priority(candidate: dict) -> tuple[int, int, int]:
        # Sorted ascending, so: overrides first, then most matched signals,
        # then the smallest time gap as a tiebreaker (the nearer-in-time match
        # is the safer default when two candidates are otherwise equally strong).
        days_after_merge = estimate_days_after_merge(
            source_pr=candidate["source_pr"], followup_pr=candidate["followup_pr"]
        )
        return (
            0 if candidate["is_override"] else 1,
            -len(candidate["matched_signals"]),
            days_after_merge,
        )

    @staticmethod
    def _deduplicate_model_candidates_by_source(candidates: list[dict]) -> list[dict]:
        used_source_pr_ids: set[int] = set()
        result: list[dict] = []
        for candidate in candidates:
            source_pr = candidate["source_pr"]
            if source_pr.id in used_source_pr_ids:
                continue

            result.append(candidate)
            used_source_pr_ids.add(source_pr.id)

        return result

    def generate_rule_based_rework_candidates(self) -> list[ReworkCandidate]:
        pr_list: list[PullRequest] = get_pull_requests_ordered_by_closed_at()
        used_pr_ids: set[int] = set()
        for rework_event in get_rework_events():
            used_pr_ids.add(rework_event.source_pr_id)
            used_pr_ids.add(rework_event.followup_pr_id)

        candidates = self._find_all_candidate_pairs(pr_list, used_pr_ids)
        # Global greedy-by-best-match assignment: a PR that's a plausible match
        # for several others should go to its STRONGEST match, not whichever
        # candidate happens to be scanned first chronologically.
        candidates.sort(key=self._candidate_priority)

        global_rework_rate = get_global_rework_rate()
        result: list[ReworkCandidate] = []
        for candidate in candidates:
            source_pr = candidate["source_pr"]
            followup_pr = candidate["followup_pr"]
            if source_pr.id in used_pr_ids or followup_pr.id in used_pr_ids:
                continue

            source_files = candidate["source_files"]
            followup_files = candidate["followup_files"]
            matched_signals = candidate["matched_signals"]

            overlapping_files = get_overlapping_files(
                source_files=source_files,
                followup_files=followup_files,
            )
            human_hours_spent = estimate_human_hours_spent(
                followup_pr=followup_pr,
                overlapping_files=overlapping_files,
            )
            author_historical_rework_rate = get_author_historical_rework_rate(
                author_login=source_pr.author_login,
                before=source_pr.closed_at,
                prior=global_rework_rate,
            )
            features = compute_rework_features(
                source_pr=source_pr,
                followup_pr=followup_pr,
                source_files=source_files,
                followup_files=followup_files,
                overlapping_files=overlapping_files,
                author_historical_rework_rate=author_historical_rework_rate,
            )
            result.append(
                ReworkCandidate(
                    source_pr_id=source_pr.id,
                    followup_pr_id=followup_pr.id,
                    repo_id=source_pr.repo_id,
                    days_after_merge=estimate_days_after_merge(
                        source_pr=source_pr,
                        followup_pr=followup_pr,
                    ),
                    overlapping_files=[file.file_path for file in overlapping_files],
                    matched_signals=matched_signals,
                    confidence=estimate_confidence(matched_signals=matched_signals),
                    severity=estimate_severity(human_hours_spent=human_hours_spent),
                    human_hours_spent=human_hours_spent,
                    ml_rework_probability=self.predict_rework_probability(features),
                    root_cause_label="placeholder",
                    features=features,
                    summary=build_summary(
                        source_pr=source_pr,
                        followup_pr=followup_pr,
                        matched_signals=matched_signals,
                    ),
                )
            )
            used_pr_ids.add(source_pr.id)
            used_pr_ids.add(followup_pr.id)

        return result

    def generate_model_based_rework_candidates(self) -> list[ReworkCandidate]:
        pr_list: list[PullRequest] = get_pull_requests_ordered_by_closed_at()

        candidates = self._find_all_model_candidate_pairs(pr_list)
        global_rework_rate = get_global_rework_rate()
        author_rework_rates: dict[tuple[str, object], float] = {}
        scored_candidates = []
        feature_rows = []

        for candidate in candidates:
            source_pr = candidate["source_pr"]
            followup_pr = candidate["followup_pr"]
            source_files = candidate["source_files"]
            followup_files = candidate["followup_files"]
            overlapping_files = get_overlapping_files(
                source_files=source_files,
                followup_files=followup_files,
            )
            author_rate_key = (source_pr.author_login, source_pr.closed_at)
            if author_rate_key not in author_rework_rates:
                author_rework_rates[author_rate_key] = (
                    get_author_historical_rework_rate(
                        author_login=source_pr.author_login,
                        before=source_pr.closed_at,
                        prior=global_rework_rate,
                    )
                )
            features = compute_rework_features(
                source_pr=source_pr,
                followup_pr=followup_pr,
                source_files=source_files,
                followup_files=followup_files,
                overlapping_files=overlapping_files,
                author_historical_rework_rate=author_rework_rates[author_rate_key],
            )
            feature_rows.append(features)
            scored_candidates.append(
                {
                    **candidate,
                    "overlapping_files": overlapping_files,
                    "features": features,
                }
            )

        probabilities = self.predict_rework_probabilities(feature_rows)
        passed_candidates = []
        for candidate, probability in zip(
            scored_candidates, probabilities, strict=True
        ):
            if probability < MODEL_REWORK_THRESHOLD:
                continue

            source_pr = candidate["source_pr"]
            followup_pr = candidate["followup_pr"]
            source_files = candidate["source_files"]
            followup_files = candidate["followup_files"]
            passed_candidates.append(
                {
                    **candidate,
                    "matched_signals": self.get_rework_signals(
                        source_pr=source_pr,
                        followup_pr=followup_pr,
                        source_files=source_files,
                        followup_files=followup_files,
                    ),
                    "ml_rework_probability": probability,
                }
            )

        passed_candidates = sorted(
            passed_candidates,
            key=lambda candidate: (
                -candidate["ml_rework_probability"],
                estimate_days_after_merge(
                    candidate["source_pr"], candidate["followup_pr"]
                ),
            ),
        )

        if DEDUPLICATE_MODEL_CANDIDATES_BY_SOURCE:
            passed_candidates = self._deduplicate_model_candidates_by_source(
                passed_candidates
            )

        result: list[ReworkCandidate] = []
        for candidate in passed_candidates:
            source_pr = candidate["source_pr"]
            followup_pr = candidate["followup_pr"]

            matched_signals = candidate["matched_signals"]
            overlapping_files = candidate["overlapping_files"]
            human_hours_spent = estimate_human_hours_spent(
                followup_pr=followup_pr,
                overlapping_files=overlapping_files,
            )
            result.append(
                ReworkCandidate(
                    source_pr_id=source_pr.id,
                    followup_pr_id=followup_pr.id,
                    repo_id=source_pr.repo_id,
                    days_after_merge=estimate_days_after_merge(
                        source_pr=source_pr,
                        followup_pr=followup_pr,
                    ),
                    overlapping_files=[file.file_path for file in overlapping_files],
                    matched_signals=matched_signals,
                    confidence=estimate_confidence(matched_signals=matched_signals),
                    severity=estimate_severity(human_hours_spent=human_hours_spent),
                    human_hours_spent=human_hours_spent,
                    ml_rework_probability=candidate["ml_rework_probability"],
                    root_cause_label="placeholder",
                    features=candidate["features"],
                    summary=build_summary(
                        source_pr=source_pr,
                        followup_pr=followup_pr,
                        matched_signals=matched_signals,
                    ),
                )
            )

        return result

    def generate_rework_candidates(self) -> list[ReworkCandidate]:
        if self.model is not None:
            return self.generate_model_based_rework_candidates()

        return self.generate_rule_based_rework_candidates()
