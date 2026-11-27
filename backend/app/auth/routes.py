from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, verify_password
from app.database.models import User
from app.database.session import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    expires_in: int


@router.post("/token", response_model=TokenResponse)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: Annotated[Session, Depends(get_db)]):
    user = db.query(User).filter(User.email == form.username, User.is_active.is_(True)).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    from app.core.config import settings
    return TokenResponse(
        access_token=create_access_token(user.email, user.role),
        role=user.role,
        expires_in=settings.access_token_minutes * 60,
    )
