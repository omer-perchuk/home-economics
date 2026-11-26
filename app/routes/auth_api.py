import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.login_token import LoginToken
from app.db.models import User
from app.db.user_session import UserSession
from app.services.google_auth_service import verify_google_credential
from app.utils.auth_tokens import hash_token, generate_raw_token
from app.utils.session_auth import SESSION_TTL, get_bearer_token, get_current_session


router = APIRouter()


class MagicLinkVerifyRequest(BaseModel):
    token: str


class GoogleCredentialRequest(BaseModel):
    credential: str


def _create_session(db: Session, user_id: int, family_id: int) -> str:
    raw_session_token = generate_raw_token()
    db.add(
        UserSession(
            session_token_hash=hash_token(raw_session_token),
            user_id=user_id,
            family_id=family_id,
            expires_at=datetime.utcnow() + SESSION_TTL,
            last_seen_at=datetime.utcnow(),
        )
    )
    db.commit()
    return raw_session_token


def _master_login_enabled() -> bool:
    return os.getenv("MASTER_LOGIN_ENABLED", "").strip().lower() in ("1", "true", "yes")


@router.post("/api/auth/master-login")
def master_login(db: Session = Depends(get_db)):
    """כניסת חירום לאתר בלי קישור מהבוט — כבויה כברירת מחדל.

    להפעלה (למשל כשהבוט לא עובד): ב-App Runner להוסיף
    MASTER_LOGIN_ENABLED=true ולשמור. לכיבוי: למחוק את המשתנה.
    Link: <frontend>/auth?master=1
    Logs in as the first admin user that belongs to a family.
    """
    if not _master_login_enabled():
        raise HTTPException(status_code=404, detail="Not found")

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

    return {
        "success": True,
        "access_token": _create_session(db, login_token.user_id, login_token.family_id),
        "family_id": login_token.family_id,
        "user_id": login_token.user_id,
    }


@router.post("/api/auth/google")
def google_login(payload: GoogleCredentialRequest, db: Session = Depends(get_db)):
    """כניסה עם חשבון גוגל שכבר חובר למשתמש קיים."""
    info = verify_google_credential(payload.credential)

    user = db.query(User).filter(User.google_sub == info["sub"]).first()

    if not user or user.family_id is None:
        # חשבון גוגל שלא חובר לאף משתמש לא נכנס.
        # כדי לחבר: נכנסים פעם אחת מהקישור של הבוט ולוחצים "חבר חשבון גוגל".
        raise HTTPException(status_code=403, detail="google_not_linked")

    if info.get("email") and user.email != info["email"]:
        user.email = info["email"]

    return {
        "success": True,
        "access_token": _create_session(db, user.id, user.family_id),
        "family_id": user.family_id,
        "user_id": user.id,
    }


@router.post("/api/auth/google/link")
def link_google(
    payload: GoogleCredentialRequest,
    session=Depends(get_current_session),
    db: Session = Depends(get_db),
):
    """מחבר חשבון גוגל למשתמש שמחובר עכשיו (נכנס דרך הקישור מהבוט)."""
    info = verify_google_credential(payload.credential)

    other = (
        db.query(User)
        .filter(User.google_sub == info["sub"], User.id != session.user_id)
        .first()
    )
    if other:
        raise HTTPException(status_code=409, detail="google_linked_to_other_user")

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.google_sub = info["sub"]
    user.email = info.get("email")
    db.commit()

    return {"success": True, "email": user.email}


@router.delete("/api/auth/google/link")
def unlink_google(session=Depends(get_current_session), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.google_sub = None
    user.email = None
    db.commit()

    return {"success": True}


@router.post("/api/auth/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    token_hash = hash_token(get_bearer_token(request))

    session = (
        db.query(UserSession)
        .filter(UserSession.session_token_hash == token_hash)
        .first()
    )
    if session and session.revoked_at is None:
        session.revoked_at = datetime.utcnow()
        db.commit()

    return {"success": True}
