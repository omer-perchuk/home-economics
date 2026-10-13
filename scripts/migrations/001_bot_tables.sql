-- טבלאות חדשות לבוט/סוכן. רק מוסיף – לא משנה טבלאות קיימות.
-- Base.metadata.create_all ב-startup יוצר אותן אוטומטית; הקובץ הזה לתיעוד / הרצה ידנית מול Neon.

CREATE TABLE IF NOT EXISTS conversation_states (
    phone VARCHAR PRIMARY KEY,
    state_json TEXT NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS processed_messages (
    message_id VARCHAR PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bot_events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    family_id INTEGER REFERENCES families(id),
    role VARCHAR NOT NULL,
    content TEXT NOT NULL,
    action_json TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_bot_events_user_id ON bot_events (user_id);
CREATE INDEX IF NOT EXISTS ix_bot_events_family_id ON bot_events (family_id);
CREATE INDEX IF NOT EXISTS ix_bot_events_created_at ON bot_events (created_at);

-- חזרה אחורה (אם צריך):
-- DROP TABLE bot_events; DROP TABLE processed_messages; DROP TABLE conversation_states;
