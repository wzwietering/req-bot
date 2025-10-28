"""add_usage_tracking

Revision ID: c7d8e9f0a1b2
Revises: 40817eac84ff
Create Date: 2025-10-25 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7d8e9f0a1b2'
down_revision: Union[str, None] = '40817eac84ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add tier column to users table
    op.add_column('users', sa.Column('tier', sa.String(), nullable=False, server_default='free'))

    # Create usage_events table
    op.create_table('usage_events',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('event_type', sa.String(), nullable=False),
    sa.Column('entity_id', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    # Create composite index for fast rolling window queries
    op.create_index('ix_usage_user_type_time', 'usage_events', ['user_id', 'event_type', 'created_at'], unique=False)


def downgrade() -> None:
    # Drop usage_events table and index
    op.drop_index('ix_usage_user_type_time', table_name='usage_events')
    op.drop_table('usage_events')

    # Remove tier column from users table
    op.drop_column('users', 'tier')
