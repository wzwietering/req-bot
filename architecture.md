# SpecScribe - Software Architecture

**Last Updated**: 2025-10-25

## Overview

SpecScribe is an AI-powered requirements gathering system that conducts structured interviews using an 8-category question framework. The system provides three interfaces (Web UI, CLI, REST API) that share the same core interview logic.

The implementation uses a monorepo architecture with separate frontend (Next.js) and backend (FastAPI) applications. Type safety is maintained across the stack through OpenAPI-generated TypeScript definitions.

**Key Architectural Characteristics**:
- Monorepo structure with Turborepo orchestration
- Type-safe contract via OpenAPI-generated TypeScript types
- Multi-provider AI support (Anthropic, OpenAI, Google)
- OAuth2 + JWT authentication
- SQLite storage with SQLAlchemy (PostgreSQL-compatible)
- Docker Compose deployment configuration

## Monorepo Structure

SpecScribe uses a Turborepo-based monorepo with NPM workspaces for the frontend and Poetry for the backend Python application.

```
specscribe/
├── apps/
│   ├── backend/              # Python FastAPI application
│   │   ├── specscribe/       # Core application code
│   │   ├── alembic/          # Database migrations
│   │   ├── tests/            # Backend tests
│   │   └── pyproject.toml    # Python dependencies
│   │
│   └── frontend/             # Next.js 15 React application
│       ├── src/              # TypeScript source code
│       ├── public/           # Static assets
│       └── package.json      # Node dependencies
│
├── packages/
│   └── shared-types/         # Auto-generated TypeScript types
│       ├── api.ts            # Generated from OpenAPI spec
│       └── index.ts          # Type exports
│
├── tools/
│   └── scripts/              # Build and type generation scripts
│
├── turbo.json                # Turborepo pipeline configuration
└── package.json              # Root workspace configuration
```

**Build System**: Turborepo manages parallel task execution across workspaces with caching and dependency tracking.

**Type Generation Flow**:
1. Backend FastAPI generates OpenAPI spec
2. `tools/scripts/generate-types.sh` fetches spec and runs `openapi-typescript`
3. Types are written to `packages/shared-types/api.ts`
4. Frontend imports type-safe schemas and API definitions

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         User Layer                          │
│  ┌───────────────┐  ┌──────────┐  ┌────────────────────┐   │
│  │   Web UI      │  │   CLI    │  │  External Apps     │   │
│  │  (Next.js)    │  │ (Typer)  │  │  (REST API)        │   │
│  └───────┬───────┘  └────┬─────┘  └─────────┬──────────┘   │
└──────────┼──────────────┼─────────────────┼────────────────┘
           │              │                 │
           └──────────────┼─────────────────┘
                          │
                          ▼
           ┌──────────────────────────────┐
           │   Authentication Layer       │
           │   (OAuth2 + JWT)             │
           └──────────────┬───────────────┘
                          │
                          ▼
           ┌──────────────────────────────┐
           │      REST API Layer          │
           │      (FastAPI)               │
           │                              │
           │  - Routes & Validation       │
           │  - Middleware Stack          │
           │  - Request/Response Schemas  │
           └──────────────┬───────────────┘
                          │
                          ▼
           ┌──────────────────────────────┐
           │    Core Business Logic       │
           │                              │
           │  - Interview Orchestration   │
           │  - Session Management        │
           │  - Question Queue            │
           │  - Service Layer             │
           └──────────────┬───────────────┘
                          │
           ┌──────────────┼──────────────┐
           │              │              │
           ▼              ▼              ▼
    ┌───────────┐  ┌───────────┐  ┌───────────┐
    │    AI     │  │  Storage  │  │   Data    │
    │ Providers │  │   Layer   │  │  Models   │
    │           │  │           │  │           │
    │ - Claude  │  │ - SQLite  │  │ - Session │
    │ - GPT     │  │ - Alembic │  │ - Question│
    │ - Gemini  │  │ - Sync    │  │ - Answer  │
    └───────────┘  └───────────┘  └───────────┘
```

## Frontend Architecture

### Technology Stack

- **Framework**: Next.js 15.5.4 with App Router and Turbopack
- **React**: 19.2.0
- **Styling**: Tailwind CSS 4.1.14
- **TypeScript**: 5.9.3
- **Type Safety**: Generated types from `@specscribe/shared-types`

### Application Structure

```
apps/frontend/src/
├── app/                          # Next.js App Router
│   ├── layout.tsx               # Root layout with AuthProvider
│   ├── page.tsx                 # Landing page
│   ├── login/                   # Login page
│   ├── auth/callback/           # OAuth callback handlers
│   ├── interview/
│   │   ├── new/                 # Create new session
│   │   └── [sessionId]/         # Interactive interview flow
│   └── sessions/
│       ├── page.tsx             # Sessions list
│       └── [id]/qa/             # Q&A view and editing
│
├── components/                   # React components
│   ├── auth/                    # Authentication UI
│   ├── interview/               # Interview interface
│   ├── layout/                  # Layout components
│   └── ui/                      # Reusable primitives
│
├── lib/                         # Utilities and services
│   ├── api/
│   │   ├── apiClient.ts         # API client with auto-refresh
│   │   ├── sessions.ts          # Session API calls
│   │   └── types.ts             # API type definitions
│   └── auth/
│       ├── api.ts               # Auth API calls
│       └── types.ts             # Auth types
│
└── hooks/                       # Custom React hooks
```

### Key Features

**Routes** (App Router):
- `/` - Landing page
- `/login` - Authentication
- `/auth/callback/{provider}` - OAuth callback
- `/interview/new` - Create session
- `/interview/{sessionId}` - Active interview
- `/sessions` - Session list
- `/sessions/{id}/qa` - Q&A view and editing

**Authentication Flow**:
1. User initiates OAuth login
2. Frontend redirects to backend `/api/v1/auth/login/{provider}`
3. Backend redirects to OAuth provider
4. Provider redirects to `/api/v1/auth/callback/{provider}`
5. Backend sets HTTP-only cookies (access + refresh tokens)
6. Frontend redirects to application

**API Client**:
- Centralized client with 401 retry logic
- Automatic token refresh on expiration
- Type-safe requests using generated types
- Custom error handling

## Backend Architecture

### Technology Stack

- **Framework**: FastAPI 0.118.3
- **Python**: 3.11+
- **ORM**: SQLAlchemy 2.0.44
- **Migrations**: Alembic 1.16.5
- **Authentication**: Authlib 1.6.5, python-jose 3.5.0
- **AI Providers**: anthropic 0.69.0, openai 2.3.0, google-genai 1.43.0

### Module Structure

```
apps/backend/specscribe/
├── api/                          # API Layer
│   ├── main.py                  # FastAPI app + middleware
│   ├── routes/                  # REST endpoints
│   │   ├── auth.py              # Authentication endpoints
│   │   ├── sessions.py          # Session CRUD
│   │   └── questions.py         # Question/Answer management
│   ├── middleware.py            # Auth, CORS, error handling
│   ├── dependencies.py          # Dependency injection
│   ├── schemas.py               # Pydantic request/response models
│   └── services/
│       └── interview_service.py # API-specific orchestration
│
├── core/                         # Business Logic Layer
│   ├── models.py                # Domain models
│   ├── database_models/         # SQLAlchemy ORM models
│   ├── services/                # 27 specialized service modules
│   │   ├── session_service.py
│   │   ├── user_service.py
│   │   ├── question_generation_service.py
│   │   └── oauth_*_service.py
│   ├── persistence/             # Data synchronization
│   │   ├── session_persistence_service.py
│   │   ├── question_synchronizer.py
│   │   ├── answer_synchronizer.py
│   │   └── requirement_synchronizer.py
│   ├── interview/               # Interview orchestration
│   │   ├── interview_conductor.py
│   │   └── question_queue.py
│   ├── storage.py               # DatabaseManager
│   ├── storage_interface.py     # Abstract storage interface
│   ├── memory_storage.py        # In-memory for testing
│   └── prompts.py               # LLM prompt templates
│
├── providers/                    # AI Provider Layer
│   ├── base.py                  # Abstract provider interface
│   ├── anthropic.py             # Claude integration
│   ├── openai.py                # GPT integration
│   └── google.py                # Gemini integration
│
├── cli.py                       # CLI interface (Typer)
└── api_server.py                # Server entry point
```

### API Endpoints (High-Level Groupings)

**Authentication** (`/api/v1/auth`):
- OAuth login/callback for Google, GitHub, Microsoft
- Token refresh and logout
- User profile management

**Sessions** (`/api/v1/sessions`):
- Create, list, retrieve, delete sessions
- Session status and completion state

**Interview Flow** (`/api/v1/sessions/{session_id}`):
- Get next question (`POST /continue`)
- Submit answers (`POST /answers`)
- Finalize and generate requirements (`POST /finalize`)
- Q&A management (create, update, delete)

### Middleware Stack

Applied in order (FastAPI middleware onion model):

1. **SessionMiddleware** - OAuth state management
2. **CORSMiddleware** - Cross-origin request handling
3. **RequestIDMiddleware** - Request tracing
4. **AuthenticationMiddleware** - JWT validation + auto-refresh
5. **ExceptionHandlingMiddleware** - Unified error responses

### Service Layer

27 service modules organized by domain concern:

- CRUD operations (questions, answers, requirements)
- OAuth handling (configuration, state, callbacks)
- Business logic (sessions, interview orchestration)
- Persistence (synchronization between Pydantic and SQLAlchemy models)

## AI Provider Layer

### Provider Interface

Abstract base class defining the AI provider contract:

```python
class BaseProvider(ABC):
    @abstractmethod
    def generate_questions(context: str) -> List[Question]

    @abstractmethod
    def analyze_answer(question: str, answer: str) -> AnswerAnalysis

    @abstractmethod
    def generate_followups(context: dict) -> List[Question]

    @abstractmethod
    def assess_completeness(session: Session) -> CompletenessAssessment

    @abstractmethod
    def summarize_requirements(session: Session) -> List[Requirement]
```

**Implementations**:
- AnthropicProvider (Claude 3.5 Sonnet, Haiku, Opus)
- OpenAIProvider (GPT-4, GPT-4 Turbo)
- GoogleProvider (Gemini 1.5 Pro, Flash)

**Features**:
- JSON response parsing with fallback
- Error handling and degradation
- Runtime provider selection

## Database & Storage

### Schema

SQLite (development) with PostgreSQL-compatible design:

```
users
├── id (PK)
├── email
├── provider (google/github/microsoft)
├── provider_id
├── name
├── avatar_url
└── timestamps

sessions
├── id (PK)
├── user_id (FK)
├── project
├── conversation_complete
├── conversation_state
├── state_context (JSON)
└── timestamps

questions
├── id (PK)
├── session_id (FK)
├── text
├── category (scope/users/constraints/etc.)
├── required
└── order_index

answers
├── id (PK)
├── session_id (FK)
├── question_id (FK)
├── text
├── is_vague
├── needs_followup
└── created_at

requirements
├── id (PK)
├── session_id (FK)
├── title
├── rationale
├── priority (MUST/SHOULD/COULD)
└── order_index

oauth_states
├── state (PK)
├── created_at
└── expires_at

refresh_tokens
├── id (PK)
├── user_id (FK)
├── token_hash
├── created_at
├── expires_at
└── revoked
```

### Migrations

Alembic 1.16.5 manages schema changes:
- Location: `apps/backend/alembic/versions/`
- Workflow: `alembic revision --autogenerate -m "msg"` → `alembic upgrade head`

### Persistence Layer

Synchronizers handle bidirectional mapping between Pydantic and SQLAlchemy models:

- QuestionSynchronizer: Question ordering and categorization
- AnswerSynchronizer: One-to-one with questions
- RequirementSynchronizer: Priority-based grouping
- SessionPersistenceService: Orchestrates synchronization

## Shared Types & Type Safety

### Type Generation Pipeline

```
Backend (FastAPI)
    ↓ Generates
OpenAPI Spec (JSON)
    ↓ tools/scripts/generate-types.sh
openapi-typescript (v7.9.1)
    ↓ Outputs
packages/shared-types/api.ts
    ↓ Frontend imports
Type-safe API calls
```

### Frontend Usage

```typescript
import type { paths, components } from '@specscribe/shared-types';

type SessionResponse = components['schemas']['SessionResponse'];
type CreateSessionRequest = components['schemas']['CreateSessionRequest'];

// Type-safe API client methods automatically inferred
const session = await apiClient.post<SessionResponse>(
  '/api/v1/sessions',
  data
);
```

Benefits:
- Compile-time type checking
- IDE auto-completion
- Breaking change detection

## Architectural Patterns

### Strategy Pattern
- AI provider abstraction (`providers/base.py`)
- Allows runtime provider selection

### Repository Pattern
- Storage abstraction (`storage_interface.py`)
- Implementations: `DatabaseManager`, `MemoryStorage`

### Service Layer
- Business logic in `core/services/` (27 modules)
- Reusable across API and CLI interfaces

### Middleware Chain
- Layered middleware in `api/middleware.py`
- Handles auth, CORS, logging, errors

### DTO Pattern
- Pydantic models for API contracts (`api/schemas.py`)
- Separated from domain models

### Synchronizer Pattern
- Bidirectional sync between Pydantic and SQLAlchemy models
- Located in `core/persistence/`

## Data Flow

### Authentication Flow

```
Frontend                Backend                 OAuth Provider
   │                       │                          │
   │  Click "Sign In"      │                          │
   │──────────────────────>│                          │
   │                       │  Redirect to provider    │
   │                       │─────────────────────────>│
   │                       │                          │
   │                       │  User authorizes         │
   │                       │<─────────────────────────│
   │                       │  (with code)             │
   │                       │                          │
   │                       │  Exchange code for token │
   │                       │─────────────────────────>│
   │                       │<─────────────────────────│
   │                       │                          │
   │                       │  Create/update user      │
   │                       │  Generate JWT pair       │
   │                       │  Set HTTP-only cookies   │
   │                       │                          │
   │  Redirect to app      │                          │
   │<──────────────────────│                          │
   │  (with cookies)       │                          │
```

### Interview Session Lifecycle

```
1. Session Creation
   User → Frontend → API → SessionService → AI Provider (generate questions)
                        → DatabaseManager (save session + questions)

2. Interview Loop
   User answer → Frontend → API → AnswerService (save answer)
                                → AI Provider (analyze quality)
                                → AI Provider (generate follow-ups if needed)
                                → QuestionService (enqueue follow-ups)
                                → InterviewConductor (get next question)

3. Completeness Assessment (periodic)
   API → AI Provider (assess session completeness)
       → SessionService (update state)

4. Requirements Generation
   User finalize → API → AI Provider (synthesize all Q&A into requirements)
                      → RequirementService (save requirements)
                      → SessionService (mark complete)
```

### Question Categories

8-category question framework:

- Scope: Problem definition and boundaries
- Users: Target users and needs
- Constraints: Platform, budget, timeline
- Non-functional: Performance, security, compliance
- Interfaces: External system integrations
- Data: Storage and management
- Risks: Potential issues and unknowns
- Success: Metrics and measurement

### Session States

State progression:

`INITIALIZING` → `INTERVIEWING` → `ANALYZING` → `GENERATING_FOLLOWUPS` → `ASSESSING_COMPLETENESS` → `GENERATING_REQUIREMENTS` → `COMPLETE`

## Design Decisions

### Monorepo with Turborepo
- Enables code sharing and type generation
- Trade-off: Setup complexity vs. type safety

### Multi-Provider AI Support
- Abstract provider interface avoids vendor lock-in
- Trade-off: Added complexity vs. flexibility

### OpenAPI Type Generation
- Eliminates manual type synchronization
- Trade-off: Build dependency vs. type safety

### OAuth2 + JWT Authentication
- Standard approach with refresh token rotation
- Supports multiple OAuth providers

### SQLite with SQLAlchemy
- Simple development setup
- SQLAlchemy abstraction enables PostgreSQL migration

### Pydantic Validation
- Runtime validation and serialization
- Automatic OpenAPI schema generation

### Service Layer
- Reusable business logic across interfaces
- 27 modules with single responsibilities

## Deployment Architecture

### Docker Compose Setup

```yaml
services:
  backend:
    build: apps/backend/
    ports: 8080:8080
    volumes: backend_data:/app/data
    healthcheck: curl http://localhost:8080/health

  frontend:
    build: apps/frontend/
    ports: 3000:3000
    environment:
      NEXT_PUBLIC_API_URL: http://backend:8080
    depends_on:
      backend: { condition: service_healthy }

volumes:
  backend_data:  # Persists SQLite database

networks:
  specscribe-network:
```

Features:
- Container isolation with bridge network
- Health check-based orchestration
- Persistent volume for SQLite database
- Environment-based configuration

### Environment Variables

Backend (`.env`):
- `DATABASE_URL` - Database connection
- `JWT_SECRET_KEY` - JWT signing key
- `OAUTH_CLIENT_ID` / `OAUTH_CLIENT_SECRET` - Per-provider OAuth credentials
- `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY` - AI provider keys
- `ALLOWED_ORIGINS` - CORS configuration

Frontend:
- `NEXT_PUBLIC_API_URL` - Backend API URL
- OAuth client IDs for redirects

## Quality Attributes

### Extensibility
- Add AI providers via `BaseProvider` interface
- Swap storage backends via `StorageInterface`
- Multi-provider OAuth support
- Modular document generation

### Reliability
- Exception handling with degradation
- Fallback behaviors for AI failures
- Input validation via Pydantic
- Database transaction management

### Type Safety
- TypeScript frontend + Python type hints
- OpenAPI → TypeScript generation
- Compile-time error detection

### Security
- OAuth2 + JWT authentication
- Refresh token rotation
- HTTP-only cookies
- CSRF protection via state parameter
- Input validation
- SQLAlchemy ORM (SQL injection prevention)

### Testability
- In-memory storage for unit tests
- Mock AI providers
- FastAPI dependency injection
- Isolated service layer

### Interface Flexibility
- Three interfaces: Web UI, CLI, REST API
- Shared core business logic
- Session persistence and resumption

## Future Considerations

### Potential Enhancements

1. Export formats: PDF, DOCX, JSON
2. Usage analytics and metrics
3. Multi-user collaboration
4. Domain-specific question templates
5. PostgreSQL migration
6. Redis caching layer
7. Webhook notifications
8. White-label deployment support

### Scalability Path

Current: Single-user, SQLite storage, local execution

Potential evolution:
- PostgreSQL via SQLAlchemy (no code changes)
- Redis for session/response caching
- Horizontal scaling (stateless API)
- Multi-tenancy (user isolation exists)
- Background job processing (Celery/RQ)

## Summary

SpecScribe is a monorepo application with distinct frontend (Next.js) and backend (FastAPI) components connected via type-safe contracts. The architecture separates concerns across API, business logic, and infrastructure layers.

Key characteristics:
- Three interfaces (Web UI, CLI, REST API) share core interview logic
- Multi-provider AI support via strategy pattern
- Type safety maintained through OpenAPI generation
- Service-oriented backend with 27 specialized modules
- OAuth2 + JWT authentication with token refresh
- SQLite storage with PostgreSQL migration path
