# SpecScribe

![SpecScribe Logo](./logo-full.svg)

**Your AI Business Analyst**

[![codecov](https://codecov.io/gh/wzwietering/req-bot/branch/master/graph/badge.svg)](https://codecov.io/gh/wzwietering/req-bot)

SpecScribe is your AI-powered business analyst that transforms vague ideas into precise, code-ready specifications. Using an intelligent 8-category interview methodology, it asks the right follow-up questions to capture every critical detail—ensuring developers have complete context from day one.

**Three interfaces, one powerful methodology:** Web UI for project managers, CLI for developers, REST API for automation.

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

## Why SpecScribe?

Most teams can't afford a full-time business analyst. SpecScribe gives you the structured methodology and intelligent questioning of an experienced BA—available instantly, adapting to your workflow.

**Built for three personas:**
- **Project Managers**: Generate professional specs in minutes, not hours—stop chasing stakeholders for missing details
- **Developers**: Get clear, unambiguous requirements with technical constraints included
- **Founders**: Turn your idea into a technical blueprint that developers understand

**The difference:** Not just a chatbot that records what you say, but an intelligent interviewer that knows what questions to ask, when to dig deeper, and how to structure results into developer-ready specifications.

## Features

- **Guided interview methodology**: 8 comprehensive question categories with intelligent follow-ups that adapt based on your answers
- **Prioritized requirements**: Generates MUST/SHOULD/COULD classifications with clear rationale—developers know what to build first
- **Your choice of AI**: Claude, GPT, or Gemini—not locked into one provider
- **Three interfaces**: Web UI for project managers, CLI for developers, REST API for automation
- **Session persistence**: Save progress and resume anytime with SQLite storage
- **Auto-generated TypeScript types** from backend OpenAPI spec
- **Secure authentication**: OAuth + JWT for web interface

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
| `conversational` | Natural conversation mode |
| `list-sessions` | Show all saved sessions |
| `show-session <id>` | Display session details and export |
| `delete-session <id>` | Delete a session |

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

#### What You Get

Generated Markdown specifications include:
- **Project Overview**: Clear description and business context
- **Structured Interview**: Q&A organized by 8 categories (Scope, Users, Technical Constraints, Success Metrics, Risks, Timeline, Budget, and Stakeholders)
- **Prioritized Requirements**: MUST/SHOULD/COULD classification with rationale explaining why each requirement matters
- **Developer-Ready**: Clear enough to start coding immediately—no guesswork required

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

## Powered By

SpecScribe supports multiple AI providers—choose the one that fits your needs and budget:

- **Anthropic Claude** (4.5 Haiku, 4.5 Sonnet, 4.1 Opus)
- **OpenAI GPT** (GPT-5)
- **Google Gemini** (Gemini 2.5 Pro, Gemini 2.0 Pro)

Switch providers anytime with the `--model` flag.

## Support

- [GitHub Issues](https://github.com/wzwietering/req-bot/issues) - Bug reports, feature requests, and discussions
- [API Docs](http://localhost:8080/docs) - Interactive API documentation (when backend is running)
- [DEVELOPMENT.md](DEVELOPMENT.md) - Detailed setup and workflow guide
- [BRAND_GUIDE.md](BRAND_GUIDE.md) - Brand identity quick reference for contributors

## License

MIT License
