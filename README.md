# Requirements Bot

[![codecov](https://codecov.io/gh/wzwietering/req-bot/branch/master/graph/badge.svg)](https://codecov.io/gh/wzwietering/req-bot)

A modern monorepo containing both a FastAPI backend for AI-powered requirements gathering and a Next.js frontend for web-based interactions.

## Overview

Requirements Bot helps software teams and developers gather comprehensive requirements for new projects through structured, AI-powered interviews. The system consists of:

- **Backend** (`apps/backend/`): FastAPI application with OAuth authentication, AI provider integrations, and comprehensive API
- **Frontend** (`apps/frontend/`): Next.js web application with modern React, TypeScript, and Tailwind CSS
- **Shared Types** (`packages/shared-types/`): Auto-generated TypeScript types from the FastAPI OpenAPI specification

The system supports multiple AI providers (Anthropic Claude, OpenAI, Google Gemini) and can be used both programmatically via API and through the web interface.

## Features

### Core Functionality
- **Interactive Interviews**: Two interview modes: structured and conversational
- **Multi-Provider Support**: Works with Anthropic Claude, OpenAI, and Google Gemini models
- **Intelligent Follow-ups**: AI analyzes answers and generates relevant follow-up questions
- **Completeness Assessment**: Automatically assesses when enough information has been gathered
- **Persistent Storage**: SQLite database storage for session persistence and retrieval
- **Session Management**: Save, load, list, and delete interview sessions
- **Structured Output**: Generates professional requirements documents in Markdown

### Technical Features
- **OAuth Authentication**: Google OAuth integration with JWT tokens and refresh token support
- **RESTful API**: Comprehensive FastAPI backend with OpenAPI documentation
- **Type Safety**: Auto-generated TypeScript types shared between backend and frontend
- **Modern Frontend**: Next.js 15+ with App Router, React 19, and Tailwind CSS 4+
- **Development Experience**: Hot reloading, concurrent development, and comprehensive tooling
- **CI/CD Ready**: Separate workflows for backend and frontend with proper testing

## Quick Start

### Prerequisites

- **Node.js** 18.0.0 or higher
- **Python** 3.11 or higher
- **Poetry** 2.1.4 or higher
- **npm** 8.0.0 or higher

### Installation

```bash
# Clone and setup everything
git clone https://github.com/wzwietering/req-bot.git
cd req-bot

# Install all dependencies (backend + frontend)
npm run setup

# Start development servers (both backend and frontend)
npm run dev
```

This will start:
- **Backend API** at `http://localhost:8080` (with docs at `/docs`)
- **Frontend Web App** at `http://localhost:3000`

### CLI Usage

For command-line usage without the web interface:

```bash
cd apps/backend
poetry install

# Run interactive requirements gathering
poetry run python -m requirements_bot.cli conversational --project "My Project"
```

## Development

For detailed development setup and contributing guidelines, see:
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Complete development guide
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Code standards and contribution process

### Available Scripts

```bash
npm run dev              # Start both backend and frontend
npm run build            # Build all applications
npm run test             # Run all tests
npm run lint             # Lint all code
npm run type-check       # Type check all TypeScript
npm run generate:types   # Generate types from backend API
```

### Project Structure

```
req-bot/
├── apps/
│   ├── backend/          # FastAPI Python application
│   └── frontend/         # Next.js React application
├── packages/
│   └── shared-types/     # Auto-generated TypeScript types
├── tools/
│   └── scripts/          # Development and build scripts
└── .github/workflows/    # CI/CD configurations
```

## Environment Variables

### Backend Configuration
Create `apps/backend/.env`:
```bash
# AI Provider Keys (choose one or more)
ANTHROPIC_API_KEY=your-anthropic-api-key
OPENAI_API_KEY=your-openai-api-key
GEMINI_API_KEY=your-gemini-api-key

# OAuth Configuration
OAUTH_CLIENT_ID=your-google-oauth-client-id
OAUTH_CLIENT_SECRET=your-google-oauth-client-secret

# JWT Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key-32-characters-minimum

# Database (optional - defaults to SQLite)
DATABASE_URL=sqlite:///./requirements_bot.db
```

### Frontend Configuration
Create `apps/frontend/.env.local`:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8080
```

See [DEVELOPMENT.md](DEVELOPMENT.md) for detailed environment setup.

## API Documentation

When running the backend, API documentation is available at:
- **Swagger UI**: `http://localhost:8080/docs`
- **ReDoc**: `http://localhost:8080/redoc`
- **OpenAPI JSON**: `http://localhost:8080/openapi.json`

## Legacy CLI Usage

The original CLI interface is still available for direct command-line usage. See the [Legacy CLI Documentation](#legacy-cli-documentation) section below for details.

---

## Legacy CLI Documentation

<details>
<summary>Click to expand original CLI documentation</summary>

### Command Usage

Requirements Bot provides two main commands:

#### Basic Interview Mode
```bash
python -m requirements_bot.cli interview --project "My Web App" --out "requirements.md" --model "anthropic:claude-3-5-haiku-20241022"
```

#### Conversational Interview Mode (Recommended)
```bash
python -m requirements_bot.cli conversational --project "My Web App" --out "requirements.md" --model "anthropic:claude-3-5-haiku-20241022" --max-questions 25
```

### Command Options

#### Common Options
- `--project`: Project name/title (required, will prompt if not provided)
- `--out`: Output file path (default: "requirements.md")
- `--model`: AI provider and model identifier (default: "anthropic:claude-3-5-haiku-20241022")
- `--db-path`: Database file path (default: "requirements_bot.db")

#### Conversational Mode Options
- `--max-questions`: Maximum number of questions to ask (default: 25)

### Example Session
```bash
$ python -m requirements_bot.cli conversational --project "E-commerce Mobile App"

=== Starting conversational interview ===
I'll ask questions to understand your requirements. I may ask follow-up questions based on your answers.

[1] [SCOPE] What problem are we solving?
> We need a mobile app for our online store so customers can shop on their phones

[2] [USERS] Who are the primary users and their key jobs?
> Our customers who want to browse products, add items to cart, and checkout quickly while mobile

   → I need to ask a follow-up: Need more specificity about user demographics

[3] [USERS] What age range and technical comfort level do your customers have?
> Mostly 25-45 year olds, pretty comfortable with mobile apps like Amazon and Target

...

✓ Assessment: Sufficient information gathered across all key areas
=== Generating requirements from 12 answers ===
Requirements written to requirements.md
```

### Output Format

The tool generates a structured Markdown document with:
- **Project Description**: Overview of the project
- **Questions and Answers**: Organized by category (scope, users, constraints, etc.)
- **Requirements**: Prioritized list of MUST/SHOULD/COULD requirements with rationale

### Question Categories

The bot organizes questions into eight key categories:
1. **Scope**: Problem definition and solution boundaries
2. **Users**: Target users and their needs
3. **Constraints**: Platform, budget, timeline limitations
4. **Non-functional**: Performance, security, compliance requirements
5. **Interfaces**: External system integrations and APIs
6. **Data**: Data storage, sources, and management
7. **Risks**: Potential risks and unknowns
8. **Success**: Success metrics and measurement criteria

</details>
