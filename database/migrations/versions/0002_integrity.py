"""0002_integrity

Revision ID: 0002_integrity
Revises: 0001_initial
Create Date: 2026-10-12
"""
from alembic import op

revision = "0002_integrity"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

DAG_TRIGGER = """
CREATE OR REPLACE FUNCTION assert_dag() RETURNS trigger AS $$
BEGIN
  IF EXISTS (
    WITH RECURSIVE walk(n) AS (
      SELECT NEW.dependent_concept_id
      UNION
      SELECT d.dependent_concept_id
        FROM concept_dependencies d
        JOIN walk ON d.prerequisite_concept_id = walk.n
    )
    SELECT 1 FROM walk WHERE n = NEW.prerequisite_concept_id
  ) THEN
    RAISE EXCEPTION 'prerequisite cycle: % -> %',
      NEW.prerequisite_concept_id, NEW.dependent_concept_id;
  END IF;
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_dag ON concept_dependencies;
CREATE TRIGGER trg_dag
  BEFORE INSERT OR UPDATE ON concept_dependencies
  FOR EACH ROW EXECUTE FUNCTION assert_dag();
"""


def upgrade() -> None:
    # 1. Install DAG acyclicity trigger function and trigger
    op.execute(DAG_TRIGGER)

    # 2. HNSW cosine index for pgvector resource semantic matching (spec §7.3, §16.1)
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_resource_embedding 
        ON learning_resources 
        USING hnsw (embedding vector_cosine_ops)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_resource_embedding")
    op.execute("DROP TRIGGER IF EXISTS trg_dag ON concept_dependencies")
    op.execute("DROP FUNCTION IF EXISTS assert_dag()")
