def get_category_emoji(category: str) -> str:
    mapping = {
        "אוכל בחוץ וקפה": "☕",
        "סופר וקניות לבית": "🛒",
        "תחבורה": "🚗",
        "דיור וחשבונות": "🏠",
        "בריאות ופארם": "💊",
        "בילויים ופנאי": "🎉",
        "ביגוד והנעלה": "👕",
        "ילדים ומשפחה": "👨‍👩‍👧",
        "לימודים": "📚",
        "חופשות ונסיעות": "✈️",
        "מתנות ותרומות": "🎁",
        "ביטוחים": "🛡️",
        "חיות מחמד": "🐾",
        "משכורת": "💰",
        "החזרים": "↩️",
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


def format_transaction_line(transaction, include_date: bool = False) -> str:
    emoji = get_category_emoji(transaction.category)
    amount = format_short_amount(transaction.amount)
    description = transaction.description if transaction.description else "ללא תיאור"
    line = f"{emoji} {description} — {amount} ₪"
    if include_date and transaction.created_at:
        line += f" · {transaction.created_at.strftime('%d/%m')}"
    return line


def format_added_entries_message(transactions, uncertain_ids=None, show_dates: bool = False) -> str:
    uncertain_ids = uncertain_ids or set()

    if len(transactions) == 1:
        tx = transactions[0]
        title = "💰 נוספה הכנסה" if tx.type == "income" else "✅ נוסף"
        lines = [
            f"{title}: {tx.description} — {format_short_amount(tx.amount)} ₪",
            f"{get_category_emoji(tx.category)} {tx.category}",
        ]
        if show_dates and tx.created_at:
            lines.append(f"📅 {tx.created_at.strftime('%d/%m/%Y')}")
        if tx.id in uncertain_ids:
            lines.append("🤔 לא בטוח בקטגוריה – אפשר לשנות בכפתור")
        return "\n".join(lines)

    total = sum(t.amount for t in transactions if t.type == "expense")
    lines = [f"✅ נוספו {len(transactions)} רשומות:", ""]
    for tx in transactions:
        line = f"{format_transaction_line(tx, include_date=show_dates)} ({tx.category})"
        if tx.id in uncertain_ids:
            line += " 🤔"
        lines.append(line)
    if total:
        lines.append("")
        lines.append(f"סה״כ הוצאות: {format_short_amount(total)} ₪")
    return "\n".join(lines)


def format_recurring_for_whatsapp(recurring_list) -> str:
    if not recurring_list:
        return "📭 אין הוראות קבע פעילות."

    lines = ["🔁 הוראות קבע", ""]

    for index, r in enumerate(recurring_list, start=1):
        emoji = get_category_emoji(r.category)
        amount = format_short_amount(r.amount)
        lines.append(f"{index}. {emoji} {r.description} — {amount} ₪ (כל {r.day_of_month} לחודש)")

    return "\n".join(lines)


def format_added_recurring_message(recurring, materialized_now: bool) -> str:
    emoji = get_category_emoji(recurring.category)
    amount = format_short_amount(recurring.amount)
    lines = [
        f"✅ נוספה הוראת קבע: {emoji} {recurring.description} — {amount} ₪ בכל {recurring.day_of_month} לחודש"
    ]

    if materialized_now:
        lines.append("נוספה רשומה גם לחודש הנוכחי.")

    return "\n".join(lines)


def format_deleted_recurring_message(deleted_items: list[str]) -> str:
    if not deleted_items:
        return "לא נמצאו הוראות קבע למחיקה."

    deleted_text = "\n".join(deleted_items)
    return f"🗑️ בוטלו {len(deleted_items)} הוראות קבע:\n\n{deleted_text}"


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

אפשר גם כמה רשומות ותאריך:
סופר 340, דלק 250
ארומה 20 אתמול

💬 שאלות ובקשות חופשיות
כמה הוצאנו על אוכל בחוץ החודש?
תמחק את הקפה של אתמול
תשנה את הסופר האחרון ל-320

📋 הצג / רשומות
מציג את כל הרשומות של החודש הנוכחי.

📊 סיכום
מציג סיכום הוצאות. אפשר גם: סיכום ספטמבר / סיכום שעבר.

🌐 אתר
שולח קישור מאובטח לאתר.

✏️ עדכן
מאפשר לבחור רשומה קיימת ולעדכן אותה.

🗑️ מחק
מאפשר לבחור רשומה קיימת ולמחוק אותה.

🔁 הוראת קבע
מאפשר להגדיר תשלום חודשי קבוע (כמו שכירות או ביטוח) שייווסף אוטומטית כל חודש, בלי צורך להזין אותו מחדש.

↩️ בטל
מבטל את הפעולה האחרונה (למשל רשומה שנוספה בטעות).

❓ עזרה
מציג את ההודעה הזאת שוב."""