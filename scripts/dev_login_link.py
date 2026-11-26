"""יוצר קישור כניסה לבדיקה מקומית, בלי הבוט.

שימוש (משורש ה-repo):
    FRONTEND_URL=http://localhost:3000 python -m scripts.dev_login_link [phone]

אם אין עדיין משפחה ומשתמש ב-DB המקומי, נוצרים "משפחת בדיקה" ומשתמש בדיקה.
אל תריץ את זה מול ה-DB של הפרודקשן.
"""

import os
import sys

os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")

from app.db.database import Base, SessionLocal, engine  # noqa: E402
from app.db.migrations import run_migrations  # noqa: E402
from app.db import login_token, user_session  # noqa: E402,F401  (registers tables)
from app.db.models import Family, User  # noqa: E402
from app.services.magic_link_service import create_magic_link  # noqa: E402


def main() -> None:
    Base.metadata.create_all(bind=engine)
    run_migrations(engine)

    phone = sys.argv[1] if len(sys.argv) > 1 else None
    db = SessionLocal()
    try:
        query = db.query(User).filter(User.family_id.isnot(None))
        if phone:
            query = query.filter(User.phone == phone)
        user = query.order_by(User.id).first()

        if not user and not phone:
            family = Family(name="משפחת בדיקה")
            db.add(family)
            db.flush()
            user = User(
                name="משתמש בדיקה",
                phone="whatsapp:+972500000000",
                family_id=family.id,
                is_admin=True,
                is_approved=True,
            )
            db.add(user)
            db.commit()
            print("נוצרו משפחת בדיקה ומשתמש בדיקה")

        if not user:
            sys.exit(f"לא נמצא משתמש עם הטלפון {phone}")

        print(f"משתמש: {user.name} ({user.phone})")
        print(create_magic_link(user_id=user.id, family_id=user.family_id))
    finally:
        db.close()


if __name__ == "__main__":
    main()
