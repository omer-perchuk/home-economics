import os
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.login_token import LoginToken
from app.db.models import User
from app.db.user_session import UserSession
from app.utils.auth_tokens import hash_token, generate_raw_token


router = APIRouter()

SESSION_TTL_MINUTES = 15


class MagicLinkVerifyRequest(BaseModel):
    token: str


class MasterLoginRequest(BaseModel):
    key: str


def _normalize_phone(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    if digits.startswith("0"):
        digits = "972" + digits[1:]
    if not digits.startswith("972"):
        digits = f"972{digits}"
    return f"whatsapp:+{digits}"


def _create_session(db: Session, user_id: int, family_id: int) -> str:
    raw_session_token = generate_raw_token()
    db.add(
        UserSession(
            session_token_hash=hash_token(raw_session_token),
            user_id=user_id,
            family_id=family_id,
            expires_at=datetime.utcnow() + timedelta(minutes=SESSION_TTL_MINUTES),
            last_seen_at=datetime.utcnow(),
        )
    )
    db.commit()
    return raw_session_token


@router.post("/api/auth/master-login")
def master_login(payload: MasterLoginRequest, db: Session = Depends(get_db)):
    """Fixed login link that does not need a one-time token from the bot.

    Enabled only when MASTER_LOGIN_KEY and MASTER_LOGIN_PHONE are set.
    Link: <frontend>/auth?master=<MASTER_LOGIN_KEY>
    """
    master_key = os.getenv("MASTER_LOGIN_KEY", "")
    master_phone = os.getenv("MASTER_LOGIN_PHONE", "")

    if not master_key or not master_phone:
        raise HTTPException(status_code=404, detail="Not found")

    if not secrets.compare_digest(payload.key.encode("utf-8"), master_key.encode("utf-8")):
        raise HTTPException(status_code=401, detail="Invalid or expired link")

    user = db.query(User).filter(User.phone == _normalize_phone(master_phone)).first()
    if not user or user.family_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired link")

    return {
        "success": True,
        "access_token": _create_session(db, user.id, user.family_id),
        "family_id": user.family_id,
        "user_id": user.id,
    }


@router.post("/api/auth/verify-magic-link")
def verify_magic_link(
    payload: MagicLinkVerifyRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    token_hash = hash_token(payload.token)

    login_token = (
        db.query(LoginToken)
        .filter(LoginToken.token_hash == token_hash)
        .first()
    )

    if not login_token:
        raise HTTPException(status_code=401, detail="Invalid or expired link")

    if login_token.used_at is not None:
        raise HTTPException(status_code=401, detail="Invalid or expired link")

    if login_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Invalid or expired link")

    login_token.used_at = datetime.utcnow()

    # 🔥 יוצרים session token
    raw_session_token = generate_raw_token()
    session_token_hash = hash_token(raw_session_token)

    user_session = UserSession(
        session_token_hash=session_token_hash,
        user_id=login_token.user_id,
        family_id=login_token.family_id,
        expires_at=datetime.utcnow() + timedelta(minutes=SESSION_TTL_MINUTES),
        last_seen_at=datetime.utcnow(),
    )

    db.add(user_session)
    db.commit()

    # 🔥 מחזירים token ל־frontend
    return {
        "success": True,
        "access_token": raw_session_token,
        "family_id": login_token.family_id,
        "user_id": login_token.user_id,
    }