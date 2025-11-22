"""Add mobile_number and OTP fields to users table

Revision ID: add_mobile_otp_fields
Revises: 
Create Date: 2025-11-22

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_mobile_otp_fields'
down_revision = '400f038407b5'  # Latest migration
branch_labels = None
depends_on = None


def upgrade():
    # Make email nullable (for OTP-only users)
    op.alter_column('users', 'email',
               existing_type=sa.String(255),
               nullable=True)
    
    # Make password_hash nullable (for OTP-only users)
    op.alter_column('users', 'password_hash',
               existing_type=sa.String(255),
               nullable=True)
    
    # Add mobile_number field
    op.add_column('users', sa.Column('mobile_number', sa.String(20), nullable=True))
    op.create_unique_constraint('uq_users_mobile_number', 'users', ['mobile_number'])
    op.create_index('ix_users_mobile_number', 'users', ['mobile_number'])
    
    # Add is_verified field
    op.add_column('users', sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'))
    
    # Add role field
    op.add_column('users', sa.Column('role', sa.String(50), nullable=True))
    
    # Add constraint: user must have email OR mobile_number
    op.create_check_constraint(
        'ck_user_has_email_or_mobile',
        'users',
        'email IS NOT NULL OR mobile_number IS NOT NULL'
    )


def downgrade():
    # Remove new constraint
    op.drop_constraint('ck_user_has_email_or_mobile', 'users', type_='check')
    
    # Remove new columns
    op.drop_column('users', 'role')
    op.drop_column('users', 'is_verified')
    
    # Remove mobile_number
    op.drop_index('ix_users_mobile_number', 'users')
    op.drop_constraint('uq_users_mobile_number', 'users', type_='unique')
    op.drop_column('users', 'mobile_number')
    
    # Restore email and password_hash as NOT NULL
    op.alter_column('users', 'password_hash',
               existing_type=sa.String(255),
               nullable=False)
    
    op.alter_column('users', 'email',
               existing_type=sa.String(255),
               nullable=False)
