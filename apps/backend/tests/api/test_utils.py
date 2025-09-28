"""Test utilities for API testing."""

from typing import Any

from fastapi.testclient import TestClient


def create_test_session(client: TestClient, session_data: dict[str, Any] = None) -> dict[str, Any]:
    """Create a test session and return the response data."""
    if session_data is None:
        session_data = {"project": "Test Project"}

    response = client.post("/api/v1/sessions", json=session_data)
    assert response.status_code == 201, f"Failed to create session: {response.text}"
    return response.json()


def get_session_questions(client: TestClient, session_id: str) -> dict[str, Any]:
    """Get the current question for a session."""
    response = client.post(f"/api/v1/sessions/{session_id}/continue")
    assert response.status_code == 200, f"Failed to get questions: {response.text}"
    return response.json()


def submit_answer(client: TestClient, session_id: str, answer_text: str) -> dict[str, Any]:
    """Submit an answer to a session."""
    response = client.post(f"/api/v1/sessions/{session_id}/answers", json={"answer_text": answer_text})
    assert response.status_code == 200, f"Failed to submit answer: {response.text}"
    return response.json()


def get_session_status(client: TestClient, session_id: str) -> dict[str, Any]:
    """Get session status."""
    response = client.get(f"/api/v1/sessions/{session_id}/status")
    assert response.status_code == 200, f"Failed to get status: {response.text}"
    return response.json()


def assert_valid_session_response(session_data: dict[str, Any]):
    """Assert that a session response has the expected structure."""
    assert "id" in session_data
    assert "project" in session_data
    assert "created_at" in session_data
    assert isinstance(session_data["id"], str)
    assert isinstance(session_data["project"], str)


def assert_valid_question_response(question_data: dict[str, Any]):
    """Assert that a question response has the expected structure."""
    assert "question" in question_data
    question = question_data["question"]
    assert "id" in question
    assert "text" in question
    assert "category" in question
    assert isinstance(question["id"], str)
    assert isinstance(question["text"], str)
    assert isinstance(question["category"], str)


def assert_valid_status_response(status_data: dict[str, Any]):
    """Assert that a status response has the expected structure."""
    assert "session_id" in status_data
    assert "progress" in status_data
    assert "conversation_complete" in status_data
    assert isinstance(status_data["session_id"], str)
    assert isinstance(status_data["progress"], dict)
    assert isinstance(status_data["conversation_complete"], bool)
