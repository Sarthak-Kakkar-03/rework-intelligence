"""
Generates presentation-ready figures (ROC curve, precision-recall curve,
confusion matrix, feature importances) and a markdown results report from
the real extracted feature dataset (data/training/real_candidate_features.csv).

Writes everything to docs/ml-classifier/ in the repo root — separate from
this folder, since docs/ is where the rest of the project's write-ups live
(docs/detection-and-estimates.md, docs/mock-data.md).

This is a reporting script, not part of the training pipeline — run it
after train_classifier.py has produced real_candidate_features.csv. It
re-trains all 4 models on the same grouped split evaluate_classifier.py
uses, purely to plot them; it doesn't touch the deployed model artifact.

Usage:
    cd backend
    uv run python scripts/ml-classifier/generate_report.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")  # headless, no display needed
import matplotlib.pyplot as plt

from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    RocCurveDisplay,
    PrecisionRecallDisplay,
    average_precision_score,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_PATH = REPO_ROOT / "data" / "training" / "real_candidate_features.csv"
OUT_DIR = REPO_ROOT / "docs" / "ml-classifier"

NON_FEATURE_COLUMNS = {"source_pr_id", "followup_pr_id", "is_rework"}
MODEL_COLORS = {
    "Logistic Regression": "#8899aa",
    "Random Forest": "#e0a72a",
    "Gradient Boosting": "#d64545",
    "MLP": "#4a7fd6",
}


def load_data() -> tuple[pd.DataFrame, pd.Series, np.ndarray]:
    df = pd.read_csv(DATA_PATH)
    feature_cols = [c for c in df.columns if c not in NON_FEATURE_COLUMNS]
    return df[feature_cols], df["is_rework"], df["source_pr_id"].to_numpy()


def build_models(seed: int) -> dict[str, object]:
    return {
        "Logistic Regression": Pipeline(
            [
                ("scale", StandardScaler()),
                ("clf", LogisticRegression(max_iter=2000, class_weight="balanced")),
            ]
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=200, class_weight="balanced", random_state=seed
        ),
        "Gradient Boosting": GradientBoostingClassifier(
            n_estimators=200, max_depth=3, learning_rate=0.05, random_state=seed
        ),
        "MLP": Pipeline(
            [
                ("scale", StandardScaler()),
                (
                    "clf",
                    MLPClassifier(
                        hidden_layer_sizes=(32, 16),
                        activation="relu",
                        max_iter=2000,
                        random_state=seed,
                    ),
                ),
            ]
        ),
    }


def plot_roc_curves(models: dict, X_test, y_test, out_path: Path) -> dict[str, float]:
    fig, ax = plt.subplots(figsize=(6, 6))
    aucs: dict[str, float] = {}
    for name, model in models.items():
        proba = model.predict_proba(X_test)[:, 1]
        aucs[name] = roc_auc_score(y_test, proba)
        RocCurveDisplay.from_predictions(
            y_test,
            proba,
            name=name,
            ax=ax,
            curve_kwargs={"color": MODEL_COLORS[name], "linewidth": 2},
        )
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", linewidth=1, label="Chance")
    ax.set_title("ROC Curve — all 4 models, real held-out test set")
    ax.legend(loc="lower right", fontsize=9)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return aucs


def plot_pr_curves(models: dict, X_test, y_test, out_path: Path) -> dict[str, float]:
    fig, ax = plt.subplots(figsize=(6, 6))
    ap_scores: dict[str, float] = {}
    for name, model in models.items():
        proba = model.predict_proba(X_test)[:, 1]
        ap_scores[name] = average_precision_score(y_test, proba)
        PrecisionRecallDisplay.from_predictions(
            y_test,
            proba,
            name=name,
            ax=ax,
            curve_kwargs={"color": MODEL_COLORS[name], "linewidth": 2},
        )
    baseline = y_test.mean()
    ax.axhline(
        baseline,
        linestyle="--",
        color="gray",
        linewidth=1,
        label=f"Baseline ({baseline:.4f})",
    )
    ax.set_title(
        "Precision-Recall Curve — real held-out test set\n(the metric that matters most at this class imbalance)"
    )
    ax.legend(loc="upper right", fontsize=9)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return ap_scores


def plot_confusion_matrix(model, X_test, y_test, out_path: Path) -> np.ndarray:
    preds = model.predict(X_test)
    cm = confusion_matrix(y_test, preds)
    fig, ax = plt.subplots(figsize=(5, 5))
    ConfusionMatrixDisplay(cm, display_labels=["Not Rework", "Rework"]).plot(
        ax=ax, cmap="Reds", colorbar=False
    )
    ax.set_title(
        "Gradient Boosting — Confusion Matrix\n(deployed model, 0.5 threshold, real test set)"
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return cm


def plot_feature_importances(model, feature_names, out_path: Path) -> pd.Series:
    importances = pd.Series(
        model.feature_importances_, index=feature_names
    ).sort_values()
    fig, ax = plt.subplots(figsize=(7, 5))
    importances.plot.barh(ax=ax, color="#d64545")
    ax.set_title("Gradient Boosting — Feature Importances")
    ax.set_xlabel("Importance")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return importances.sort_values(ascending=False)


def write_report(
    out_dir: Path,
    n_total: int,
    n_train: int,
    n_train_pos: int,
    n_test: int,
    n_test_pos: int,
    roc_aucs: dict[str, float],
    ap_scores: dict[str, float],
    cm: np.ndarray,
    importances: pd.Series,
) -> None:
    tn, fp, fn, tp = cm.ravel()
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0

    lines = [
        "# ML Rework Classifier — Results Report",
        "",
        "Generated by `backend/scripts/ml-classifier/generate_report.py`. See",
        "`backend/scripts/ml-classifier/README.md` for the full write-up (dataset construction,",
        "wiring instructions, limitations) — this doc is the presentation-ready",
        "figures and numbers only.",
        "",
        "## Dataset",
        "",
        f"- {n_total:,} total candidate pairs (same repo, correct order, within a 90-day window)",
        f"- Train: {n_train:,} pairs ({n_train_pos} genuine rework)",
        f"- Test (held out, never seen during training): {n_test:,} pairs ({n_test_pos} genuine rework)",
        "",
        "## Model Comparison",
        "",
        "| Model | ROC-AUC | PR-AUC (Average Precision) |",
        "|---|---|---|",
    ]
    for name in roc_aucs:
        marker = " ✅ deployed" if name == "Gradient Boosting" else ""
        lines.append(
            f"| {name}{marker} | {roc_aucs[name]:.4f} | {ap_scores[name]:.4f} |"
        )

    lines += [
        "",
        "![ROC Curve](roc_curve.png)",
        "",
        "![Precision-Recall Curve](pr_curve.png)",
        "",
        "PR-AUC is the more informative metric here — ROC-AUC looks deceptively",
        "good for all 4 models because the negative class is 99.6% of the data;",
        "PR-AUC is what actually distinguishes how well each model ranks the rare",
        "positive class, which is why it's the deciding metric for choosing",
        "Gradient Boosting.",
        "",
        "## Confusion Matrix (Gradient Boosting, deployed model)",
        "",
        "![Confusion Matrix](confusion_matrix.png)",
        "",
        f"- True Positives: {tp}  ·  False Positives: {fp}",
        f"- False Negatives: {fn}  ·  True Negatives: {tn}",
        f"- Precision: {precision:.3f}  ·  Recall: {recall:.3f}",
        "",
        "## Feature Importances (Gradient Boosting)",
        "",
        "![Feature Importances](feature_importance.png)",
        "",
        "```",
    ]
    for name, value in importances.items():
        lines.append(f"{name:<32} {value:.4f}")
    lines.append("```")

    (out_dir / "README.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    X, y, groups = load_data()
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.3, random_state=0)
    train_idx, test_idx = next(splitter.split(X, y, groups=groups))
    X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

    models = build_models(seed=0)
    for model in models.values():
        model.fit(X_train, y_train)

    roc_aucs = plot_roc_curves(models, X_test, y_test, OUT_DIR / "roc_curve.png")
    ap_scores = plot_pr_curves(models, X_test, y_test, OUT_DIR / "pr_curve.png")

    gb = models["Gradient Boosting"]
    cm = plot_confusion_matrix(gb, X_test, y_test, OUT_DIR / "confusion_matrix.png")
    importances = plot_feature_importances(
        gb, X.columns, OUT_DIR / "feature_importance.png"
    )

    write_report(
        OUT_DIR,
        n_total=len(X),
        n_train=len(X_train),
        n_train_pos=int(y_train.sum()),
        n_test=len(X_test),
        n_test_pos=int(y_test.sum()),
        roc_aucs=roc_aucs,
        ap_scores=ap_scores,
        cm=cm,
        importances=importances,
    )

    print(f"Wrote figures and report to {OUT_DIR}")
    for name in roc_aucs:
        print(f"  {name}: ROC-AUC={roc_aucs[name]:.4f}  PR-AUC={ap_scores[name]:.4f}")


if __name__ == "__main__":
    main()
