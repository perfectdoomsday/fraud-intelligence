from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from fastapi.responses import Response
import asyncio
import socket
from sqlalchemy import text
from app.core.config import settings
from app.database.session import engine

from app.database.models import Transaction
from app.database.session import SessionLocal

router = APIRouter(tags=["System"])


@router.get("/health")
def health():
    return {"status": "ok", "service": "fraud-intelligence-api"}


@router.get("/metrics")
@router.get("/monitoring/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/monitoring/system")
def system_health():
    components = {"api": "healthy"}
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        components["postgresql"] = "healthy"
    except Exception:
        components["postgresql"] = "unavailable"
    try:
        import redis
        redis.Redis.from_url(settings.redis_url, socket_timeout=1).ping()
        components["redis"] = "healthy"
    except Exception:
        components["redis"] = "unavailable_or_using_local_fallback"
    components["kafka"] = "reachable" if _tcp_reachable(settings.kafka_bootstrap_servers.split(",")[0]) else "unavailable"
    return {"components": components, "overall": "healthy" if all(v in {"healthy", "reachable", "unavailable_or_using_local_fallback"} for v in components.values()) else "degraded"}


def _tcp_reachable(address: str) -> bool:
    try:
        host, port = address.rsplit(":", 1)
        with socket.create_connection((host, int(port)), timeout=0.8):
            return True
    except Exception:
        return False


@router.websocket("/ws/transactions")
async def transaction_stream(websocket: WebSocket):
    # Dashboard transport only. Authenticate websocket with a token in production deployments.
    await websocket.accept()
    db = SessionLocal()
    try:
        last_id = db.query(Transaction.id).order_by(Transaction.id.desc()).limit(1).scalar() or 0
    finally:
        db.close()
    try:
        while True:
            await asyncio.sleep(1.5)
            db = SessionLocal()
            try:
                rows = db.query(Transaction).filter(Transaction.id > last_id).order_by(Transaction.id.asc()).limit(100).all()
                messages = [{"transaction_id": row.transaction_id, "customer_id": row.customer_id,
                             "amount": row.amount, "currency": row.currency, "risk_score": row.risk_score,
                             "risk_category": row.risk_category, "decision": row.decision,
                             "processing_status": row.processing_status, "timestamp": row.timestamp.isoformat()}
                            for row in rows]
                if rows:
                    last_id = rows[-1].id
            finally:
                db.close()
            for message in messages:
                await websocket.send_json(message)
    except WebSocketDisconnect:
        return
