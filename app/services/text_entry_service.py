"""הוספת רשומה מטקסט חופשי ("קפה 15") — משותף לבוט ולאתר.

סדר זיהוי הקטגוריה: זיכרון (משתמש -> משפחה -> גלובלי) -> מילות מפתח -> AI.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import Transaction
from app.services.ai_categorizer import categorize_transaction_text
from app.services.merchant_memory_service import (
    extract_merchant_key,
    find_memory_candidates,
    upsert_memory,
)
from app.services.rule_based_categorizer import categorize_by_keywords


def parse_text_entry(raw_message: str) -> dict:
    """פענוח בסיסי לפי מילות מפתח. amount <= 0 אומר שאין כאן רשומה."""
    return categorize_by_keywords(raw_message)


def add_transaction_from_text(
    db: Session,
    raw_message: str,
    user_id: int,
    family_id: int,
    user_phone: Optional[str] = None,
    created_at: Optional[datetime] = None,
    base_result: Optional[dict] = None,
) -> Optional[dict]:
    """יוצר רשומה מטקסט. מחזיר את התוצאה המפוענחת (כולל transaction_id),
    או None אם לא נמצא סכום בטקסט."""
    if base_result is None:
        base_result = parse_text_entry(raw_message)
    print("=== RULE BASED RESULT ===", base_result)

    if base_result["amount"] <= 0:
        return None

    merchant_key = extract_merchant_key(raw_message)

    memory_candidates = {"user": [], "family": [], "global": []}
    if merchant_key:
        memory_candidates = find_memory_candidates(db, user_id, family_id, merchant_key)

    parsed_result = {**base_result}

    if memory_candidates["user"]:
        best = memory_candidates["user"][0]
        parsed_result["category"] = best.category
        parsed_result["type"] = best.tx_type
        print("=== USING USER MEMORY ===", best.category, best.tx_type)

    elif memory_candidates["family"]:
        best = memory_candidates["family"][0]
        parsed_result["category"] = best.category
        parsed_result["type"] = best.tx_type
        print("=== USING FAMILY MEMORY ===", best.category, best.tx_type)

    elif memory_candidates["global"]:
        best = memory_candidates["global"][0]
        parsed_result["category"] = best.category
        parsed_result["type"] = best.tx_type
        print("=== USING GLOBAL MEMORY ===", best.category, best.tx_type)

    # אם אין memory אבל rule-based זיהה קטגוריה - מספיק
    elif parsed_result["category"] != "אחר":
        print("=== USING RULE BASED CATEGORY ===", parsed_result["category"])

    # אם עדיין יצא 'אחר' - רק אז נשלח ל-AI
    else:
        ai_result = categorize_transaction_text(raw_message)
        print("=== AI CATEGORY RESULT ===", ai_result)

        if ai_result["amount"] > 0:
            parsed_result["category"] = ai_result["category"]
            parsed_result["type"] = ai_result["type"]

    transaction = Transaction(
        original_text=parsed_result["original_text"],
        description=parsed_result["description"],
        amount=parsed_result["amount"],
        type=parsed_result["type"],
        category=parsed_result["category"],
        family_id=family_id,
        user_id=user_id,
        user_phone=user_phone,
    )
    if created_at is not None:
        transaction.created_at = created_at

    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    # auto-learning: כל רשומה שנשמרה מחזקת את הזיכרון
    if merchant_key:
        for scope_type, scope_id in (
            ("user", user_id),
            ("family", family_id),
            ("global", None),
        ):
            upsert_memory(
                db,
                scope_type=scope_type,
                scope_id=scope_id,
                merchant_key=merchant_key,
                category=parsed_result["category"],
                tx_type=parsed_result["type"],
            )

    parsed_result["transaction_id"] = transaction.id
    return parsed_result
