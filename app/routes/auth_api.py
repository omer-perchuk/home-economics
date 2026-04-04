from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.login_token import LoginToken
from app.db.user_session import UserSession
from app.utils.auth_tokens import hash_token, generate_raw_token


router = APIRouter()

SESSION_TTL_MINUTES = 15


class MagicLinkVerifyRequest(BaseModel):
    token: str


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

    response.set_cookie(
        key="session_token",
        value=raw_session_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=SESSION_TTL_MINUTES * 60,
    )

    return {
        "success": True,
        "family_id": login_token.family_id,
        "user_id": login_token.user_id,
    }