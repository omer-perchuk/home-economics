import os
import tempfile

# חייב לקרות לפני ה-import של האפליקציה: DB זמני, בלי מפתחות אמיתיים
_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file.name}"
os.environ.pop("OPENAI_API_KEY", None)
os.environ.pop("META_ACCESS_TOKEN", None)

import pytest

from app.db.database import Base, SessionLocal, engine
from app.db.models import Family, User


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def family_user(db):
    family = Family(name="בדיקה")
    db.add(family)
    db.commit()
    user = User(name="עומר", phone="whatsapp:+972500000001", family_id=family.id, is_admin=True, is_approved=True)
    db.add(user)
    db.commit()
    return family, user


@pytest.fixture
def other_family_user(db):
    family = Family(name="שכנים")
    db.add(family)
    db.commit()
    user = User(name="שכן", phone="whatsapp:+972500000002", family_id=family.id)
    db.add(user)
    db.commit()
    return family, user
