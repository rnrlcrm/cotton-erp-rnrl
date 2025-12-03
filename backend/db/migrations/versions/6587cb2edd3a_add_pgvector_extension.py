"""add_pgvector_extension

Enable pgvector extension for vector similarity search.
This is the foundation for AI-powered semantic search.

Revision ID: 6587cb2edd3a
Revises: 10a27d6b7de1
Create Date: 2025-12-03

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision = '6587cb2edd3a'
down_revision = '10a27d6b7de1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Enable pgvector extension for PostgreSQL."""
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')


def downgrade() -> None:
    """Remove pgvector extension."""
    op.execute('DROP EXTENSION IF EXISTS vector CASCADE')
