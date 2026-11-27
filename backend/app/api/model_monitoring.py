from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencies import can_manage_models, can_read
from app.core.config import settings
from app.database.models import AuditLog, DriftReport, ModelVersion, Transaction
from app.database.session import get_db

router = APIRouter(tags=["Model Intelligence & Monitoring"])


class PromotionRequest(BaseModel):
    version: str = Field(min_length=1, max_length=100)
    approved: bool
    reason: str = Field(min_length=5, max_length=1000)


@router.get("/models")
def list_models(_user=Depends(can_read), db: Session = Depends(get_db)):
    rows = db.query(ModelVersion).order_by(ModelVersion.created_at.desc()).all()
    return [{"version": row.version, "status": row.status, "artifact_uri": row.artifact_uri,
             "metrics": row.metrics, "created_at": row.created_at} for row in rows]


@router.get("/models/active")
def active_model(_user=Depends(can_read)):
    path = Path(settings.model_artifact_path)
    return {"version": "artifact-present" if path.exists() else "rules-fallback-v1",
            "artifact_available": path.exists(), "artifact_path": str(path),
            "mode": "trained_model" if path.exists() else "transparent_rules_fallback"}


@router.get("/models/performance")
def model_performance(_user=Depends(can_read), db: Session = Depends(get_db)):
    rows = db.query(ModelVersion).order_by(ModelVersion.created_at.desc()).limit(20).all()
    return [{"version": row.version, **(row.metrics or {})} for row in rows]


@router.post("/models/{model_id}/promote")
def promote_model(model_id: str, payload: PromotionRequest, user=Depends(can_manage_models), db: Session = Depends(get_db)):
    candidate = db.query(ModelVersion).filter(ModelVersion.version == payload.version).first()
    if not candidate or candidate.id != int(model_id):
        raise HTTPException(status_code=404, detail="Candidate model version not found")
    if not payload.approved:
        candidate.status = "REJECTED"
    else:
        if not Path(candidate.artifact_uri).exists():
            raise HTTPException(status_code=409, detail="Model artifact does not exist")
        db.query(ModelVersion).filter(ModelVersion.status == "CHAMPION").update({"status": "ARCHIVED"})
        candidate.status = "CHAMPION"
    db.add(AuditLog(actor=user.email, action="MODEL_PROMOTION_DECISION", resource_type="model",
                    resource_id=payload.version, details={"approved": payload.approved, "reason": payload.reason}))
    db.commit()
    return {"version": candidate.version, "status": candidate.status}


@router.get("/monitoring/drift")
def drift_reports(_user=Depends(can_read), db: Session = Depends(get_db)):
    return [{"report_id": row.report_id, "drift_detected": row.drift_detected,
             "drift_share": row.drift_share, "affected_features": row.affected_features,
             "details": row.details, "created_at": row.created_at}
            for row in db.query(DriftReport).order_by(DriftReport.created_at.desc()).limit(100).all()]


@router.get("/monitoring/data-quality")
def data_quality(_user=Depends(can_read), db: Session = Depends(get_db)):
    from sqlalchemy import func
    total = db.query(func.count(Transaction.id)).scalar() or 0
    invalid = db.query(func.count(Transaction.id)).filter_by(processing_status="FAILED").scalar() or 0
    return {"total_transactions": total, "failed_transactions": invalid,
            "invalid_rate": invalid / total if total else 0}
