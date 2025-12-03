"""add_embedding_tables

Create embedding tables for semantic search in Trade Desk.

Revision ID: 535888366798
Revises: 6587cb2edd3a
Create Date: 2025-12-03

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector



# revision identifiers, used by Alembic.
revision = '535888366798'
down_revision = '6587cb2edd3a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create embedding tables with vector indexes."""
    
    # Requirement embeddings
    op.create_table(
        'requirement_embeddings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('requirement_id', sa.UUID(), nullable=False),
        sa.Column('embedding', Vector(384), nullable=False),
        sa.Column('text_hash', sa.String(64), nullable=False),
        sa.Column('model_version', sa.String(50), nullable=False, server_default='all-MiniLM-L6-v2'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['requirement_id'], ['requirements.id'], ondelete='CASCADE'),
    )
    
    op.create_index('ix_requirement_embeddings_requirement_id', 'requirement_embeddings', ['requirement_id'], unique=True)
    op.create_index('ix_requirement_embeddings_text_hash', 'requirement_embeddings', ['text_hash'])
    
    op.execute(
        'CREATE INDEX ix_requirement_embeddings_vector '
        'ON requirement_embeddings USING ivfflat (embedding vector_cosine_ops) '
        'WITH (lists = 100)'
    )
    
    # Availability embeddings
    op.create_table(
        'availability_embeddings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('availability_id', sa.UUID(), nullable=False),
        sa.Column('embedding', Vector(384), nullable=False),
        sa.Column('text_hash', sa.String(64), nullable=False),
        sa.Column('model_version', sa.String(50), nullable=False, server_default='all-MiniLM-L6-v2'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['availability_id'], ['availabilities.id'], ondelete='CASCADE'),
    )
    
    op.create_index('ix_availability_embeddings_availability_id', 'availability_embeddings', ['availability_id'], unique=True)
    op.create_index('ix_availability_embeddings_text_hash', 'availability_embeddings', ['text_hash'])
    
    op.execute(
        'CREATE INDEX ix_availability_embeddings_vector '
        'ON availability_embeddings USING ivfflat (embedding vector_cosine_ops) '
        'WITH (lists = 100)'
    )


def downgrade() -> None:
    """Drop embedding tables."""
    op.drop_table('availability_embeddings')
    op.drop_table('requirement_embeddings')
