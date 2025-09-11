"""Add conversation state tracking

Revision ID: b1c2d3e4f5g6
Revises: ae8371ad187a
Create Date: 2025-09-11 10:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5g6"
down_revision: Union[str, None] = "ae8371ad187a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add conversation state tracking fields to sessions table."""
    op.add_column(
        "sessions",
        sa.Column(
            "conversation_state",
            sa.String(),
            nullable=False,
            server_default="initializing",
        ),
    )
    op.add_column("sessions", sa.Column("state_context", sa.Text(), nullable=True))
    op.add_column(
        "sessions", sa.Column("last_state_change", sa.DateTime(), nullable=True)
    )

    # Add index for efficient state-based queries
    op.create_index(
        "ix_sessions_conversation_state",
        "sessions",
        ["conversation_state"],
        unique=False,
    )


def downgrade() -> None:
    """Remove conversation state tracking fields."""
    op.drop_index("ix_sessions_conversation_state", table_name="sessions")
    op.drop_column("sessions", "last_state_change")
    op.drop_column("sessions", "state_context")
    op.drop_column("sessions", "conversation_state")
