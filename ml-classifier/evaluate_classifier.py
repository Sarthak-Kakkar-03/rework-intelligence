"""
Train and evaluate the rework classifier on the real extracted feature set
(data/training/real_candidate_features.csv, produced by train_classifier.py).

The candidate universe is heavily imbalanced (53 positives out of ~14k
pairs, ~0.4%) — this is what a real same-repo/90-day candidate net actually
looks like, not the artificially-balanced sandbox dataset. Plain accuracy is
meaningless here (predicting "never rework" scores >99%); we report
ROC-AUC, average precision (PR-AUC), and precision/recall/F1 at a threshold
tuned for reasonable recall.

Split is grouped by source_pr_id so every candidate row for a given source
PR lands entirely in train or entirely in test — a naive random row split
would leak information across the split, since one source PR appears in
many (mostly-negative) candidate rows.

WIRING INTO THE APP — this script doesn't touch the app at all; it's purely
for deciding *which model* to deploy. Once you're happy with the comparison,
`train_final_model.py` is the one that actually produces the artifact the
app loads. For presentation-ready figures (ROC/PR curves, confusion matrix,
feature importances) instead of terminal text, use `generate_report.py`
instead — it runs the same comparison but saves images + a markdown report
to `docs/ml-classifier/`.

Usage:
    cd ml-classifier
    ../backend/.venv/bin/python evaluate_classifier.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = REPO_ROOT / "data" / "training" / "real_candidate_features.csv"

NON_FEATURE_COLUMNS = {"source_pr_id", "followup_pr_id", "is_rework"}


def load_data() -> tuple[pd.DataFrame, pd.Series, np.ndarray]:
    df = pd.read_csv(DATA_PATH)
    feature_cols = [c for c in df.columns if c not in NON_FEATURE_COLUMNS]
    return df[feature_cols], df["is_rework"], df["source_pr_id"].to_numpy()


def evaluate(name: str, model, X_train, X_test, y_train, y_test) -> None:
    model.fit(X_train, y_train)
    proba = model.predict_proba(X_test)[:, 1]

    # A fixed 0.5 threshold is meaningless at this class imbalance (positive
    # priors are ~0.4%); use the top-N-by-score approach a real reviewer
    # would actually face — how many of the true positives show up in the
    # top 100 flagged pairs.
    top_n = 100
    top_indices = np.argsort(-proba)[:top_n]
    positives_in_top_n = int(y_test.to_numpy()[top_indices].sum())
    total_positives = int(y_test.sum())

    print(f"\n=== {name} ===")
    print("ROC-AUC:", round(roc_auc_score(y_test, proba), 4))
    print("Average Precision (PR-AUC):", round(average_precision_score(y_test, proba), 4))
    print(f"Of the top {top_n} highest-scored pairs: {positives_in_top_n}/{total_positives} true positives captured")
    print(classification_report(y_test, (proba >= 0.5).astype(int), digits=3, zero_division=0))


def main() -> None:
    X, y, groups = load_data()

    splitter = GroupShuffleSplit(n_splits=1, test_size=0.3, random_state=0)
    train_idx, test_idx = next(splitter.split(X, y, groups=groups))
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

    print(f"Train: {len(X_train)} rows, {y_train.sum()} positives")
    print(f"Test:  {len(X_test)} rows, {y_test.sum()} positives")

    evaluate(
        "Logistic Regression (class_weight=balanced)",
        Pipeline(
            [
                ("scale", StandardScaler()),
                ("clf", LogisticRegression(max_iter=2000, class_weight="balanced")),
            ]
        ),
        X_train, X_test, y_train, y_test,
    )

    evaluate(
        "Random Forest (class_weight=balanced)",
        RandomForestClassifier(n_estimators=200, class_weight="balanced", random_state=0),
        X_train, X_test, y_train, y_test,
    )

    evaluate(
        "Gradient Boosting",
        GradientBoostingClassifier(n_estimators=200, max_depth=3, learning_rate=0.05, random_state=0),
        X_train, X_test, y_train, y_test,
    )

    evaluate(
        "MLP (small feedforward net)",
        Pipeline(
            [
                ("scale", StandardScaler()),
                (
                    "clf",
                    MLPClassifier(
                        hidden_layer_sizes=(32, 16),
                        activation="relu",
                        max_iter=2000,
                        random_state=0,
                    ),
                ),
            ]
        ),
        X_train, X_test, y_train, y_test,
    )

    gb = GradientBoostingClassifier(n_estimators=200, max_depth=3, learning_rate=0.05, random_state=0)
    gb.fit(X_train, y_train)
    importances = pd.Series(gb.feature_importances_, index=X.columns).sort_values(ascending=False)
    print("\n=== Gradient Boosting feature importances ===")
    print(importances.to_string())


if __name__ == "__main__":
    main()
