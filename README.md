# Requirements Bot

[![codecov](https://codecov.io/gh/wzwietering/req-bot/branch/master/graph/badge.svg)](https://codecov.io/gh/wzwietering/req-bot)

AI-powered requirements gathering through structured interviews. FastAPI backend + Next.js frontend.

## Quick Start

```bash
git clone https://github.com/wzwietering/req-bot.git
cd req-bot
npm run setup    # Install all dependencies
npm run dev      # Start backend (8080) + frontend (3000)
```

**Prerequisites**: Node.js 18+, Python 3.11+, Poetry 2.1.4+

### Environment Setup

```bash
# Backend
cp apps/backend/.env.example apps/backend/.env
# Edit .env - add at least one AI provider key (ANTHROPIC_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY)

# Frontend
cp apps/frontend/.env.local.example apps/frontend/.env.local
# Edit .env.local - set NEXT_PUBLIC_API_URL and GOOGLE_CLIENT_ID
```

See `.env.example` files for all options.

## Features

- **Two interview modes**: conversational (recommended) and structured
- **Multi-provider**: Anthropic Claude, OpenAI, Google Gemini
- **Three interfaces**: Web UI, CLI, REST API
- **Auto-generated TypeScript types** from backend OpenAPI spec
- **OAuth + JWT** for web authentication
- **Session persistence** with SQLite

## Usage

### Web Interface

1. Visit `http://localhost:3000`
2. Sign in with Google
3. Start interview → Answer questions → Export requirements

### CLI

```bash
cd apps/backend
export ANTHROPIC_API_KEY=your-key

# Start conversational interview
poetry run python -m requirements_bot.cli conversational --project "My Project"

# List sessions
poetry run python -m requirements_bot.cli sessions list

# Load saved session
poetry run python -m requirements_bot.cli load <session-id>
```

<details>
<summary>CLI Options & Examples</summary>

#### Available Commands

| Command | Description |
|---------|-------------|
| `conversational` | Natural conversation mode (recommended) |
| `interview` | Structured question-by-question mode |
| `sessions list` | Show all saved sessions |
| `sessions load <id>` | Continue a session |
| `sessions delete <id>` | Delete a session |

#### Common Options

| Option | Default | Description |
|--------|---------|-------------|
| `--project TEXT` | (required) | Project name |
| `--out PATH` | requirements.md | Output file path |
| `--model TEXT` | anthropic:claude-3-5-haiku-20241022 | Format: `provider:model-name` |
| `--db-path PATH` | requirements_bot.db | Database location |
| `--max-questions INT` | 25 | Max questions (conversational only) |

#### Examples

```bash
# Different AI providers
poetry run python -m requirements_bot.cli conversational \
  --project "E-commerce App" \
  --model "openai:gpt-4"

poetry run python -m requirements_bot.cli conversational \
  --project "Mobile App" \
  --model "gemini:gemini-1.5-pro"

# Custom output
poetry run python -m requirements_bot.cli conversational \
  --project "My Project" \
  --out "./docs/requirements.md" \
  --max-questions 15
```

#### Output Format

Generated Markdown includes:
- Project description and context
- Interview Q&A organized by category (Scope, Users, Constraints, etc.)
- Prioritized requirements (MUST/SHOULD/COULD) with rationale

</details>

### API

Interactive docs: `http://localhost:8080/docs`

## Development

Root commands:
```bash
npm run dev              # Start both servers
npm run build            # Build all apps
npm run test             # Run all tests
npm run lint             # Lint all code
npm run type-check       # TypeScript checking
npm run generate:types   # Backend API changes → regenerate types
```

<details>
<summary>Backend Commands</summary>

```bash
cd apps/backend

poetry run python requirements_bot/api_server.py  # Start server
poetry run pytest                                 # Tests
poetry run pytest --cov=requirements_bot         # Tests + coverage
poetry run ruff check .                          # Lint
poetry run ruff format .                         # Format
poetry run alembic upgrade head                  # Run migrations
```

</details>

<details>
<summary>Frontend Commands</summary>

```bash
cd apps/frontend

npm run dev          # Dev server
npm run build        # Production build
npm run start        # Production server
npm run lint         # Lint
npm run type-check   # Type checking
```

</details>

<details>
<summary>Project Structure</summary>

```
req-bot/
├── apps/
│   ├── backend/          # FastAPI Python app
│   └── frontend/         # Next.js React app
├── packages/
│   └── shared-types/     # Auto-generated TypeScript types
├── tools/scripts/        # Build scripts
└── .github/workflows/    # CI/CD
```

</details>

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for code standards and PR process.

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed setup and workflows.

**Key rules**: Functions ≤20 lines, single responsibility, type everything, test everything.

## Support

- [GitHub Issues](https://github.com/wzwietering/req-bot/issues) - Bug reports and features
- [API Docs](http://localhost:8080/docs) - When backend running
- [DEVELOPMENT.md](DEVELOPMENT.md) - Setup help

## License

MIT License
