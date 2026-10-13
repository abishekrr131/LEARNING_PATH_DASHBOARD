"""Migrates SQLite palp_local.db to update check constraints for:
1. assessments: allows type 'weekly_test'
2. questions: allows source 'gemini' and review_status 'generated'
"""
import sqlite3
from pathlib import Path

db_path = Path("palp_local.db")

def migrate():
    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA foreign_keys = OFF")
    cur = con.cursor()

    cur.execute("BEGIN TRANSACTION")

    # 1. Migrate assessments table
    cur.execute("""
    CREATE TABLE assessments_new (
        id INTEGER NOT NULL, 
        user_id INTEGER NOT NULL, 
        type VARCHAR(30) NOT NULL, 
        target_id INTEGER NOT NULL, 
        started_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, 
        completed_at DATETIME, 
        score FLOAT, 
        PRIMARY KEY (id), 
        CONSTRAINT assessment_type_enum CHECK (type IN ('initial','verification','practice','followup','probe','special','weekly_test')), 
        FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
        FOREIGN KEY(target_id) REFERENCES career_targets (id)
    )
    """)
    cur.execute("INSERT INTO assessments_new SELECT * FROM assessments")
    cur.execute("DROP TABLE assessments")
    cur.execute("ALTER TABLE assessments_new RENAME TO assessments")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_assessments_user_id ON assessments (user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_assessments_target_id ON assessments (target_id)")

    # 2. Migrate questions table
    cur.execute("""
    CREATE TABLE questions_new (
        id INTEGER NOT NULL, 
        concept_id INTEGER NOT NULL, 
        question_text TEXT NOT NULL, 
        options_json JSON NOT NULL, 
        correct_answer VARCHAR(10) NOT NULL, 
        explanation TEXT NOT NULL, 
        difficulty_hint FLOAT NOT NULL, 
        source VARCHAR(20) NOT NULL, 
        review_status VARCHAR(20) NOT NULL, 
        reviewed_by INTEGER, 
        needs_human_review BOOLEAN NOT NULL, 
        PRIMARY KEY (id), 
        CONSTRAINT src_enum CHECK (source IN ('curated','ai_generated','imported','gemini')), 
        CONSTRAINT rev_enum CHECK (review_status IN ('pending','approved','rejected','generated')), 
        CONSTRAINT scorable_items_must_be_reviewed CHECK (source IN ('curated','gemini') OR review_status IN ('approved','generated')), 
        FOREIGN KEY(concept_id) REFERENCES concepts (id) ON DELETE CASCADE, 
        FOREIGN KEY(reviewed_by) REFERENCES users (id) ON DELETE SET NULL
    )
    """)
    cur.execute("INSERT INTO questions_new SELECT * FROM questions")
    cur.execute("DROP TABLE questions")
    cur.execute("ALTER TABLE questions_new RENAME TO questions")
    cur.execute("CREATE INDEX IF NOT EXISTS ix_questions_concept_id ON questions (concept_id)")

    con.commit()
    con.execute("PRAGMA foreign_keys = ON")
    con.close()
    print("Successfully updated palp_local.db constraints for assessments and questions tables!")

if __name__ == "__main__":
    migrate()
