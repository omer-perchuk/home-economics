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
def master_login(db: Session = Depends(get_db)):
    """TEMPORARY: fixed login link with no token. Remove when the bot works again.

    Link: <frontend>/auth?master=1
    Logs in as the first admin user that belongs to a family.
    """
    user = (
        db.query(User)
        .filter(User.is_admin.is_(True), User.family_id.isnot(None))
        .order_by(User.id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="No admin user found")

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