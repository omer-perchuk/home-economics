def get_category_emoji(category: str) -> str:
    mapping = {
        "אוכל בחוץ וקפה": "☕",
        "סופר וקניות לבית": "🛒",
        "תחבורה": "🚗",
        "דיור וחשבונות": "🏠",
        "בריאות ופארם": "💊",
        "בילויים ופנאי": "🎉",
        "הכנסות": "💰",
        "אחר": "📦",
    }
    return mapping.get(category, "📌")


def format_short_amount(amount: float) -> str:
    if float(amount).is_integer():
        return str(int(amount))
    return f"{amount:.2f}"


def format_summary_for_whatsapp_short(summary: dict) -> str:
    month = summary.get("month")
    year = summary.get("year")
    expenses_total = summary.get("expenses_total", 0)
    categories = summary.get("categories", [])

    lines = [f"📊 סיכום {month}/{year}", ""]

    if expenses_total <= 0 or not categories:
        lines.append("אין הוצאות בחודש הזה.")
        return "\n".join(lines)

    for item in categories:
        category = item["category"]
        amount = item["amount"]
        percent = 0 if expenses_total == 0 else (amount / expenses_total) * 100
        emoji = get_category_emoji(category)

        lines.append(
            f"{emoji} {category}: {format_short_amount(amount)} ₪ ({percent:.0f}%)"
        )

    lines.append("")
    lines.append(f"סה״כ: {format_short_amount(expenses_total)} ₪")

    return "\n".join(lines)


def format_transactions_for_whatsapp_short(transactions, include_delete_hint: bool = False) -> str:
    if not transactions:
        return "📭 אין רשומות לחודש הזה."

    lines = ["📋 רשומות החודש", ""]

    for index, tx in enumerate(transactions, start=1):
        emoji = get_category_emoji(tx.category)
        amount = format_short_amount(tx.amount)
        description = tx.description if tx.description else "ללא תיאור"
        lines.append(f"{index}. {emoji} {description} — {amount} ₪")

    if include_delete_hint:
        lines.append("")
        lines.append("🗑️ שלח מספר אחד או כמה מספרים למחיקה")

    return "\n".join(lines)


def format_updated_transaction_message(transaction) -> str:
    emoji = get_category_emoji(transaction.category)
    amount = format_short_amount(transaction.amount)
    return f"✏️ עודכן: {amount} ₪ · {emoji} {transaction.category}"


def format_added_transaction_message(parsed: dict) -> str:
    emoji = get_category_emoji(parsed["category"])
    amount = format_short_amount(parsed["amount"])

    if parsed["type"] == "income":
        return f"💰 נוספה הכנסה של {amount} ₪ לקטגוריה: {emoji} {parsed['category']}"

    return f"✅ נוסף {amount} ₪ לקטגוריה: {emoji} {parsed['category']}"


def format_deleted_transactions_message(deleted_items: list[str]) -> str:
    if not deleted_items:
        return "לא נמצאו רשומות למחיקה."

    deleted_text = "\n".join(deleted_items)
    return f"🗑️ נמחקו {len(deleted_items)} רשומות:\n\n{deleted_text}"


def format_help_message():
    return """💡 איך משתמשים בבוט?

📝 הוספת רשומה
שלח שם חנות וסכום.
לדוגמה:
ארומה 15
שופרסל 200
משכורת 12000

📋 הצג / רשומות
מציג את כל הרשומות של החודש הנוכחי.

📊 סיכום
מציג סיכום הוצאות לפי חודש שתבחר.

🌐 אתר
שולח קישור מאובטח לאתר.

✏️ עדכן
מאפשר לבחור רשומה קיימת ולעדכן אותה.

🗑️ מחק
מאפשר לבחור רשומה קיימת ולמחוק אותה.

❓ עזרה
מציג את ההודעה הזאת שוב."""