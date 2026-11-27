from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import can_investigate, can_read
from app.database.models import AuditLog, FraudAlert
from app.database.session import get_db
from app.schemas.alerts import AlertOut, AlertStatusUpdate, AssignAlert

router = APIRouter(prefix="/alerts", tags=["Fraud Alerts"])
ALLOWED_TRANSITIONS = {
    "NEW": {"ACKNOWLEDGED"},
    "ACKNOWLEDGED": {"INVESTIGATING", "CLOSED"},
    "INVESTIGATING": {"CONFIRMED_FRAUD", "FALSE_POSITIVE"},
    "CONFIRMED_FRAUD": {"CLOSED"},
    "FALSE_POSITIVE": {"CLOSED"},
    "CLOSED": set(),
}


@router.get("", response_model=list[AlertOut])
def list_alerts(_user=Depends(can_read), db: Session = Depends(get_db), status: str | None = None, severity: str | None = None):
    query = db.query(FraudAlert)
    if status:
        query = query.filter(FraudAlert.status == status.upper())
    if severity:
        query = query.filter(FraudAlert.severity == severity.upper())
    return query.order_by(FraudAlert.created_at.desc()).limit(500).all()


@router.get("/{alert_id}", response_model=AlertOut)
def get_alert(alert_id: str, _user=Depends(can_read), db: Session = Depends(get_db)):
    alert = db.query(FraudAlert).filter(FraudAlert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.patch("/{alert_id}/status", response_model=AlertOut)
def update_status(alert_id: str, payload: AlertStatusUpdate, user=Depends(can_investigate), db: Session = Depends(get_db)):
    alert = db.query(FraudAlert).filter(FraudAlert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    previous = alert.status
    if payload.status not in ALLOWED_TRANSITIONS.get(previous, set()):
        raise HTTPException(status_code=409, detail=f"Invalid alert transition: {previous} -> {payload.status}")
    alert.status = payload.status
    db.add(AuditLog(actor=user.email, action="ALERT_STATUS_CHANGED", resource_type="alert", resource_id=alert_id,
                    details={"from": previous, "to": payload.status}))
    db.commit()
    db.refresh(alert)
    return alert


@router.post("/{alert_id}/assign", response_model=AlertOut)
def assign_alert(alert_id: str, payload: AssignAlert, user=Depends(can_investigate), db: Session = Depends(get_db)):
    alert = db.query(FraudAlert).filter(FraudAlert.alert_id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.assigned_to = payload.assigned_to
    db.add(AuditLog(actor=user.email, action="ALERT_ASSIGNED", resource_type="alert", resource_id=alert_id,
                    details={"assigned_to": payload.assigned_to}))
    db.commit()
    db.refresh(alert)
    return alert
