from requirements_bot.core.database_models import RequirementTable
from requirements_bot.core.models import Requirement, Session


class RequirementSynchronizer:
    """Handles synchronization of requirements between session objects and database."""

    def sync_requirements(self, session: Session, merged_session, db_session) -> None:
        """Synchronize requirements between session and database."""
        existing_requirements = {r.id: r for r in merged_session.requirements}
        current_requirement_ids = set()

        for i, requirement in enumerate(session.requirements):
            current_requirement_ids.add(requirement.id)
            if requirement.id in existing_requirements:
                self._update_existing_requirement(
                    existing_requirements[requirement.id], requirement, i
                )
            else:
                self._add_new_requirement(requirement, session.id, i, db_session)

        self._remove_orphaned_requirements(
            existing_requirements, current_requirement_ids, db_session
        )

    def convert_requirements_from_table(self, session_table) -> list[Requirement]:
        """Convert database requirement records to Requirement objects."""
        requirements_sorted = sorted(
            session_table.requirements, key=lambda r: r.order_index
        )
        return [
            Requirement(
                id=r.id,
                title=r.title,
                rationale=r.rationale,
                priority=r.priority,
            )
            for r in requirements_sorted
        ]

    def _update_existing_requirement(
        self, existing_r, requirement: Requirement, order_index: int
    ) -> None:
        """Update existing requirement with new data."""
        existing_r.title = requirement.title
        existing_r.rationale = requirement.rationale
        existing_r.priority = requirement.priority
        existing_r.order_index = order_index

    def _add_new_requirement(
        self, requirement: Requirement, session_id: str, order_index: int, db_session
    ) -> None:
        """Add new requirement to database."""
        r_table = RequirementTable(
            id=requirement.id,
            title=requirement.title,
            rationale=requirement.rationale,
            priority=requirement.priority,
            session_id=session_id,
            order_index=order_index,
        )
        db_session.add(r_table)

    def _remove_orphaned_requirements(
        self, existing_requirements: dict, current_ids: set, db_session
    ) -> None:
        """Remove requirements that are no longer present in session."""
        for r_id, existing_r in existing_requirements.items():
            if r_id not in current_ids:
                db_session.delete(existing_r)
