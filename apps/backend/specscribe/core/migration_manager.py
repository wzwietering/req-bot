"""Database migration management system using Alembic."""

import logging
from typing import Any

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import sessionmaker

from alembic import command
from specscribe.core.database_models import (
    AnswerTable as Answer,
)
from specscribe.core.database_models import (
    QuestionTable as Question,
)
from specscribe.core.database_models import (
    RequirementTable as Requirement,
)
from specscribe.core.database_models import (
    SessionTable as SessionModel,
)
from specscribe.core.database_models import enable_sqlite_foreign_keys

logger = logging.getLogger(__name__)


class MigrationManager:
    """Manages database migrations using Alembic's built-in capabilities."""

    def __init__(self, db_path: str, alembic_config_path: str = "alembic.ini"):
        """Initialize migration manager."""
        logger.info(f"Initializing migration manager for database: {db_path}")

        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}")

        # Enable foreign key enforcement for SQLite
        enable_sqlite_foreign_keys(self.engine)

        self.SessionLocal = sessionmaker(bind=self.engine)

        # Setup Alembic configuration
        logger.debug(f"Setting up Alembic configuration from: {alembic_config_path}")
        self.alembic_cfg = Config(alembic_config_path)
        self.alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

        logger.info("Migration manager initialized successfully")

    def get_current_revision(self) -> str | None:
        """Get current database revision."""
        try:
            with self.engine.connect() as conn:
                context = MigrationContext.configure(conn)
                current = context.get_current_revision()
                logger.debug(f"Current database revision: {current or 'None (fresh database)'}")
                return current
        except Exception as e:
            logger.error(f"Failed to get current revision: {e}")
            raise

    def get_all_revisions(self) -> list[str]:
        """Get all available revisions from migration scripts."""
        script_dir = ScriptDirectory.from_config(self.alembic_cfg)
        return [rev.revision for rev in script_dir.walk_revisions()]

    def get_pending_revisions(self) -> list[str]:
        """Get revisions that haven't been applied yet in upgrade order."""
        script_dir = ScriptDirectory.from_config(self.alembic_cfg)
        current = self.get_current_revision()

        if not current:
            # No current revision, all revisions are pending in upgrade order
            all_revs = list(script_dir.iterate_revisions("base", "heads"))
            return [rev.revision for rev in reversed(all_revs)]

        # Get revisions from current to head in upgrade order
        pending_revs = list(script_dir.iterate_revisions(current, "heads"))
        # Remove the first one since it's the current revision
        if pending_revs and pending_revs[0].revision == current:
            pending_revs = pending_revs[1:]

        # Return in upgrade order (base -> head)
        return [rev.revision for rev in reversed(pending_revs)]

    def migrate_to_revision(self, revision: str = "head") -> bool:
        """Migrate to specific revision."""
        try:
            logger.info(f"Starting migration to {revision}")
            current_revision = self.get_current_revision()

            # Perform migration
            command.upgrade(self.alembic_cfg, revision)

            new_revision = self.get_current_revision()
            if new_revision != current_revision:
                logger.info(f"Successfully migrated from {current_revision} to {new_revision}")
            else:
                logger.info(f"No migration needed - already at revision {current_revision}")

            return True

        except Exception as e:
            logger.error(f"Migration to {revision} failed: {e}")
            return False

    def rollback_to_revision(self, revision: str) -> bool:
        """Rollback to specific revision."""
        try:
            logger.info(f"Starting rollback to revision: {revision}")
            current_revision = self.get_current_revision()

            if not current_revision:
                logger.warning("No current revision to rollback from - database may be uninitialized")
                return False

            if current_revision == revision:
                logger.info(f"Already at target revision {revision} - no rollback needed")
                return True

            # Perform rollback
            command.downgrade(self.alembic_cfg, revision)

            new_revision = self.get_current_revision()
            if new_revision == revision:
                logger.info(f"Rollback successful: {current_revision} -> {new_revision}")
                return True
            else:
                logger.error(f"Rollback verification failed - expected {revision}, got {new_revision}")
                return False

        except Exception as e:
            logger.error(f"Rollback to {revision} failed: {e}")
            return False

    def validate_migration_integrity(self) -> tuple[bool, list[str]]:
        """Validate database integrity after migration."""
        issues: list[str] = []

        with self.SessionLocal() as session:
            try:
                # Check foreign key integrity (PRAGMA is SQLite-specific and safe)
                result = session.execute(text("PRAGMA foreign_key_check"))
                fk_violations = result.fetchall()
                if fk_violations:
                    issues.append(f"Foreign key violations: {fk_violations}")

                # Use SQLAlchemy ORM queries instead of raw SQL to prevent injection
                # These queries are built using the ORM, making them safe from SQL injection
                try:
                    # Check for orphaned questions
                    orphaned_questions = (
                        session.query(func.count(Question.id))
                        .outerjoin(SessionModel, Question.session_id == SessionModel.id)
                        .filter(SessionModel.id.is_(None))
                        .scalar()
                    )
                    if orphaned_questions > 0:
                        issues.append(f"Orphaned questions: {orphaned_questions} records")

                    # Check for orphaned answers (from questions perspective)
                    orphaned_answers_q = (
                        session.query(func.count(Answer.id))
                        .outerjoin(Question, Answer.question_id == Question.id)
                        .filter(Question.id.is_(None))
                        .scalar()
                    )
                    if orphaned_answers_q > 0:
                        issues.append(f"Orphaned answers: {orphaned_answers_q} records")

                    # Check for answer-session mismatch
                    orphaned_answers_s = (
                        session.query(func.count(Answer.id))
                        .outerjoin(SessionModel, Answer.session_id == SessionModel.id)
                        .filter(SessionModel.id.is_(None))
                        .scalar()
                    )
                    if orphaned_answers_s > 0:
                        issues.append(f"Answer-session mismatch: {orphaned_answers_s} records")

                    # Check for orphaned requirements
                    orphaned_requirements = (
                        session.query(func.count(Requirement.id))
                        .outerjoin(SessionModel, Requirement.session_id == SessionModel.id)
                        .filter(SessionModel.id.is_(None))
                        .scalar()
                    )
                    if orphaned_requirements > 0:
                        issues.append(f"Orphaned requirements: {orphaned_requirements} records")

                except ImportError:
                    # Fallback to safe parameterized queries if models aren't available
                    # Note: These table/column names are hardcoded and not user-controlled, so they're safe
                    safe_integrity_checks = [
                        (
                            "Orphaned questions",
                            text(
                                "SELECT COUNT(*) FROM questions q "
                                "LEFT JOIN sessions s ON q.session_id = s.id "
                                "WHERE s.id IS NULL"
                            ),
                        ),
                        (
                            "Orphaned answers",
                            text(
                                "SELECT COUNT(*) FROM answers a "
                                "LEFT JOIN questions q ON a.question_id = q.id "
                                "WHERE q.id IS NULL"
                            ),
                        ),
                        (
                            "Answer-session mismatch",
                            text(
                                "SELECT COUNT(*) FROM answers a "
                                "LEFT JOIN sessions s ON a.session_id = s.id "
                                "WHERE s.id IS NULL"
                            ),
                        ),
                        (
                            "Orphaned requirements",
                            text(
                                "SELECT COUNT(*) FROM requirements r "
                                "LEFT JOIN sessions s ON r.session_id = s.id "
                                "WHERE s.id IS NULL"
                            ),
                        ),
                    ]

                    for check_name, query in safe_integrity_checks:
                        try:
                            result = session.execute(query)
                            count = result.scalar()
                            if count and count > 0:
                                issues.append(f"{check_name}: {count} records")
                        except Exception as e:
                            issues.append(f"Check '{check_name}' failed: {e}")

            except Exception as e:
                issues.append(f"Database integrity check failed: {e}")

        return len(issues) == 0, issues

    def get_migration_status(self) -> dict[str, Any]:
        """Get basic migration status."""
        return {
            "current_revision": self.get_current_revision(),
            "all_revisions": self.get_all_revisions(),
            "pending_revisions": self.get_pending_revisions(),
        }

    def create_migration(self, message: str, autogenerate: bool = True) -> str | None:
        """Create a new migration."""
        try:
            if autogenerate:
                command.revision(self.alembic_cfg, message=message, autogenerate=True)
            else:
                command.revision(self.alembic_cfg, message=message)

            logger.info(f"Created migration: {message}")
            return message

        except Exception as e:
            logger.error(f"Failed to create migration '{message}': {e}")
            return None


def create_migration_manager(db_path: str = "specscribe.db") -> MigrationManager:
    """Factory function to create migration manager."""
    return MigrationManager(db_path)


if __name__ == "__main__":
    # Example usage
    manager = MigrationManager("test_migrations.db")

    print("Migration Status:")
    status = manager.get_migration_status()
    print(f"Current revision: {status['current_revision']}")
    print(f"Available revisions: {status['all_revisions']}")
    print(f"Pending revisions: {status['pending_revisions']}")

    # Check integrity separately
    integrity_ok, issues = manager.validate_migration_integrity()
    print(f"Integrity status: {'OK' if integrity_ok else 'Issues found'}")
    if not integrity_ok:
        print(f"Issues: {issues}")
