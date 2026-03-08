from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.services.parser_service import parse_expense_text
from app.services.report_service import get_category_summary
from app.db.database import Base, engine, get_db
from app.db.models import Transaction
from app.routes.whatsapp import router as whatsapp_router
from app.routes.dashboard_api import router as dashboard_api_router
from app.routes.settings_api import router as settings_api_router

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://192.168.68.101:3000",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(whatsapp_router)
app.include_router(dashboard_api_router)
app.include_router(settings_api_router)


class ExpenseInput(BaseModel):
    text: str


@app.get("/")
def root():
    return {"message": "Home Economics Bot is running"}


@app.post("/parse-expense")
def parse_expense(data: ExpenseInput, db: Session = Depends(get_db)):
    parsed_data = parse_expense_text(data.text)

    if parsed_data["amount"] is not None:
        transaction = Transaction(
            original_text=parsed_data["original_text"],
            description=parsed_data["description"],
            amount=parsed_data["amount"],
            type=parsed_data["type"],
            category=parsed_data["category"]
        )

        db.add(transaction)
        db.commit()
        db.refresh(transaction)

        parsed_data["id"] = transaction.id

    return parsed_data


@app.get("/transactions")
def get_transactions(db: Session = Depends(get_db)):
    transactions = db.query(Transaction).order_by(Transaction.id.desc()).all()

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
def category_report(db: Session = Depends(get_db)):
    return get_category_summary(db)