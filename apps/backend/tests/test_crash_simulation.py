import threading
import time
from unittest.mock import Mock

import pytest

from requirements_bot.core.conversation_state import ConversationState
from requirements_bot.core.models import Answer, Question, Session
from requirements_bot.core.recovery import StateRecoveryManager
from requirements_bot.core.state_manager import ConversationStateManager


class CrashSimulator:
    """Utility to simulate crashes at specific conversation states."""

    def __init__(self, state_manager: ConversationStateManager):
        self.state_manager = state_manager
        self.crash_at_state = None
        self.crashed = False

    def set_crash_point(self, state: ConversationState):
        """Set which state should trigger a simulated crash."""
        self.crash_at_state = state
        self.crashed = False

    def maybe_crash(self, session: Session):
        """Check if we should simulate a crash at current state."""
        if self.crash_at_state and session.conversation_state == self.crash_at_state and not self.crashed:
            self.crashed = True
            raise Exception(f"Simulated crash at state: {self.crash_at_state.value}")


class TestCrashSimulation:
    """Test crash simulation and recovery mechanisms."""

    @pytest.fixture
    def mock_storage(self):
        storage = Mock()
        storage.save_session.return_value = "test_session_id"
        storage.load_session.return_value = None
        return storage

    @pytest.fixture
    def state_manager(self, mock_storage):
        return ConversationStateManager(mock_storage)

    @pytest.fixture
    def recovery_manager(self, mock_storage):
        session_manager = Mock()
        session_manager.state_manager = ConversationStateManager(mock_storage)
        question_queue_manager = Mock()
        provider = Mock()
        return StateRecoveryManager(session_manager, question_queue_manager, provider)

    @pytest.fixture
    def sample_session(self):
        questions = [
            Question(id="q1", text="What is the purpose?", category="scope"),
            Question(id="q2", text="Who are the users?", category="users"),
        ]
        return Session(
            user_id="test-user-id",
            project="Test Project",
            questions=questions,
            answers=[],
            requirements=[],
            conversation_state=ConversationState.INITIALIZING,
        )

    def test_crash_during_question_generation(self, state_manager, sample_session, mock_storage):
        """Test crash during question generation phase."""
        crash_sim = CrashSimulator(state_manager)
        crash_sim.set_crash_point(ConversationState.GENERATING_QUESTIONS)

        # Transition to generating questions - should crash
        state_manager.transition_to(sample_session, ConversationState.GENERATING_QUESTIONS)

        with pytest.raises(Exception, match="Simulated crash"):
            crash_sim.maybe_crash(sample_session)

        # Verify state was set before crash
        assert sample_session.conversation_state == ConversationState.GENERATING_QUESTIONS

    def test_crash_during_answer_processing(self, state_manager, sample_session):
        """Test crash during answer processing."""
        crash_sim = CrashSimulator(state_manager)
        crash_sim.set_crash_point(ConversationState.PROCESSING_ANSWER)

        # Set up session as if we're processing an answer
        sample_session.conversation_state = ConversationState.WAITING_FOR_INPUT
        sample_session.answers = [Answer(question_id="q1", text="Test answer")]

        state_manager.transition_to(sample_session, ConversationState.PROCESSING_ANSWER)

        with pytest.raises(Exception, match="Simulated crash"):
            crash_sim.maybe_crash(sample_session)

    def test_recovery_from_generating_questions(self, recovery_manager, sample_session):
        """Test recovery from interrupted question generation."""
        sample_session.conversation_state = ConversationState.GENERATING_QUESTIONS

        # Mock successful question generation
        recovery_manager.provider.generate_questions.return_value = [
            Question(id="q3", text="Generated question", category="scope")
        ]
        recovery_manager.question_queue_manager.initialize_from_seeds.return_value = [
            Question(id="seed1", text="Seed question", category="scope")
        ]

        result = recovery_manager.attempt_recovery(sample_session)
        assert result is True
        assert sample_session.conversation_state == ConversationState.WAITING_FOR_INPUT

    def test_recovery_from_processing_answer(self, recovery_manager, sample_session):
        """Test recovery from interrupted answer processing."""
        sample_session.conversation_state = ConversationState.PROCESSING_ANSWER
        sample_session.answers = [
            Answer(question_id="q1", text="Test answer"),
            Answer(question_id="q2", text="Last answer to reprocess"),
        ]

        result = recovery_manager.attempt_recovery(sample_session)
        assert result is True
        assert len(sample_session.answers) == 1  # Last answer removed
        assert sample_session.conversation_state == ConversationState.WAITING_FOR_INPUT

    def test_recovery_from_generating_followups(self, recovery_manager, sample_session):
        """Test recovery from interrupted follow-up generation."""
        sample_session.conversation_state = ConversationState.GENERATING_FOLLOWUPS

        # Mock the state manager to not fail on transitions
        recovery_manager.session_manager.state_manager.transition_to = Mock()

        result = recovery_manager.attempt_recovery(sample_session)
        assert result is True

    def test_recovery_from_completeness_assessment(self, recovery_manager, sample_session):
        """Test recovery from interrupted completeness assessment."""
        sample_session.conversation_state = ConversationState.ASSESSING_COMPLETENESS

        # Mock the state manager to not fail on transitions
        recovery_manager.session_manager.state_manager.transition_to = Mock()

        result = recovery_manager.attempt_recovery(sample_session)
        assert result is True
        assert not sample_session.conversation_complete

    def test_recovery_from_requirements_generation(self, recovery_manager, sample_session):
        """Test recovery from interrupted requirements generation."""
        sample_session.conversation_state = ConversationState.GENERATING_REQUIREMENTS

        # Mock the state manager to not fail on transitions
        recovery_manager.session_manager.state_manager.transition_to = Mock()

        result = recovery_manager.attempt_recovery(sample_session)
        assert result is True

    def test_recovery_failure_fallback(self, recovery_manager, sample_session):
        """Test fallback when specific recovery fails."""
        sample_session.conversation_state = ConversationState.GENERATING_QUESTIONS
        sample_session.questions = []  # No existing questions to fall back to

        # Make question generation fail
        recovery_manager.provider.generate_questions.side_effect = Exception("Generation failed")
        recovery_manager.question_queue_manager.initialize_from_seeds.side_effect = Exception("Seed generation failed")

        result = recovery_manager.attempt_recovery(sample_session)
        assert result is False  # Recovery failed

    def test_concurrent_access_during_crash(self, state_manager, mock_storage):
        """Test that concurrent access during crashes is handled safely."""
        session1 = Session(user_id="test-user-id-1", project="Project 1", questions=[], answers=[])
        session2 = Session(user_id="test-user-id-2", project="Project 2", questions=[], answers=[])

        def transition_with_delay(session, state):
            time.sleep(0.1)  # Simulate processing time
            state_manager.transition_to(session, state)

        # Start concurrent transitions
        thread1 = threading.Thread(
            target=transition_with_delay,
            args=(session1, ConversationState.GENERATING_QUESTIONS),
        )
        thread2 = threading.Thread(
            target=transition_with_delay,
            args=(session2, ConversationState.GENERATING_QUESTIONS),
        )

        thread1.start()
        thread2.start()
        thread1.join()
        thread2.join()

        # Both sessions should have transitioned successfully
        assert session1.conversation_state == ConversationState.GENERATING_QUESTIONS
        assert session2.conversation_state == ConversationState.GENERATING_QUESTIONS

        # Storage should have been called for both sessions
        assert mock_storage.save_session.call_count == 2

    def test_database_failure_during_state_change(self, mock_storage, sample_session):
        """Test handling of database failures during state transitions."""
        mock_storage.save_session.side_effect = Exception("Database connection lost")

        state_manager = ConversationStateManager(mock_storage)

        # Should not raise exception, just handle gracefully
        state_manager.transition_to(sample_session, ConversationState.GENERATING_QUESTIONS)

        # State should still be updated in memory
        assert sample_session.conversation_state == ConversationState.GENERATING_QUESTIONS

    def test_network_failure_during_llm_call(self, recovery_manager, sample_session):
        """Test recovery when LLM calls fail due to network issues."""
        sample_session.conversation_state = ConversationState.GENERATING_QUESTIONS
        sample_session.state_context.llm_operation_id = "failed_llm_call"
        sample_session.questions = []  # No existing questions to fall back to

        # Simulate network failure in provider call
        recovery_manager.provider.generate_questions.side_effect = Exception("Network timeout")
        recovery_manager.question_queue_manager.initialize_from_seeds.side_effect = Exception("Network timeout")

        # Recovery should handle this gracefully
        result = recovery_manager.attempt_recovery(sample_session)
        assert result is False  # This specific recovery fails, but doesn't crash

    def test_complete_crash_recovery_flow(self, recovery_manager, sample_session, mock_storage):
        """Test complete flow from crash to successful recovery."""
        # Set up session as if it crashed during answer processing
        sample_session.conversation_state = ConversationState.PROCESSING_ANSWER
        sample_session.answers = [Answer(question_id="q1", text="Partial answer")]

        # Mock successful recovery components
        recovery_manager.question_queue_manager.initialize_from_seeds.return_value = []

        # Step 1: Detect crash state
        assert recovery_manager.session_manager.state_manager.can_recover_from_interruption(sample_session)

        # Step 2: Determine recovery strategy
        recovery_action = recovery_manager.session_manager.state_manager.determine_recovery_action(sample_session)
        assert recovery_action == "reprocess_last_answer"

        # Step 3: Execute recovery
        result = recovery_manager.attempt_recovery(sample_session)
        assert result is True

        # Step 4: Verify session state after recovery
        assert sample_session.conversation_state == ConversationState.WAITING_FOR_INPUT
        assert len(sample_session.answers) == 0  # Answer was removed for reprocessing
