"""Migration script to add adaptive first-week plan columns to learning_schedule table."""
import sqlite3
import os

DB_PATH = "palp_local.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    existing_cols = {row[1] for row in cursor.execute("PRAGMA table_info(learning_schedule)").fetchall()}

    columns_to_add = [
        ("subject", "VARCHAR(150)"),
        ("topic_name", "VARCHAR(200)"),
        ("learning_objective", "TEXT"),
        ("resource_title", "VARCHAR(255)"),
        ("resource_url", "TEXT"),
        ("practice_activity", "VARCHAR(255)"),
        ("mastery_target", "FLOAT DEFAULT 0.80"),
        ("follow_up_assessment", "VARCHAR(255)"),
        ("plan_reason", "TEXT"),
    ]

    for col_name, col_type in columns_to_add:
        if col_name not in existing_cols:
            print(f"Adding column {col_name} ({col_type}) to learning_schedule...")
            cursor.execute(f"ALTER TABLE learning_schedule ADD COLUMN {col_name} {col_type}")

    conn.commit()
    conn.close()
    print("learning_schedule table migration complete.")

if __name__ == "__main__":
    migrate()
