import base64
import hashlib
import hmac
import json
import time
from typing import Annotated

from argon2 import PasswordHasher
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.models import User
from app.database.session import get_db

_password_hasher = PasswordHasher()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/auth/token")
ROLE_PERMISSIONS = {
    "administrator": {"read", "investigate", "manage_users", "manage_models", "ingest"},
    "fraud_analyst": {"read", "investigate", "ingest"},
    "investigator": {"read", "investigate"},
    "ml_engineer": {"read", "manage_models", "ingest"},
    "read_only_auditor": {"read"},
}


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return _password_hasher.verify(hashed_password, password)
    except Exception:
        return False


def create_access_token(subject: str, role: str) -> str:
    header = {"alg": settings.jwt_algorithm, "typ": "JWT"}
    payload = {"sub": subject, "role": role, "exp": int(time.time()) + settings.access_token_minutes * 60}
    encoded_header = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    encoded_payload = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    if settings.jwt_algorithm != "HS256":
        raise RuntimeError("Only HS256 is implemented by the local token helper")
    signature = hmac.new(settings.jwt_secret_key.encode(), signing_input, hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_payload}.{_b64url_encode(signature)}"


def decode_access_token(token: str) -> dict:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
        header = json.loads(_b64url_decode(encoded_header))
        payload = json.loads(_b64url_decode(encoded_payload))
        if header.get("alg") != settings.jwt_algorithm or settings.jwt_algorithm != "HS256":
            raise ValueError("Unexpected signing algorithm")
        signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
        expected = hmac.new(settings.jwt_secret_key.encode(), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64url_decode(encoded_signature)):
            raise ValueError("Invalid token signature")
        if int(payload.get("exp", 0)) <= int(time.time()):
            raise ValueError("Token expired")
        return payload
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid or expired token") from exc


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], db: Annotated[Session, Depends(get_db)]
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        email = payload.get("sub")
        if not email:
            raise unauthorized
    except ValueError as exc:
        raise unauthorized from exc
    user = db.query(User).filter(User.email == email, User.is_active.is_(True)).first()
    if not user:
        raise unauthorized
    return user


def require_permission(permission: str):
    def dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        if permission not in ROLE_PERMISSIONS.get(user.role, set()):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return dependency
