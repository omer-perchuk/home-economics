import json
from pathlib import Path

DEFAULT_CATEGORIES = {
    "אוכל בחוץ וקפה": [
        "ארומה", "קפה", "קופיקס", "מסעדה", "מקדונלדס", "בורגר", "פיצה",
        "סושי", "בית קפה", "וולט", "תן ביס", "קפה גרג", "ארקפה"
    ],
    "סופר וקניות לבית": [
        "שופרסל", "רמי לוי", "ויקטורי", "יוחננוף", "סופר", "מכולת",
        "קניות", "טיב טעם", "קרפור", "אושר עד"
    ],
    "תחבורה": [
        "דלק", "רכבת", "אוטובוס", "מונית", "פז", "סונול", "דור אלון",
        "חניה", "כביש 6", "רב קו"
    ],
    "דיור וחשבונות": [
        "ארנונה", "חשמל", "מים", "גז", "שכר דירה", "שכירות", "ועד בית",
        "אינטרנט", "סלקום", "פלאפון", "פרטנר", "הוט", "yes", "יס"
    ],
    "בריאות ופארם": [
        "סופר פארם", "בית מרקחת", "תרופה", "רופא", "בדיקה", "פארם", "כללית"
    ],
    "בילויים ופנאי": [
        "סרט", "קולנוע", "הופעה", "בילוי", "מתנה", "פנאי", "חופשה"
    ],
    "הכנסות": [
        "משכורת", "שכר", "הכנסה", "בונוס", "החזר"
    ],
    "אחר": []
}


def load_categories():
    base_dir = Path(__file__).resolve().parents[2]
    categories_file = base_dir / "data" / "categories.json"

    if categories_file.exists():
        with open(categories_file, "r", encoding="utf-8") as file:
            return json.load(file)

    return DEFAULT_CATEGORIES


def detect_category(description: str) -> str:
    if not description:
        return "אחר"

    categories = load_categories()
    description_lower = description.lower()

    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword.lower() in description_lower:
                return category

    return "אחר"