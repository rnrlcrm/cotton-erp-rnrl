"""add_event_outbox_table

Revision ID: 001_outbox
Revises: 
Create Date: 2025-11-30

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_outbox'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create event_outbox table for Transactional Outbox pattern"""
    
    # Create outbox_status enum
    op.execute("""
        CREATE TYPE outbox_status AS ENUM ('pending', 'published', 'failed', 'processing')
    """)
    
    # Create event_outbox table
    op.create_table(
        'event_outbox',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('aggregate_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('aggregate_type', sa.String(50), nullable=False, index=True),
        sa.Column('event_type', sa.String(100), nullable=False, index=True),
        sa.Column('payload', postgresql.JSONB, nullable=False),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('status', sa.Enum('pending', 'published', 'failed', 'processing', name='outbox_status'), nullable=False, index=True),
        sa.Column('retry_count', sa.Integer, nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer, nullable=False, server_default='5'),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True, index=True),
        sa.Column('last_error', sa.Text, nullable=True),
        sa.Column('topic_name', sa.String(200), nullable=False, index=True),
        sa.Column('message_id', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()'), index=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('idempotency_key', sa.String(255), nullable=True, unique=True, index=True),
        sa.Column('version', sa.Integer, nullable=False, server_default='1'),
    )
    
    # Create indexes for efficient querying
    op.create_index('idx_outbox_status_created', 'event_outbox', ['status', 'created_at'])
    op.create_index('idx_outbox_status_next_retry', 'event_outbox', ['status', 'next_retry_at'])
    op.create_index('idx_outbox_topic_created', 'event_outbox', ['topic_name', 'created_at'])


def downgrade() -> None:
    """Drop event_outbox table"""
    op.drop_index('idx_outbox_topic_created', table_name='event_outbox')
    op.drop_index('idx_outbox_status_next_retry', table_name='event_outbox')
    op.drop_index('idx_outbox_status_created', table_name='event_outbox')
    op.drop_table('event_outbox')
    op.execute('DROP TYPE outbox_status')
