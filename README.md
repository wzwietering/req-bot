# Requirements Bot

A console assistant for gathering software requirements through interactive interviews with AI-powered analysis.

## Overview

Requirements Bot helps software teams and developers gather comprehensive requirements for new projects through structured, AI-powered interviews. It supports multiple AI providers (Anthropic Claude, OpenAI, Google Gemini) and generates requirements documents in Markdown format.

## Features

- **Interactive Interviews**: Two interview modes: structured and conversational
- **Multi-Provider Support**: Works with Anthropic Claude, OpenAI, and Google Gemini models
- **Intelligent Follow-ups**: AI analyzes answers and generates relevant follow-up questions
- **Completeness Assessment**: Automatically assesses when enough information has been gathered
- **Persistent Storage**: SQLite database storage for session persistence and retrieval
- **Session Management**: Save, load, list, and delete interview sessions
- **Structured Output**: Generates professional requirements documents in Markdown
- **Question Categories**: Organizes questions by scope, users, constraints, non-functional requirements, interfaces, data, risks, and success metrics

## Installation

### Prerequisites

- Python 3.11 or higher
- Poetry (recommended) or pip

### Using Poetry

```bash
git clone <repository-url>
cd req-bot
poetry install
```

### Using pip

```bash
git clone <repository-url>
cd req-bot
pip install -e .
```

### Database Setup

Requirements Bot uses SQLite for persistent storage. The database will be created automatically on first use. For development or to manage database migrations:

```bash
# Initialize database (optional - happens automatically)
alembic upgrade head

# Create new migration after model changes
alembic revision --autogenerate -m "Description of changes"
```

## Environment Variables

You'll need API keys for the AI providers you want to use:

| Variable | Provider | Required | Description |
|----------|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic Claude | Optional | API key from <https://console.anthropic.com> |
| `OPENAI_API_KEY` | OpenAI | Optional | API key from <https://platform.openai.com> |
| `GEMINI_API_KEY` | Google Gemini | Optional | API key from Google AI Studio |

**Note**: You only need to set the API key for the provider you intend to use.

### Setting Environment Variables

**Linux/macOS:**

```bash
export ANTHROPIC_API_KEY="your-anthropic-api-key"
export OPENAI_API_KEY="your-openai-api-key"
export GEMINI_API_KEY="your-gemini-api-key"
```

**Windows:**

```cmd
set ANTHROPIC_API_KEY=your-anthropic-api-key
set OPENAI_API_KEY=your-openai-api-key
set GEMINI_API_KEY=your-gemini-api-key
```

## Usage

Requirements Bot provides two main commands:

### Basic Interview Mode

Runs a structured interview with a fixed set of questions:

```bash
python -m requirements_bot.cli interview --project "My Web App" --out "requirements.md" --model "anthropic:claude-3-haiku-20240307"
```

### Conversational Interview Mode (Recommended)

Runs an intelligent conversational interview with follow-up questions and automatic completeness assessment:

```bash
python -m requirements_bot.cli conversational --project "My Web App" --out "requirements.md" --model "anthropic:claude-3-haiku-20240307" --max-questions 25
```

### Command Options

#### Common Options

- `--project`: Project name/title (required, will prompt if not provided)
- `--out`: Output file path (default: "requirements.md")
- `--model`: AI provider and model identifier (default: "anthropic:claude-3-haiku-20240307")
- `--db-path`: Database file path (default: "requirements_bot.db")

#### Conversational Mode Options

- `--max-questions`: Maximum number of questions to ask (default: 25)

### Session Management

Requirements Bot automatically saves interview sessions to a SQLite database. Sessions persist between runs and can be resumed or referenced later. The database includes:

- **Sessions**: Interview metadata and completion status
- **Questions**: All questions asked during interviews
- **Answers**: User responses with analysis flags
- **Requirements**: Generated requirements with priorities

## Example Session

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

## Output Format

The tool generates a structured Markdown document with:

- **Project Description**: Overview of the project
- **Questions and Answers**: Organized by category (scope, users, constraints, etc.)
- **Requirements**: Prioritized list of MUST/SHOULD/COULD requirements with rationale

Example output structure:

```markdown
# Requirements Document

## Project Description
E-commerce Mobile App

## Questions and Answers

### Scope
**Q: What problem are we solving?**
A: We need a mobile app for our online store...

### Users
**Q: Who are the primary users and their key jobs?**
A: Our customers who want to browse products...

## Requirements

### MUST Requirements
**REQ-001: User Authentication**
*Rationale: Essential for personalized shopping experience*

### SHOULD Requirements
**REQ-002: Push Notifications**
*Rationale: Improves user engagement and retention*
```

## Architecture

The project is structured with a modular provider system:

- `requirements_bot/cli.py`: Command-line interface
- `requirements_bot/core/`: Core business logic and models
  - `database.py`: SQLAlchemy ORM models
  - `storage.py`: Database storage implementation
  - `storage_interface.py`: Abstract storage interface
  - `memory_storage.py`: In-memory storage for testing
- `requirements_bot/providers/`: AI provider implementations
  - `anthropic.py`: Anthropic Claude integration
  - `openai.py`: OpenAI integration
  - `google.py`: Google Gemini integration
  - `base.py`: Abstract provider interface
- `alembic/`: Database migration management
- `tests/`: Comprehensive test suite including storage tests

## Question Categories

The bot organizes questions into eight key categories:

1. **Scope**: Problem definition and solution boundaries
2. **Users**: Target users and their needs
3. **Constraints**: Platform, budget, timeline limitations
4. **Non-functional**: Performance, security, compliance requirements
5. **Interfaces**: External system integrations and APIs
6. **Data**: Data storage, sources, and management
7. **Risks**: Potential risks and unknowns
8. **Success**: Success metrics and measurement criteria
