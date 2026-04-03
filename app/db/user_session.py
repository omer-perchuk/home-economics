from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from app.db.database import Base


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_token_hash = Column(String, nullable=False, unique=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    family_id = Column(Integer, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    last_seen_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)