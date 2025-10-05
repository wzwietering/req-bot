# Future Extensions for Req-Bot

## 1. Executive Summary

- Req-Bot already implements a reusable question → answer → follow-up pipeline with persistence, provider abstraction, and dual CLI/web surfaces.
- Hard-coded requirements engineering assumptions (categories, prompts, artifacts) constrain reuse; generalizing these touch points lets the flow serve other discovery and intake workflows.
- Recommended direction: introduce domain “playbooks” that specify seeds, prompts, artifact schemas, and UI metadata; refactor pipeline services to consume the playbook rather than requirements-specific literals.
- Initial expansion targets: incident postmortems, bug triage, QA test planning, sales discovery, support knowledge base drafting, and security/compliance evidence gathering.

## 2. Current Capabilities Snapshot

| Capability                                 | Location(s)                                                                      | Notes                                                                                                                 |
| ------------------------------------------ | -------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Interview orchestration with state machine | `apps/backend/requirements_bot/core/pipeline.py`, `.../core/services`            | Conversational and simple flows share session setup, loop management, completeness checks, and finalization services. |
| Provider abstraction                       | `apps/backend/requirements_bot/providers/base.py`                                | Supports Anthropic, OpenAI, Google; operations: question gen, answer analysis, completeness, summarization.           |
| Storage + persistence                      | `apps/backend/requirements_bot/core/storage.py`, `.../persistence`               | SQLite/Alembic-backed, thread-safe locks, CLI user support; easily swappable implementations.                         |
| CLI + Frontend surfaces                    | `apps/backend/requirements_bot/cli.py`, `apps/frontend/src/components/interview` | Same pipeline logic accessible via Typer CLI and Next.js UI with shared types.                                        |
| Telemetry & recovery                       | `apps/backend/requirements_bot/core/logging.py`, `.../core/state_manager.py`     | Structured spans, checkpointing, resumable sessions.                                                                  |

These pieces are domain-agnostic building blocks already suitable for broader application once requirements-specific assumptions are lifted.

## 3. Requirements-Specific Coupling

| Coupled Area                                                                                  | Impact                                                                                                                          | File(s)                                                                                                                 |
| --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Question categories + seed questions fixed to requirements (scope, users, etc.)               | Validation blockers for other domains; front-end badges, color themes rely on same enum.                                        | `core/models.py` (`Question.category`), `core/interview/question_queue.py` (seed list), `frontend/.../QuestionCard.tsx` |
| Prompts frame LLM as "requirements engineering expert" and expect requirements-focused output | Answer analysis and completeness heuristics oriented to business requirements, causing irrelevant follow-up behavior elsewhere. | `core/prompts.py`                                                                                                       |
| Artifact model is `Requirement` with MUST/SHOULD/COULD priorities                             | API responses/UI assume requirement document; prevents emitting alternate artifact types.                                       | `core/models.py`, `core/services/session_finalization_service.py`, `frontend/.../RequirementsView.tsx`                  |
| Session schemas hard-code requirement counts & metadata                                       | Extending to new domains would require parallel schema changes; currently no domain identifier persisted.                       | `api/schemas.py`, `shared-types`, `frontend/lib/api/types.ts`                                                           |
| CLI defaults and documentation focused on requirements use case                               | User experience tied to requirements; other domains lack entry points.                                                          | `README.md`, `apps/backend/requirements_bot/cli.py`                                                                     |

## 4. Generalization Strategy

1. **Domain Playbooks**

   - Create a `DomainPlaybook` interface encapsulating:
     - Category taxonomy & display metadata
     - Seed question templates + payload (possibly dynamic by project type)
     - Prompt families for question generation, answer analysis, completeness, and artifact summarization
     - Artifact schema & renderer (backend serializer + optional frontend component)
   - Store playbooks under `apps/backend/requirements_bot/domains/` with JSON/YAML or Python definitions to allow easy addition.

2. **Session & Pipeline Awareness**

   - Add `domain_id` to `Session` model and persist it via API/CLI at creation time.
   - Modify `SessionSetupManager` and `InterviewConductor` to fetch playbook configuration based on `domain_id`.
   - Refactor `QuestionGenerationService`, `InterviewLoopManager`, and `SessionFinalizationService` to obtain prompts and artifact builders from the playbook instead of hard-coded functions.

3. **Artifact Abstraction**

   - Replace `Requirement` model with a generic `SessionArtifact` base; specific playbooks can declare pydantic subclasses (e.g., `Requirement`, `IncidentFinding`, `TestCase`).
   - Update provider interface to `summarize_artifacts(...) -> list[BaseModel]` with playbook-supplied schema.
   - Ensure Markdown export (`Session.to_markdown`) delegates to playbook-specific renderer so CLI exports remain relevant.

4. **Prompt Modularization**

   - Move existing requirement prompts into a playbook, and allow playbooks to provide Jinja templates for consistent formatting.
   - Enable per-domain guardrails (e.g., highlight what completeness means for postmortems vs. sales discovery).

5. **Frontend Adaptation**

   - Extend interview context to request domain metadata (labels, colors, artifact component mapping) from the backend when a session is created.
   - Provide dynamic UI rendering: e.g., `ArtifactView` component registry keyed by domain.
   - Introduce domain selector on the interview setup page, defaulting to “Requirements”.

6. **CLI Enhancements**
   - Add `--domain` option to CLI commands; display domain-specific hints and output file names.
   - Update `README.md` and `DEVELOPMENT.md` to document domain playbook authoring.

## 5. Potential Domain Playbooks

| Domain                                  | Core Goals                                           | Seed Areas                                         | Artifact Concept                                                       | Notes                                                                      |
| --------------------------------------- | ---------------------------------------------------- | -------------------------------------------------- | ---------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| **Incident Postmortem Drafting**        | Capture timeline, impact, detection, remediation     | detection, impact, root cause, lessons             | `IncidentFinding` (timeline items, contributing factors, action items) | Follow-up prompts ensure missing timeline data is gathered before closure. |
| **Bug Triage Intake**                   | Collect reproducible bug reports & metadata          | environment, repro steps, expected vs actual, logs | `BugReport` (severity, ownership recommendations)                      | Completeness check ensures repro steps and impact assessed.                |
| **QA Test Planning**                    | Derive test charters from feature briefs             | user journeys, risk areas, data permutations       | `TestCaseDraft` (scenario, expected outcome, coverage notes)           | Summarizer produces prioritized test suites.                               |
| **Sales Discovery Coaching**            | Structure discovery calls & highlight MEDDIC factors | stakeholders, budget, timeline, pain               | `OpportunityBrief` (MEDDIC fields, next actions)                       | Could integrate scoring heuristics from completeness results.              |
| **Support Knowledge Base Articles**     | Turn resolved tickets into reusable docs             | symptoms, troubleshooting, resolution, prevention  | `KBArticle` (problem, solution, prevention tips)                       | Fit for contact-center workflows.                                          |
| **Security/Compliance Evidence Intake** | Document control implementations and gaps            | control scope, evidence, owner, frequency          | `ControlNarrative` (status, evidence links, gaps)                      | Completeness ensures required control families addressed.                  |

## 6. Incremental Implementation Roadmap

1. **Spike: Domain Metadata Plumbing**

   - Add `domain_id` column to sessions (migration + shared types regeneration).
   - Implement simple registry returning current requirements playbook; retrofit existing flow to use it.

2. **Refactor Prompts & Artifacts**

   - Move requirements prompts to playbook config; update provider calls to accept prompt content from playbook.
   - Introduce `SessionArtifact` abstraction and adjust summarization/markdown export.

3. **Frontend Domain Awareness**

   - Update session creation API to accept `domain_id` and return domain metadata (category labels, colors, artifact display template identifier).
   - Dynamically render question badges and artifact panels using metadata.

4. **Author Second Playbook (Incident Postmortem)**

   - Define prompts, seed questions, artifact schema, and Markdown/rendering logic.
   - Validate end-to-end via CLI and UI, ensuring follow-up logic and completeness behave as expected.

5. **Documentation & Templates**

   - Write `docs/domains.md` describing how to add new playbooks.
   - Provide scaffolding script to generate a new playbook skeleton.

6. **Stretch: Marketplace / Configurable Playbooks**
   - Allow loading playbooks from external files or admin UI for teams to customize without code changes.
   - Add versioning and validation for playbooks to ensure consistent experience.

## 7. Risks & Mitigations

| Risk                                                                                 | Impact | Mitigation                                                                                                                                        |
| ------------------------------------------------------------------------------------ | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| Over-generalizing core pipeline could introduce regressions in requirements use case | High   | Build comprehensive regression suite with fixtures for the existing domain before refactor; leverage feature flags to toggle new playbook system. |
| Prompt drift across domains decreases LLM reliability                                | Medium | Maintain domain-specific prompt unit tests and sample transcripts; use provider fallbacks to handle malformed responses.                          |
| Frontend complexity increases with dynamic artifacts                                 | Medium | Implement component registry pattern with lazy loading and type-safe props generated from shared types.                                           |
| Migration of existing sessions when adding `domain_id`                               | Low    | Default legacy sessions to `requirements` domain; provide migration script to patch existing rows.                                                |

## 8. Success Metrics

- Number of distinct playbooks in production (target ≥ 2 within first iteration).
- Interview completion rate and average number of follow-up questions per session per domain.
- User satisfaction metrics for new domains (e.g., usefulness ratings on generated artifacts).
- Reduction in manual effort for targeted workflows (e.g., time saved drafting incidents or test plans).

## 9. Conclusion

The existing architecture already encapsulates the hardest parts of conversational discovery: adaptive questioning, persistence, provider abstraction, and multi-surface delivery. By formalizing domain-specific knowledge into configurable playbooks and generalizing artifacts, Req-Bot can evolve from a requirements-focused assistant into a versatile intake engine for many adjacent workflows, expanding its value without re-engineering the core pipeline.
