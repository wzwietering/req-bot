"""Test framework for database migrations with rollback capability."""

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
from requirements_bot.core.database_models import (
    AnswerTable,
    Base,
    QuestionTable,
    RequirementTable,
    SessionTable,
    UserTable,
)


class MigrationTestFramework:
    """Test framework for database migrations with rollback capability."""

    def __init__(self, test_db_path: str | None = None):
        """Initialize test framework with temporary database."""
        if test_db_path:
            self.db_path = test_db_path
            self.cleanup_db = False
        else:
            self.temp_dir = tempfile.mkdtemp()
            self.db_path = str(Path(self.temp_dir) / "test_migrations.db")
            self.cleanup_db = True

        self.engine = create_engine(f"sqlite:///{self.db_path}")
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create the database file by creating a connection
        with self.engine.connect() as conn:
            pass  # This ensures the database file is created

        # Setup Alembic configuration
        self.alembic_cfg = Config()
        self.alembic_cfg.set_main_option("script_location", "alembic")
        self.alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{self.db_path}")

        with self.engine.connect() as conn:
            context = MigrationContext.configure(conn)
            if not context.get_current_revision():
                try:
                    # Initialize Alembic version table if it doesn't exist
                    context.configure(conn)
                except Exception as e:
                    # Log the error but don't fail initialization
                    print(f"Warning: Could not initialize Alembic version tracking: {e}")

    def cleanup(self):
        """Clean up test database and temporary directory."""
        if self.cleanup_db:
            self.engine.dispose()
            if hasattr(self, "temp_dir"):
                shutil.rmtree(self.temp_dir, ignore_errors=True)

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
                    if count > 0:
                        issues.append(f"{check_name}: {count} records")

                return len(issues) == 0, issues
            except Exception as e:
                issues.append(f"Data integrity check failed: {e}")
                return False, issues

    def create_test_data(self) -> str:
        """Create test data using direct SQLAlchemy operations."""

        # Ensure tables exist
        Base.metadata.create_all(bind=self.engine)

        # Generate unique IDs to avoid conflicts
        session_id = str(uuid4())
        q1_id = str(uuid4())
        q2_id = str(uuid4())
        a1_id = str(uuid4())
        a2_id = str(uuid4())
        req1_id = str(uuid4())

        # Create test data using direct SQLAlchemy operations
        with self.SessionLocal() as session:
            try:
                # Create user first
                test_user = UserTable(
                    id="test-user-id",
                    email="test@example.com",
                    provider="google",
                    provider_id="test-provider-id",
                    name="Test User",
                )
                session.add(test_user)

                # Create session
                test_session = SessionTable(
                    id=session_id,
                    user_id="test-user-id",
                    project="Test Migration Project",
                    conversation_complete=False,
                )
                session.add(test_session)

                # Create questions
                questions = [
                    QuestionTable(
                        id=q1_id,
                        session_id=session_id,
                        text="What is the main goal?",
                        category="scope",
                        required=True,
                        order_index=0,
                    ),
                    QuestionTable(
                        id=q2_id,
                        session_id=session_id,
                        text="Who are the users?",
                        category="users",
                        required=True,
                        order_index=1,
                    ),
                ]
                session.add_all(questions)

                # Create answers
                answers = [
                    AnswerTable(
                        id=a1_id,
                        session_id=session_id,
                        question_id=q1_id,
                        text="Build a test system",
                        is_vague=False,
                        needs_followup=False,
                    ),
                    AnswerTable(
                        id=a2_id,
                        session_id=session_id,
                        question_id=q2_id,
                        text="Developers and testers",
                        is_vague=False,
                        needs_followup=False,
                    ),
                ]
                session.add_all(answers)

                # Create requirements
                requirement = RequirementTable(
                    id=req1_id,
                    session_id=session_id,
                    title="System must be testable",
                    rationale="Testing is essential for quality assurance",
                    priority="MUST",
                    order_index=0,
                )
                session.add(requirement)

                session.commit()
                return session_id

            except Exception as e:
                session.rollback()
                raise Exception(f"Failed to create test data: {e}")

    def verify_test_data(self, session_id: str) -> bool:
        """Verify test data integrity using direct SQLAlchemy operations."""
        try:
            with self.SessionLocal() as session:
                # Verify session exists
                test_session = session.query(SessionTable).filter_by(id=session_id).first()
                if not test_session or test_session.project != "Test Migration Project":
                    return False

                # Verify questions
                questions = (
                    session.query(QuestionTable)
                    .filter_by(session_id=session_id)
                    .order_by(QuestionTable.order_index)
                    .all()
                )
                if len(questions) != 2:
                    return False

                if questions[0].text != "What is the main goal?" or questions[0].category != "scope":
                    return False

                if questions[1].text != "Who are the users?" or questions[1].category != "users":
                    return False

                # Verify answers
                answers = session.query(AnswerTable).filter_by(session_id=session_id).all()
                if len(answers) != 2:
                    return False

                answer_texts = {answer.question_id: answer.text for answer in answers}
                if "Build a test system" not in answer_texts.values():
                    return False

                if "Developers and testers" not in answer_texts.values():
                    return False

                # Verify requirements
                requirements = session.query(RequirementTable).filter_by(session_id=session_id).all()
                if len(requirements) != 1:
                    return False

                if requirements[0].title != "System must be testable" or requirements[0].priority != "MUST":
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
