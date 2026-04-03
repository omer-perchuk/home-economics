from datetime import datetime, timedelta
from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.user_session import UserSession
from app.utils.auth_tokens import hash_token

SESSION_TTL_MINUTES = 15


def get_current_session(
    request: Request,
    db: Session = Depends(get_db),
):
    raw_token = request.cookies.get("session_token")

    if not raw_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    token_hash = hash_token(raw_token)

    session = (
        db.query(UserSession)
        .filter(UserSession.session_token_hash == token_hash)
        .first()
    )

    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")

    if session.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Session revoked")

    if session.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Session expired")

    # 🔥 הארכת זמן (כמו שרצית)
    now = datetime.utcnow()
    session.last_seen_at = now
    session.expires_at = now + timedelta(minutes=SESSION_TTL_MINUTES)

    db.commit()

    return session