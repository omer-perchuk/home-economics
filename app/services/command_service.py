def detect_command(message: str) -> str | None:
    message = message.strip().lower()

    command_keywords = {
        "delete": [
            "מחק",
            "למחוק",
            "מחיקה",
            "תמחק",
            "מחקי",
            "למחיקה",
        ],
        "update": [
            "עדכן",
            "עדכון",
            "לעדכן",
            "תעדכן",
            "תעדכני",
            "ערוך",
            "עריכה",
        ],
        "list": [
            "רשימה",
            "תראה",
            "הצג",
            "הוצאות",
            "תציג",
            "תראי",
            "תציגי",
            "רשומות",
        ],
        "summary": [
            "סיכום",
            "סיכום חודשי",
            "תסכם",
            "סכם",
            "תראי סיכום",
            "תראה סיכום",
        ],
        "help": [
            "עזרה",
            "help",
            "?",
            "מה אפשר לעשות",
            "מה אתה יודע לעשות",
            "פקודות",
        ],
    }

    for command, keywords in command_keywords.items():
        for keyword in keywords:
            if keyword in message:
                return command

    return None