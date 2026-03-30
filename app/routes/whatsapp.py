import os
import httpx

from fastapi import APIRouter, Request, Depends, BackgroundTasks, HTTPException
from fastapi.responses import Response, PlainTextResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Transaction
from app.services.ai_categorizer import categorize_transaction_text
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

DASHBOARD_URL = "https://aws-migration-test.d11fqx2zyfwk68.amplifyapp.com"

META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
META_VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "")
META_PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID", "")


def normalize_phone_for_db(phone: str) -> str:
    """
    Meta usually sends phone numbers like: 9725XXXXXXXX
    We normalize to whatsapp:+9725XXXXXXXX so it stays compatible
    with your existing family lookup logic.
    """
    digits = "".join(ch for ch in phone if ch.isdigit())
    if not digits:
        return phone

    if digits.startswith("0"):
        digits = "972" + digits[1:]

    if not digits.startswith("972"):
        return f"whatsapp:+{digits}"

    return f"whatsapp:+{digits}"


async def send_whatsapp_message(to_number: str, message: str) -> None:
    """
    Send WhatsApp message via Meta Cloud API.
    Expects to_number in one of:
    - whatsapp:+9725XXXXXXXX
    - +9725XXXXXXXX
    - 9725XXXXXXXX
    """
    if not META_ACCESS_TOKEN or not META_PHONE_NUMBER_ID:
        print("Meta credentials are missing. Message was not sent.")
        return

    digits = "".join(ch for ch in to_number if ch.isdigit())
    if not digits:
        print(f"Invalid destination number: {to_number}")
        return

    url = f"https://graph.facebook.com/v22.0/{META_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": digits,
        "type": "text",
        "text": {"body": message},
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
        print(f"Sent WhatsApp reply to {digits}: {message}")
    except Exception as e:
        print(f"Failed to send WhatsApp reply to {digits}: {e}")


def build_empty_ok_response() -> Response:
    return Response(status_code=200, content="")


@router.get("/webhook/whatsapp")
async def verify_whatsapp_webhook(request: Request):
    """
    Meta webhook verification endpoint.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == META_VERIFY_TOKEN:
        return PlainTextResponse(content=challenge or "", status_code=200)

    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Meta incoming webhook endpoint.
    """
    body = await request.json()
    print("Incoming Meta webhook:", body)

    try:
        entry = body["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        messages = value.get("messages", [])
        if not messages:
            return build_empty_ok_response()

        message_data = messages[0]

        # Ignore statuses and non-text messages for now
        if message_data.get("type") != "text":
            return build_empty_ok_response()

        raw_message = message_data["text"]["body"].strip()
        message = raw_message.lower()

        sender_raw = message_data.get("from", "")
        sender = normalize_phone_for_db(sender_raw)

    except Exception as e:
        print(f"Failed to parse Meta webhook: {e}")
        return build_empty_ok_response()

    user, family = get_user_and_family_by_phone(db, sender)

    if not user or not family:
        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            "המספר שלך לא רשום במערכת. צריך להוסיף אותך קודם בקובץ המשפחות."
        )
        return build_empty_ok_response()

    print("Incoming message:", raw_message)

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

        ai_result = categorize_transaction_text(raw_message)

        if ai_result["amount"] <= 0:
            background_tasks.add_task(
                send_whatsapp_message,
                sender,
                "לא הצלחתי להבין. שלח למשל: שופרסל 280"
            )
            return build_empty_ok_response()

        transaction.original_text = ai_result["original_text"]
        transaction.description = ai_result["description"]
        transaction.amount = ai_result["amount"]
        transaction.type = ai_result["type"]
        transaction.category = ai_result["category"]

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
    ai_result = categorize_transaction_text(raw_message)

    if ai_result["amount"] > 0:
        transaction = Transaction(
            original_text=ai_result["original_text"],
            description=ai_result["description"],
            amount=ai_result["amount"],
            type=ai_result["type"],
            category=ai_result["category"],
            family_id=family.id,
            user_id=user.id,
            user_phone=user.phone,
        )

        db.add(transaction)
        db.commit()

        background_tasks.add_task(
            send_whatsapp_message,
            sender,
            format_added_transaction_message(ai_result)
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