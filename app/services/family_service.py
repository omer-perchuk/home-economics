from sqlalchemy.orm import Session

from app.db.models import User, Family


def get_user_and_family_by_phone(db: Session, phone: str):
    user = db.query(User).filter(User.phone == phone).first()

    if not user:
        return None, None

    family = db.query(Family).filter(Family.id == user.family_id).first()

    return user, family