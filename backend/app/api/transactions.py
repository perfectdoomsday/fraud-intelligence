from typing import Annotated
import csv
import io

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import can_ingest, can_read
from app.core.config import settings
from app.database.models import Transaction
from app.database.session import get_db
from app.schemas.transactions import BulkTransactions, PaginatedTransactions, TransactionCreate, TransactionOut
from app.streaming.kafka_producer import publisher

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def ingest_transaction(
    payload: TransactionCreate,
    _user=Depends(can_ingest),
    db: Session = Depends(get_db),
):
    existing = db.query(Transaction).filter(Transaction.transaction_id == payload.transaction_id).first()
    if existing:
        return {"status": "already_received", "transaction_id": payload.transaction_id}
    try:
        publisher.publish(payload.model_dump(mode="json"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Streaming broker unavailable; transaction not accepted") from exc
    return {"status": "queued", "transaction_id": payload.transaction_id}


@router.post("/bulk", status_code=status.HTTP_202_ACCEPTED)
def ingest_bulk(payload: BulkTransactions, _user=Depends(can_ingest)):
    if len(payload.transactions) > settings.max_bulk_transactions:
        raise HTTPException(status_code=413, detail="Bulk upload exceeds configured limit")
    accepted, failed = [], []
    for tx in payload.transactions:
        try:
            publisher.publish(tx.model_dump(mode="json"))
            accepted.append(tx.transaction_id)
        except Exception:
            failed.append(tx.transaction_id)
    return {"accepted": accepted, "failed": failed, "accepted_count": len(accepted), "failed_count": len(failed)}


@router.post("/upload-csv", status_code=status.HTTP_202_ACCEPTED)
async def upload_csv(file: UploadFile = File(...), _user=Depends(can_ingest)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="Upload a .csv file")
    content = await file.read(20 * 1024 * 1024 + 1)
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="CSV upload exceeds 20 MB")
    try:
        reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
        if not reader.fieldnames:
            raise ValueError("CSV must include a header row")
        accepted, rejected = [], []
        for index, row in enumerate(reader, start=2):
            try:
                validated = TransactionCreate.model_validate({key: value for key, value in row.items() if key in TransactionCreate.model_fields})
                publisher.publish(validated.model_dump(mode="json"))
                accepted.append(validated.transaction_id)
            except Exception as exc:
                rejected.append({"row": index, "error": str(exc)[:300]})
        return {"accepted_count": len(accepted), "rejected_count": len(rejected),
                "accepted_transaction_ids": accepted[:50], "rejected_rows": rejected[:100]}
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=PaginatedTransactions)
def list_transactions(
    _user=Depends(can_read), db: Session = Depends(get_db),
    page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200),
    risk: str | None = None, search: str | None = None,
):
    query = db.query(Transaction)
    if risk:
        query = query.filter(Transaction.risk_category == risk.upper())
    if search:
        term = f"%{search}%"
        query = query.filter((Transaction.transaction_id.ilike(term)) | (Transaction.customer_id.ilike(term)) | (Transaction.merchant_id.ilike(term)))
    total = query.count()
    items = query.order_by(Transaction.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/{transaction_id}", response_model=TransactionOut)
def get_transaction(transaction_id: str, _user=Depends(can_read), db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found or still queued")
    return tx
