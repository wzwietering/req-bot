"""Initial schema

Revision ID: ae8371ad187a
Revises:
Create Date: 2025-08-29 21:19:33.412148

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "ae8371ad187a"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### Create initial database schema ###
    # Create sessions table
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("project", sa.String(), nullable=False),
        sa.Column("conversation_complete", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create questions table
    op.create_table(
        "questions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_questions_session_id", "questions", ["session_id"], unique=False
    )

    # Create answers table
    op.create_table(
        "answers",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("question_id", sa.String(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("is_vague", sa.Boolean(), nullable=True),
        sa.Column("needs_followup", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["question_id"],
            ["questions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("question_id"),
    )
    op.create_index("ix_answers_question_id", "answers", ["question_id"], unique=False)
    op.create_index("ix_answers_session_id", "answers", ["session_id"], unique=False)

    # Create requirements table
    op.create_table(
        "requirements",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("priority", sa.String(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["sessions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_requirements_session_id", "requirements", ["session_id"], unique=False
    )


def downgrade() -> None:
    # ### Drop all initial schema tables ###
    # WARNING: This will destroy all data

    # Drop tables in reverse dependency order
    op.drop_index("ix_requirements_session_id", table_name="requirements")
    op.drop_table("requirements")

    op.drop_index("ix_answers_session_id", table_name="answers")
    op.drop_index("ix_answers_question_id", table_name="answers")
    op.drop_table("answers")

    op.drop_index("ix_questions_session_id", table_name="questions")
    op.drop_table("questions")

    op.drop_table("sessions")
