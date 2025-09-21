"""Test data validation for API request/response schemas."""

import uuid
from datetime import datetime

from fastapi.testclient import TestClient

from tests.api.test_utils import create_test_session


class TestSessionCreateRequestValidation:
    """Test validation of SessionCreateRequest schema."""

    def test_valid_project_names(self, client: TestClient):
        """Test various valid project names."""
        valid_names = [
            "Simple Project",
            "Project123",
            "My-Project_Name",
            "Project (Version 2)",
            "A",  # Minimum length
            "A" * 200,  # Maximum length
            "Project with spaces and numbers 123",
            "Multi-word project name with hyphens and underscores_test",
        ]

        for project_name in valid_names:
            response = client.post("/api/v1/sessions", json={"project": project_name})
            assert response.status_code == 201, f"Failed for project name: {project_name}"
            data = response.json()
            assert data["project"] == project_name.strip()

    def test_invalid_project_names(self, client: TestClient):
        """Test various invalid project names."""
        invalid_names = [
            "",  # Empty
            "   ",  # Whitespace only
            "\t",  # Tab only
            "\n",  # Newline only
            "A" * 201,  # Too long
            "Project<script>",  # HTML tags
            'Project"quote',  # Double quote
            "Project'single",  # Single quote
            "Project&amp;",  # HTML entity
            "Project\nNewline",  # Newline character
            "Project\rCarriage",  # Carriage return
            "Project\tTab",  # Tab character
        ]

        for project_name in invalid_names:
            response = client.post("/api/v1/sessions", json={"project": project_name})
            assert response.status_code == 422, f"Should reject project name: {project_name}"

    def test_project_name_trimming(self, client: TestClient):
        """Test that project names are properly trimmed."""
        test_cases = [
            ("  Project Name  ", "Project Name"),
            ("\tProject\t", "Project"),
            ("   Multi Word Project   ", "Multi Word Project"),
        ]

        for input_name, expected_name in test_cases:
            response = client.post("/api/v1/sessions", json={"project": input_name})
            assert response.status_code == 201
            data = response.json()
            assert data["project"] == expected_name

    def test_missing_required_fields(self, client: TestClient):
        """Test requests missing required fields."""
        invalid_requests = [
            {},  # No project field
            {"not_project": "value"},  # Wrong field name
            {"project": None},  # None value
        ]

        for invalid_request in invalid_requests:
            response = client.post("/api/v1/sessions", json=invalid_request)
            assert response.status_code == 422

    def test_extra_fields_ignored(self, client: TestClient):
        """Test that extra fields in request are ignored."""
        request_data = {"project": "Test Project", "extra_field": "should be ignored", "another_field": 123}

        response = client.post("/api/v1/sessions", json=request_data)
        assert response.status_code == 201
        data = response.json()
        assert data["project"] == "Test Project"
        # Extra fields should not appear in response
        assert "extra_field" not in data
        assert "another_field" not in data


class TestSessionCreateResponseValidation:
    """Test SessionCreateResponse schema validation."""

    def test_response_structure(self, client: TestClient, sample_session_data):
        """Test that response has correct structure and types."""
        response = client.post("/api/v1/sessions", json=sample_session_data)
        assert response.status_code == 201
        data = response.json()

        # Required fields
        assert "id" in data
        assert "project" in data
        assert "conversation_state" in data
        assert "created_at" in data

        # Type validation
        assert isinstance(data["id"], str)
        assert isinstance(data["project"], str)
        assert isinstance(data["conversation_state"], str)
        assert isinstance(data["created_at"], str)

        # UUID validation
        uuid.UUID(data["id"])  # Should not raise

        # DateTime validation
        datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))

        # Enum validation
        valid_states = [
            "initializing",
            "generating_questions",
            "waiting_for_input",
            "processing_answer",
            "generating_followups",
            "assessing_completeness",
            "generating_requirements",
            "completed",
            "failed",
        ]
        assert data["conversation_state"] in valid_states


class TestQuestionAnswerRequestValidation:
    """Test validation of QuestionAnswerRequest schema."""

    def test_valid_answer_texts(self, client: TestClient, sample_session_data):
        """Test various valid answer texts."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # Get first question
        continue_response = client.post(f"/api/v1/sessions/{session_id}/continue")
        assert continue_response.status_code == 200

        valid_answers = [
            "Simple answer",
            "A",  # Minimum length
            "A" * 5000,  # Maximum length
            "Answer with numbers 123 and symbols !@#$%",
            "Multi-line\nanswer\nwith\nbreaks",
            "Answer with unicode: ñáéíóú 中文 🎉",
            "Answer with quotes: 'single' and \"double\"",
            "Long detailed answer explaining the requirements in great detail with multiple sentences and "
            "comprehensive coverage of all aspects.",
        ]

        for i, answer_text in enumerate(valid_answers):
            # Get question for each answer (in case session progresses)
            if i > 0:
                continue_response = client.post(f"/api/v1/sessions/{session_id}/continue")
                if continue_response.json().get("conversation_complete"):
                    break

            response = client.post(f"/api/v1/sessions/{session_id}/answers", json={"answer_text": answer_text})
            assert response.status_code == 200, f"Failed for answer: {answer_text[:50]}..."
            data = response.json()
            assert data["answer"]["text"] == answer_text.strip()

    def test_invalid_answer_texts(self, client: TestClient, sample_session_data):
        """Test various invalid answer texts."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # Get first question
        continue_response = client.post(f"/api/v1/sessions/{session_id}/continue")
        assert continue_response.status_code == 200

        invalid_answers = [
            "",  # Empty
            "   ",  # Whitespace only
            "\t\n\r",  # Only whitespace characters
            "A" * 5001,  # Too long
        ]

        for answer_text in invalid_answers:
            response = client.post(f"/api/v1/sessions/{session_id}/answers", json={"answer_text": answer_text})
            assert response.status_code == 422, f"Should reject answer: {repr(answer_text)}"

    def test_answer_text_trimming(self, client: TestClient, sample_session_data):
        """Test that answer texts are properly trimmed."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # Get first question
        continue_response = client.post(f"/api/v1/sessions/{session_id}/continue")
        assert continue_response.status_code == 200

        test_cases = [
            ("  Answer with spaces  ", "Answer with spaces"),
            ("\tTabbed answer\t", "Tabbed answer"),
            ("   Multi line\n  answer   ", "Multi line\n  answer"),
        ]

        for i, (input_answer, expected_answer) in enumerate(test_cases):
            # Get new question if needed
            if i > 0:
                continue_response = client.post(f"/api/v1/sessions/{session_id}/continue")
                if continue_response.json().get("conversation_complete"):
                    break

            response = client.post(f"/api/v1/sessions/{session_id}/answers", json={"answer_text": input_answer})
            assert response.status_code == 200
            data = response.json()
            assert data["answer"]["text"] == expected_answer


class TestResponseSchemaValidation:
    """Test validation of response schemas."""

    def test_session_list_response_structure(self, client: TestClient, sample_session_data):
        """Test SessionListResponse structure."""
        # Create a few sessions
        for i in range(3):
            create_test_session(client, {"project": f"Test Project {i + 1}"})

        response = client.get("/api/v1/sessions")
        assert response.status_code == 200
        data = response.json()

        # Validate structure
        assert "sessions" in data
        assert isinstance(data["sessions"], list)
        assert len(data["sessions"]) == 3

        # Validate each session summary
        for session in data["sessions"]:
            required_fields = [
                "id",
                "project",
                "conversation_state",
                "conversation_complete",
                "questions_count",
                "answers_count",
                "requirements_count",
                "created_at",
                "updated_at",
            ]
            for field in required_fields:
                assert field in session

            # Type validation
            assert isinstance(session["id"], str)
            assert isinstance(session["project"], str)
            assert isinstance(session["conversation_state"], str)
            assert isinstance(session["conversation_complete"], bool)
            assert isinstance(session["questions_count"], int)
            assert isinstance(session["answers_count"], int)
            assert isinstance(session["requirements_count"], int)
            assert isinstance(session["created_at"], str)
            assert isinstance(session["updated_at"], str)

    def test_session_detail_response_structure(self, client: TestClient, sample_session_data):
        """Test SessionDetailResponse structure."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        response = client.get(f"/api/v1/sessions/{session_id}")
        assert response.status_code == 200
        data = response.json()

        # Required fields
        required_fields = [
            "id",
            "project",
            "questions",
            "answers",
            "requirements",
            "conversation_complete",
            "conversation_state",
            "created_at",
            "updated_at",
        ]
        for field in required_fields:
            assert field in data

        # Type validation
        assert isinstance(data["id"], str)
        assert isinstance(data["project"], str)
        assert isinstance(data["questions"], list)
        assert isinstance(data["answers"], list)
        assert isinstance(data["requirements"], list)
        assert isinstance(data["conversation_complete"], bool)
        assert isinstance(data["conversation_state"], str)
        assert isinstance(data["created_at"], str)
        assert isinstance(data["updated_at"], str)

    def test_session_continue_response_structure(self, client: TestClient, sample_session_data):
        """Test SessionContinueResponse structure."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        response = client.post(f"/api/v1/sessions/{session_id}/continue")
        assert response.status_code == 200
        data = response.json()

        # Required fields
        required_fields = ["session_id", "next_question", "conversation_complete", "conversation_state"]
        for field in required_fields:
            assert field in data

        # Type validation
        assert isinstance(data["session_id"], str)
        assert isinstance(data["conversation_complete"], bool)
        assert isinstance(data["conversation_state"], str)
        # next_question can be None or dict
        if data["next_question"] is not None:
            assert isinstance(data["next_question"], dict)
            question = data["next_question"]
            assert "id" in question
            assert "text" in question
            assert "category" in question
            assert "required" in question

    def test_answer_submission_response_structure(self, client: TestClient, sample_session_data):
        """Test AnswerSubmissionResponse structure."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # Get first question
        continue_response = client.post(f"/api/v1/sessions/{session_id}/continue")
        assert continue_response.status_code == 200

        # Submit answer
        response = client.post(
            f"/api/v1/sessions/{session_id}/answers", json={"answer_text": "Test answer for validation"}
        )
        assert response.status_code == 200
        data = response.json()

        # Required fields
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

        # Type validation
        assert isinstance(data["session_id"], str)
        assert isinstance(data["question"], dict)
        assert isinstance(data["answer"], dict)
        assert isinstance(data["conversation_complete"], bool)
        assert isinstance(data["conversation_state"], str)
        assert isinstance(data["requirements_generated"], bool)

        # Question structure
        question = data["question"]
        assert "id" in question
        assert "text" in question
        assert "category" in question

        # Answer structure
        answer = data["answer"]
        assert "question_id" in answer
        assert "text" in answer
        assert "is_vague" in answer
        assert "needs_followup" in answer

    def test_session_status_response_structure(self, client: TestClient, sample_session_data):
        """Test SessionStatusResponse structure."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        response = client.get(f"/api/v1/sessions/{session_id}/status")
        assert response.status_code == 200
        data = response.json()

        # Required fields
        required_fields = ["session_id", "conversation_state", "conversation_complete", "current_question", "progress"]
        for field in required_fields:
            assert field in data

        # Type validation
        assert isinstance(data["session_id"], str)
        assert isinstance(data["conversation_state"], str)
        assert isinstance(data["conversation_complete"], bool)
        # current_question can be None or dict
        if data["current_question"] is not None:
            assert isinstance(data["current_question"], dict)

        # Progress structure validation
        progress = data["progress"]
        assert isinstance(progress, dict)
        progress_fields = ["total_questions", "answered_questions", "remaining_questions", "completion_percentage"]
        for field in progress_fields:
            assert field in progress

        assert isinstance(progress["total_questions"], int)
        assert isinstance(progress["answered_questions"], int)
        assert isinstance(progress["remaining_questions"], int)
        assert isinstance(progress["completion_percentage"], float)

        # Value validation
        assert progress["total_questions"] >= 0
        assert progress["answered_questions"] >= 0
        assert progress["remaining_questions"] >= 0
        assert 0.0 <= progress["completion_percentage"] <= 100.0
        assert progress["total_questions"] == progress["answered_questions"] + progress["remaining_questions"]


class TestErrorResponseValidation:
    """Test error response schema validation."""

    def test_validation_error_structure(self, client: TestClient):
        """Test structure of validation error responses."""
        # Trigger validation error
        response = client.post("/api/v1/sessions", json={"project": ""})
        assert response.status_code == 422
        data = response.json()

        # Should have error information
        assert "error" in data
        # May have additional fields like "detail" depending on middleware

    def test_not_found_error_structure(self, client: TestClient):
        """Test structure of 404 error responses."""
        fake_session_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/sessions/{fake_session_id}")
        assert response.status_code == 404
        data = response.json()

        # Should have error information
        assert "error" in data
        assert "message" in data

    def test_consistency_across_error_types(self, client: TestClient):
        """Test that different error types have consistent response structure."""
        error_responses = [
            client.post("/api/v1/sessions", json={}),  # 422 Validation error
            client.get(f"/api/v1/sessions/{uuid.uuid4()}"),  # 404 Not found
            client.get("/api/v1/sessions/invalid-uuid"),  # 422 Invalid UUID
        ]

        for response in error_responses:
            assert response.status_code >= 400
            data = response.json()
            # All should have at least an error field
            assert "error" in data
