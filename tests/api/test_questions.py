"""Test question/answer workflow API endpoints."""

import uuid

from fastapi.testclient import TestClient

from tests.api.test_utils import (
    create_test_session,
)


class TestSessionContinue:
    """Test session continue endpoint."""

    def test_continue_new_session(self, client: TestClient, sample_session_data):
        """Test continuing a newly created session to get first question."""
        # Create a session
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # Continue the session to get first question
        response = client.post(f"/api/v1/sessions/{session_id}/continue")

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert "session_id" in data
        assert "next_question" in data
        assert "conversation_complete" in data
        assert "conversation_state" in data

        # Validate data
        assert data["session_id"] == session_id
        assert data["conversation_complete"] is False
        assert data["next_question"] is not None

        # Validate question structure
        question = data["next_question"]
        assert "id" in question
        assert "text" in question
        assert "category" in question
        assert "required" in question
        assert isinstance(question["text"], str)
        assert isinstance(question["category"], str)
        assert isinstance(question["required"], bool)

    def test_continue_completed_session(self, client: TestClient, sample_session_data):
        """Test continuing a completed session returns no next question."""
        # This test will need to create a session and complete it first
        # For now, we'll create a basic test structure
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # TODO: Complete the session by answering all questions
        # For now, just test the structure

        response = client.post(f"/api/v1/sessions/{session_id}/continue")
        assert response.status_code == 200
        data = response.json()

        assert "session_id" in data
        assert "next_question" in data
        assert "conversation_complete" in data
        assert "conversation_state" in data

    def test_continue_nonexistent_session(self, client: TestClient):
        """Test continuing non-existent session fails."""
        fake_session_id = str(uuid.uuid4())
        response = client.post(f"/api/v1/sessions/{fake_session_id}/continue")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "not found" in data["message"].lower()

    def test_continue_invalid_session_id(self, client: TestClient):
        """Test continuing with invalid session ID format."""
        response = client.post("/api/v1/sessions/invalid-uuid/continue")

        assert response.status_code == 400
        data = response.json()
        assert "error" in data


class TestAnswerSubmission:
    """Test answer submission endpoint."""

    def test_submit_answer_success(self, client: TestClient, sample_session_data):
        """Test successful answer submission."""
        # Create session and get first question
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # Get first question
        continue_response = client.post(f"/api/v1/sessions/{session_id}/continue")
        assert continue_response.status_code == 200
        question_data = continue_response.json()
        assert question_data["next_question"] is not None

        # Submit answer
        answer_text = "This is a comprehensive test answer for the first question."
        response = client.post(f"/api/v1/sessions/{session_id}/answers", json={"answer_text": answer_text})

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        required_fields = [
            "session_id",
            "question",
            "answer",
            "conversation_complete",
            "conversation_state",
            "requirements_generated",
        ]
        for field in required_fields:
            assert field in data

        # Validate data
        assert data["session_id"] == session_id
        assert isinstance(data["conversation_complete"], bool)
        assert isinstance(data["requirements_generated"], bool)

        # Validate question structure
        question = data["question"]
        assert "id" in question
        assert "text" in question
        assert "category" in question

        # Validate answer structure
        answer = data["answer"]
        assert "question_id" in answer
        assert "text" in answer
        assert "is_vague" in answer
        assert "needs_followup" in answer
        assert answer["text"] == answer_text

    def test_submit_answer_minimal_text(self, client: TestClient, sample_session_data):
        """Test submitting answer with minimal valid text."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # Get first question
        continue_response = client.post(f"/api/v1/sessions/{session_id}/continue")
        assert continue_response.status_code == 200

        # Submit minimal answer
        response = client.post(f"/api/v1/sessions/{session_id}/answers", json={"answer_text": "A"})

        assert response.status_code == 200

    def test_submit_answer_max_length_text(self, client: TestClient, sample_session_data):
        """Test submitting answer with maximum length text."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # Get first question
        continue_response = client.post(f"/api/v1/sessions/{session_id}/continue")
        assert continue_response.status_code == 200

        # Submit max length answer (5000 characters)
        long_answer = "A" * 5000
        response = client.post(f"/api/v1/sessions/{session_id}/answers", json={"answer_text": long_answer})

        assert response.status_code == 200
        data = response.json()
        assert data["answer"]["text"] == long_answer

    def test_submit_answer_empty_text(self, client: TestClient, sample_session_data):
        """Test submitting answer with empty text fails."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # Get first question
        continue_response = client.post(f"/api/v1/sessions/{session_id}/continue")
        assert continue_response.status_code == 200

        # Submit empty answer
        response = client.post(f"/api/v1/sessions/{session_id}/answers", json={"answer_text": ""})

        assert response.status_code == 422

    def test_submit_answer_whitespace_only_text(self, client: TestClient, sample_session_data):
        """Test submitting answer with whitespace-only text fails."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # Get first question
        continue_response = client.post(f"/api/v1/sessions/{session_id}/continue")
        assert continue_response.status_code == 200

        # Submit whitespace-only answer
        response = client.post(f"/api/v1/sessions/{session_id}/answers", json={"answer_text": "   "})

        assert response.status_code == 422

    def test_submit_answer_too_long_text(self, client: TestClient, sample_session_data):
        """Test submitting answer with too long text fails."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # Get first question
        continue_response = client.post(f"/api/v1/sessions/{session_id}/continue")
        assert continue_response.status_code == 200

        # Submit overly long answer (over 5000 characters)
        long_answer = "A" * 5001
        response = client.post(f"/api/v1/sessions/{session_id}/answers", json={"answer_text": long_answer})

        assert response.status_code == 422

    def test_submit_answer_nonexistent_session(self, client: TestClient):
        """Test submitting answer to non-existent session fails."""
        fake_session_id = str(uuid.uuid4())
        response = client.post(f"/api/v1/sessions/{fake_session_id}/answers", json={"answer_text": "Test answer"})

        assert response.status_code == 404

    def test_submit_answer_invalid_session_id(self, client: TestClient):
        """Test submitting answer with invalid session ID format."""
        response = client.post("/api/v1/sessions/invalid-uuid/answers", json={"answer_text": "Test answer"})

        assert response.status_code == 400

    def test_submit_answer_missing_field(self, client: TestClient, sample_session_data):
        """Test submitting answer without answer_text field fails."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # Get first question
        continue_response = client.post(f"/api/v1/sessions/{session_id}/continue")
        assert continue_response.status_code == 200

        # Submit answer without answer_text field
        response = client.post(f"/api/v1/sessions/{session_id}/answers", json={})

        assert response.status_code == 422


class TestCurrentQuestion:
    """Test current question endpoint."""

    def test_get_current_question_with_question(self, client: TestClient, sample_session_data):
        """Test getting current question when one exists."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # Get current question
        response = client.get(f"/api/v1/sessions/{session_id}/questions/current")

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert "current_question" in data
        assert "conversation_complete" in data
        assert "conversation_state" in data

        # Initially should have a question and not be complete
        assert data["current_question"] is not None
        assert data["conversation_complete"] is False

        # Validate question structure
        question = data["current_question"]
        assert "id" in question
        assert "text" in question
        assert "category" in question
        assert "required" in question

    def test_get_current_question_nonexistent_session(self, client: TestClient):
        """Test getting current question for non-existent session."""
        fake_session_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/sessions/{fake_session_id}/questions/current")

        assert response.status_code == 404

    def test_get_current_question_invalid_session_id(self, client: TestClient):
        """Test getting current question with invalid session ID format."""
        response = client.get("/api/v1/sessions/invalid-uuid/questions/current")

        assert response.status_code == 400


class TestSessionStatus:
    """Test session status endpoint."""

    def test_get_session_status_new_session(self, client: TestClient, sample_session_data):
        """Test getting status of a newly created session."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # Get session status
        response = client.get(f"/api/v1/sessions/{session_id}/status")

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        required_fields = ["session_id", "conversation_state", "conversation_complete", "current_question", "progress"]
        for field in required_fields:
            assert field in data

        # Validate data
        assert data["session_id"] == session_id
        assert isinstance(data["conversation_complete"], bool)
        assert data["current_question"] is not None

        # Validate progress structure
        progress = data["progress"]
        assert "total_questions" in progress
        assert "answered_questions" in progress
        assert "remaining_questions" in progress
        assert "completion_percentage" in progress

        # Validate progress values for new session
        assert isinstance(progress["total_questions"], int)
        assert isinstance(progress["answered_questions"], int)
        assert isinstance(progress["remaining_questions"], int)
        assert isinstance(progress["completion_percentage"], float)
        assert progress["answered_questions"] == 0
        assert progress["completion_percentage"] == 0.0

    def test_get_session_status_after_answer(self, client: TestClient, sample_session_data):
        """Test getting status after submitting an answer."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # Get first question and submit answer
        continue_response = client.post(f"/api/v1/sessions/{session_id}/continue")
        assert continue_response.status_code == 200

        answer_response = client.post(
            f"/api/v1/sessions/{session_id}/answers", json={"answer_text": "Test answer for status check"}
        )
        assert answer_response.status_code == 200

        # Get status after answering
        status_response = client.get(f"/api/v1/sessions/{session_id}/status")
        assert status_response.status_code == 200
        status_data = status_response.json()

        # Progress should reflect answered question
        progress = status_data["progress"]
        assert progress["answered_questions"] > 0
        assert progress["completion_percentage"] > 0.0

    def test_get_session_status_nonexistent_session(self, client: TestClient):
        """Test getting status for non-existent session."""
        fake_session_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/sessions/{fake_session_id}/status")

        assert response.status_code == 404

    def test_get_session_status_invalid_session_id(self, client: TestClient):
        """Test getting status with invalid session ID format."""
        response = client.get("/api/v1/sessions/invalid-uuid/status")

        assert response.status_code == 400


class TestQuestionAnswerWorkflow:
    """Integration tests for question/answer workflow."""

    def test_complete_question_answer_cycle(self, client: TestClient, sample_session_data):
        """Test complete cycle: continue -> answer -> status -> continue."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # 1. Continue to get first question
        continue_response = client.post(f"/api/v1/sessions/{session_id}/continue")
        assert continue_response.status_code == 200
        continue_data = continue_response.json()
        assert continue_data["next_question"] is not None
        first_question_id = continue_data["next_question"]["id"]

        # 2. Check current question endpoint matches
        current_response = client.get(f"/api/v1/sessions/{session_id}/questions/current")
        assert current_response.status_code == 200
        current_data = current_response.json()
        assert current_data["current_question"]["id"] == first_question_id

        # 3. Submit answer
        answer_response = client.post(
            f"/api/v1/sessions/{session_id}/answers",
            json={"answer_text": "Comprehensive test answer for first question"},
        )
        assert answer_response.status_code == 200
        answer_data = answer_response.json()
        assert answer_data["question"]["id"] == first_question_id

        # 4. Check status reflects progress
        status_response = client.get(f"/api/v1/sessions/{session_id}/status")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["progress"]["answered_questions"] >= 1
        assert status_data["progress"]["completion_percentage"] > 0

        # 5. Continue again to get next question or completion
        continue2_response = client.post(f"/api/v1/sessions/{session_id}/continue")
        assert continue2_response.status_code == 200
        continue2_data = continue2_response.json()

        # Should either have next question or be complete
        if continue2_data["conversation_complete"]:
            assert continue2_data["next_question"] is None
        else:
            assert continue2_data["next_question"] is not None
            # Next question should be different from first
            assert continue2_data["next_question"]["id"] != first_question_id

    def test_multiple_answers_workflow(self, client: TestClient, sample_session_data):
        """Test submitting multiple answers in sequence."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        answered_questions = []
        max_answers = 5  # Limit to prevent infinite loop

        for i in range(max_answers):
            # Get next question
            continue_response = client.post(f"/api/v1/sessions/{session_id}/continue")
            assert continue_response.status_code == 200
            continue_data = continue_response.json()

            if continue_data["conversation_complete"]:
                break

            assert continue_data["next_question"] is not None
            question_id = continue_data["next_question"]["id"]

            # Submit answer
            answer_response = client.post(
                f"/api/v1/sessions/{session_id}/answers",
                json={"answer_text": f"Test answer {i + 1} for question {question_id}"},
            )
            assert answer_response.status_code == 200

            answered_questions.append(question_id)

            # Verify progress increases
            status_response = client.get(f"/api/v1/sessions/{session_id}/status")
            assert status_response.status_code == 200
            status_data = status_response.json()
            assert status_data["progress"]["answered_questions"] == i + 1

        # Should have answered at least one question
        assert len(answered_questions) >= 1

    def test_workflow_with_whitespace_trimming(self, client: TestClient, sample_session_data):
        """Test that answer text is properly trimmed of whitespace."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # Get first question
        continue_response = client.post(f"/api/v1/sessions/{session_id}/continue")
        assert continue_response.status_code == 200

        # Submit answer with leading/trailing whitespace
        untrimmed_answer = "   Test answer with whitespace   "
        trimmed_answer = "Test answer with whitespace"

        answer_response = client.post(f"/api/v1/sessions/{session_id}/answers", json={"answer_text": untrimmed_answer})
        assert answer_response.status_code == 200
        answer_data = answer_response.json()

        # Verify answer is trimmed
        assert answer_data["answer"]["text"] == trimmed_answer
