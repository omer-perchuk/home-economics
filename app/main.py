from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.services.parser_service import parse_expense_text
from app.db.database import get_db
from app.db.models import Transaction

from app.db.login_token import LoginToken
from app.db.user_session import UserSession

from app.routes.whatsapp import router as whatsapp_router
from app.routes.dashboard_api import router as dashboard_api_router
from app.routes.settings_api import router as settings_api_router
from app.routes.auth_api import router as auth_api_router

from app.utils.session_auth import get_current_session

app = FastAPI()


@app.on_event("startup")
def startup():
    print("=== APP STARTUP ===")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(whatsapp_router)
app.include_router(dashboard_api_router)
app.include_router(settings_api_router)
app.include_router(auth_api_router)


class ExpenseInput(BaseModel):
    text: str


@app.get("/")
def root():
    return {"message": "Home Economics Bot is running"}


@app.post("/parse-expense")
def parse_expense(data: ExpenseInput):
    parsed_data = parse_expense_text(data.text)
    return parsed_data


@app.get("/transactions")
def get_transactions(
    session=Depends(get_current_session),
    db: Session = Depends(get_db)
):
    transactions = (
        db.query(Transaction)
        .filter(Transaction.family_id == session.family_id)
        .order_by(Transaction.id.desc())
        .all()
    )

    return [
        {
            "id": t.id,
            "original_text": t.original_text,
            "description": t.description,
            "amount": t.amount,
            "type": t.type,
            "category": t.category,
            "created_at": t.created_at,
        }
        for t in transactions
    ]


@app.get("/report/categories")
def category_report(
    session=Depends(get_current_session),
    db: Session = Depends(get_db)
):
    transactions = (
        db.query(Transaction)
        .filter(Transaction.family_id == session.family_id)
        .all()
    )

    summary = {}

    for t in transactions:
        summary[t.category] = summary.get(t.category, 0) + t.amount

    return summary


@app.get("/debug/families")
def debug_families(db: Session = Depends(get_db)):
    from app.db.models import Family, User

    families = db.query(Family).all()
    result = []

    for f in families:
        users = db.query(User).filter(User.family_id == f.id).all()

        result.append({
            "family": f.name,
            "members": [
                {
                    "name": u.name,
                    "phone": u.phone,
                    "is_admin": u.is_admin,
                    "is_approved": u.is_approved,
                }
                for u in users
            ]
        })

    return result


@app.get("/debug/fix-transaction-families")
def fix_transaction_families(db: Session = Depends(get_db)):
    from app.db.models import Transaction, User

    transactions = db.query(Transaction).all()
    updated = 0

    for transaction in transactions:
        if not transaction.user_phone:
            continue

        user = db.query(User).filter(User.phone == transaction.user_phone).first()
        if not user:
            continue

        if transaction.family_id != user.family_id:
            transaction.family_id = user.family_id
            transaction.user_id = user.id
            updated += 1

    db.commit()

    return {"updated_transactions": updated}


@app.get("/api/me")
def get_me(session=Depends(get_current_session)):
    return {
        "user_id": session.user_id,
        "family_id": session.family_id
    }