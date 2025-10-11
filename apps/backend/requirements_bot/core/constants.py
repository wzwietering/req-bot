# Interview Question Limits - Just-in-time generation strategy
# These constants control the interview flow to balance thoroughness with efficiency.

# Start with 1 question to minimize upfront LLM costs and reduce time-to-first-question.
# Rationale: Users can start answering immediately without waiting for batch generation.
MAX_INITIAL_QUESTIONS = 1

# Generate new questions on-demand as the user progresses.
# Rationale: Just-in-time generation adapts to user responses and avoids wasted API calls.
MIN_QUEUE_SIZE = 1

# Target 3 questions per requirement area to get sufficient detail.
# Rationale: Empirically determined to gather enough context without over-questioning.
# Can be adjusted based on project complexity.
QUESTIONS_PER_AREA = 3

# Retry Configuration
DEFAULT_MAX_RETRIES = 3
RETRY_BASE_DELAY = 0.1  # Base delay in seconds for exponential backoff

# Default Paths
DEFAULT_DB_PATH = "requirements_bot.db"

# Interview Defaults
DEFAULT_MAX_QUESTIONS = 15

# CLI User
CLI_USER_ID = "cli-user"
