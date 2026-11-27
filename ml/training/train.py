from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (average_precision_score, f1_score, precision_score, recall_score,
                             roc_auc_score, confusion_matrix)

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from app.services.feature_engineering import FEATURE_COLUMNS  # noqa: E402


def temporal_split(df: pd.DataFrame):
    ordered = df.sort_values("timestamp").reset_index(drop=True)
    n = len(ordered)
    return ordered.iloc[: int(n * .7)], ordered.iloc[int(n * .7): int(n * .85)], ordered.iloc[int(n * .85):]


def metrics(y_true, probability):
    pred = (probability >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, pred, labels=[0, 1]).ravel()
    return {
        "precision": float(precision_score(y_true, pred, zero_division=0)),
        "recall": float(recall_score(y_true, pred, zero_division=0)),
        "f1": float(f1_score(y_true, pred, zero_division=0)),
        "pr_auc": float(average_precision_score(y_true, probability)),
        "roc_auc": float(roc_auc_score(y_true, probability)) if len(np.unique(y_true)) > 1 else 0.0,
        "false_positive_rate": float(fp / max(fp + tn, 1)),
        "false_negative_rate": float(fn / max(fn + tp, 1)),
        "fraud_amount_detected": None,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=ROOT / "data" / "synthetic_transactions.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "champion.joblib")
    args = parser.parse_args()
    df = pd.read_csv(args.input)
    train, valid, test = temporal_split(df)
    x_train, y_train = train[FEATURE_COLUMNS].fillna(0), train["label_is_fraud"].astype(int)
    x_valid, y_valid = valid[FEATURE_COLUMNS].fillna(0), valid["label_is_fraud"].astype(int)
    x_test, y_test = test[FEATURE_COLUMNS].fillna(0), test["label_is_fraud"].astype(int)
    candidates = {}
    try:
        from xgboost import XGBClassifier
        started = time.perf_counter()
        xgb = XGBClassifier(n_estimators=350, max_depth=5, learning_rate=0.05,
                            subsample=0.85, colsample_bytree=0.85, reg_lambda=2,
                            eval_metric="aucpr", scale_pos_weight=max(1, (y_train == 0).sum() / max((y_train == 1).sum(), 1)),
                            n_jobs=-1, random_state=42)
        xgb.fit(x_train, y_train)
        candidates["xgboost"] = (xgb, time.perf_counter() - started)
    except ImportError:
        print("xgboost not installed; skipping")
    try:
        from lightgbm import LGBMClassifier
        started = time.perf_counter()
        lgbm = LGBMClassifier(n_estimators=350, learning_rate=0.04, num_leaves=31,
                              class_weight="balanced", verbosity=-1, random_state=42)
        lgbm.fit(x_train, y_train)
        candidates["lightgbm"] = (lgbm, time.perf_counter() - started)
    except ImportError:
        print("lightgbm not installed; skipping")
    if not candidates:
        raise RuntimeError("Install backend/requirements-ml.txt to train XGBoost or LightGBM")

    results = {}
    best_name, best_model, best_ap = None, None, -1
    for name, (model, duration) in candidates.items():
        valid_prob = model.predict_proba(x_valid)[:, 1]
        valid_scores = metrics(y_valid, valid_prob)
        test_prob = model.predict_proba(x_test)[:, 1]
        test_scores = metrics(y_test, test_prob)
        results[name] = {"training_seconds": duration, "validation": valid_scores, "test": test_scores}
        if valid_scores["pr_auc"] > best_ap:
            best_name, best_model, best_ap = name, model, valid_scores["pr_auc"]

    # Fit the winning learner on train + validation only; keep the temporal test untouched.
    x_tv = pd.concat([x_train, x_valid], ignore_index=True)
    y_tv = pd.concat([y_train, y_valid], ignore_index=True)
    best_model.fit(x_tv, y_tv)
    clean = x_tv[y_tv == 0]
    anomaly = IsolationForest(n_estimators=180, contamination=0.02, random_state=42, n_jobs=-1).fit(clean)
    bounds = anomaly.decision_function(clean)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    version = f"{best_name}-temporal-v1"
    joblib.dump({"version": version, "supervised_model": best_model, "anomaly_model": anomaly,
                 "anomaly_bounds": [float(bounds.min()), float(bounds.max())],
                 "feature_columns": FEATURE_COLUMNS, "best_model": best_name}, args.output)
    report = {"selected_model": best_name, "version": version, "metrics": results,
              "split": {"train": len(train), "validation": len(valid), "test": len(test)},
              "warning": "Synthetic dataset metrics are not evidence of real-world fraud performance."}
    report_path = args.output.with_suffix(".metrics.json")
    report_path.write_text(json.dumps(report, indent=2))

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    if tracking_uri:
        try:
            import mlflow
            import mlflow.sklearn
            mlflow.set_tracking_uri(tracking_uri)
            mlflow.set_experiment(os.getenv("MLFLOW_EXPERIMENT_NAME", "fraud-detection"))
            with mlflow.start_run(run_name=version):
                mlflow.log_param("selected_model", best_name)
                mlflow.log_param("temporal_split", "70/15/15")
                mlflow.log_param("training_rows", len(train))
                for candidate_name, candidate_report in results.items():
                    for metric_name, metric_value in candidate_report["validation"].items():
                        if isinstance(metric_value, (float, int)):
                            mlflow.log_metric(f"{candidate_name}_validation_{metric_name}", float(metric_value))
                    for metric_name, metric_value in candidate_report["test"].items():
                        if isinstance(metric_value, (float, int)):
                            mlflow.log_metric(f"{candidate_name}_test_{metric_name}", float(metric_value))
                mlflow.log_artifact(str(report_path))
                mlflow.log_artifact(str(args.output))
        except Exception as exc:
            print(f"MLflow logging skipped: {exc}")

    print(json.dumps(report, indent=2))
    print(f"Saved artifact: {args.output}\nSaved report: {report_path}")


if __name__ == "__main__":
    main()
