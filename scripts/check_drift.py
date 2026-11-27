"""Compare reference and current feature windows and persist a drift report."""
import argparse
import json
from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.database.base import Base  # noqa: E402
from app.database.models import DriftReport  # noqa: E402
from app.database.session import SessionLocal, engine  # noqa: E402
from app.services.drift_monitor import compare_feature_frames  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--threshold", type=float, default=0.2)
    args = parser.parse_args()
    reference, current = pd.read_csv(args.reference), pd.read_csv(args.current)
    report = compare_feature_frames(reference, current, args.threshold)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.add(DriftReport(report_id=report["report_id"], drift_detected=report["drift_detected"],
                           drift_share=report["drift_share"], affected_features=report["affected_features"],
                           details=report["details"]))
        db.commit()
    finally:
        db.close()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
