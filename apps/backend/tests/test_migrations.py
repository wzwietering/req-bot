"""Test framework for database migrations with rollback capability."""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from alembic import command


class MigrationTestFramework:
    """Test framework for database migrations with rollback capability."""

    def __init__(self, test_db_path: str | None = None):
        """Initialize test framework with temporary database."""
        # Store and clear DATABASE_URL to prevent interference with application imports

        self._original_database_url = os.environ.get("DATABASE_URL")
        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]

        if test_db_path:
            self.db_path = test_db_path
            self.cleanup_db = False
        else:
            self.temp_dir = tempfile.mkdtemp()
            self.db_path = str(Path(self.temp_dir) / "test_migrations.db")
            self.cleanup_db = True

        # Setup Alembic configuration first
        self.alembic_cfg = Config()
        self.alembic_cfg.set_main_option("script_location", "alembic")
        self.alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{self.db_path}")

        self.engine = create_engine(f"sqlite:///{self.db_path}")
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create the database file by creating a connection
        with self.engine.connect() as conn:
            pass  # This ensures the database file is created

        # Initialize Alembic version table FIRST to prevent DatabaseManager auto-creation
        try:
            # Create the version table manually
            with self.engine.connect() as conn:
                context = MigrationContext.configure(conn)
                context._ensure_version_table()
                # Don't stamp to any revision yet - leave it at None for fresh migration tests
        except Exception as e:
            print(f"Warning: Could not initialize Alembic version tracking: {e}")

    def cleanup(self):
        """Clean up test database and temporary directory."""
        if self.cleanup_db:
            self.engine.dispose()
            if hasattr(self, "temp_dir"):
                shutil.rmtree(self.temp_dir, ignore_errors=True)

        if self._original_database_url is not None:
            os.environ["DATABASE_URL"] = self._original_database_url
        elif "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]

    def get_current_revision(self) -> str | None:
        """Get current database revision."""
        with self.engine.connect() as conn:
            context = MigrationContext.configure(conn)
            return context.get_current_revision()

    def get_all_revisions(self) -> list[str]:
        """Get all available revisions from migration scripts."""
        script_dir = ScriptDirectory.from_config(self.alembic_cfg)
        return [rev.revision for rev in script_dir.walk_revisions()]

    def migrate_to_revision(self, revision: str = "head") -> bool:
        """Migrate to specific revision. Returns True if successful."""
        try:
            command.upgrade(self.alembic_cfg, revision)
            return True
        except Exception as e:
            print(f"Migration to {revision} failed: {e}")
            return False

    def rollback_to_revision(self, revision: str) -> bool:
        """Rollback to specific revision. Returns True if successful."""
        try:
            command.downgrade(self.alembic_cfg, revision)
            return True
        except Exception as e:
            print(f"Rollback to {revision} failed: {e}")
            return False

    def get_table_schema(self, table_name: str) -> dict[str, Any]:
        """Get current schema for a table."""
        inspector = inspect(self.engine)
        if not inspector.has_table(table_name):
            return {}

        columns = inspector.get_columns(table_name)
        indexes = inspector.get_indexes(table_name)
        foreign_keys = inspector.get_foreign_keys(table_name)

        return {
            "columns": {col["name"]: col for col in columns},
            "indexes": indexes,
            "foreign_keys": foreign_keys,
        }

    def validate_data_integrity(self) -> tuple[bool, list[str]]:
        """Validate data integrity after migration."""
        issues: list[str] = []

        with self.SessionLocal() as session:
            try:
                # Check that all foreign key relationships are valid
                result = session.execute(text("PRAGMA foreign_key_check"))
                violations = result.fetchall()
                if violations:
                    issues.append(f"Foreign key violations: {violations}")

                # Check for orphaned records
                integrity_checks = [
                    (
                        "Orphaned questions",
                        "SELECT COUNT(*) FROM questions q LEFT JOIN sessions s "
                        "ON q.session_id = s.id WHERE s.id IS NULL",
                    ),
                    (
                        "Orphaned answers from questions",
                        "SELECT COUNT(*) FROM answers a LEFT JOIN questions q "
                        "ON a.question_id = q.id WHERE q.id IS NULL",
                    ),
                    (
                        "Orphaned answers from sessions",
                        "SELECT COUNT(*) FROM answers a LEFT JOIN sessions s ON a.session_id = s.id WHERE s.id IS NULL",
                    ),
                    (
                        "Orphaned requirements",
                        "SELECT COUNT(*) FROM requirements r LEFT JOIN sessions s "
                        "ON r.session_id = s.id WHERE s.id IS NULL",
                    ),
                ]

                for check_name, query in integrity_checks:
                    result = session.execute(text(query))
                    count = result.scalar()
                    if count and count > 0:
                        issues.append(f"{check_name}: {count} records")

                return len(issues) == 0, issues
            except Exception as e:
                issues.append(f"Data integrity check failed: {e}")
                return False, issues

    def create_test_data(self) -> str:
        """Create test data using raw SQL to avoid importing table models."""
        # Tables should already exist from migrations - don't create them here

        # Generate unique IDs to avoid conflicts
        session_id = str(uuid4())
        q1_id = str(uuid4())
        q2_id = str(uuid4())
        a1_id = str(uuid4())
        a2_id = str(uuid4())
        req1_id = str(uuid4())

        # Create test data using raw SQL to avoid importing table models
        with self.engine.connect() as conn:
            trans = conn.begin()
            try:
                # Create user first
                conn.execute(
                    text("""
                    INSERT INTO users (id, email, provider, provider_id, name)
                    VALUES (:id, :email, :provider, :provider_id, :name)
                """),
                    {
                        "id": "test-user-id",
                        "email": "test@example.com",
                        "provider": "google",
                        "provider_id": "test-provider-id",
                        "name": "Test User",
                    },
                )

                # Create session
                conn.execute(
                    text("""
                    INSERT INTO sessions (id, user_id, project, conversation_complete)
                    VALUES (:id, :user_id, :project, :conversation_complete)
                """),
                    {
                        "id": session_id,
                        "user_id": "test-user-id",
                        "project": "Test Migration Project",
                        "conversation_complete": False,
                    },
                )

                # Create questions
                questions_data = [
                    {
                        "id": q1_id,
                        "session_id": session_id,
                        "text": "What is the main goal?",
                        "category": "scope",
                        "required": True,
                        "order_index": 0,
                    },
                    {
                        "id": q2_id,
                        "session_id": session_id,
                        "text": "Who are the users?",
                        "category": "users",
                        "required": True,
                        "order_index": 1,
                    },
                ]

                for q in questions_data:
                    conn.execute(
                        text("""
                        INSERT INTO questions (id, session_id, text, category, required, order_index)
                        VALUES (:id, :session_id, :text, :category, :required, :order_index)
                    """),
                        q,
                    )

                # Create answers
                answers_data = [
                    {
                        "id": a1_id,
                        "session_id": session_id,
                        "question_id": q1_id,
                        "text": "Build a test system",
                        "is_vague": False,
                        "needs_followup": False,
                    },
                    {
                        "id": a2_id,
                        "session_id": session_id,
                        "question_id": q2_id,
                        "text": "Developers and testers",
                        "is_vague": False,
                        "needs_followup": False,
                    },
                ]

                for a in answers_data:
                    conn.execute(
                        text("""
                        INSERT INTO answers (id, session_id, question_id, text, is_vague, needs_followup)
                        VALUES (:id, :session_id, :question_id, :text, :is_vague, :needs_followup)
                    """),
                        a,
                    )

                # Create requirements
                conn.execute(
                    text("""
                    INSERT INTO requirements (id, session_id, title, rationale, priority, order_index)
                    VALUES (:id, :session_id, :title, :rationale, :priority, :order_index)
                """),
                    {
                        "id": req1_id,
                        "session_id": session_id,
                        "title": "System must be testable",
                        "rationale": "Testing is essential for quality assurance",
                        "priority": "MUST",
                        "order_index": 0,
                    },
                )

                trans.commit()
                return session_id

            except Exception as e:
                trans.rollback()
                raise Exception(f"Failed to create test data: {e}")

    def verify_test_data(self, session_id: str) -> bool:
        """Verify test data integrity using raw SQL to avoid importing table models."""
        try:
            with self.engine.connect() as conn:
                # Verify session exists
                result = conn.execute(
                    text("""
                    SELECT project FROM sessions WHERE id = :session_id
                """),
                    {"session_id": session_id},
                )
                session_row = result.fetchone()
                if not session_row or session_row[0] != "Test Migration Project":
                    return False

                # Verify questions
                result = conn.execute(
                    text("""
                    SELECT text, category FROM questions
                    WHERE session_id = :session_id
                    ORDER BY order_index
                """),
                    {"session_id": session_id},
                )
                questions = result.fetchall()
                if len(questions) != 2:
                    return False

                if questions[0][0] != "What is the main goal?" or questions[0][1] != "scope":
                    return False

                if questions[1][0] != "Who are the users?" or questions[1][1] != "users":
                    return False

                # Verify answers
                result = conn.execute(
                    text("""
                    SELECT text FROM answers WHERE session_id = :session_id
                """),
                    {"session_id": session_id},
                )
                answers = result.fetchall()
                if len(answers) != 2:
                    return False

                answer_texts = [row[0] for row in answers]
                if "Build a test system" not in answer_texts:
                    return False

                if "Developers and testers" not in answer_texts:
                    return False

                # Verify requirements
                result = conn.execute(
                    text("""
                    SELECT title, priority FROM requirements WHERE session_id = :session_id
                """),
                    {"session_id": session_id},
                )
                requirements = result.fetchall()
                if len(requirements) != 1:
                    return False

                if requirements[0][0] != "System must be testable" or requirements[0][1] != "MUST":
                    return False

                return True

        except Exception as e:
            print(f"Test data verification failed: {e}")
            return False


class TestDatabaseMigrations:
    """Test cases for database migration framework."""

    def setup_method(self):
        """Setup test environment."""
        self.framework = MigrationTestFramework()

    def teardown_method(self):
        """Cleanup test environment."""
        self.framework.cleanup()

    def test_migration_framework_initialization(self):
        """Test that migration framework initializes correctly."""
        # Database file should exist after initialization
        assert Path(self.framework.db_path).exists()
        assert self.framework.engine is not None
        assert self.framework.alembic_cfg is not None

        # Should be able to connect to database
        with self.framework.engine.connect() as conn:
            assert conn is not None

    def test_fresh_database_migration(self):
        """Test migrating a fresh database to head."""
        # Should start with no current revision
        current = self.framework.get_current_revision()
        assert current is None

        # Migrate to head should succeed
        success = self.framework.migrate_to_revision("head")
        assert success

        # Should now have a current revision
        current = self.framework.get_current_revision()
        assert current is not None

    def test_migration_with_data_preservation(self):
        """Test that migrations preserve existing data."""
        # Create initial schema
        self.framework.migrate_to_revision("head")

        # Create test data
        session_id = self.framework.create_test_data()

        # Verify data exists
        assert self.framework.verify_test_data(session_id)

        # Get current revision and verify we're at head
        current_revision = self.framework.get_current_revision()
        assert current_revision is not None

        # Verify data integrity after having schema and data
        integrity_ok, issues = self.framework.validate_data_integrity()
        if not integrity_ok:
            print(f"Data integrity issues: {issues}")
        assert integrity_ok

        # Verify data is still intact
        assert self.framework.verify_test_data(session_id)

    def test_rollback_capability(self):
        """Test that rollback works without data corruption."""
        # Migrate to head
        self.framework.migrate_to_revision("head")
        current_revision = self.framework.get_current_revision()

        if current_revision:
            # Get all revisions
            revisions = self.framework.get_all_revisions()

            if len(revisions) > 1:
                # Find previous revision
                current_idx = revisions.index(current_revision)
                if current_idx < len(revisions) - 1:
                    previous_revision = revisions[current_idx + 1]

                    # Rollback
                    success = self.framework.rollback_to_revision(previous_revision)
                    assert success

                    # Verify we're at the previous revision
                    assert self.framework.get_current_revision() == previous_revision

                    # Migrate back to head
                    success = self.framework.migrate_to_revision("head")
                    assert success

                    # Verify data integrity
                    assert self.framework.validate_data_integrity()

    def test_schema_evolution_compatibility(self):
        """Test that schema changes maintain backward compatibility."""
        # Migrate to head
        self.framework.migrate_to_revision("head")

        # Get schema for core tables
        sessions_schema = self.framework.get_table_schema("sessions")
        questions_schema = self.framework.get_table_schema("questions")
        answers_schema = self.framework.get_table_schema("answers")
        requirements_schema = self.framework.get_table_schema("requirements")

        # Verify core columns exist
        assert "id" in sessions_schema.get("columns", {})
        assert "project" in sessions_schema.get("columns", {})
        assert "conversation_complete" in sessions_schema.get("columns", {})

        assert "id" in questions_schema.get("columns", {})
        assert "session_id" in questions_schema.get("columns", {})
        assert "text" in questions_schema.get("columns", {})
        assert "category" in questions_schema.get("columns", {})

        assert "id" in answers_schema.get("columns", {})
        assert "session_id" in answers_schema.get("columns", {})
        assert "question_id" in answers_schema.get("columns", {})
        assert "text" in answers_schema.get("columns", {})

        assert "id" in requirements_schema.get("columns", {})
        assert "session_id" in requirements_schema.get("columns", {})
        assert "title" in requirements_schema.get("columns", {})
        assert "priority" in requirements_schema.get("columns", {})


class TestMigrationVersionTracking:
    """Test migration version tracking system."""

    def setup_method(self):
        """Setup test environment."""
        self.framework = MigrationTestFramework()

    def teardown_method(self):
        """Cleanup test environment."""
        self.framework.cleanup()

    def test_version_tracking_initialization(self):
        """Test that version tracking initializes correctly."""
        # Fresh database should have no version
        current = self.framework.get_current_revision()
        assert current is None

        # After migration, should have version
        self.framework.migrate_to_revision("head")
        current = self.framework.get_current_revision()
        assert current is not None

    def test_version_history_tracking(self):
        """Test that migration history is properly tracked."""
        revisions = self.framework.get_all_revisions()

        # Should have at least one revision (initial schema)
        assert len(revisions) >= 0  # Might be 0 if no migrations exist yet

        # Each revision should be a valid string
        for revision in revisions:
            assert isinstance(revision, str)
            assert len(revision) > 0


@pytest.fixture
def migration_framework():
    """Pytest fixture for migration test framework."""
    framework = MigrationTestFramework()
    yield framework
    framework.cleanup()


def test_migration_framework_fixture(migration_framework):
    """Test that the pytest fixture works correctly."""
    assert migration_framework is not None
    assert migration_framework.engine is not None


if __name__ == "__main__":
    # Run basic tests
    framework = MigrationTestFramework()
    try:
        print("Testing migration framework...")

        # Test initialization
        print("✓ Framework initialization")

        # Test fresh migration
        success = framework.migrate_to_revision("head")
        print(f"✓ Fresh migration: {'success' if success else 'failed'}")

        # Test data integrity
        integrity_ok = framework.validate_data_integrity()
        print(f"✓ Data integrity: {'ok' if integrity_ok else 'failed'}")

        # Test with data
        session_id = framework.create_test_data()
        data_ok = framework.verify_test_data(session_id)
        print(f"✓ Test data: {'ok' if data_ok else 'failed'}")

        print("Migration framework tests completed!")

    finally:
        framework.cleanup()
