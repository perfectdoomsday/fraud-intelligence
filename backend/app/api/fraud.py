from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import can_ingest, can_read
from app.database.session import get_db
from app.schemas.transactions import TransactionCreate
from app.services.transaction_processor import process_transaction

router = APIRouter(prefix="/fraud", tags=["Fraud Detection"])


@router.post("/predict")
def predict(payload: TransactionCreate, _user=Depends(can_ingest), db: Session = Depends(get_db)):
    """Synchronous inference path for testing; production ingestion should use Kafka."""
    try:
        return process_transaction(db, payload.model_dump(mode="python"))
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/risk-distribution")
def risk_distribution_alias(_user=Depends(can_read), db: Session = Depends(get_db)):
    from sqlalchemy import func
    from app.database.models import Transaction
    rows = db.query(Transaction.risk_category, func.count(Transaction.id)).filter(
        Transaction.risk_category.isnot(None)
    ).group_by(Transaction.risk_category).all()
    return [{"category": category, "count": count} for category, count in rows]
