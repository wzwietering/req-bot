from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Engine,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    event,
)
from sqlalchemy.orm import declarative_base, relationship

# Single unified Base for all models
Base: Any = declarative_base()


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

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    email = Column(String, nullable=False, unique=True)
    provider = Column(String, nullable=False)  # 'google', 'github', 'microsoft'
    provider_id = Column(String, nullable=False)  # OAuth provider's user ID
    name = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Relationships
    sessions = relationship("SessionTable", back_populates="user", cascade="all, delete-orphan")

    # Unique constraint on provider + provider_id
    __table_args__ = (
        Index("ix_users_email", "email"),
        Index("ix_users_provider_id", "provider", "provider_id", unique=True),
    )


class SessionTable(Base):
    """Core session table for requirements gathering."""

    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project = Column(String, nullable=False)
    conversation_complete = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Conversation state tracking
    conversation_state = Column(String, nullable=False, default="initializing")
    state_context = Column(Text, nullable=True)  # JSON serialized StateContext
    last_state_change = Column(DateTime, default=lambda: datetime.now(UTC))

    # Relationships
    user = relationship("UserTable", back_populates="sessions")
    questions = relationship(
        "QuestionTable",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="QuestionTable.order_index",
    )
    answers = relationship("AnswerTable", back_populates="session", cascade="all, delete-orphan")
    requirements = relationship(
        "RequirementTable",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="RequirementTable.order_index",
    )


class QuestionTable(Base):
    """Questions table."""

    __tablename__ = "questions"

    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    text = Column(Text, nullable=False)
    category = Column(String, nullable=False)
    required = Column(Boolean, default=True)
    order_index = Column(Integer, nullable=False)

    # Relationships
    session = relationship("SessionTable", back_populates="questions")
    answer = relationship("AnswerTable", back_populates="question", uselist=False)

    # Indexes
    __table_args__ = (Index("ix_questions_session_id", "session_id"),)


class AnswerTable(Base):
    """Answers table."""

    __tablename__ = "answers"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(
        String,
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    text = Column(Text, nullable=False)
    is_vague = Column(Boolean, default=False)
    needs_followup = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    # Relationships
    session = relationship("SessionTable", back_populates="answers")
    question = relationship("QuestionTable", back_populates="answer")

    # Indexes
    __table_args__ = (
        Index("ix_answers_session_id", "session_id"),
        Index("ix_answers_question_id", "question_id"),
    )


class RequirementTable(Base):
    """Requirements table."""

    __tablename__ = "requirements"

    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=False)
    rationale = Column(Text)
    priority = Column(String, nullable=False, default="MUST")
    order_index = Column(Integer, nullable=False)

    # Relationships
    session = relationship("SessionTable", back_populates="requirements")

    # Indexes
    __table_args__ = (Index("ix_requirements_session_id", "session_id"),)


class OAuthStateTable(Base):
    """OAuth state storage for CSRF protection."""

    __tablename__ = "oauth_states"

    state = Column(String, primary_key=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    expires_at = Column(DateTime, nullable=False)

    # Index for cleanup queries
    __table_args__ = (Index("ix_oauth_states_expires_at", "expires_at"),)


class RefreshTokenTable(Base):
    """Refresh token storage for JWT authentication."""

    __tablename__ = "refresh_tokens"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(UTC))
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)

    # Relationships
    user = relationship("UserTable")

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
