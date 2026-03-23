import json
from openai import OpenAI

client = OpenAI()

ALLOWED_CATEGORIES = [
    "סופר וקניות לבית",
    "אוכל בחוץ וקפה",
    "תחבורה",
    "בריאות ופארם",
    "דיור וחשבונות",
    "בילויים ופנאי",
    "ביגוד והנעלה",
    "ילדים ומשפחה",
    "לימודים",
    "חופשות ונסיעות",
    "מתנות ותרומות",
    "ביטוחים",
    "חיות מחמד",
    "משכורת",
    "החזרים",
    "הכנסות",
    "אחר",
]


def _normalize_result(data, original_text):
    description = str(data.get("description", "")).strip() or original_text.strip()
    amount = data.get("amount", 0)
    tx_type = str(data.get("type", "expense")).strip().lower()
    category = str(data.get("category", "אחר")).strip()

    try:
        amount = float(amount)
    except Exception:
        amount = 0.0

    if tx_type not in ["expense", "income"]:
        tx_type = "expense"

    if category not in ALLOWED_CATEGORIES:
        category = "אחר"

    return {
        "description": description,
        "amount": amount,
        "type": tx_type,
        "category": category,
        "original_text": original_text,
    }


def categorize_transaction_text(user_text):
    categories_text = ", ".join(ALLOWED_CATEGORIES)

    prompt = f"""
אתה מסווג הודעות של ניהול הוצאות והכנסות למשק בית.

החזר JSON בלבד, בלי markdown ובלי הסברים.

מבנה חובה:
{{
  "description": "string",
  "amount": number,
  "type": "expense או income",
  "category": "אחת מהקטגוריות המותרות בלבד"
}}

קטגוריות מותרות:
{categories_text}

חוקים:
- אם זו הוצאה → type = expense
- אם זו הכנסה → type = income
- category חייבת להיות אחת מהרשימה בלבד
- amount חייב להיות מספר בלבד
- description צריך להיות קצר וברור
- אם אינך בטוח → category = "אחר"

⚠️ חוקים חשובים לסיווג:
- בתי קפה, מסעדות, juice bar → "אוכל בחוץ וקפה"
- סופרמרקטים, מכולת → "סופר וקניות לבית"
- תחנות דלק → "תחבורה"
- פארם / בתי מרקחת → "בריאות ופארם"
- בגדים / מותגי אופנה → "ביגוד והנעלה"

⚡ דוגמאות אמיתיות:
- "ארומה 18" → אוכל בחוץ וקפה
- "rebar 35" → אוכל בחוץ וקפה
- "yellow 20" → תחבורה
- "קפה לנדוור 40" → אוכל בחוץ וקפה

- "רמי לוי 200" → סופר וקניות לבית
- "שופרסל 150" → סופר וקניות לבית

- "גולף קידס 120" → ביגוד והנעלה
- "זארה 300" → ביגוד והנעלה

- "פז 300" → תחבורה

טקסט המשתמש:
{user_text}
""".strip()

    response = client.responses.create(
        model="gpt-4o-mini",
        input=prompt,
    )

    content = response.output_text.strip()

    try:
        data = json.loads(content)
        return _normalize_result(data, user_text)
    except Exception:
        return {
            "description": user_text.strip(),
            "amount": 0.0,
            "type": "expense",
            "category": "אחר",
            "original_text": user_text,
        }