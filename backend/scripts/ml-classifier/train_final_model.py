"""
Train the final, deployed Gradient Boosting rework classifier on the FULL
real_candidate_features.csv (produced by train_classifier.py) and save it as
a committed artifact the running app loads at request time.

Gradient Boosting was chosen after evaluate_classifier.py compared it
against logistic regression on the same real, held-out data (0.998 vs 0.995
ROC-AUC, and it caught 9/9 true positives in the top 100 highest-scored
candidates vs logistic regression's 8/9).

Unlike evaluate_classifier.py (which holds out a test split to validate the
approach), this trains on every available labeled row — once you've decided
on a model, there's no reason to withhold real labels from the deployed
artifact.

The feature order is saved alongside the model (metadata.json) so
classifier.py never has to guess or hardcode it separately — it's read from
this file, and this file matches ReworkFeatures' field order by construction
(see train_classifier.py, which builds rows from features.model_dump()).

WIRING INTO THE APP — this script writes directly into the live app's own
package, no copy/paste step needed:
    - Writes `backend/app/services/rework_detection/artifacts/
      rework_classifier.joblib` and `metadata.json` — the exact path
      `classifier.py`'s `predict_rework_probability()` loads from.
    - Re-run this (after re-running train_classifier.py first) whenever the
      underlying seed dataset changes meaningfully — there's no automatic
      retraining pipeline, this is the manual refresh step.
    - Requires `scikit-learn` + `joblib` as real (non-dev) backend
      dependencies, since the running app needs them to load this file, not
      just this training script.

Usage:
    cd backend
    uv run python scripts/ml-classifier/train_final_model.py
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_PATH = REPO_ROOT / "data" / "training" / "real_candidate_features.csv"
ARTIFACT_DIR = (
    REPO_ROOT / "backend" / "app" / "services" / "rework_detection" / "artifacts"
)
MODEL_PATH = ARTIFACT_DIR / "rework_classifier.joblib"
METADATA_PATH = ARTIFACT_DIR / "metadata.json"

NON_FEATURE_COLUMNS = {"source_pr_id", "followup_pr_id", "is_rework"}


def train_GB_model() -> None:
    df = pd.read_csv(DATA_PATH)
    feature_columns = [c for c in df.columns if c not in NON_FEATURE_COLUMNS]

    # .to_numpy() deliberately drops column names before fitting, so the
    # saved model has no feature_names_in_ — inference then feeds it a plain
    # ordered array (matching metadata.json's feature_order) with no sklearn
    # "X does not have valid feature names" warning at request time.
    X = df[feature_columns].to_numpy()
    y = df["is_rework"]

    model = GradientBoostingClassifier(
        n_estimators=200, max_depth=3, learning_rate=0.05, random_state=0
    )
    model.fit(X, y)

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    METADATA_PATH.write_text(
        json.dumps(
            {
                "feature_order": feature_columns,
                "model_type": "GradientBoostingClassifier",
                "trained_on_rows": len(df),
                "trained_on_positives": int(y.sum()),
            },
            indent=2,
        )
    )

    print(f"Trained on {len(df)} rows ({int(y.sum())} positives)")
    print(f"Saved model to {MODEL_PATH}")
    print(f"Saved metadata to {METADATA_PATH}")


if __name__ == "__main__":
    train_GB_model()
