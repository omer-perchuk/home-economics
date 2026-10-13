import json
from datetime import datetime, timedelta

from app.db.database import SessionLocal
from app.db.models import ConversationState

# state ישן מזה נחשב לא רלוונטי (המשתמש כבר המשיך הלאה)
STATE_TTL = timedelta(hours=24)


def set_user_state(user_id: str, state: dict):
    db = SessionLocal()
    try:
        row = db.query(ConversationState).filter(ConversationState.phone == user_id).first()
        payload = json.dumps(state, ensure_ascii=False)

        if row:
            row.state_json = payload
            row.updated_at = datetime.utcnow()
        else:
            db.add(ConversationState(phone=user_id, state_json=payload, updated_at=datetime.utcnow()))

        db.commit()
    finally:
        db.close()


def get_user_state(user_id: str):
    db = SessionLocal()
    try:
        row = db.query(ConversationState).filter(ConversationState.phone == user_id).first()
        if not row:
            return None

        if row.updated_at < datetime.utcnow() - STATE_TTL:
            db.delete(row)
            db.commit()
            return None

        return json.loads(row.state_json)
    finally:
        db.close()


def clear_user_state(user_id: str):
    db = SessionLocal()
    try:
        db.query(ConversationState).filter(ConversationState.phone == user_id).delete()
        db.commit()
    finally:
        db.close()
