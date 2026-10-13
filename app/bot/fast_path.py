"""
המסלול המהיר: פרסור דטרמיניסטי של הודעות בפורמט מוכר ("ארומה 20", "סופר 340, דלק 250 אתמול").
אין כאן קריאות ל-DB או ל-LLM – רק טקסט פנימה, רשומות החוצה.
אם ההודעה לא בפורמט פשוט מחזירים None, וההודעה עוברת לסוכן.
"""
import re
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

try:
    from zoneinfo import ZoneInfo

    ISRAEL_TZ = ZoneInfo("Asia/Jerusalem")
except Exception:  # אין tzdata במערכת
    ISRAEL_TZ = timezone(timedelta(hours=2))


MAX_DESCRIPTION_WORDS = 5

# מילים בתחילת הודעה שמעידות על בקשה (ולא על רשומה) – הולך לסוכן
AGENT_TRIGGER_WORDS = {
    "תמחק", "מחק", "למחוק", "תמחוק",
    "תוריד", "להוריד", "הורד",
    "תעדכן", "עדכן", "לעדכן",
    "תשנה", "שנה", "לשנות",
    "תתקן", "תקן", "לתקן",
    "תבטל", "בטל", "לבטל",
    "תעביר", "להעביר",
    "תראה", "הראה", "תציג", "הצג",
    "כמה", "מה", "מתי", "איך", "למה", "האם", "איפה", "מי",
}

# מילות מילוי שמורידים מתחילת התיאור
FILLER_WORDS = {
    "שילמתי", "שילמנו", "קניתי", "קנינו", "הוצאתי", "הוצאנו",
    "תוסיף", "הוסף", "להוסיף", "תרשום", "רשום", "לרשום",
    "על", "ב", "של",
}

CURRENCY_PATTERN = r'₪|ש"ח|ש״ח|שח|שקלים|שקל|nis|ils'

WEEKDAYS = {
    "ראשון": 6,
    "שני": 0,
    "שלישי": 1,
    "רביעי": 2,
    "חמישי": 3,
    "שישי": 4,
    "שבת": 5,
}

RELATIVE_DAYS = {
    "היום": 0,
    "אתמול": 1,
    "שלשום": 2,
}


def today_il() -> date:
    return datetime.now(ISRAEL_TZ).date()


def _normalize_amounts(text: str) -> str:
    # 1,200 -> 1200
    text = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", text)
    # 1.5k / 2K -> 1500 / 2000
    text = re.sub(
        r"(\d+(?:\.\d+)?)\s*[kK](?![a-zA-Z])",
        lambda m: _format_number(float(m.group(1)) * 1000),
        text,
    )
    # 2 אלף -> 2000
    text = re.sub(
        r"(\d+(?:\.\d+)?)\s*אלף",
        lambda m: _format_number(float(m.group(1)) * 1000),
        text,
    )
    # מטבע – מסירים לגמרי
    text = re.sub(rf"(?<![א-תa-zA-Z])(?:{CURRENCY_PATTERN})(?![א-תa-zA-Z])", " ", text, flags=re.IGNORECASE)
    return text


def _format_number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return str(value)


def extract_date(text: str, today: Optional[date] = None):
    """
    מחפש ביטוי תאריך בטקסט. מחזיר (date או None, הטקסט בלי ביטוי התאריך).
    """
    today = today or today_il()

    # 12/10 או 12/10/2026 או 12/10/26
    match = re.search(r"(?<![\d/])(\d{1,2})/(\d{1,2})(?:/(\d{2}|\d{4}))?(?![\d/])", text)
    if match:
        day, month = int(match.group(1)), int(match.group(2))
        year = match.group(3)
        if year:
            year = int(year)
            if year < 100:
                year += 2000
        else:
            year = today.year
        try:
            result = date(year, month, day)
        except ValueError:
            result = None

        if result:
            if not match.group(3) and result > today:
                result = date(year - 1, month, day)
            return result, (text[: match.start()] + " " + text[match.end():])

    # ביום ראשון / יום שני
    weekday_pattern = "|".join(WEEKDAYS.keys())
    match = re.search(rf"(?:^|\s)ב?יום\s+({weekday_pattern})(?=\s|$)", text)
    if match:
        target = WEEKDAYS[match.group(1)]
        delta = (today.weekday() - target) % 7
        return today - timedelta(days=delta), (text[: match.start()] + " " + text[match.end():])

    # היום / אתמול / שלשום (גם עם ב/מ בהתחלה)
    relative_pattern = "|".join(RELATIVE_DAYS.keys())
    match = re.search(rf"(?:^|\s)[במ]?({relative_pattern})(?=\s|$)", text)
    if match:
        delta = RELATIVE_DAYS[match.group(1)]
        return today - timedelta(days=delta), (text[: match.start()] + " " + text[match.end():])

    return None, text


def _clean_description(text: str) -> str:
    text = re.sub(r"[-–:•*,;]+", " ", text)
    words = text.split()

    while words and words[0] in FILLER_WORDS:
        words.pop(0)
    while words and words[-1] in FILLER_WORDS:
        words.pop()

    return " ".join(words).strip()


def parse_single_entry(part: str, today: Optional[date] = None) -> Optional[dict]:
    part = part.strip()
    if not part or "?" in part:
        return None

    entry_date, without_date = extract_date(part, today)
    normalized = _normalize_amounts(without_date)

    numbers = re.findall(r"(?<![\d.])\d+(?:\.\d+)?(?![\d.])", normalized)
    if len(numbers) != 1:
        return None

    amount = float(numbers[0])
    if amount <= 0:
        return None

    description_raw = re.sub(r"(?<![\d.])\d+(?:\.\d+)?(?![\d.])", " ", normalized, count=1)
    first_word = description_raw.split()[0] if description_raw.split() else ""
    if first_word in AGENT_TRIGGER_WORDS:
        return None

    description = _clean_description(description_raw)
    if not description:
        return None

    if len(description.split()) > MAX_DESCRIPTION_WORDS:
        return None

    return {
        "original_text": part,
        "description": description,
        "amount": amount,
        "date": entry_date,
    }


def parse_entries(text: str, today: Optional[date] = None) -> Optional[List[dict]]:
    """
    מפרק הודעה לרשומה אחת או יותר. מחזיר None אם משהו בהודעה לא בפורמט פשוט –
    עדיף לשלוח לסוכן מאשר לרשום משהו לא נכון.
    """
    if not text or not text.strip():
        return None

    # פסיק בין ספרות הוא מפריד אלפים, לא מפריד רשומות
    protected = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", text)
    parts = [p for p in re.split(r"[\n,;]+", protected) if p.strip()]

    if not parts:
        return None

    entries = []
    for part in parts:
        entry = parse_single_entry(part, today)
        if entry is None:
            return None
        entries.append(entry)

    return entries
