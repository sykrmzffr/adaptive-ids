"""
train.py - cross-validate, train and evaluate the Random Forest.

Run from the project root (after preprocess.py):
    python training/train.py

Output: models/rf_model.joblib, models/model_meta.json,
        eval/offline/*.png, eval/offline/metrics.json
"""
import json
import os
import platform
import subprocess
import time
from datetime import datetime

import joblib
import matplotlib
matplotlib.use("Agg")                      # no screen needed (WSL)
import matplotlib.pyplot as plt
import numpy as np
import sklearn
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (ConfusionMatrixDisplay, PrecisionRecallDisplay,
                             RocCurveDisplay, classification_report,
                             confusion_matrix, roc_auc_score)
from sklearn.model_selection import StratifiedKFold, cross_validate

SEED = 42
CV_SUBSAMPLE = 300_000      # rows used for 5-fold CV (full data x5 is very slow)
OUT = "eval/offline"
os.makedirs(OUT, exist_ok=True)
os.makedirs("models", exist_ok=True)


def make_rf():
    # Parameters from report section 3.5.3
    return RandomForestClassifier(n_estimators=100, criterion="gini",
                                  min_samples_split=2, max_depth=None,
                                  n_jobs=-1, random_state=SEED)


def main():
    d = np.load("data/processed.npz", allow_pickle=False)
    X_tr, y_tr, X_te, y_te = d["X_train"], d["y_train"], d["X_test"], d["y_test"]
    features, classes = list(d["features"]), list(d["classes"])
    binary = len(classes) == 2
    print(f"train {X_tr.shape}, test {X_te.shape}, classes {classes}")

    # ---- 1. 5-fold CV. SMOTE sits INSIDE the pipeline, so each fold is
    #         oversampled from its own training part only (no leakage).
    rng = np.random.default_rng(SEED)
    idx = rng.choice(len(y_tr), size=min(CV_SUBSAMPLE, len(y_tr)), replace=False)
    pipe = Pipeline([("smote", SMOTE(random_state=SEED)), ("rf", make_rf())])
    scoring = ["accuracy", "precision_macro", "recall_macro", "f1_macro"]
    t = time.time()
    cv = cross_validate(pipe, X_tr[idx], y_tr[idx], cv=StratifiedKFold(5, shuffle=True, random_state=SEED),
                        scoring=scoring, return_train_score=True, n_jobs=1)
    cv_summary = {k: [float(np.mean(v)), float(np.std(v))] for k, v in cv.items()
                  if k.startswith(("test_", "train_"))}
    print(f"CV done in {time.time()-t:.0f}s:", json.dumps(cv_summary, indent=1))

    # ---- 2. Final model: SMOTE the full training split, fit once.
    t = time.time()
    X_bal, y_bal = SMOTE(random_state=SEED).fit_resample(X_tr, y_tr)
    print(f"SMOTE: {len(y_tr):,} -> {len(y_bal):,} rows ({time.time()-t:.0f}s)")
    model = make_rf()
    t = time.time()
    model.fit(X_bal, y_bal)
    train_secs = time.time() - t
    print(f"Fit in {train_secs:.0f}s")

    # ---- 3. Evaluate on the untouched test split
    y_pred = model.predict(X_te)
    proba = model.predict_proba(X_te)
    rep = classification_report(y_te, y_pred, target_names=classes, output_dict=True, digits=4)
    print(classification_report(y_te, y_pred, target_names=classes, digits=4))
    cm = confusion_matrix(y_te, y_pred)
    metrics = {"cv_5fold_mean_std": cv_summary, "test_report": rep,
               "confusion_matrix": cm.tolist(), "train_seconds": train_secs}
    if binary:
        metrics["roc_auc"] = float(roc_auc_score(y_te, proba[:, 1]))
        tn, fp, fn, tp = cm.ravel()
        metrics["test_FPR"] = float(fp / (fp + tn))
        metrics["test_detection_rate"] = float(tp / (tp + fn))

    # ---- 4. Figures for Chapter 4
    ConfusionMatrixDisplay(cm, display_labels=classes).plot(values_format="d")
    plt.title("Confusion matrix (test set)"); plt.savefig(f"{OUT}/confusion_matrix.png", dpi=150, bbox_inches="tight"); plt.close()

    imp = model.feature_importances_
    order = np.argsort(imp)
    plt.figure(figsize=(7, 4.5)); plt.barh(np.array(features)[order], imp[order])
    plt.xlabel("Gini importance"); plt.title("Feature importance")
    plt.savefig(f"{OUT}/feature_importance.png", dpi=150, bbox_inches="tight"); plt.close()
    metrics["feature_importance"] = dict(zip(features, map(float, imp)))

    if binary:
        RocCurveDisplay.from_predictions(y_te, proba[:, 1]); plt.title("ROC (test set)")
        plt.savefig(f"{OUT}/roc.png", dpi=150, bbox_inches="tight"); plt.close()
        PrecisionRecallDisplay.from_predictions(y_te, proba[:, 1]); plt.title("Precision-recall (test set)")
        plt.savefig(f"{OUT}/pr.png", dpi=150, bbox_inches="tight"); plt.close()
        # Score histogram - this is what the EMA threshold has to work with
        plt.figure(figsize=(7, 4))
        bins = np.linspace(0, 1, 51)
        plt.hist(proba[y_te == 0, 1], bins=bins, alpha=.7, label="benign", log=True)
        plt.hist(proba[y_te == 1, 1], bins=bins, alpha=.7, label="attack", log=True)
        plt.xlabel("P(attack)"); plt.ylabel("flows (log scale)"); plt.legend()
        plt.savefig(f"{OUT}/score_histogram.png", dpi=150, bbox_inches="tight"); plt.close()
        b = proba[y_te == 0, 1]
        metrics["benign_score_percentiles"] = {p: float(np.percentile(b, p)) for p in (50, 90, 99, 99.9)}

    # ---- 5. Single-flow latency (what the Pi will do). n_jobs=1: with -1,
    #         every single prediction pays thread start-up overhead.
    model.set_params(n_jobs=1)
    one = X_te[:1]
    for _ in range(20): model.predict_proba(one)          # warm-up
    t = time.perf_counter()
    for i in range(500): model.predict_proba(X_te[i:i + 1])
    metrics["laptop_single_flow_ms"] = (time.perf_counter() - t) / 500 * 1000

    # ---- 6. Save model + everything needed to use it correctly later
    joblib.dump(model, "models/rf_model.joblib", compress=3)
    metrics["model_file_mb"] = os.path.getsize("models/rf_model.joblib") / 1e6
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        commit = None
    meta = {"features": features, "classes": classes, "positive_class_index": 1 if binary else None,
            "sklearn_version": sklearn.__version__, "python_version": platform.python_version(),
            "trained_at": datetime.now().isoformat(timespec="seconds"), "git_commit": commit,
            "seed": SEED, "test_accuracy": rep["accuracy"]}
    with open("models/model_meta.json", "w") as fh:
        json.dump(meta, fh, indent=2)
    with open(f"{OUT}/metrics.json", "w") as fh:
        json.dump(metrics, fh, indent=2)
    print(f"Saved. Model {metrics['model_file_mb']:.1f} MB, "
          f"{metrics['laptop_single_flow_ms']:.2f} ms per flow on this machine.")


if __name__ == "__main__":
    main()
