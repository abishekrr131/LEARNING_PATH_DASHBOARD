"""0001_initial

Revision ID: 0001_initial
Revises: None
Create Date: 2026-10-12
"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from backend.app.models.base import Base
import backend.app.models  # ensure all models registered

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure pgvector extension exists
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    # Create all tables declared in Base.metadata
    bind = op.get_bind()
    Base.metadata.create_all(bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind)
