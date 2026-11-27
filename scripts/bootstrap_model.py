"""Train a compact reproducible synthetic demo model if no artifact exists."""
from pathlib import Path
import sys

import joblib
from sklearn.ensemble import IsolationForest, RandomForestClassifier

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))
from scripts.generate_data import generate_transactions  # noqa: E402
from app.services.feature_engineering import FEATURE_COLUMNS  # noqa: E402


def main():
    target = ROOT / "artifacts" / "demo_fraud_model.joblib"
    if target.exists():
        print(f"Demo model already exists: {target}")
        return
    print("Training compact baseline using synthetic data. It is for local demonstration only.")
    df = generate_transactions(n=12000, fraud_rate=0.02, seed=2026)
    x = df[FEATURE_COLUMNS].astype(float)
    y = df["label_is_fraud"].astype(int)
    model = RandomForestClassifier(n_estimators=90, max_depth=10, min_samples_leaf=3,
                                   class_weight="balanced_subsample", n_jobs=-1, random_state=2026)
    model.fit(x, y)
    clean = x[y == 0]
    anomaly = IsolationForest(n_estimators=100, contamination=0.02, random_state=2026, n_jobs=-1)
    anomaly.fit(clean)
    decision = anomaly.decision_function(clean)
    target.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"version": "synthetic-rf-isoforest-v1", "supervised_model": model,
                 "anomaly_model": anomaly,
                 "anomaly_bounds": [float(decision.min()), float(decision.max())],
                 "feature_columns": FEATURE_COLUMNS,
                 "training_data": "synthetic; not validated for real-world use"}, target)
    print(f"Saved demo artifact: {target}")


if __name__ == "__main__":
    main()
