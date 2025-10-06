import logging
from abc import ABC, abstractmethod
from pathlib import Path

from requirements_bot.core.interview_constants import EXIT_COMMANDS, EXIT_SIGNAL

try:
    from prompt_toolkit import prompt
    from prompt_toolkit.completion import WordCompleter
    from prompt_toolkit.history import FileHistory
    from rich.console import Console
    from rich.panel import Panel

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


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

    def print_interview_header(self, remaining_questions: int = 0) -> None:
        """Print interview start header."""
        self.print("\n=== Starting conversational interview ===")
        self.print(
            "I'll ask questions to understand your requirements. I may ask follow-up questions using your answers."
        )
        self.print_info("💡 Tip: Type 'exit', 'quit', or 'done' to save your progress and exit anytime.")

    def print_requirements_generation(self, answer_count: int) -> None:
        """Print requirements generation start message."""
        self.print(f"\n=== Generating requirements from {answer_count} answers ===")

    def print_question_with_progress(
        self, question_text: str, question_number: int, total_questions: int, category: str = ""
    ) -> None:
        """Print a question with progress information and category."""
        if category:
            progress_info = f"[{question_number}/{total_questions}] [{category.upper()}]"
        else:
            progress_info = f"[{question_number}/{total_questions}]"
        self.print(f"\n{progress_info} {question_text}")

    def print_assessment_feedback(self, reasoning: str, missing_areas: list[str] = None) -> None:
        """Print completeness assessment feedback."""
        self.print_success(f"Assessment: {reasoning}")
        if missing_areas:
            self.print_info(f"Still need info on: {', '.join(missing_areas)}")

    def print_follow_up_context(self, analysis_notes: str) -> None:
        """Print context for follow-up questions."""
        self.print(f"   → I need to ask a follow-up: {analysis_notes}")

    def print_session_message(self, message: str, is_warning: bool = False) -> None:
        """Print session-related messages (creation, resumption, etc)."""
        if is_warning:
            self.print_info(f"⚠ {message}")
        else:
            self.print_info(message)

    def print_exit_message(self) -> None:
        """Print exit message when user exits interview."""
        self.print_success("Exiting interview. Session has been saved.")


class RichConsoleIO(IOInterface):
    """Rich console implementation with enhanced input/output features."""

    def __init__(self, session_id: str | None = None):
        self.session_id = session_id
        self.console = Console() if RICH_AVAILABLE else None
        self.history_file = None

        if RICH_AVAILABLE and session_id:
            sanitized_id = self._sanitize_session_id(session_id)
            history_dir = Path.home() / ".req_bot" / "history"
            history_dir.mkdir(parents=True, exist_ok=True)
            self.history_file = str(history_dir / f"{sanitized_id}.txt")

    def _sanitize_session_id(self, session_id: str) -> str:
        """Sanitize session ID to prevent path traversal attacks.

        Args:
            session_id: Raw session ID from user input

        Returns:
            Sanitized session ID (max 50 characters) safe for use in filenames
        """
        # Remove path separators and dangerous characters, keep only alphanumeric, dash, underscore
        sanitized = "".join(c for c in session_id if c.isalnum() or c in "-_")
        # Limit length to 50 characters to prevent extremely long filenames
        return sanitized[:50] if sanitized else "unknown_session"

    def print(self, message: str) -> None:
        if self.console:
            # Create a nice panel for questions/messages
            if message.strip().endswith("?"):
                panel = Panel(message, title="🤖 Question", border_style="blue", padding=(1, 2))
                self.console.print(panel)
            else:
                self.console.print(f"[blue]ℹ[/blue] {message}")
        else:
            print(message)

    def input(self, prompt_str: str) -> str:
        """Get input from user with rich features or fallback to basic input."""
        if RICH_AVAILABLE:
            return self._rich_input(prompt_str)
        return input(prompt_str).strip()

    def _rich_input(self, prompt_str: str) -> str:
        """Handle rich input with styling, history, and completions."""
        try:
            self._display_styled_prompt(prompt_str)
            result = self._get_prompt_input()
            return self._process_input_result(result)
        except (KeyboardInterrupt, EOFError):
            self._display_exit_tip()
            return ""
        except Exception as e:
            self._log_rich_input_error(e)
            return input(prompt_str).strip()

    def _display_styled_prompt(self, prompt_str: str) -> None:
        """Display the prompt with rich styling."""
        if self.console:
            self.console.print(f"[bold green]{prompt_str}[/bold green]", end="")

    def _get_prompt_input(self) -> str:
        """Get input using prompt_toolkit with history and completions."""
        history = FileHistory(self.history_file) if self.history_file else None
        completer = self._create_completer()

        return prompt(
            "",  # Empty prompt since we already displayed it with styling
            history=history,
            completer=completer,
            complete_while_typing=False,
        )

    def _create_completer(self) -> "WordCompleter":
        """Create auto-completer with common requirements terms and exit commands."""
        completions = [
            "yes",
            "no",
            "maybe",
            "not sure",
            "I don't know",
            "web application",
            "mobile app",
            "desktop app",
            "API",
            "user authentication",
            "database",
            "file upload",
            "search",
            "real-time",
            "notifications",
            "payments",
            "reporting",
        ] + list(EXIT_COMMANDS)
        return WordCompleter(completions, ignore_case=True)

    def _process_input_result(self, result: str) -> str:
        """Process input result and handle exit commands."""
        result_clean = result.strip()
        if result_clean.lower() in EXIT_COMMANDS:
            self.print_info("Session saved! Use --session-id to resume later.")
            return EXIT_SIGNAL
        return result_clean

    def _display_exit_tip(self) -> None:
        """Display helpful exit tip when user interrupts input."""
        if self.console:
            self.console.print("\n[yellow]💡 Tip: Type 'exit' or 'quit' to save and exit gracefully[/yellow]\n")

    def _log_rich_input_error(self, error: Exception) -> None:
        """Log error when rich input fails."""
        logger = logging.getLogger("requirements_bot")
        logger.warning(
            "Rich input failed, falling back to basic input",
            extra={
                "error": str(error),
                "error_type": type(error).__name__,
                "component": "io",
                "operation": "rich_input",
            },
        )

    def print_success(self, message: str) -> None:
        """Print a success message with green styling."""
        if self.console:
            self.console.print(f"[green]✓[/green] {message}")
        else:
            print(f"✓ {message}")

    def print_error(self, message: str) -> None:
        """Print an error message with red styling."""
        if self.console:
            self.console.print(f"[red]✗[/red] {message}")
        else:
            print(f"✗ {message}")

    def print_thinking(self, message: str = "Processing...") -> None:
        """Print a thinking/processing message."""
        if self.console:
            self.console.print(f"[yellow]🤔[/yellow] {message}")
        else:
            print(f"🤔 {message}")

    def print_info(self, message: str) -> None:
        """Print an informational message with blue styling."""
        if self.console:
            self.console.print(f"[cyan]ℹ[/cyan] {message}")
        else:
            print(f"ℹ {message}")

    def print_interview_header(self, remaining_questions: int = 0) -> None:
        """Print rich interview start header."""
        if self.console:
            header_panel = Panel(
                "🤖 [bold blue]Conversational Interview Mode[/bold blue]\n\n"
                "I'll ask questions to understand your requirements.\n"
                "I may ask follow-up questions based on your answers.\n\n"
                "[dim]💡 Tip: Type 'exit', 'quit', or 'done' to save and exit anytime[/dim]",
                title="🚀 Starting Interview",
                border_style="bright_blue",
                padding=(1, 2),
            )
            self.console.print(header_panel)
        else:
            # Fallback to parent implementation
            super().print_interview_header(remaining_questions)

    def print_requirements_generation(self, answer_count: int) -> None:
        """Print rich requirements generation message."""
        if self.console:
            gen_panel = Panel(
                f"🔄 [bold green]Generating Requirements[/bold green]\n\n"
                f"Processing [bold yellow]{answer_count}[/bold yellow] answers...\n"
                "Creating comprehensive requirements document",
                title="📝 Requirements Generation",
                border_style="green",
                padding=(1, 2),
            )
            self.console.print(gen_panel)
        else:
            super().print_requirements_generation(answer_count)

    def print_question_with_progress(
        self, question_text: str, question_number: int, total_questions: int, category: str = ""
    ) -> None:
        """Print rich question with progress bar and category."""
        if self.console:
            # Create progress bar

            progress_text = f"Question {question_number} of {total_questions}"
            if category:
                progress_text += f" • {category.upper()}"

            # Create question panel with progress
            question_panel = Panel(
                f"[bold white]{question_text}[/bold white]",
                title=f"🤔 {progress_text}",
                border_style="blue",
                padding=(1, 2),
            )
            self.console.print(question_panel)
        else:
            super().print_question_with_progress(question_text, question_number, total_questions, category)

    def print_assessment_feedback(self, reasoning: str, missing_areas: list[str] = None) -> None:
        """Print rich assessment feedback."""
        if self.console:
            feedback_content = f"[bold green]✓[/bold green] {reasoning}"
            if missing_areas:
                feedback_content += f"\n\n[yellow]⚠ Still need info on:[/yellow] {', '.join(missing_areas)}"

            feedback_panel = Panel(
                feedback_content, title="📊 Completeness Assessment", border_style="green", padding=(1, 2)
            )
            self.console.print(feedback_panel)
        else:
            super().print_assessment_feedback(reasoning, missing_areas)


class ConsoleIO(RichConsoleIO):
    """Legacy alias for backward compatibility."""

    def __init__(self):
        super().__init__(session_id=None)


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

    def print_success(self, message: str) -> None:
        self.printed_messages.append(f"SUCCESS: {message}")

    def print_error(self, message: str) -> None:
        self.printed_messages.append(f"ERROR: {message}")

    def print_info(self, message: str) -> None:
        self.printed_messages.append(f"INFO: {message}")

    def print_thinking(self, message: str = "Processing...") -> None:
        self.printed_messages.append(f"THINKING: {message}")
