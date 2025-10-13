"""Test Question CRUD API endpoints."""

import uuid

from fastapi.testclient import TestClient

from tests.api.test_utils import create_test_session


class TestQuestionsList:
    """Test list questions endpoint."""

    def test_list_questions_success(self, client: TestClient, sample_session_data):
        """Test listing questions for valid session."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        response = client.get(f"/api/v1/sessions/{session_id}/questions")

        assert response.status_code == 200
        data = response.json()

        assert "session_id" in data
        assert "questions" in data
        assert data["session_id"] == session_id
        assert isinstance(data["questions"], list)
        assert len(data["questions"]) > 0

    def test_list_questions_empty_session(self, client: TestClient, sample_session_data):
        """Test listing questions for new session with initial questions."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        response = client.get(f"/api/v1/sessions/{session_id}/questions")

        assert response.status_code == 200
        data = response.json()
        # Even new sessions should have initial questions
        assert len(data["questions"]) >= 1

    def test_list_questions_not_found(self, client: TestClient):
        """Test listing questions for non-existent session."""
        fake_session_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/sessions/{fake_session_id}/questions")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data

    def test_list_questions_invalid_uuid(self, client: TestClient):
        """Test listing questions with invalid session ID format."""
        response = client.get("/api/v1/sessions/invalid-uuid/questions")

        assert response.status_code == 400
        data = response.json()
        assert "error" in data


class TestQuestionGet:
    """Test get single question endpoint."""

    def test_get_question_success(self, client: TestClient, sample_session_data):
        """Test getting single question details."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # Get list of questions first
        list_response = client.get(f"/api/v1/sessions/{session_id}/questions")
        questions = list_response.json()["questions"]
        assert len(questions) > 0
        question_id = questions[0]["id"]

        # Get single question
        response = client.get(f"/api/v1/sessions/{session_id}/questions/{question_id}")

        assert response.status_code == 200
        data = response.json()

        assert "session_id" in data
        assert "question" in data
        assert "answer" in data
        assert data["session_id"] == session_id
        assert data["question"]["id"] == question_id

    def test_get_question_without_answer(self, client: TestClient, sample_session_data):
        """Test getting unanswered question."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        list_response = client.get(f"/api/v1/sessions/{session_id}/questions")
        question_id = list_response.json()["questions"][0]["id"]

        response = client.get(f"/api/v1/sessions/{session_id}/questions/{question_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] is None

    def test_get_question_with_answer(self, client: TestClient, sample_session_data):
        """Test getting question that has been answered."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # Continue and answer first question
        client.post(f"/api/v1/sessions/{session_id}/continue")
        answer_response = client.post(f"/api/v1/sessions/{session_id}/answers", json={"answer_text": "Test answer"})
        question_id = answer_response.json()["question"]["id"]

        # Get question details
        response = client.get(f"/api/v1/sessions/{session_id}/questions/{question_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] is not None
        assert data["answer"]["text"] == "Test answer"

    def test_get_question_not_found(self, client: TestClient, sample_session_data):
        """Test getting non-existent question."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        fake_question_id = "q_nonexistent"
        response = client.get(f"/api/v1/sessions/{session_id}/questions/{fake_question_id}")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data


class TestQuestionCreate:
    """Test create question endpoint."""

    def test_create_question_success(self, client: TestClient, sample_session_data):
        """Test creating new question with valid data."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        question_data = {"text": "What is your budget?", "category": "constraints", "required": True}

        response = client.post(f"/api/v1/sessions/{session_id}/questions", json=question_data)

        assert response.status_code == 201
        data = response.json()

        assert "question" in data
        assert data["question"]["text"] == question_data["text"]
        assert data["question"]["category"] == question_data["category"]
        assert data["question"]["required"] == question_data["required"]
        assert data["answer"] is None

    def test_create_question_all_categories(self, client: TestClient, sample_session_data):
        """Test creating questions with each category type."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        categories = ["scope", "users", "constraints", "nonfunctional", "interfaces", "data", "risks", "success"]

        for category in categories:
            question_data = {"text": f"Test question for {category}", "category": category, "required": True}

            response = client.post(f"/api/v1/sessions/{session_id}/questions", json=question_data)

            assert response.status_code == 201, f"Failed for category: {category}"
            assert response.json()["question"]["category"] == category

    def test_create_question_optional_required_field(self, client: TestClient, sample_session_data):
        """Test creating question with required=false."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        question_data = {"text": "Optional question", "category": "scope", "required": False}

        response = client.post(f"/api/v1/sessions/{session_id}/questions", json=question_data)

        assert response.status_code == 201
        assert response.json()["question"]["required"] is False

    def test_create_question_empty_text(self, client: TestClient, sample_session_data):
        """Test creating question with empty text fails."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        question_data = {"text": "", "category": "scope", "required": True}

        response = client.post(f"/api/v1/sessions/{session_id}/questions", json=question_data)

        assert response.status_code == 422

    def test_create_question_whitespace_text(self, client: TestClient, sample_session_data):
        """Test creating question with whitespace-only text fails."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        question_data = {"text": "   ", "category": "scope", "required": True}

        response = client.post(f"/api/v1/sessions/{session_id}/questions", json=question_data)

        assert response.status_code == 422

    def test_create_question_too_long_text(self, client: TestClient, sample_session_data):
        """Test creating question with text > 1000 chars fails."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        question_data = {"text": "A" * 1001, "category": "scope", "required": True}

        response = client.post(f"/api/v1/sessions/{session_id}/questions", json=question_data)

        assert response.status_code == 422

    def test_create_question_invalid_category(self, client: TestClient, sample_session_data):
        """Test creating question with invalid category fails."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        question_data = {"text": "Test question", "category": "invalid_category", "required": True}

        response = client.post(f"/api/v1/sessions/{session_id}/questions", json=question_data)

        assert response.status_code == 422


class TestQuestionUpdate:
    """Test update question endpoint."""

    def test_update_question_text_only(self, client: TestClient, sample_session_data):
        """Test updating just question text."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        list_response = client.get(f"/api/v1/sessions/{session_id}/questions")
        question_id = list_response.json()["questions"][0]["id"]

        update_data = {"text": "Updated question text"}

        response = client.put(f"/api/v1/sessions/{session_id}/questions/{question_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["question"]["text"] == "Updated question text"

    def test_update_question_category_only(self, client: TestClient, sample_session_data):
        """Test updating just question category."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        list_response = client.get(f"/api/v1/sessions/{session_id}/questions")
        question = list_response.json()["questions"][0]
        question_id = question["id"]
        original_text = question["text"]

        update_data = {"category": "risks"}

        response = client.put(f"/api/v1/sessions/{session_id}/questions/{question_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["question"]["category"] == "risks"
        assert data["question"]["text"] == original_text

    def test_update_question_required_only(self, client: TestClient, sample_session_data):
        """Test updating just required flag."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        list_response = client.get(f"/api/v1/sessions/{session_id}/questions")
        question_id = list_response.json()["questions"][0]["id"]

        update_data = {"required": False}

        response = client.put(f"/api/v1/sessions/{session_id}/questions/{question_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["question"]["required"] is False

    def test_update_question_all_fields(self, client: TestClient, sample_session_data):
        """Test updating all fields at once."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        list_response = client.get(f"/api/v1/sessions/{session_id}/questions")
        question_id = list_response.json()["questions"][0]["id"]

        update_data = {"text": "Completely new text", "category": "data", "required": False}

        response = client.put(f"/api/v1/sessions/{session_id}/questions/{question_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["question"]["text"] == "Completely new text"
        assert data["question"]["category"] == "data"
        assert data["question"]["required"] is False

    def test_update_question_empty_text(self, client: TestClient, sample_session_data):
        """Test updating question with empty text fails."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        list_response = client.get(f"/api/v1/sessions/{session_id}/questions")
        question_id = list_response.json()["questions"][0]["id"]

        update_data = {"text": ""}

        response = client.put(f"/api/v1/sessions/{session_id}/questions/{question_id}", json=update_data)

        assert response.status_code == 422

    def test_update_question_not_found(self, client: TestClient, sample_session_data):
        """Test updating non-existent question fails."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        fake_question_id = "q_nonexistent"
        update_data = {"text": "New text"}

        response = client.put(f"/api/v1/sessions/{session_id}/questions/{fake_question_id}", json=update_data)

        assert response.status_code == 404

    def test_update_question_invalid_category(self, client: TestClient, sample_session_data):
        """Test updating question with invalid category fails."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        list_response = client.get(f"/api/v1/sessions/{session_id}/questions")
        question_id = list_response.json()["questions"][0]["id"]

        update_data = {"category": "invalid_category"}

        response = client.put(f"/api/v1/sessions/{session_id}/questions/{question_id}", json=update_data)

        assert response.status_code == 422


class TestQuestionDelete:
    """Test delete question endpoint."""

    def test_delete_question_success(self, client: TestClient, sample_session_data):
        """Test deleting unanswered question."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # Create a custom question to delete
        create_response = client.post(
            f"/api/v1/sessions/{session_id}/questions",
            json={"text": "Question to delete", "category": "scope", "required": True},
        )
        question_id = create_response.json()["question"]["id"]

        # Delete the question
        response = client.delete(f"/api/v1/sessions/{session_id}/questions/{question_id}")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert question_id in data["message"]

    def test_delete_question_with_answer(self, client: TestClient, sample_session_data):
        """Test that we can delete an answered question by first deleting its answer."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # Answer first question
        client.post(f"/api/v1/sessions/{session_id}/continue")
        answer_response = client.post(f"/api/v1/sessions/{session_id}/answers", json={"answer_text": "Test answer"})
        question_id = answer_response.json()["question"]["id"]

        # First delete the answer
        delete_answer_response = client.delete(f"/api/v1/sessions/{session_id}/answers/{question_id}")
        assert delete_answer_response.status_code == 200

        # Now delete the question
        response = client.delete(f"/api/v1/sessions/{session_id}/questions/{question_id}")

        assert response.status_code == 200

        # Verify both are gone
        question_list = client.get(f"/api/v1/sessions/{session_id}/questions")
        questions = question_list.json()["questions"]
        assert not any(q["id"] == question_id for q in questions)

    def test_delete_question_not_found(self, client: TestClient, sample_session_data):
        """Test deleting non-existent question fails."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        fake_question_id = "q_nonexistent"
        response = client.delete(f"/api/v1/sessions/{session_id}/questions/{fake_question_id}")

        assert response.status_code == 404

    def test_delete_question_verify_removed(self, client: TestClient, sample_session_data):
        """Test deleted question is removed from list."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # Create a custom question
        create_response = client.post(
            f"/api/v1/sessions/{session_id}/questions",
            json={"text": "Question to verify deletion", "category": "scope", "required": True},
        )
        question_id = create_response.json()["question"]["id"]

        # Get initial count
        list_before = client.get(f"/api/v1/sessions/{session_id}/questions")
        count_before = len(list_before.json()["questions"])

        # Delete question
        client.delete(f"/api/v1/sessions/{session_id}/questions/{question_id}")

        # Verify count decreased
        list_after = client.get(f"/api/v1/sessions/{session_id}/questions")
        count_after = len(list_after.json()["questions"])
        assert count_after == count_before - 1

        # Verify question not in list
        questions = list_after.json()["questions"]
        assert not any(q["id"] == question_id for q in questions)
