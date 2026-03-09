from fastapi import APIRouter, Request, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from twilio.twiml.messaging_response import MessagingResponse

from app.db.database import get_db
from app.db.models import Transaction
from app.services.parser_service import parse_expense_text
from app.services.report_service import (
    get_current_month_transactions,
    get_month_summary,
    parse_month_input,
    delete_transaction_by_id,
)
from app.services.state_service import (
    set_user_state,
    get_user_state,
    clear_user_state,
)
from app.services.command_service import detect_command
from app.services.whatsapp_format_service import (
    format_summary_for_whatsapp_short,
    format_transactions_for_whatsapp_short,
    format_updated_transaction_message,
    format_added_transaction_message,
    format_deleted_transactions_message,
    format_help_message,
    format_short_amount,
)

router = APIRouter()

DASHBOARD_URL = "https://home-economics-flax.vercel.app"


def build_twiml_message(message: str) -> Response:
    response = MessagingResponse()
    response.message(body=message)
    xml_content = str(response)
    print("Twilio response XML:", xml_content)
    return Response(
        content=xml_content,
        media_type="text/xml; charset=utf-8"
    )


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    form = await request.form()

    message = form.get("Body", "").strip().lower()
    sender = form.get("From", "")

    print("Incoming message:", message)

    user_state = get_user_state(sender)
    command = detect_command(message)

    # ===============================
    # מחיקה - בחירת מספרים
    # ===============================
    if user_state and user_state.get("action") == "delete_select":
        transaction_ids = user_state.get("transaction_ids", [])

        parts = message.replace(",", " ").split()
        selected_indexes = []

        for p in parts:
            if p.isdigit():
                selected_indexes.append(int(p) - 1)

        if not selected_indexes:
            return build_twiml_message("🗑️ שלח מספר רשומה או כמה מספרים למחיקה.")

        deleted = []

        for index in selected_indexes:
            if 0 <= index < len(transaction_ids):
                transaction_id = transaction_ids[index]
                t = delete_transaction_by_id(db, transaction_id)

                if t:
                    amount = format_short_amount(t.amount)
                    description = t.description if t.description else "ללא תיאור"
                    deleted.append(f"{description} — {amount} ₪")

        clear_user_state(sender)

        return build_twiml_message(
            format_deleted_transactions_message(deleted)
        )

    # ===============================
    # סיכום - מחכים לחודש
    # ===============================
    if user_state and user_state.get("action") == "awaiting_summary_month":
        parsed_month = parse_month_input(message)

        if not parsed_month:
            return build_twiml_message(
                "📅 לא הבנתי את החודש. שלח למשל: 3/2026 או מרץ 2026"
            )

        month, year = parsed_month
        summary = get_month_summary(db, month, year)

        clear_user_state(sender)

        formatted_summary = format_summary_for_whatsapp_short(summary)

        return build_twiml_message(
            f"""{formatted_summary}

📊 לאתר:
{DASHBOARD_URL}"""
        )

    # ===============================
    # עדכון - בחירת רשומה
    # ===============================
    if user_state and user_state.get("action") == "update_select":
        if not message.isdigit():
            return build_twiml_message("✏️ שלח מספר רשומה לעדכון.")

        selected_index = int(message) - 1
        transaction_ids = user_state.get("transaction_ids", [])

        if selected_index < 0 or selected_index >= len(transaction_ids):
            return build_twiml_message("המספר לא תקין.")

        transaction_id = transaction_ids[selected_index]

        set_user_state(
            sender,
            {
                "action": "update_new_value",
                "transaction_id": transaction_id,
            }
        )

        return build_twiml_message(
            "✏️ שלח ערך חדש.\nלדוגמה: ארומה 42"
        )

    # ===============================
    # עדכון - קבלת ערך חדש
    # ===============================
    if user_state and user_state.get("action") == "update_new_value":
        transaction_id = user_state.get("transaction_id")

        transaction = (
            db.query(Transaction)
            .filter(Transaction.id == transaction_id)
            .first()
        )

        if not transaction:
            clear_user_state(sender)
            return build_twiml_message("לא נמצאה רשומה לעדכון.")

        parsed = parse_expense_text(message)

        if parsed["amount"] is None:
            return build_twiml_message(
                "לא הצלחתי להבין. שלח למשל: שופרסל 280"
            )

        transaction.original_text = parsed["original_text"]
        transaction.description = parsed["description"]
        transaction.amount = parsed["amount"]
        transaction.type = parsed["type"]
        transaction.category = parsed["category"]

        db.commit()

        clear_user_state(sender)

        return build_twiml_message(
            format_updated_transaction_message(transaction)
        )

    # ===============================
    # פקודת מחיקה
    # ===============================
    if command == "delete":
        transactions = get_current_month_transactions(db)

        if not transactions:
            return build_twiml_message("📭 אין רשומות בחודש הנוכחי.")

        transaction_ids = [t.id for t in transactions]

        set_user_state(
            sender,
            {
                "action": "delete_select",
                "transaction_ids": transaction_ids,
            }
        )

        formatted = format_transactions_for_whatsapp_short(
            transactions,
            include_delete_hint=True
        )

        return build_twiml_message(formatted)

    # ===============================
    # פקודת עדכון
    # ===============================
    if command == "update":
        transactions = get_current_month_transactions(db)

        if not transactions:
            return build_twiml_message("📭 אין רשומות לעדכון.")

        transaction_ids = [t.id for t in transactions]

        set_user_state(
            sender,
            {
                "action": "update_select",
                "transaction_ids": transaction_ids,
            }
        )

        formatted = format_transactions_for_whatsapp_short(transactions)

        return build_twiml_message(
            f"{formatted}\n\n✏️ שלח את מספר הרשומה לעדכון"
        )

    # ===============================
    # רשימת רשומות חודש נוכחי
    # ===============================
    if command == "list":
        transactions = get_current_month_transactions(db)
        formatted = format_transactions_for_whatsapp_short(transactions)

        return build_twiml_message(
            f"""{formatted}

📊 לאתר:
{DASHBOARD_URL}"""
        )

    # ===============================
    # פקודת סיכום
    # ===============================
    if command == "summary":
        set_user_state(
            sender,
            {"action": "awaiting_summary_month"}
        )

        return build_twiml_message(
            "📅 איזה חודש?\nלמשל: 3/2026 או מרץ 2026"
        )

    # ===============================
    # פקודת אתר
    # ===============================
    if command == "site":
        return build_twiml_message(
            f"""📊 קישור לאתר:
{DASHBOARD_URL}"""
        )

    # ===============================
    # פקודת עזרה
    # ===============================
    if command == "help":
        return build_twiml_message(
            format_help_message()
        )

    # ===============================
    # הוספת הוצאה / הכנסה
    # ===============================
    parsed = parse_expense_text(message)

    if parsed["amount"] is not None:
        transaction = Transaction(
            original_text=parsed["original_text"],
            description=parsed["description"],
            amount=parsed["amount"],
            type=parsed["type"],
            category=parsed["category"],
        )

        db.add(transaction)
        db.commit()

        return build_twiml_message(
            format_added_transaction_message(parsed)
        )

    # ===============================
    # אם לא הבין
    # ===============================
    return build_twiml_message(
        "🤔 לא הבנתי. שלח 'עזרה' לפקודות."
    )