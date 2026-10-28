"""
Diagnostic check to inspect the exact column type of options_json in the live database
and confirm that the INSERT statement matches it.
"""
from __future__ import annotations
import sys
import os
import sqlalchemy as sa

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_live_options_json_column_type(engine):
    with engine.connect() as conn:
        # Check dialect
        dialect_name = engine.dialect.name
        if dialect_name == "postgresql":
            row = conn.execute(sa.text("""
                SELECT data_type, udt_name
                FROM information_schema.columns
                WHERE table_name = 'questions' AND column_name = 'options_json'
            """)).fetchone()
            if row:
                print(f"PostgreSQL information_schema: data_type='{row[0]}', udt_name='{row[1]}'")
                return row[1].upper() # e.g. 'JSON' or 'JSONB'
        else:
            print(f"Non-PostgreSQL dialect: {dialect_name}")
            return "JSON"
    return "JSON"

if __name__ == "__main__":
    print("Column inspector ready.")
