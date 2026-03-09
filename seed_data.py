from app.db.database import SessionLocal
from app.db.models import Family, User


def seed():
    db = SessionLocal()

    try:
        existing_family = db.query(Family).filter(Family.name == "משפחת עומר").first()
        if existing_family:
            print("Family already exists")
            return

        family = Family(name="משפחת עומר")
        db.add(family)
        db.commit()
        db.refresh(family)

        user = User(
            name="עומר",
            phone="whatsapp:+972536278656",  # לשנות למספר שלך
            family_id=family.id,
        )
        db.add(user)
        db.commit()

        user2 = User(
            name="יוליה",
            phone="whatsapp:+972502222222",
            family_id=family.id
        )

        db.add(user2)
        db.commit()

        print("Seed data created successfully")

    finally:
        db.close()


if __name__ == "__main__":
    seed()