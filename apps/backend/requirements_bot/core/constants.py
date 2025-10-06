# Interview Question Limits - Just-in-time generation strategy
MAX_INITIAL_QUESTIONS = 1  # Start with just 1 question
MAX_QUEUED_QUESTIONS = 2  # Never queue more than 2 questions ahead
MAX_FOLLOWUPS_PER_ANSWER = 2  # Max 2 follow-ups per answer
MIN_QUEUE_SIZE = 1  # Generate new question when queue drops below this
QUESTIONS_PER_AREA = 3  # Target number of questions per requirement area

# Retry Configuration
DEFAULT_MAX_RETRIES = 3
RETRY_BASE_DELAY = 0.1  # Base delay in seconds for exponential backoff

# Default Paths
DEFAULT_DB_PATH = "requirements_bot.db"

# Interview Defaults
DEFAULT_MAX_QUESTIONS = 15

# CLI User
CLI_USER_ID = "cli-user"
