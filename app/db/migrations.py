"""מיגרציות קטנות שרצות בעליית השרת.

`Base.metadata.create_all` יוצר טבלאות חדשות, אבל לא מוסיף עמודות לטבלה
שכבר קיימת. כאן מוסיפים עמודות חסרות בצורה בטוחה: אם העמודה כבר קיימת,
לא קורה כלום. עובד גם על Postgres (Neon) וגם על SQLite מקומי.
"""

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine


def _add_column_if_missing(engine: Engine, table: str, column: str, ddl_type: str) -> None:
    existing = {c["name"] for c in inspect(engine).get_columns(table)}
    if column in existing:
        return
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}"))


def run_migrations(engine: Engine) -> None:
    if not inspect(engine).has_table("users"):
        return

    _add_column_if_missing(engine, "users", "google_sub", "VARCHAR")
    _add_column_if_missing(engine, "users", "email", "VARCHAR")

    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_google_sub "
                "ON users (google_sub)"
            )
        )
