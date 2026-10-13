"""Database migration script to add metadata columns to questions and learning_resources."""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "palp_local.db")

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Update questions table
    q_cols = [col[1] for col in cur.execute("PRAGMA table_info(questions)").fetchall()]
    new_q_cols = [
        ("source_url", "TEXT"),
        ("source_title", "VARCHAR(255)"),
        ("exam_year", "VARCHAR(100)"),
        ("license", "VARCHAR(100)"),
        ("verified", "BOOLEAN DEFAULT 1"),
    ]
    for col_name, col_type in new_q_cols:
        if col_name not in q_cols:
            print(f"Adding column {col_name} to questions table...")
            cur.execute(f"ALTER TABLE questions ADD COLUMN {col_name} {col_type}")

    # 2. Update learning_resources table
    lr_cols = [col[1] for col in cur.execute("PRAGMA table_info(learning_resources)").fetchall()]
    new_lr_cols = [
        ("provider", "VARCHAR(150) DEFAULT ''"),
        ("estimated_duration_min", "INTEGER DEFAULT 30"),
        ("difficulty", "VARCHAR(50) DEFAULT 'Intermediate'"),
        ("attribution", "TEXT DEFAULT ''"),
        ("license", "VARCHAR(100) DEFAULT ''"),
    ]
    for col_name, col_type in new_lr_cols:
        if col_name not in lr_cols:
            print(f"Adding column {col_name} to learning_resources table...")
            cur.execute(f"ALTER TABLE learning_resources ADD COLUMN {col_name} {col_type}")

    conn.commit()
    conn.close()
    print("Migration completed successfully.")

if __name__ == "__main__":
    migrate()
