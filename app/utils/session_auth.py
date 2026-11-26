from datetime import datetime, timedelta

from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.user_session import UserSession
from app.utils.auth_tokens import hash_token


# כניסה תקפה 30 יום מהשימוש האחרון באתר.
SESSION_TTL = timedelta(days=30)

# כדי לא לכתוב ל-DB בכל בקשה, מאריכים את התוקף לכל היותר פעם בשעה.
SESSION_TOUCH_INTERVAL = timedelta(hours=1)


def get_bearer_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    return auth_header[len("Bearer "):]


def get_current_session(request: Request, db: Session = Depends(get_db)):
    raw_token = get_bearer_token(request)
    token_hash = hash_token(raw_token)

    session = (
        db.query(UserSession)
        .filter(UserSession.session_token_hash == token_hash)
        .first()
    )

    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")

    now = datetime.utcnow()

    if session.revoked_at is not None or session.expires_at < now:
        raise HTTPException(status_code=401, detail="Session expired")

    if session.last_seen_at is None or now - session.last_seen_at > SESSION_TOUCH_INTERVAL:
        session.last_seen_at = now
        session.expires_at = now + SESSION_TTL
        db.commit()

    return session
