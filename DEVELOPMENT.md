# Development Guide

This document provides everything you need to start developing with the Requirements Bot monorepo.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/wzwietering/req-bot.git
cd req-bot

# Run setup (installs all dependencies)
npm run setup

# Start development servers
npm run dev
```

This starts both backend (port 8000) and frontend (port 3000) in development mode with hot reloading.

## Prerequisites

- **Node.js** 18.0.0 or higher
- **Python** 3.11 or higher
- **Poetry** 2.1.4 or higher
- **npm** 8.0.0 or higher

### Installation

#### Node.js
```bash
# Using nvm (recommended)
nvm install 18
nvm use 18
```

#### Poetry
```bash
# Using pipx (recommended)
pipx install poetry

# Or using pip
pip install poetry
```

## Project Structure

```
req-bot/
├── apps/
│   ├── backend/          # FastAPI Python application
│   └── frontend/         # Next.js React application
├── packages/
│   └── shared-types/     # Auto-generated TypeScript types from backend
├── tools/
│   └── scripts/          # Development and build scripts
└── .github/workflows/    # CI/CD configurations
```

## Development Workflow

### 1. Environment Setup

#### Backend Environment Variables
Create `apps/backend/.env`:
```bash
DATABASE_URL=sqlite:///./dev.db
JWT_SECRET_KEY=your-super-secret-jwt-key-32-characters-minimum
OAUTH_CLIENT_ID=your-oauth-client-id
OAUTH_CLIENT_SECRET=your-oauth-client-secret
```

#### Frontend Environment Variables
Create `apps/frontend/.env.local`:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 2. Available Commands

#### Root Commands (run from project root)
```bash
npm run dev              # Start both backend and frontend
npm run build            # Build all applications
npm run test             # Run all tests
npm run lint             # Lint all code
npm run type-check       # Type check all TypeScript
npm run generate:types   # Generate types from backend API
npm run clean            # Clean all build artifacts
```

#### Backend Commands (run from apps/backend/)
```bash
cd apps/backend

poetry run python requirements_bot/api_server.py  # Start API server
poetry run alembic upgrade head                   # Run migrations
poetry run pytest                                 # Run tests
poetry run ruff check .                          # Lint
poetry run ruff format .                         # Format
poetry run coverage run -m pytest                # Run tests with coverage
```

#### Frontend Commands (run from apps/frontend/)
```bash
cd apps/frontend

npm run dev          # Start Next.js dev server
npm run build        # Build for production
npm run start        # Start production server
npm run lint         # Run ESLint
npm run type-check   # Run TypeScript compiler
```

### 3. Type Generation Workflow

The monorepo uses auto-generated TypeScript types from the FastAPI backend:

1. **Backend changes**: When you modify API routes, schemas, or models
2. **Generate types**: Run `npm run generate:types`
3. **Frontend usage**: Import types from `@req-bot/shared-types`

```typescript
// In frontend code
import type { paths, components } from '@req-bot/shared-types';

// Use generated types
type SessionResponse = components['schemas']['SessionResponse'];
type CreateSessionRequest = components['schemas']['CreateSessionRequest'];
```

The type generation:
- Starts the backend server temporarily
- Fetches the OpenAPI spec from `/openapi.json`
- Generates TypeScript types using `openapi-typescript`
- Saves to `packages/shared-types/api.ts`

### 4. Database Management

#### Migrations
```bash
cd apps/backend

# Create new migration
poetry run alembic revision --autogenerate -m "Description"

# Apply migrations
poetry run alembic upgrade head

# View migration history
poetry run alembic history
```

#### Database Reset
```bash
cd apps/backend
rm dev.db  # Delete database file
poetry run alembic upgrade head  # Recreate with migrations
```

### 5. Testing

#### Backend Tests
```bash
cd apps/backend
poetry run pytest                    # Run all tests
poetry run pytest tests/api/         # Run API tests only
poetry run pytest -v                 # Verbose output
poetry run pytest --cov=requirements_bot  # With coverage
```

#### Frontend Tests (when added)
```bash
cd apps/frontend
npm test                # Run tests
npm run test:watch      # Watch mode
npm run test:coverage   # With coverage
```

### 6. Code Quality

#### Linting and Formatting
```bash
# Backend (uses ruff)
cd apps/backend
poetry run ruff check .      # Lint
poetry run ruff format .     # Format

# Frontend (uses ESLint + Prettier via Next.js)
cd apps/frontend
npm run lint                # Lint
npm run lint -- --fix      # Lint and fix
```

#### Pre-commit Hooks
The backend includes pre-commit configuration:
```bash
cd apps/backend
poetry run pre-commit install    # Install hooks
poetry run pre-commit run --all-files  # Run manually
```

### 7. Troubleshooting

#### Type Generation Issues
- **Server won't start**: Check backend environment variables
- **Dependencies missing**: Run `cd apps/backend && poetry install --sync`
- **Port conflicts**: Ensure port 8000 is available

#### Build Issues
- **Types not found**: Run `npm run generate:types` first
- **Cache issues**: Run `npm run clean` then rebuild
- **Poetry environment**: Try `poetry env remove python` then `poetry install`

#### Common Conda Issues
If using conda, the type generation script will automatically detect and initialize conda environments. If you encounter issues:

```bash
# Ensure conda is initialized
conda init bash
source ~/.bashrc

# Check conda environment
conda info --envs
```

### 8. Development Best Practices

#### Code Organization
- Keep functions under 20 lines
- Use clear, descriptive names
- Single responsibility principle
- Early returns to reduce nesting

#### API Development
- Add type hints to all Python functions
- Use Pydantic models for request/response schemas
- Add comprehensive tests for new endpoints
- Update API documentation

#### Frontend Development
- Use TypeScript strictly (no `any` types)
- Import API types from shared-types package
- Follow Next.js App Router conventions
- Use React Query for API calls

#### Git Workflow
- Create feature branches from `master`
- Write descriptive commit messages
- Keep commits atomic and focused
- Run tests before pushing

### 9. Production Deployment

#### Backend
```bash
cd apps/backend
poetry build                    # Create wheel
poetry run alembic upgrade head # Run migrations
poetry run uvicorn requirements_bot.api_server:app --host 0.0.0.0 --port 8000
```

#### Frontend
```bash
cd apps/frontend
npm run build    # Create optimized build
npm run start    # Start production server
```

## Getting Help

- Check existing issues on GitHub
- Review test files for usage examples
- Read FastAPI and Next.js documentation
- Ask questions in pull requests

## Next Steps

After setup, you might want to:
1. Explore the backend API at `http://localhost:8000/docs`
2. Check the frontend at `http://localhost:3000`
3. Review the test suite to understand expected behavior
4. Read `CONTRIBUTING.md` for code standards