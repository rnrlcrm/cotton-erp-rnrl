"""Add negotiation tables

Revision ID: 829002a353b4
Revises: 68b3985ccb14
Create Date: 2025-12-04 07:31:54.035266

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '829002a353b4'
down_revision = '68b3985ccb14'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create negotiations table
    op.create_table(
        'negotiations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('match_token_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column('requirement_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('availability_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('buyer_partner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('seller_partner_id', postgresql.UUID(as_uuid=True), nullable=False),
        
        sa.Column('status', sa.String(20), nullable=False, server_default='INITIATED'),
        sa.Column('current_round', sa.Integer, nullable=False, server_default='0'),
        sa.Column('current_price_per_unit', sa.Numeric(12, 2), nullable=True),
        sa.Column('current_quantity', sa.Integer, nullable=True),
        sa.Column('current_terms', postgresql.JSONB, nullable=True),
        sa.Column('last_offer_by', sa.String(10), nullable=True),
        
        sa.Column('initiated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        
        sa.Column('accepted_by', sa.String(10), nullable=True),
        sa.Column('rejected_by', sa.String(10), nullable=True),
        sa.Column('rejection_reason', sa.Text, nullable=True),
        sa.Column('trade_id', postgresql.UUID(as_uuid=True), nullable=True),
        
        sa.Column('ai_suggestions_enabled', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('auto_negotiate_buyer', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('auto_negotiate_seller', sa.Boolean, nullable=False, server_default='false'),
        
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        
        sa.ForeignKeyConstraint(['match_token_id'], ['match_tokens.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['requirement_id'], ['requirements.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['availability_id'], ['availabilities.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['buyer_partner_id'], ['business_partners.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['seller_partner_id'], ['business_partners.id'], ondelete='CASCADE'),
        
        sa.CheckConstraint("status IN ('INITIATED', 'IN_PROGRESS', 'ACCEPTED', 'REJECTED', 'EXPIRED')", name='valid_negotiation_status'),
        sa.CheckConstraint("accepted_by IN ('BUYER', 'SELLER') OR accepted_by IS NULL", name='valid_accepted_by'),
        sa.CheckConstraint("rejected_by IN ('BUYER', 'SELLER') OR rejected_by IS NULL", name='valid_rejected_by'),
        sa.CheckConstraint("last_offer_by IN ('BUYER', 'SELLER') OR last_offer_by IS NULL", name='valid_last_offer_by'),
        sa.CheckConstraint('current_price_per_unit > 0 OR current_price_per_unit IS NULL', name='positive_price'),
        sa.CheckConstraint('current_quantity > 0 OR current_quantity IS NULL', name='positive_quantity'),
    )
    
    # Create indexes for negotiations
    op.create_index('ix_negotiations_match_token_id', 'negotiations', ['match_token_id'])
    op.create_index('ix_negotiations_requirement_id', 'negotiations', ['requirement_id'])
    op.create_index('ix_negotiations_availability_id', 'negotiations', ['availability_id'])
    op.create_index('ix_negotiations_buyer_partner_id', 'negotiations', ['buyer_partner_id'])
    op.create_index('ix_negotiations_seller_partner_id', 'negotiations', ['seller_partner_id'])
    op.create_index('ix_negotiations_status', 'negotiations', ['status'])
    op.create_index('ix_negotiations_expires_at', 'negotiations', ['expires_at'])
    
    # Create negotiation_offers table
    op.create_table(
        'negotiation_offers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('negotiation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('round_number', sa.Integer, nullable=False),
        sa.Column('offered_by', sa.String(10), nullable=False),
        
        sa.Column('price_per_unit', sa.Numeric(12, 2), nullable=False),
        sa.Column('quantity', sa.Integer, nullable=False),
        sa.Column('delivery_terms', postgresql.JSONB, nullable=True),
        sa.Column('payment_terms', postgresql.JSONB, nullable=True),
        sa.Column('quality_conditions', postgresql.JSONB, nullable=True),
        
        sa.Column('message', sa.Text, nullable=True),
        sa.Column('ai_generated', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('ai_confidence', sa.Float, nullable=True),
        sa.Column('ai_reasoning', sa.Text, nullable=True),
        
        sa.Column('status', sa.String(20), nullable=False, server_default='PENDING'),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('response_message', sa.Text, nullable=True),
        
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        
        sa.ForeignKeyConstraint(['negotiation_id'], ['negotiations.id'], ondelete='CASCADE'),
        
        sa.CheckConstraint("offered_by IN ('BUYER', 'SELLER')", name='valid_offered_by'),
        sa.CheckConstraint("status IN ('PENDING', 'ACCEPTED', 'REJECTED', 'COUNTERED', 'EXPIRED')", name='valid_offer_status'),
        sa.CheckConstraint('round_number > 0', name='positive_round'),
        sa.CheckConstraint('price_per_unit > 0', name='positive_offer_price'),
        sa.CheckConstraint('quantity > 0', name='positive_offer_quantity'),
        sa.CheckConstraint('ai_confidence >= 0 AND ai_confidence <= 1 OR ai_confidence IS NULL', name='valid_confidence'),
    )
    
    # Create indexes for negotiation_offers
    op.create_index('ix_negotiation_offers_negotiation_id', 'negotiation_offers', ['negotiation_id'])
    op.create_index('ix_negotiation_offers_negotiation_round', 'negotiation_offers', ['negotiation_id', 'round_number'])
    op.create_index('ix_negotiation_offers_status', 'negotiation_offers', ['status'])
    
    # Create negotiation_messages table
    op.create_table(
        'negotiation_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('negotiation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sender', sa.String(10), nullable=False),
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('message_type', sa.String(20), nullable=False, server_default='TEXT'),
        
        sa.Column('read_by_buyer', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('read_by_seller', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('read_by_buyer_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('read_by_seller_at', sa.DateTime(timezone=True), nullable=True),
        
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        
        sa.ForeignKeyConstraint(['negotiation_id'], ['negotiations.id'], ondelete='CASCADE'),
        
        sa.CheckConstraint("sender IN ('BUYER', 'SELLER', 'SYSTEM', 'AI_BOT')", name='valid_sender'),
        sa.CheckConstraint("message_type IN ('TEXT', 'OFFER', 'ACCEPTANCE', 'REJECTION', 'SYSTEM', 'AI_SUGGESTION')", name='valid_message_type'),
    )
    
    # Create indexes for negotiation_messages
    op.create_index('ix_negotiation_messages_negotiation_id', 'negotiation_messages', ['negotiation_id'])
    op.create_index('ix_negotiation_messages_created_at', 'negotiation_messages', ['created_at'])
    op.create_index('ix_negotiation_messages_unread_buyer', 'negotiation_messages', ['negotiation_id'], 
                    postgresql_where=sa.text('read_by_buyer = false'))
    op.create_index('ix_negotiation_messages_unread_seller', 'negotiation_messages', ['negotiation_id'],
                    postgresql_where=sa.text('read_by_seller = false'))


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('negotiation_messages')
    op.drop_table('negotiation_offers')
    op.drop_table('negotiations')
