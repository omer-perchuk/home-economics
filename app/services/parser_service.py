import re

from app.services.category_service import detect_category


def clean_amount_text(text: str) -> str:
    text = text.replace("₪", "")
    text = text.replace(",", "")
    return text


def extract_amount(text: str):
    text = clean_amount_text(text)

    match = re.search(r"(\d+(?:\.\d{1,2})?)", text)
    if not match:
        return None, None

    amount = float(match.group(1))
    return amount, match


def clean_description(text: str, amount_match) -> str:
    if not amount_match:
        return text.strip()

    description = text[:amount_match.start()] + text[amount_match.end():]
    description = description.strip()

    phrases_to_remove = [
        "קניתי",
        "שילמתי",
        "שולם",
        "על",
        "ב",
        "עבור",
        "הוצאתי",
        "עלה לי",
        "הכנסתי",
        "קיבלתי",
    ]

    for phrase in phrases_to_remove:
        description = re.sub(rf"\b{phrase}\b", "", description, flags=re.IGNORECASE)

    description = re.sub(r"\s+", " ", description).strip()
    return description


def detect_transaction_type(description: str, category: str) -> str:
    income_keywords = ["משכורת", "הכנסה", "בונוס", "החזר", "שכר", "קיבלתי"]

    if category == "הכנסות":
        return "income"

    for word in income_keywords:
        if word in description:
            return "income"

    return "expense"


def parse_expense_text(text: str) -> dict:
    original_text = text.strip()

    amount, amount_match = extract_amount(original_text)

    if amount is None:
        return {
            "original_text": original_text,
            "description": original_text,
            "amount": None,
            "type": "expense",
            "category": "אחר",
            "error": "No amount found",
        }

    description = clean_description(original_text, amount_match)

    if not description:
        description = "ללא תיאור"

    category = detect_category(description)
    transaction_type = detect_transaction_type(description, category)

    return {
        "original_text": original_text,
        "description": description,
        "amount": amount,
        "type": transaction_type,
        "category": category,
        "error": None,
    }