from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.api.dependencies import can_read
from app.database.models import FraudAlert, FraudPrediction, Transaction
from app.database.session import get_db

router = APIRouter(tags=["Analytics"])


@router.get("/analytics/overview")
def overview(_user=Depends(can_read), db: Session = Depends(get_db)):
    total = db.query(func.count(Transaction.id)).scalar() or 0
    processed = db.query(func.count(Transaction.id)).filter(Transaction.processing_status == "PROCESSED").scalar() or 0
    flagged = db.query(func.count(Transaction.id)).filter(Transaction.risk_category.in_(["HIGH", "CRITICAL"])).scalar() or 0
    critical = db.query(func.count(FraudAlert.id)).filter(FraudAlert.severity == "CRITICAL", FraudAlert.status.notin_(["CLOSED", "FALSE_POSITIVE"])).scalar() or 0
    active_alerts = db.query(func.count(FraudAlert.id)).filter(FraudAlert.status.notin_(["CLOSED", "FALSE_POSITIVE"])).scalar() or 0
    suspected_amount = db.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(Transaction.risk_category.in_(["HIGH", "CRITICAL"])).scalar() or 0
    confirmed = db.query(func.count(FraudAlert.id)).filter(FraudAlert.status == "CONFIRMED_FRAUD").scalar() or 0
    avg_risk = db.query(func.avg(Transaction.risk_score)).filter(Transaction.risk_score.isnot(None)).scalar() or 0
    return {
        "total_transactions": total,
        "processed_transactions": processed,
        "flagged_transactions": flagged,
        "active_alerts": active_alerts,
        "critical_alerts": critical,
        "confirmed_fraud_cases": confirmed,
        "suspected_fraud_amount": round(float(suspected_amount), 2),
        "average_risk_score": round(float(avg_risk), 2),
        "estimated_loss_prevented": None,
        "estimated_loss_prevented_note": "Not calculated: prevented loss requires an independently validated counterfactual.",
        "detection_rate": round(flagged / processed, 4) if processed else 0,
        "data_mode": "synthetic_demo_or_user_supplied",
    }


@router.get("/analytics/risk-distribution")
def risk_distribution(_user=Depends(can_read), db: Session = Depends(get_db)):
    rows = db.query(Transaction.risk_category, func.count(Transaction.id)).filter(Transaction.risk_category.isnot(None)).group_by(Transaction.risk_category).all()
    return [{"category": category, "count": count} for category, count in rows]


@router.get("/analytics/trends")
def trends(_user=Depends(can_read), db: Session = Depends(get_db), days: int = 7):
    days = min(max(days, 1), 90)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = db.query(func.date(Transaction.created_at), func.count(Transaction.id),
                    func.sum(case((Transaction.risk_category.in_(["HIGH", "CRITICAL"]), 1), else_=0))) \
        .filter(Transaction.created_at >= since).group_by(func.date(Transaction.created_at)).order_by(func.date(Transaction.created_at)).all()
    return [{"date": str(day), "transactions": count, "flagged": flagged or 0} for day, count, flagged in rows]


@router.get("/fraud/predictions")
def predictions(_user=Depends(can_read), db: Session = Depends(get_db), limit: int = 100):
    rows = db.query(FraudPrediction).order_by(FraudPrediction.created_at.desc()).limit(min(max(limit, 1), 500)).all()
    return [{"transaction_id": row.transaction_id, "fraud_probability": row.fraud_probability,
             "anomaly_score": row.anomaly_score, "risk_score": row.risk_score,
             "risk_category": row.risk_category, "decision": row.decision,
             "model_version": row.model_version, "created_at": row.created_at} for row in rows]
