from datetime import UTC, datetime
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
Base = declarative_base()


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


class SessionTable(Base):
    """Core session table for requirements gathering."""

    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    project = Column(String, nullable=False)
    conversation_complete = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    # Relationships
    questions = relationship(
        "QuestionTable", back_populates="session", cascade="all, delete-orphan"
    )
    answers = relationship(
        "AnswerTable", back_populates="session", cascade="all, delete-orphan"
    )
    requirements = relationship(
        "RequirementTable",
        back_populates="session",
        cascade="all, delete-orphan",
    )


class QuestionTable(Base):
    """Questions table."""

    __tablename__ = "questions"

    id = Column(String, primary_key=True)
    session_id = Column(
        String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
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
    session_id = Column(
        String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
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
    session_id = Column(
        String, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(String, nullable=False)
    rationale = Column(Text)
    priority = Column(String, nullable=False, default="MUST")
    order_index = Column(Integer, nullable=False)

    # Relationships
    session = relationship("SessionTable", back_populates="requirements")

    # Indexes
    __table_args__ = (Index("ix_requirements_session_id", "session_id"),)


# Export core models only
__all__ = [
    "Base",
    "SessionTable",
    "QuestionTable",
    "AnswerTable",
    "RequirementTable",
    "enable_sqlite_foreign_keys",
]
