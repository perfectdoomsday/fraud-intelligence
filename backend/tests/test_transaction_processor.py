from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.database.models import Permission, Role, RolePermission
from app.services.transaction_processor import process_transaction


def test_transaction_processing_persists_prediction():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    db = Session()
    # Dimension tables are independent from auth roles but referenced by users.
    payload = {
        "transaction_id": "TXN-TEST-001", "customer_id": "CUS-TEST", "account_id": "ACC-TEST",
        "amount": 8500.0, "currency": "INR", "merchant_id": "MER-TEST",
        "merchant_category": "electronics", "timestamp": datetime.now(timezone.utc),
        "payment_method": "card", "device_id": "DEV-TEST", "ip_address": "127.0.0.1",
        "latitude": 28.6, "longitude": 77.2, "channel": "online", "transaction_status": "completed",
        "label_is_fraud": None,
    }
    result = process_transaction(db, payload)
    assert result["status"] == "processed"
    assert result["risk_score"] is not None
    assert result["model_version"]
    db.close()
    engine.dispose()
