from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

# SQLAlchemy Base
Base = declarative_base()


class SessionTable(Base):
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
        "RequirementTable", back_populates="session", cascade="all, delete-orphan"
    )


class QuestionTable(Base):
    __tablename__ = "questions"

    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
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
    __tablename__ = "answers"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    question_id = Column(
        String, ForeignKey("questions.id"), nullable=False, unique=True
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
    __tablename__ = "requirements"

    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    title = Column(String, nullable=False)
    rationale = Column(Text)
    priority = Column(String, nullable=False, default="MUST")
    order_index = Column(Integer, nullable=False)

    # Relationships
    session = relationship("SessionTable", back_populates="requirements")

    # Indexes
    __table_args__ = (Index("ix_requirements_session_id", "session_id"),)
