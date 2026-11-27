"""Register a local challenger artifact in PostgreSQL after offline evaluation."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.database.base import Base  # noqa: E402
from app.database.models import ModelVersion  # noqa: E402
from app.database.session import SessionLocal, engine  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, default=ROOT / "artifacts" / "champion.joblib")
    parser.add_argument("--metrics", type=Path, default=None)
    parser.add_argument("--version", default=None)
    args = parser.parse_args()
    if not args.artifact.exists():
        raise FileNotFoundError(args.artifact)
    metrics_path = args.metrics or args.artifact.with_suffix(".metrics.json")
    metrics_doc = json.loads(metrics_path.read_text()) if metrics_path.exists() else {}
    version = args.version or metrics_doc.get("version") or args.artifact.stem
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        existing = db.query(ModelVersion).filter_by(version=version).first()
        if existing:
            raise SystemExit(f"Version already registered: {version}")
        row = ModelVersion(version=version, artifact_uri=str(args.artifact.resolve()),
                           status="CANDIDATE", metrics=metrics_doc)
        db.add(row)
        db.commit()
        print(f"Registered candidate {version} with id={row.id}. Promotion requires an authorized review.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
