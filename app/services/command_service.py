import re

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
        "תעדכן",
        "לעדכן",
        "עדכון",
        "ערוך",
        "תערוך",
        "עריכה",
        "לערוך",
        "ערוך רשומה",
        "עריכה לרשומה",
        "שנה רשומה",
        "לשנות רשומה",
        "תשנה רשומה",
        "עדכן רשומה",
        "תעדכן רשומה",
        "שנה",
        "לשנות",
        "שינוי",
        "לתקן",
        "תקן",
        "לתקן רשומה",
        "תקן רשומה",
        "edit",
        "modify"
    ],

    "recurring": [
        "הוראת קבע",
        "הוראות קבע",
        "תשלום קבוע",
        "תשלומים קבועים",
        "הוראת קבע חדשה",
        "recurring"
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
    ],

    "cancel": [
        "ביטול",
        "בטל",
        "לבטל",
        "cancel",
        "יציאה",
        "חזרה",
        "עצור",
        "צא",
        "נו באי",
        "דיי"
    ]
}


# כמה מילים מותר להוסיף אחרי מילת הפקודה ("סיכום ספטמבר", "מחק אחרון").
# הודעה ארוכה יותר היא בקשה חופשית – הולכת לסוכן.
MAX_EXTRA_WORDS = {"summary": 2}
DEFAULT_MAX_EXTRA_WORDS = 1


def _tokenize(text: str):
    return re.sub(r"[^\w\s/]", " ", text.lower()).split()


def detect_command(text: str, strict: bool = True):
    """
    מזהה פקודה רק כשההודעה מתחילה במילת הפקודה (מילים שלמות).
    בעבר נבדק keyword in text, כך ש"דייג 80" זוהה כביטול (מכיל "דיי")
    ו"הוצאות רכב 300" זוהה כרשימה.

    strict=False (כשהסוכן כבוי) – לא מגבילים את אורך ההודעה.
    """
    tokens = _tokenize(text)
    if not tokens:
        return None

    has_amount = any(re.fullmatch(r"\d+(?:\.\d+)?", t) for t in tokens)

    best = None
    best_length = 0

    for command, keywords in COMMAND_KEYWORDS.items():
        # הודעה עם סכום היא רשומה, חוץ מ"סיכום 9/2026" וכדומה
        if has_amount and command != "summary":
            continue

        for keyword in keywords:
            keyword_tokens = keyword.lower().split()
            if tokens[: len(keyword_tokens)] != keyword_tokens:
                continue

            extra = len(tokens) - len(keyword_tokens)
            if strict and extra > MAX_EXTRA_WORDS.get(command, DEFAULT_MAX_EXTRA_WORDS):
                continue

            if len(keyword_tokens) > best_length:
                best = command
                best_length = len(keyword_tokens)

    return best
