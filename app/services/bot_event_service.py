import json
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import BotEvent, ProcessedMessage

UNDO_WINDOW = timedelta(minutes=30)
HISTORY_WINDOW = timedelta(hours=48)


def mark_message_processed(db: Session, message_id: str) -> bool:
    """
    מחזיר True אם זו הפעם הראשונה שההודעה מגיעה.
    Meta שולחת שוב את אותה הודעה אם התשובה התעכבה – במקרה כזה מחזירים False.
    """
    if not message_id:
        return True

    db.add(ProcessedMessage(message_id=message_id))
    try:
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False


def log_event(
    db: Session,
    user_id: int,
    family_id: Optional[int],
    role: str,
    content: str,
    action: Optional[dict] = None,
) -> BotEvent:
    event = BotEvent(
        user_id=user_id,
        family_id=family_id,
        role=role,
        content=content,
        action_json=json.dumps(action, ensure_ascii=False) if action else None,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_recent_history(db: Session, user_id: int, limit: int = 12):
    since = datetime.utcnow() - HISTORY_WINDOW
    events = (
        db.query(BotEvent)
        .filter(BotEvent.user_id == user_id, BotEvent.created_at >= since)
        .order_by(BotEvent.id.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(events))


def get_undoable_action(db: Session, user_id: int, event_id: Optional[int] = None):
    """
    הפעולה האחרונה שאפשר לבטל (או פעולה ספציפית לפי event_id מכפתור).
    """
    query = db.query(BotEvent).filter(
        BotEvent.user_id == user_id,
        BotEvent.action_json.isnot(None),
        BotEvent.created_at >= datetime.utcnow() - UNDO_WINDOW,
    )

    if event_id is not None:
        query = query.filter(BotEvent.id == event_id)

    event = query.order_by(BotEvent.id.desc()).first()
    if not event:
        return None, None

    action = json.loads(event.action_json)
    if action.get("undone"):
        return None, None

    return event, action


def mark_action_undone(db: Session, event: BotEvent):
    action = json.loads(event.action_json)
    action["undone"] = True
    event.action_json = json.dumps(action, ensure_ascii=False)
    db.commit()
