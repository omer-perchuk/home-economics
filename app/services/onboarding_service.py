from sqlalchemy.orm import Session

from app.db.models import User, Family, JoinRequest


def get_or_create_user_by_phone(db: Session, phone: str) -> User:
    user = db.query(User).filter(User.phone == phone).first()
    if user:
        return user

    user = User(
        phone=phone,
        name=phone,
        family_id=None,
        is_admin=False,
        is_approved=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_family_for_user(db: Session, user: User, family_name: str) -> Family:
    family = Family(name=family_name)
    db.add(family)
    db.commit()
    db.refresh(family)

    user.family_id = family.id
    user.is_admin = True
    user.is_approved = True
    db.commit()
    db.refresh(user)

    return family


def find_admin_by_phone(db: Session, phone: str):
    return (
        db.query(User)
        .filter(
            User.phone == phone,
            User.is_admin == True,
            User.family_id.isnot(None),
            User.is_approved == True,
        )
        .first()
    )


def create_join_request(db: Session, requester: User, admin: User) -> JoinRequest:
    req = JoinRequest(
        requester_user_id=requester.id,
        requester_phone=requester.phone,
        admin_user_id=admin.id,
        family_id=admin.family_id,
        status="pending",
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


def get_pending_join_request_for_admin(db: Session, request_id: int, admin_user_id: int):
    return (
        db.query(JoinRequest)
        .filter(
            JoinRequest.id == request_id,
            JoinRequest.admin_user_id == admin_user_id,
            JoinRequest.status == "pending",
        )
        .first()
    )


def approve_join_request(db: Session, join_request: JoinRequest):
    requester = db.query(User).filter(User.id == join_request.requester_user_id).first()
    if not requester:
        return None

    requester.family_id = join_request.family_id
    requester.is_approved = True
    join_request.status = "approved"
    db.commit()
    db.refresh(requester)
    return requester


def reject_join_request(db: Session, join_request: JoinRequest):
    join_request.status = "rejected"
    db.commit()