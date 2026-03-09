COMMAND_KEYWORDS = {

    "summary": [
        "סיכום",
        "סכם",
        "מה הסיכום",
        "כמה הוצאתי",
        "כמה הוצאות",
        "כמה הוצאנו",
        "מה מצב החשבון",
        "מצב",
        "סטטוס"
    ],

    "list": [
        "הצג",
        "תראה",
        "רשימה",
        "רשימת הוצאות",
        "תראה הוצאות",
        "הוצאות",
        "מה הוצאתי",
        "מה הוצאנו"
    ],

    "delete": [
        "מחק",
        "למחוק",
        "מחיקה",
        "תמחק",
        "תמחוק",
        "הסר",
        "להסיר"
    ],

    "update": [
        "עדכן",
        "לעדכן",
        "עדכון",
        "שנה",
        "לשנות",
        "שינוי",
        "לתקן",
        "תקן"
    ],

    "site": [
        "אתר",
        "פתח אתר",
        "שלח אתר",
        "דשבורד",
        "dashboard",
        "קישור"
    ],

    "help": [
        "עזרה",
        "פקודות",
        "מה אפשר",
        "איך משתמשים",
        "איך להשתמש",
        "help"
    ]
}


def detect_command(text: str):

    text = text.lower()

    for command, keywords in COMMAND_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                return command

    return None