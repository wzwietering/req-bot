import uuid
from datetime import datetime
from pathlib import Path

import pytest

from requirements_bot.core.memory_storage import MemoryStorage
from requirements_bot.core.models import Answer, Question, Requirement, Session, UserCreate
from requirements_bot.core.services.user_service import UserService
from requirements_bot.core.storage import DatabaseManager


class TestMemoryStorage:
    """Test the in-memory storage implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.storage = MemoryStorage()
        self.sample_session = Session(
            id="test-session-123",
            user_id="test-user-123",
            project="Test Project",
            questions=[
                Question(
                    id="q1",
                    text="What is the main purpose?",
                    category="scope",
                    required=True,
                )
            ],
            answers=[
                Answer(
                    question_id="q1",
                    text="To test the system",
                    is_vague=False,
                    needs_followup=False,
                )
            ],
            requirements=[
                Requirement(
                    id="r1",
                    title="Test Requirement",
                    rationale="For testing purposes",
                    priority="MUST",
                )
            ],
        )

    def test_save_and_load_session(self):
        """Test saving and loading a session."""
        # Save session
        session_id = self.storage.save_session(self.sample_session)
        assert session_id == self.sample_session.id

        # Load session
        loaded_session = self.storage.load_session(session_id)
        assert loaded_session is not None
        assert loaded_session.id == self.sample_session.id
        assert loaded_session.project == self.sample_session.project
        assert len(loaded_session.questions) == 1
        assert len(loaded_session.answers) == 1
        assert len(loaded_session.requirements) == 1

    def test_load_nonexistent_session(self):
        """Test loading a session that doesn't exist."""
        loaded_session = self.storage.load_session("nonexistent")
        assert loaded_session is None

    def test_list_sessions(self):
        """Test listing sessions."""
        # Initially empty
        sessions = self.storage.list_sessions()
        assert len(sessions) == 0

        # Add a session
        self.storage.save_session(self.sample_session)
        sessions = self.storage.list_sessions()
        assert len(sessions) == 1

        session_id, project, updated_at, conversation_complete = sessions[0]
        assert session_id == self.sample_session.id
        assert project == self.sample_session.project
        assert isinstance(updated_at, datetime)
        assert conversation_complete == self.sample_session.conversation_complete

    def test_delete_session(self):
        """Test deleting a session."""
        # Save session first
        self.storage.save_session(self.sample_session)

        # Delete session
        result = self.storage.delete_session(self.sample_session.id)
        assert result is True

        # Verify it's gone
        loaded_session = self.storage.load_session(self.sample_session.id)
        assert loaded_session is None

        # Try to delete again
        result = self.storage.delete_session(self.sample_session.id)
        assert result is False


class TestDatabaseManager:
    """Test the database storage implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary database in current directory for testing
        import os

        self.temp_db_name = f"test_db_{os.getpid()}_{id(self)}.db"

        self.storage = DatabaseManager(db_path=self.temp_db_name)

        # Create a test user first to satisfy foreign key constraints
        with self.storage.SessionLocal() as db_session:
            user_service = UserService(db_session)
            test_user = UserCreate(
                email="test@example.com", provider="google", provider_id="test-provider-id-123", name="Test User"
            )
            created_user = user_service.create_user(test_user)
            self.test_user_id = created_user.id
            db_session.commit()

        self.sample_session = Session(
            id=str(uuid.uuid4()),
            user_id=self.test_user_id,
            project="Database Test Project",
            questions=[
                Question(
                    id="q1",
                    text="What database should we use?",
                    category="data",
                    required=True,
                )
            ],
            answers=[
                Answer(
                    question_id="q1",
                    text="SQLite for testing",
                    is_vague=False,
                    needs_followup=False,
                )
            ],
            requirements=[
                Requirement(
                    id="r1",
                    title="Database Requirement",
                    rationale="Need persistent storage",
                    priority="MUST",
                )
            ],
        )

    def teardown_method(self):
        """Clean up test fixtures."""
        # Close database connections first
        if hasattr(self.storage, "engine"):
            self.storage.engine.dispose()
        Path(self.temp_db_name).unlink(missing_ok=True)

    def test_path_validation(self):
        """Test that path traversal attacks are prevented."""
        with pytest.raises(ValueError, match="Database path outside working directory"):
            DatabaseManager(db_path="../../../etc/malicious.db")

    def test_session_id_validation(self):
        """Test that invalid session IDs are rejected."""
        with pytest.raises(ValueError, match="Invalid session ID format"):
            self.storage._validate_session_id("invalid-id")

        # Valid UUID should pass
        valid_id = "550e8400-e29b-41d4-a716-446655440000"
        assert self.storage._validate_session_id(valid_id) == valid_id

    def test_save_and_load_session(self):
        """Test saving and loading a session with database."""
        # Save session
        session_id = self.storage.save_session(self.sample_session)
        assert session_id == self.sample_session.id

        # Load session
        loaded_session = self.storage.load_session(session_id)
        assert loaded_session is not None
        assert loaded_session.id == self.sample_session.id
        assert loaded_session.project == self.sample_session.project
        assert len(loaded_session.questions) == 1
        assert len(loaded_session.answers) == 1
        assert len(loaded_session.requirements) == 1

        # Verify question details
        question = loaded_session.questions[0]
        assert question.id == "q1"
        assert question.text == "What database should we use?"
        assert question.category == "data"
        assert question.required is True

    def test_upsert_functionality(self):
        """Test that updates work correctly (upsert pattern)."""
        # Save initial session
        self.storage.save_session(self.sample_session)

        # Modify and save again
        self.sample_session.project = "Updated Project Name"
        self.sample_session.conversation_complete = True

        # Add another question
        new_question = Question(
            id="q2",
            text="What about performance?",
            category="nonfunctional",
            required=False,
        )
        self.sample_session.questions.append(new_question)

        # Save updated session
        self.storage.save_session(self.sample_session)

        # Load and verify updates
        loaded_session = self.storage.load_session(self.sample_session.id)
        assert loaded_session is not None
        assert loaded_session.project == "Updated Project Name"
        assert loaded_session.conversation_complete is True
        assert len(loaded_session.questions) == 2

        # Find the new question
        new_q = next((q for q in loaded_session.questions if q.id == "q2"), None)
        assert new_q is not None
        assert new_q.text == "What about performance?"
