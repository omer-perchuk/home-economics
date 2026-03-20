from sqlalchemy.orm import Session
from app.db.models import Family

DEFAULT_TITLE = "כלכלת הבית"


def get_settings(db: Session, family_id: int):
    family = db.query(Family).filter(Family.id == family_id).first()

    if not family:
        return {"dashboard_title": DEFAULT_TITLE}

    return {
        "dashboard_title": family.dashboard_title or DEFAULT_TITLE
    }


def update_dashboard_title(db: Session, family_id: int, new_title: str):
    family = db.query(Family).filter(Family.id == family_id).first()

    if not family:
        return {"dashboard_title": DEFAULT_TITLE}

    family.dashboard_title = new_title.strip() or DEFAULT_TITLE
    db.commit()
    db.refresh(family)

    return {
        "dashboard_title": family.dashboard_title
    }