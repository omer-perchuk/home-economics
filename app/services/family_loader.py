from app.db.database import SessionLocal
from app.db.models import Family, User
from app.config.families_config import FAMILIES


def load_families():
    db = SessionLocal()

    try:
        for family_data in FAMILIES:
            family = db.query(Family).filter(
                Family.name == family_data["family_name"]
            ).first()

            if not family:
                family = Family(
                    name=family_data["family_name"],
                    slug=family_data["family_slug"],
                    twilio_whatsapp_number=family_data["twilio_number"],
                )
                db.add(family)
                db.commit()
                db.refresh(family)
            else:
                family.slug = family_data["family_slug"]
                family.twilio_whatsapp_number = family_data["twilio_number"]
                db.commit()
                db.refresh(family)

            for member in family_data["members"]:
                existing_user = db.query(User).filter(
                    User.phone == member["phone"]
                ).first()

                if not existing_user:
                    user = User(
                        name=member["name"],
                        phone=member["phone"],
                        family_id=family.id,
                    )
                    db.add(user)
                else:
                    existing_user.name = member["name"]
                    existing_user.family_id = family.id

            db.commit()

    finally:
        db.close()