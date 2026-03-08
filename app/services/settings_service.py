import json
import os

SETTINGS_FILE = "data/app_settings.json"


def ensure_settings_file():
    os.makedirs("data", exist_ok=True)

    if not os.path.exists(SETTINGS_FILE):
        default_settings = {
            "dashboard_title": "כלכלת הבית"
        }
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(default_settings, f, ensure_ascii=False, indent=2)


def get_settings():
    ensure_settings_file()

    with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def update_dashboard_title(new_title: str):
    ensure_settings_file()

    settings = get_settings()
    settings["dashboard_title"] = new_title

    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

    return settings