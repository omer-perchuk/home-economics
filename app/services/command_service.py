def detect_command(message: str) -> str | None:
    normalized = message.strip().lower()

    list_commands = {
        "רשימה",
        "הצג",
        "תראה",
        "הוצאות",
        "רשומות",
        "תציג",
        "להציג",
        "הצגה",
        "show",
        "list",
    }

    summary_commands = {
        "סיכום",
        "סכם",
        "סיכום חודשי",
        "דוח",
        "דוח",
        "summary",
        "report",
    }

    delete_commands = {
        "מחק",
        "מחיקה",
        "למחוק",
        "delete",
        "remove",
    }

    update_commands = {
        "עדכן",
        "עדכון",
        "לעדכן",
        "ערוך",
        "עריכה",
        "edit",
        "update",
    }

    help_commands = {
        "עזרה",
        "help",
        "?",
    }

    site_commands = {
        "אתר",
        "לאתר",
        "דשבורד",
        "dashboard",
        "site",
        "web",
    }

    if normalized in list_commands:
        return "list"

    if normalized in summary_commands:
        return "summary"

    if normalized in delete_commands:
        return "delete"

    if normalized in update_commands:
        return "update"

    if normalized in help_commands:
        return "help"

    if normalized in site_commands:
        return "site"

    return None