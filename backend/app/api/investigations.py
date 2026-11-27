import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.api.dependencies import can_investigate, can_read
from app.database.models import AuditLog, FraudAlert, InvestigationCase, InvestigationNote
from app.database.session import get_db
from app.schemas.investigations import CaseCreate, CaseOut, CaseUpdate, NoteCreate

router = APIRouter(prefix="/cases", tags=["Investigations"])


@router.get("", response_model=list[CaseOut])
def list_cases(_user=Depends(can_read), db: Session = Depends(get_db)):
    return db.query(InvestigationCase).options(joinedload(InvestigationCase.notes)).order_by(InvestigationCase.created_at.desc()).limit(200).all()


@router.post("", response_model=CaseOut, status_code=201)
def create_case(payload: CaseCreate, user=Depends(can_investigate), db: Session = Depends(get_db)):
    alert = db.query(FraudAlert).filter(FraudAlert.alert_id == payload.alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    case = InvestigationCase(case_id=f"CASE-{uuid.uuid4().hex[:12].upper()}", alert_id=payload.alert_id,
                             title=payload.title, assigned_to=payload.assigned_to)
    db.add(case)
    db.flush()
    db.add(AuditLog(actor=user.email, action="CASE_CREATED", resource_type="case", resource_id=case.case_id,
                    details={"alert_id": payload.alert_id}))
    db.commit()
    return db.query(InvestigationCase).options(joinedload(InvestigationCase.notes)).filter_by(id=case.id).first()


@router.get("/{case_id}", response_model=CaseOut)
def get_case(case_id: str, _user=Depends(can_read), db: Session = Depends(get_db)):
    case = db.query(InvestigationCase).options(joinedload(InvestigationCase.notes)).filter_by(case_id=case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.patch("/{case_id}", response_model=CaseOut)
def update_case(case_id: str, payload: CaseUpdate, user=Depends(can_investigate), db: Session = Depends(get_db)):
    case = db.query(InvestigationCase).filter_by(case_id=case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(case, field, value)
    db.add(AuditLog(actor=user.email, action="CASE_UPDATED", resource_type="case", resource_id=case_id,
                    details=changes))
    db.commit()
    return db.query(InvestigationCase).options(joinedload(InvestigationCase.notes)).filter_by(id=case.id).first()


@router.post("/{case_id}/notes")
def add_note(case_id: str, payload: NoteCreate, user=Depends(can_investigate), db: Session = Depends(get_db)):
    case = db.query(InvestigationCase).filter_by(case_id=case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    note = InvestigationNote(case_id=case.id, author=user.email, note=payload.note)
    db.add(note)
    db.add(AuditLog(actor=user.email, action="CASE_NOTE_ADDED", resource_type="case", resource_id=case_id, details={}))
    db.commit()
    return {"status": "saved"}
