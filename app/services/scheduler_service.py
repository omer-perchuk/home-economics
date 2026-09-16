import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.db.database import SessionLocal
from app.services.recurring_service import process_due_recurring_transactions
from app.services.whatsapp_format_service import format_short_amount

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def _notify_recurring_created(recurring, transaction) -> None:
    if not recurring.user_id:
        return

    from app.db.models import User
    from app.routes.whatsapp import send_whatsapp_message

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == recurring.user_id).first()
        if not user:
            return

        amount = format_short_amount(transaction.amount)
        message = f"🔁 הוראת קבע בוצעה: {transaction.description} — {amount} ₪"
        asyncio.run(send_whatsapp_message(user.phone, message))
    except Exception:
        logger.exception("Failed to send recurring transaction notification")
    finally:
        db.close()


def run_recurring_check() -> None:
    db = SessionLocal()
    try:
        created = process_due_recurring_transactions(db)
    except Exception:
        logger.exception("Failed to process recurring transactions")
        return
    finally:
        db.close()

    for recurring, transaction in created:
        _notify_recurring_created(recurring, transaction)


def start_scheduler() -> None:
    if scheduler.running:
        return

    scheduler.add_job(
        run_recurring_check,
        "interval",
        hours=24,
        id="recurring_transactions_daily",
        replace_existing=True,
    )
    scheduler.add_job(run_recurring_check, "date", id="recurring_transactions_startup")
    scheduler.start()
