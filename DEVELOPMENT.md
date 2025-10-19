# Development Guide

**Last Updated**: 2025-10-05 | **Owner**: Core Team

## Quick Start

```bash
git clone https://github.com/wzwietering/req-bot.git
cd specscribe
npm run setup    # Install dependencies
npm run dev      # Start backend (8080) + frontend (3000)
```

**Prerequisites**: Node.js 18+, Python 3.11+, Poetry 2.1.4+, npm 8+

Install: `nvm install 18 && nvm use 18` | `pipx install poetry`

## Project Structure

```
specscribe/
├── apps/backend/         # FastAPI Python
├── apps/frontend/        # Next.js React
├── packages/shared-types/  # Auto-generated types
└── tools/scripts/        # Build scripts
```

## Environment Setup

```bash
# Backend
cp apps/backend/.env.example apps/backend/.env
# Edit: Add AI provider key (Anthropic/OpenAI/Gemini), OAuth (Google), JWT secret
# CLI-only → just one AI key needed

# Frontend
cp apps/frontend/.env.local.example apps/frontend/.env.local
# Edit: Set NEXT_PUBLIC_API_URL, GOOGLE_CLIENT_ID
```

See `.env.example` files for all configuration options.

## Available Commands

| Context | Command | Purpose |
|---------|---------|---------|
| **Root** | `npm run dev` | Start backend + frontend |
| | `npm run build` | Build all |
| | `npm run test` | Run all tests |
| | `npm run lint` | Lint all |
| | `npm run generate:types` | Generate types from API |
| **Backend** | `poetry run pytest` | Run tests |
| `apps/backend` | `poetry run pytest --cov` | Tests + coverage |
| | `poetry run ruff check .` | Lint |
| | `poetry run ruff format .` | Format |
| | `alembic upgrade head` | Apply migrations |
| | `alembic revision -m "msg"` | Create migration |
| | `python -m specscribe.cli conversational` | CLI mode |
| **Frontend** | `npm run dev` | Dev server |
| `apps/frontend` | `npm run build` | Production build |
| | `npm run lint` | ESLint |

## Key Workflows

### Type Generation
Backend API changes → `npm run generate:types`

Use in frontend: `import type { components } from '@specscribe/shared-types'`

### Database
```bash
alembic revision --autogenerate -m "msg"  # Create migration
alembic upgrade head                       # Apply
rm dev.db && alembic upgrade head          # Reset
```

### Testing
```bash
# Backend: poetry run pytest [tests/api/] [-v] [--cov]
# Frontend: npm test [-- --watch] [-- --coverage]
```

### Code Quality
```bash
# Backend: poetry run ruff check . && poetry run ruff format .
# Frontend: npm run lint [-- --fix]
# Pre-commit: cd apps/backend && poetry run pre-commit install
```

## Best Practices

Functions ≤20 lines, single responsibility | Early returns | Max 2-level nesting | Type hints everywhere | No `any` | Atomic commits

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Server won't start | Check `.env`, ensure port 8080 free |
| Types not found | `npm run generate:types` |
| Dependencies missing | `cd apps/backend && poetry install --sync` |
| Cache issues | `npm run clean && npm run build` |
| Poetry environment | `cd apps/backend && poetry env remove python && poetry install` |
| Conda issues | `conda init bash && source ~/.bashrc` |

## Feature Development

**General**: Create branch → Edit code → Add tests → Run tests → Generate types (if API changed) → Lint

**Backend**: Edit `apps/backend/` → `poetry run pytest` → Update schemas → `npm run generate:types` → Test at `/docs`

**Frontend**: Edit `apps/frontend/src/` → `npm run type-check` → `npm run lint` → Test at `localhost:3000`

**CLI**: Edit `apps/backend/specscribe/cli.py` → Test with `python -m specscribe.cli conversational`

**Add AI Provider**: Create `providers/my_provider.py` → Implement interface → Add to factory → Add env var → Tests

## Production Deployment

**Backend**: `poetry build && alembic upgrade head && uvicorn specscribe.api_server:app --host 0.0.0.0 --port 8080`

**Frontend**: `npm run build && npm run start`

## Performance & Debugging

**Backend Performance**: Database indexes, caching, connection pooling | Profile with `cProfile`/`py-spy`

**Frontend Performance**: React Query caching, code splitting, Image optimization, lazy loading

**Backend Debug**: `export SPECSCRIBE_LOG_LEVEL=DEBUG` | `python -m pdb api_server.py` | Use `log_event()`

**Frontend Debug**: React DevTools, Network tab, `console.log`, build output

## Resources

[CONTRIBUTING.md](CONTRIBUTING.md) | [GitHub Issues](https://github.com/wzwietering/req-bot/issues) | API docs: `localhost:8080/docs` | Test files for examples

## Next Steps

Explore: `localhost:8080/docs` + `localhost:3000` | Try CLI: `python -m specscribe.cli conversational` | Read tests + [CONTRIBUTING.md](CONTRIBUTING.md)
