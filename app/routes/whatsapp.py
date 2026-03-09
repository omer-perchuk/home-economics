import os

from fastapi import APIRouter, Request, Depends, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy.orm import Session
from twilio.rest import Client

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
from app.services.family_service import get_user_and_family_by_phone
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

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")


def send_whatsapp_message(to_number: str, message: str) -> None:
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        print("Twilio credentials are missing. Message was not sent.")
        return

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            to=to_number,
            body=message,
        )
        print(f"Sent WhatsApp reply to {to_number}: {message}")
    except Exception as e:
        print(f"Failed to send WhatsApp reply to {to_number}: {e}")


def build_empty_ok_response() -> Response:
    return Response(status_code=200, content="")


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    form = await request.form()

    message = form.get("Body", "").strip().lower()
    sender = form.get("From", "")

    user, family = get_user_and_family_by_phone(db, sender)

    if not user or not family:
        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            "המספר שלך לא רשום במערכת. צריך להוסיף אותך קודם בקובץ המשפחות."
        )
        return build_empty_ok_response()

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
            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "🗑️ שלח מספר רשומה או כמה מספרים למחיקה."
            )
            return build_empty_ok_response()

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

        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            format_deleted_transactions_message(deleted)
        )
        return build_empty_ok_response()

    # ===============================
    # סיכום - מחכים לחודש
    # ===============================
    if user_state and user_state.get("action") == "awaiting_summary_month":
        parsed_month = parse_month_input(message)

        if not parsed_month:
            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "📅 לא הבנתי את החודש. שלח למשל: 3/2026 או מרץ 2026"
            )
            return build_empty_ok_response()

        month, year = parsed_month
        summary = get_month_summary(db, month, year, family.id)

        clear_user_state(sender)

        formatted_summary = format_summary_for_whatsapp_short(summary)

        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            f"""{formatted_summary}

📊 לאתר:
{DASHBOARD_URL}"""
        )
        return build_empty_ok_response()

    # ===============================
    # עדכון - בחירת רשומה
    # ===============================
    if user_state and user_state.get("action") == "update_select":
        if not message.isdigit():
            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "✏️ שלח מספר רשומה לעדכון."
            )
            return build_empty_ok_response()

        selected_index = int(message) - 1
        transaction_ids = user_state.get("transaction_ids", [])

        if selected_index < 0 or selected_index >= len(transaction_ids):
            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "המספר לא תקין."
            )
            return build_empty_ok_response()

        transaction_id = transaction_ids[selected_index]

        set_user_state(
            sender,
            {
                "action": "update_new_value",
                "transaction_id": transaction_id,
            }
        )

        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            "✏️ שלח ערך חדש.\nלדוגמה: ארומה 42"
        )
        return build_empty_ok_response()

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
            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "לא נמצאה רשומה לעדכון."
            )
            return build_empty_ok_response()

        parsed = parse_expense_text(message)

        if parsed["amount"] is None:
            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "לא הצלחתי להבין. שלח למשל: שופרסל 280"
            )
            return build_empty_ok_response()

        transaction.original_text = parsed["original_text"]
        transaction.description = parsed["description"]
        transaction.amount = parsed["amount"]
        transaction.type = parsed["type"]
        transaction.category = parsed["category"]

        db.commit()

        clear_user_state(sender)

        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            format_updated_transaction_message(transaction)
        )
        return build_empty_ok_response()

    # ===============================
    # פקודת מחיקה
    # ===============================
    if command == "delete":
        transactions = get_current_month_transactions(db, family.id)

        if not transactions:
            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "📭 אין רשומות בחודש הנוכחי."
            )
            return build_empty_ok_response()

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

        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            formatted
        )
        return build_empty_ok_response()

    # ===============================
    # פקודת עדכון
    # ===============================
    if command == "update":
        transactions = get_current_month_transactions(db, family.id)
        if not transactions:
            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "📭 אין רשומות לעדכון."
            )
            return build_empty_ok_response()

        transaction_ids = [t.id for t in transactions]

        set_user_state(
            sender,
            {
                "action": "update_select",
                "transaction_ids": transaction_ids,
            }
        )

        formatted = format_transactions_for_whatsapp_short(transactions)

        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            f"{formatted}\n\n✏️ שלח את מספר הרשומה לעדכון"
        )
        return build_empty_ok_response()

    # ===============================
    # רשימת רשומות חודש נוכחי
    # ===============================
    if command == "list":
        transactions = get_current_month_transactions(db, family.id)
        formatted = format_transactions_for_whatsapp_short(transactions)

        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            f"""{formatted}

📊 לאתר:
{DASHBOARD_URL}"""
        )
        return build_empty_ok_response()

    # ===============================
    # פקודת סיכום
    # ===============================
    if command == "summary":
        set_user_state(
            sender,
            {"action": "awaiting_summary_month"}
        )

        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            "📅 איזה חודש?\nלמשל: 3/2026 או מרץ 2026"
        )
        return build_empty_ok_response()

    # ===============================
    # פקודת אתר
    # ===============================
    if command == "site":
        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            f"""📊 קישור לאתר:
{DASHBOARD_URL}"""
        )
        return build_empty_ok_response()

    # ===============================
    # פקודת עזרה
    # ===============================
    if command == "help":
        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            format_help_message()
        )
        return build_empty_ok_response()

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
            family_id=family.id,
            user_id=user.id,
            user_phone=user.phone,
        )

        db.add(transaction)
        db.commit()

        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            format_added_transaction_message(parsed)
        )
        return build_empty_ok_response()

    # ===============================
    # אם לא הבין
    # ===============================
    background_tasks.add_task(
        send_whatsapp_message,
        sender,
        "🤔 לא הבנתי. שלח 'עזרה' לפקודות."
    )
    return build_empty_ok_response()