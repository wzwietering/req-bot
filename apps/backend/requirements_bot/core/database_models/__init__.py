from datetime import UTC, datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    Engine,
    ForeignKey,
    Index,
    String,
    Text,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# Single unified Base for all models using SQLAlchemy 2.0 style
class Base(DeclarativeBase):
    """Base class for all database models with proper typing support."""

    pass


# Function to enable foreign key enforcement - to be called by engines
def enable_sqlite_foreign_keys(engine: Engine):
    """Enable foreign key enforcement for SQLite connections on an engine."""

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, connection_record) -> None:
        """Enable foreign key enforcement for SQLite connections."""
        if "sqlite" in str(dbapi_connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()


class UserTable(Base):
    """User table for OAuth2 authentication."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String, unique=True)
    provider: Mapped[str] = mapped_column(String)  # 'google', 'github', 'microsoft'
    provider_id: Mapped[str] = mapped_column(String)  # OAuth provider's user ID
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    # Relationships
    sessions: Mapped[list["SessionTable"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    # Unique constraint on provider + provider_id
    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_provider_id", "provider", "provider_id", unique=True),
    )


class SessionTable(Base):
    """Core session table for requirements gathering."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    project: Mapped[str] = mapped_column(String)
    conversation_complete: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    # Conversation state tracking
    conversation_state: Mapped[str] = mapped_column(String, default="initializing")
    state_context: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON serialized StateContext
    last_state_change: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    # Relationships
    user: Mapped["UserTable"] = relationship(back_populates="sessions")
    questions: Mapped[list["QuestionTable"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="QuestionTable.order_index"
    )
    answers: Mapped[list["AnswerTable"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    requirements: Mapped[list["RequirementTable"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="RequirementTable.order_index"
    )


class QuestionTable(Base):
    """Questions table."""

    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"))
    text: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String)
    required: Mapped[bool] = mapped_column(default=True)
    order_index: Mapped[int] = mapped_column()

    # Relationships
    session: Mapped["SessionTable"] = relationship(back_populates="questions")
    answer: Mapped[Optional["AnswerTable"]] = relationship(back_populates="question")

    # Indexes
    __table_args__ = (Index("ix_questions_session_id", "session_id"),)


class AnswerTable(Base):
    """Answers table."""

    __tablename__ = "answers"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"))
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id", ondelete="CASCADE"), unique=True)
    text: Mapped[str] = mapped_column(Text)
    is_vague: Mapped[bool] = mapped_column(default=False)
    needs_followup: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    # Relationships
    session: Mapped["SessionTable"] = relationship(back_populates="answers")
    question: Mapped["QuestionTable"] = relationship(back_populates="answer")

    # Indexes
    __table_args__ = (
        Index("ix_answers_session_id", "session_id"),
        Index("ix_answers_question_id", "question_id"),
    )


class RequirementTable(Base):
    """Requirements table."""

    __tablename__ = "requirements"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String, default="MUST")
    order_index: Mapped[int] = mapped_column()

    # Relationships
    session: Mapped["SessionTable"] = relationship(back_populates="requirements")

    # Indexes
    __table_args__ = (Index("ix_requirements_session_id", "session_id"),)


class OAuthStateTable(Base):
    """OAuth state storage for CSRF protection."""

    __tablename__ = "oauth_states"

    state: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    expires_at: Mapped[datetime] = mapped_column(DateTime)

    # Index for cleanup queries
    __table_args__ = (Index("ix_oauth_states_expires_at", "expires_at"),)


class RefreshTokenTable(Base):
    """Refresh token storage for JWT authentication."""

    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked: Mapped[bool] = mapped_column(default=False)

    # Relationships
    user: Mapped["UserTable"] = relationship()

    # Indexes
    __table_args__ = (
        Index("ix_refresh_tokens_user_id", "user_id"),
        Index("ix_refresh_tokens_expires_at", "expires_at"),
        Index("ix_refresh_tokens_token_hash", "token_hash", unique=True),
    )


# Export core models only
__all__ = [
    "Base",
    "UserTable",
    "SessionTable",
    "QuestionTable",
    "AnswerTable",
    "RequirementTable",
    "OAuthStateTable",
    "RefreshTokenTable",
    "enable_sqlite_foreign_keys",
]
