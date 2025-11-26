"""add sub-user support

Revision ID: add_sub_user_support
Revises: 
Create Date: 2025-11-26

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_sub_user_support'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add parent_user_id column to users table
    op.add_column('users', sa.Column('parent_user_id', postgresql.UUID(as_uuid=True), nullable=True, comment='Parent user ID for sub-users (max 2 per parent)'))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_users_parent_user_id',
        'users',
        'users',
        ['parent_user_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # Add index for better query performance
    op.create_index('ix_users_parent_user_id', 'users', ['parent_user_id'])


def downgrade() -> None:
    # Remove index
    op.drop_index('ix_users_parent_user_id', table_name='users')
    
    # Remove foreign key
    op.drop_constraint('fk_users_parent_user_id', 'users', type_='foreignkey')
    
    # Remove column
    op.drop_column('users', 'parent_user_id')
