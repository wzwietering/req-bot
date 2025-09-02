from abc import ABC, abstractmethod


class IOInterface(ABC):
    """Abstract interface for user input/output operations."""

    @abstractmethod
    def print(self, message: str) -> None:
        """Print a message to the user."""
        pass

    @abstractmethod
    def input(self, prompt: str) -> str:
        """Get input from the user with a prompt."""
        pass


class ConsoleIO(IOInterface):
    """Console-based implementation of IOInterface."""

    def print(self, message: str) -> None:
        print(message)

    def input(self, prompt: str) -> str:
        return input(prompt).strip()


class TestableIO(IOInterface):
    """Testable implementation of IOInterface with predefined responses."""

    def __init__(self, responses: list[str] | None = None):
        self.responses = responses or []
        self.response_index = 0
        self.printed_messages: list[str] = []

    def print(self, message: str) -> None:
        self.printed_messages.append(message)

    def input(self, prompt: str) -> str:
        if self.response_index < len(self.responses):
            response = self.responses[self.response_index]
            self.response_index += 1
            return response
        return ""
