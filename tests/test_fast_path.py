from datetime import date, datetime

import pytest

from app.bot.fast_path import parse_entries
from app.services.command_service import detect_command
from app.services.report_service import parse_month_input

TODAY = date(2026, 10, 13)  # יום שלישי


@pytest.mark.parametrize(
    "text, expected",
    [
        ("ארומה 20", [("ארומה", 20, None)]),
        ("סופר 340, דלק 250", [("סופר", 340, None), ("דלק", 250, None)]),
        ("סופר 340\nדלק 250 שלשום", [("סופר", 340, None), ("דלק", 250, date(2026, 10, 11))]),
        ("ארומה 20 אתמול", [("ארומה", 20, date(2026, 10, 12))]),
        ("דלק 250 ביום ראשון", [("דלק", 250, date(2026, 10, 11))]),
        ("קפה 18 12/10", [("קפה", 18, date(2026, 10, 12))]),
        ("שילמתי 50 על דלק", [("דלק", 50, None)]),
        ("₪20 קפה", [("קפה", 20, None)]),
        ('רמי לוי 200 ש"ח', [("רמי לוי", 200, None)]),
        ("שופרסל 1,200", [("שופרסל", 1200, None)]),
        ("טיסה 1.5k", [("טיסה", 1500, None)]),
        ("משכורת 12000", [("משכורת", 12000, None)]),
        ("דייג 80", [("דייג", 80, None)]),
        ("ויקטורי 120", [("ויקטורי", 120, None)]),
    ],
)
def test_parse_entries(text, expected):
    entries = parse_entries(text, TODAY)
    assert [(e["description"], e["amount"], e["date"]) for e in entries] == expected


@pytest.mark.parametrize(
    "text",
    [
        "תמחק את הקפה 20",          # בקשה – לסוכן
        "כמה הוצאתי על קפה",        # שאלה בלי סכום
        "קפה 20?",                  # סימן שאלה
        "כביש 6 40",                # שני מספרים – לא ברור מה הסכום
        "50",                       # סכום בלי תיאור
        "סופר 340, דלק",            # חלק בלי סכום – לא רושמים חצי
        "",
    ],
)
def test_parse_entries_rejects_non_simple(text):
    assert parse_entries(text, TODAY) is None


@pytest.mark.parametrize(
    "text, expected",
    [
        ("דייג 80", None),                     # היה מזוהה כ"ביטול" (מכיל "דיי")
        ("הוצאות רכב 300", None),              # היה מזוהה כ"רשימה"
        ("מתקן 200", None),                     # היה מזוהה כ"עדכון" (מכיל "תקן")
        ("יצאנו לפיצה 90", None),
        ("סיכום", "summary"),
        ("סיכום ספטמבר", "summary"),
        ("סיכום 9/2026", "summary"),
        ("כמה הוצאתי החודש", "summary"),
        ("מחק", "delete"),
        ("ביטול", "cancel"),
        ("הוראת קבע", "recurring"),
        ("עזרה", "help"),
        ("תמחק את הקפה של אתמול", None),      # ארוך – לסוכן
    ],
)
def test_detect_command(text, expected):
    assert detect_command(text) == expected


def test_detect_command_non_strict_allows_long_messages():
    assert detect_command("תמחק את הקפה של אתמול", strict=False) == "delete"


@pytest.mark.parametrize(
    "text, expected",
    [
        ("3/2026", (3, 2026)),
        ("מרץ 2026", (3, 2026)),
        ("סיכום ספטמבר", (9, 2026)),
        ("סיכום נובמבר", (11, 2025)),
        ("סיכום שעבר", (9, 2026)),
        ("סיכום חודש שעבר", (9, 2026)),
        ("החודש", (10, 2026)),
        ("סיכום 9", (9, 2026)),
        ("סיכום", None),
    ],
)
def test_parse_month_input(text, expected):
    assert parse_month_input(text, datetime(2026, 10, 13)) == expected
