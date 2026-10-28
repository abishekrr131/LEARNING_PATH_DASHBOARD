def get_options_json_col_type(engine):
    """Detects whether PostgreSQL questions.options_json is JSON or JSONB."""
    import sqlalchemy as sa
    from sqlalchemy.dialects import postgresql
    if engine.dialect.name == "postgresql":
        try:
            with engine.connect() as conn:
                row = conn.execute(sa.text("""
                    SELECT udt_name FROM information_schema.columns 
                    WHERE table_name = 'questions' AND column_name = 'options_json'
                """)).fetchone()
                if row and row[0].lower() == "jsonb":
                    return postgresql.JSONB
        except Exception:
            pass
    return sa.JSON
