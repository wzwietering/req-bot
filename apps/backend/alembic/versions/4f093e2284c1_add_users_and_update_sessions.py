"""add_users_and_update_sessions

Revision ID: 4f093e2284c1
Revises: b1c2d3e4f5g6
Create Date: 2025-09-21 09:04:10.676594

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4f093e2284c1'
down_revision: Union[str, None] = 'b1c2d3e4f5g6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add users table and update sessions with user relationship."""
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('provider_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('avatar_url', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )

    # Create indexes for users table
    op.create_index('ix_users_email', 'users', ['email'], unique=False)
    op.create_index('ix_users_provider_id', 'users', ['provider', 'provider_id'], unique=True)

    # For SQLite, use batch mode to add column and foreign key constraint
    with op.batch_alter_table('sessions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.String(), nullable=False))
        batch_op.create_foreign_key(
            'fk_sessions_user_id',
            'users',
            ['user_id'],
            ['id'],
            ondelete='CASCADE'
        )
        batch_op.create_index('ix_sessions_user_id', ['user_id'], unique=False)


def downgrade() -> None:
    """Remove users table and user relationship from sessions."""
    # For SQLite, use batch mode to handle constraint drops
    with op.batch_alter_table('sessions', schema=None) as batch_op:
        batch_op.drop_index('ix_sessions_user_id')
        batch_op.drop_constraint('fk_sessions_user_id', type_='foreignkey')
        batch_op.drop_column('user_id')

    # Drop users table indexes and table
    op.drop_index('ix_users_provider_id', table_name='users')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')