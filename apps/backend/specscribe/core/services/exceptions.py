"""Service layer exceptions for business logic errors."""


class QuestionNotFoundError(Exception):
    """Raised when a question cannot be found in a session."""

    def __init__(self, question_id: str):
        self.question_id = question_id
        super().__init__(f"Question {question_id} not found")


class AnswerNotFoundError(Exception):
    """Raised when an answer cannot be found for a question."""

    def __init__(self, question_id: str):
        self.question_id = question_id
        super().__init__(f"Answer for question {question_id} not found")


class SessionCompleteError(Exception):
    """Raised when attempting to modify a completed session."""

    def __init__(self, operation: str):
        self.operation = operation
        super().__init__(f"Cannot {operation} for a completed session")


class QuotaExceededError(Exception):
    """Raised when user has exceeded their quota limit."""

    def __init__(self, current: int, limit: int, window_days: int = 30):
        self.current = current
        self.limit = limit
        self.window_days = window_days
        super().__init__(f"Quota exceeded ({current}/{limit} questions used in {window_days} days)")


class UserNotFoundError(Exception):
    """Raised when a user is not found in the database."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        super().__init__(f"User not found: {user_id}")
