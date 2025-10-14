"""Test Answer CRUD API endpoints."""

import uuid

from fastapi.testclient import TestClient

from tests.api.test_utils import create_test_session


class TestAnswersList:
    """Test list answers endpoint."""

    def test_list_answers_success(self, client: TestClient, sample_session_data):
        """Test listing answers for session with answers."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # Answer a question
        client.post(f"/api/v1/sessions/{session_id}/continue")
        client.post(f"/api/v1/sessions/{session_id}/answers", json={"answer_text": "Test answer"})

        response = client.get(f"/api/v1/sessions/{session_id}/answers")

        assert response.status_code == 200
        data = response.json()

        assert "session_id" in data
        assert "answers" in data
        assert data["session_id"] == session_id
        assert isinstance(data["answers"], list)
        assert len(data["answers"]) >= 1

    def test_list_answers_empty(self, client: TestClient, sample_session_data):
        """Test listing answers for new session with no answers."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        response = client.get(f"/api/v1/sessions/{session_id}/answers")

        assert response.status_code == 200
        data = response.json()
        assert len(data["answers"]) == 0

    def test_list_answers_multiple(self, client: TestClient, sample_session_data):
        """Test listing session with multiple answers."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # Answer multiple questions
        for i in range(3):
            client.post(f"/api/v1/sessions/{session_id}/continue")
            client.post(f"/api/v1/sessions/{session_id}/answers", json={"answer_text": f"Answer {i + 1}"})

        response = client.get(f"/api/v1/sessions/{session_id}/answers")

        assert response.status_code == 200
        data = response.json()
        assert len(data["answers"]) >= 3

    def test_list_answers_not_found(self, client: TestClient):
        """Test listing answers for non-existent session."""
        fake_session_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/sessions/{fake_session_id}/answers")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data

    def test_list_answers_invalid_uuid(self, client: TestClient):
        """Test listing answers with invalid session ID format."""
        response = client.get("/api/v1/sessions/invalid-uuid/answers")

        assert response.status_code == 400
        data = response.json()
        assert "error" in data


class TestAnswerGet:
    """Test get single answer endpoint."""

    def test_get_answer_success(self, client: TestClient, sample_session_data):
        """Test getting answer by question_id."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # Answer first question
        client.post(f"/api/v1/sessions/{session_id}/continue")
        answer_response = client.post(f"/api/v1/sessions/{session_id}/answers", json={"answer_text": "Test answer"})
        question_id = answer_response.json()["question"]["id"]

        # Get answer
        response = client.get(f"/api/v1/sessions/{session_id}/answers/{question_id}")

        assert response.status_code == 200
        data = response.json()

        assert "session_id" in data
        assert "answer" in data
        assert "question" in data
        assert data["session_id"] == session_id
        assert data["answer"]["question_id"] == question_id
        assert data["answer"]["text"] == "Test answer"

    def test_get_answer_with_question_details(self, client: TestClient, sample_session_data):
        """Test that answer includes question details."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        client.post(f"/api/v1/sessions/{session_id}/continue")
        answer_response = client.post(f"/api/v1/sessions/{session_id}/answers", json={"answer_text": "Test answer"})
        question_id = answer_response.json()["question"]["id"]

        response = client.get(f"/api/v1/sessions/{session_id}/answers/{question_id}")

        assert response.status_code == 200
        data = response.json()
        question = data["question"]

        assert "id" in question
        assert "text" in question
        assert "category" in question
        assert "required" in question
        assert question["id"] == question_id

    def test_get_answer_not_found(self, client: TestClient, sample_session_data):
        """Test getting answer for unanswered question."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # Get an unanswered question ID
        list_response = client.get(f"/api/v1/sessions/{session_id}/questions")
        question_id = list_response.json()["questions"][0]["id"]

        response = client.get(f"/api/v1/sessions/{session_id}/answers/{question_id}")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data

    def test_get_answer_invalid_session(self, client: TestClient):
        """Test getting answer for non-existent session."""
        fake_session_id = str(uuid.uuid4())
        fake_question_id = "q_fake"
        response = client.get(f"/api/v1/sessions/{fake_session_id}/answers/{fake_question_id}")

        assert response.status_code == 404


class TestAnswerUpdate:
    """Test update answer endpoint."""

    def test_update_answer_success(self, client: TestClient, sample_session_data):
        """Test updating answer text successfully."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # Answer question
        client.post(f"/api/v1/sessions/{session_id}/continue")
        answer_response = client.post(f"/api/v1/sessions/{session_id}/answers", json={"answer_text": "Original answer"})
        question_id = answer_response.json()["question"]["id"]

        # Update answer
        update_data = {"text": "Updated answer text"}
        response = client.put(f"/api/v1/sessions/{session_id}/answers/{question_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["answer"]["text"] == "Updated answer text"
        assert data["answer"]["question_id"] == question_id

    def test_update_answer_minimal_text(self, client: TestClient, sample_session_data):
        """Test updating answer with single character."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        client.post(f"/api/v1/sessions/{session_id}/continue")
        answer_response = client.post(f"/api/v1/sessions/{session_id}/answers", json={"answer_text": "Original"})
        question_id = answer_response.json()["question"]["id"]

        update_data = {"text": "A"}
        response = client.put(f"/api/v1/sessions/{session_id}/answers/{question_id}", json=update_data)

        assert response.status_code == 200
        assert response.json()["answer"]["text"] == "A"

    def test_update_answer_max_length(self, client: TestClient, sample_session_data):
        """Test updating answer with 5000 characters."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        client.post(f"/api/v1/sessions/{session_id}/continue")
        answer_response = client.post(f"/api/v1/sessions/{session_id}/answers", json={"answer_text": "Original"})
        question_id = answer_response.json()["question"]["id"]

        long_text = "A" * 5000
        update_data = {"text": long_text}
        response = client.put(f"/api/v1/sessions/{session_id}/answers/{question_id}", json=update_data)

        assert response.status_code == 200
        assert response.json()["answer"]["text"] == long_text

    def test_update_answer_empty_text(self, client: TestClient, sample_session_data):
        """Test updating answer with empty text fails."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        client.post(f"/api/v1/sessions/{session_id}/continue")
        answer_response = client.post(f"/api/v1/sessions/{session_id}/answers", json={"answer_text": "Original"})
        question_id = answer_response.json()["question"]["id"]

        update_data = {"text": ""}
        response = client.put(f"/api/v1/sessions/{session_id}/answers/{question_id}", json=update_data)

        assert response.status_code == 422

    def test_update_answer_whitespace(self, client: TestClient, sample_session_data):
        """Test updating answer with whitespace-only text fails."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        client.post(f"/api/v1/sessions/{session_id}/continue")
        answer_response = client.post(f"/api/v1/sessions/{session_id}/answers", json={"answer_text": "Original"})
        question_id = answer_response.json()["question"]["id"]

        update_data = {"text": "   "}
        response = client.put(f"/api/v1/sessions/{session_id}/answers/{question_id}", json=update_data)

        assert response.status_code == 422

    def test_update_answer_too_long(self, client: TestClient, sample_session_data):
        """Test updating answer with > 5000 characters fails."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        client.post(f"/api/v1/sessions/{session_id}/continue")
        answer_response = client.post(f"/api/v1/sessions/{session_id}/answers", json={"answer_text": "Original"})
        question_id = answer_response.json()["question"]["id"]

        long_text = "A" * 5001
        update_data = {"text": long_text}
        response = client.put(f"/api/v1/sessions/{session_id}/answers/{question_id}", json=update_data)

        assert response.status_code == 422

    def test_update_answer_not_found(self, client: TestClient, sample_session_data):
        """Test updating non-existent answer fails."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        fake_question_id = "q_nonexistent"
        update_data = {"text": "New text"}

        response = client.put(f"/api/v1/sessions/{session_id}/answers/{fake_question_id}", json=update_data)

        assert response.status_code == 404

    def test_update_answer_whitespace_trimmed(self, client: TestClient, sample_session_data):
        """Test that updated answer text is trimmed."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        client.post(f"/api/v1/sessions/{session_id}/continue")
        answer_response = client.post(f"/api/v1/sessions/{session_id}/answers", json={"answer_text": "Original"})
        question_id = answer_response.json()["question"]["id"]

        update_data = {"text": "   Trimmed text   "}
        response = client.put(f"/api/v1/sessions/{session_id}/answers/{question_id}", json=update_data)

        assert response.status_code == 200
        assert response.json()["answer"]["text"] == "Trimmed text"


class TestAnswerDelete:
    """Test delete answer endpoint."""

    def test_delete_answer_success(self, client: TestClient, sample_session_data):
        """Test deleting answer marks question as unanswered."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # Answer question
        client.post(f"/api/v1/sessions/{session_id}/continue")
        answer_response = client.post(f"/api/v1/sessions/{session_id}/answers", json={"answer_text": "Test answer"})
        question_id = answer_response.json()["question"]["id"]

        # Delete answer
        response = client.delete(f"/api/v1/sessions/{session_id}/answers/{question_id}")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert question_id in data["message"]

    def test_delete_answer_not_found(self, client: TestClient, sample_session_data):
        """Test deleting non-existent answer fails."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        fake_question_id = "q_nonexistent"
        response = client.delete(f"/api/v1/sessions/{session_id}/answers/{fake_question_id}")

        assert response.status_code == 404

    def test_delete_answer_verify_removed(self, client: TestClient, sample_session_data):
        """Test deleted answer is removed from list."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # Answer question
        client.post(f"/api/v1/sessions/{session_id}/continue")
        answer_response = client.post(f"/api/v1/sessions/{session_id}/answers", json={"answer_text": "Test answer"})
        question_id = answer_response.json()["question"]["id"]

        # Get initial count
        list_before = client.get(f"/api/v1/sessions/{session_id}/answers")
        count_before = len(list_before.json()["answers"])

        # Delete answer
        client.delete(f"/api/v1/sessions/{session_id}/answers/{question_id}")

        # Verify count decreased
        list_after = client.get(f"/api/v1/sessions/{session_id}/answers")
        count_after = len(list_after.json()["answers"])
        assert count_after == count_before - 1

        # Verify answer not in list
        answers = list_after.json()["answers"]
        assert not any(a["question_id"] == question_id for a in answers)


class TestAnswerCRUDIntegration:
    """Integration tests for answer CRUD operations."""

    def test_answer_workflow(self, client: TestClient, sample_session_data):
        """Test complete answer workflow: create via submit, update, delete."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # 1. Create answer via submit
        client.post(f"/api/v1/sessions/{session_id}/continue")
        answer_response = client.post(f"/api/v1/sessions/{session_id}/answers", json={"answer_text": "Original answer"})
        question_id = answer_response.json()["question"]["id"]

        # 2. Verify answer exists
        get_response = client.get(f"/api/v1/sessions/{session_id}/answers/{question_id}")
        assert get_response.status_code == 200
        assert get_response.json()["answer"]["text"] == "Original answer"

        # 3. Update answer
        update_response = client.put(
            f"/api/v1/sessions/{session_id}/answers/{question_id}", json={"text": "Updated answer"}
        )
        assert update_response.status_code == 200
        assert update_response.json()["answer"]["text"] == "Updated answer"

        # 4. Verify update persisted
        get_response2 = client.get(f"/api/v1/sessions/{session_id}/answers/{question_id}")
        assert get_response2.json()["answer"]["text"] == "Updated answer"

        # 5. Delete answer
        delete_response = client.delete(f"/api/v1/sessions/{session_id}/answers/{question_id}")
        assert delete_response.status_code == 200

        # 6. Verify answer is gone
        get_response3 = client.get(f"/api/v1/sessions/{session_id}/answers/{question_id}")
        assert get_response3.status_code == 404

    def test_multiple_answers_management(self, client: TestClient, sample_session_data):
        """Test managing multiple answers."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        question_ids = []

        # Answer 3 questions
        for i in range(3):
            client.post(f"/api/v1/sessions/{session_id}/continue")
            answer_response = client.post(
                f"/api/v1/sessions/{session_id}/answers", json={"answer_text": f"Answer {i + 1}"}
            )
            question_ids.append(answer_response.json()["question"]["id"])

        # Verify all answers exist
        list_response = client.get(f"/api/v1/sessions/{session_id}/answers")
        answers = list_response.json()["answers"]
        assert len(answers) >= 3

        # Update middle answer
        client.put(f"/api/v1/sessions/{session_id}/answers/{question_ids[1]}", json={"text": "Updated middle answer"})

        # Delete first answer
        client.delete(f"/api/v1/sessions/{session_id}/answers/{question_ids[0]}")

        # Verify correct state
        final_list = client.get(f"/api/v1/sessions/{session_id}/answers")
        final_answers = final_list.json()["answers"]

        # First should be gone, second updated, third unchanged
        assert not any(a["question_id"] == question_ids[0] for a in final_answers)

        middle_answer = next((a for a in final_answers if a["question_id"] == question_ids[1]), None)
        assert middle_answer is not None
        assert middle_answer["text"] == "Updated middle answer"
