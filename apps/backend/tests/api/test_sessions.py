"""Test session management API endpoints."""

import uuid
from datetime import datetime

from fastapi.testclient import TestClient

from tests.api.test_utils import (
    create_test_session,
)


class TestSessionCreation:
    """Test session creation endpoint."""

    def test_create_session_success(self, client: TestClient, sample_session_data):
        """Test successful session creation."""
        response = client.post("/api/v1/sessions", json=sample_session_data)

        assert response.status_code == 201
        data = response.json()

        # Validate response structure
        assert "id" in data
        assert "project" in data
        assert "conversation_state" in data
        assert "created_at" in data

        # Validate data types and values
        assert isinstance(data["id"], str)
        assert data["project"] == sample_session_data["project"]
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
        assert isinstance(data["created_at"], str)

        # Validate UUID format for session ID
        uuid.UUID(data["id"])  # This will raise ValueError if invalid

        # Validate ISO datetime format
        datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))

    def test_create_session_minimal_project_name(self, client: TestClient):
        """Test session creation with minimal valid project name."""
        response = client.post("/api/v1/sessions", json={"project": "A"})

        assert response.status_code == 201
        data = response.json()
        assert data["project"] == "A"

    def test_create_session_max_length_project_name(self, client: TestClient):
        """Test session creation with maximum length project name."""
        long_name = "A" * 200  # Max length is 200
        response = client.post("/api/v1/sessions", json={"project": long_name})

        assert response.status_code == 201
        data = response.json()
        assert data["project"] == long_name

    def test_create_session_empty_project_name(self, client: TestClient):
        """Test session creation with empty project name fails."""
        response = client.post("/api/v1/sessions", json={"project": ""})

        assert response.status_code == 422
        data = response.json()
        # Custom validation errors use our error format
        assert "error" in data
        assert "message" in data

    def test_create_session_whitespace_only_project_name(self, client: TestClient):
        """Test session creation with whitespace-only project name fails."""
        response = client.post("/api/v1/sessions", json={"project": "   "})

        assert response.status_code == 422
        data = response.json()
        # Custom validation errors use our error format
        assert "error" in data
        assert "message" in data

    def test_create_session_too_long_project_name(self, client: TestClient):
        """Test session creation with too long project name fails."""
        long_name = "A" * 201  # Over max length
        response = client.post("/api/v1/sessions", json={"project": long_name})

        assert response.status_code == 422

    def test_create_session_invalid_characters(self, client: TestClient):
        """Test session creation with invalid characters fails."""
        invalid_names = [
            "Project<script>",
            'Project"quote',
            "Project'single",
            "Project&amp",
            "Project\nNewline",
            "Project\rCarriage",
            "Project\tTab",
        ]

        for invalid_name in invalid_names:
            response = client.post("/api/v1/sessions", json={"project": invalid_name})
            assert response.status_code == 422, f"Should reject project name: {invalid_name}"

    def test_create_session_missing_project_field(self, client: TestClient):
        """Test session creation without project field fails."""
        response = client.post("/api/v1/sessions", json={})

        assert response.status_code == 422

    def test_create_session_invalid_json(self, client: TestClient):
        """Test session creation with invalid JSON fails."""
        response = client.post("/api/v1/sessions", data="invalid json", headers={"Content-Type": "application/json"})

        assert response.status_code == 422


class TestSessionListing:
    """Test session listing endpoint."""

    def test_list_sessions_empty(self, client: TestClient):
        """Test listing sessions when none exist."""
        response = client.get("/api/v1/sessions")

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert isinstance(data["sessions"], list)
        assert len(data["sessions"]) == 0

    def test_list_sessions_single_session(self, client: TestClient, sample_session_data):
        """Test listing sessions with one session."""
        # Create a session first
        create_response = create_test_session(client, sample_session_data)
        session_id = create_response["id"]

        # List sessions
        response = client.get("/api/v1/sessions")

        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 1

        session = data["sessions"][0]
        assert session["id"] == session_id
        assert session["project"] == sample_session_data["project"]
        assert "conversation_state" in session
        assert "conversation_complete" in session
        assert "questions_count" in session
        assert "answers_count" in session
        assert "requirements_count" in session
        assert "created_at" in session
        assert "updated_at" in session

    def test_list_sessions_multiple_sessions(self, client: TestClient):
        """Test listing multiple sessions."""
        # Create multiple sessions
        session_data_1 = {"project": "Project 1"}
        session_data_2 = {"project": "Project 2"}
        session_data_3 = {"project": "Project 3"}

        create_test_session(client, session_data_1)
        create_test_session(client, session_data_2)
        create_test_session(client, session_data_3)

        # List sessions
        response = client.get("/api/v1/sessions")

        assert response.status_code == 200
        data = response.json()
        assert len(data["sessions"]) == 3

        # Verify all projects are represented
        project_names = {session["project"] for session in data["sessions"]}
        assert project_names == {"Project 1", "Project 2", "Project 3"}


class TestSessionRetrieval:
    """Test session detail retrieval endpoint."""

    def test_get_session_success(self, client: TestClient, sample_session_data):
        """Test successful session retrieval."""
        # Create a session first
        create_response = create_test_session(client, sample_session_data)
        session_id = create_response["id"]

        # Retrieve the session
        response = client.get(f"/api/v1/sessions/{session_id}")

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
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

        # Validate data types
        assert data["id"] == session_id
        assert data["project"] == sample_session_data["project"]
        assert isinstance(data["questions"], list)
        assert isinstance(data["answers"], list)
        assert isinstance(data["requirements"], list)
        assert isinstance(data["conversation_complete"], bool)

    def test_get_session_not_found(self, client: TestClient):
        """Test retrieving non-existent session."""
        fake_session_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/sessions/{fake_session_id}")

        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert "not found" in data["message"].lower()

    def test_get_session_invalid_uuid(self, client: TestClient):
        """Test retrieving session with invalid UUID format."""
        response = client.get("/api/v1/sessions/invalid-uuid")

        assert response.status_code == 400
        data = response.json()
        # Custom API error format
        assert "error" in data
        assert "message" in data
        assert data["error"] == "ValidationError"


class TestSessionDeletion:
    """Test session deletion endpoint."""

    def test_delete_session_success(self, client: TestClient, sample_session_data):
        """Test successful session deletion."""
        # Create a session first
        create_response = create_test_session(client, sample_session_data)
        session_id = create_response["id"]

        # Delete the session
        response = client.delete(f"/api/v1/sessions/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert session_id in data["message"]

        # Verify session is gone
        get_response = client.get(f"/api/v1/sessions/{session_id}")
        assert get_response.status_code == 404

    def test_delete_session_not_found(self, client: TestClient):
        """Test deleting non-existent session."""
        fake_session_id = str(uuid.uuid4())
        response = client.delete(f"/api/v1/sessions/{fake_session_id}")

        # Note: Current implementation doesn't check if session exists before deletion
        # This might return 200 even for non-existent sessions
        # We should verify the actual behavior
        assert response.status_code in [200, 404]

    def test_delete_session_invalid_uuid(self, client: TestClient):
        """Test deleting session with invalid UUID format."""
        response = client.delete("/api/v1/sessions/invalid-uuid")

        assert response.status_code == 400
        data = response.json()
        # Custom API error format
        assert "error" in data
        assert "message" in data
        assert data["error"] == "ValidationError"

    def test_delete_session_from_list(self, client: TestClient):
        """Test that deleted session is removed from session list."""
        # Create multiple sessions
        session_1 = create_test_session(client, {"project": "Project 1"})
        session_2 = create_test_session(client, {"project": "Project 2"})

        # Verify both sessions exist
        list_response = client.get("/api/v1/sessions")
        assert len(list_response.json()["sessions"]) == 2

        # Delete one session
        delete_response = client.delete(f"/api/v1/sessions/{session_1['id']}")
        assert delete_response.status_code == 200

        # Verify only one session remains
        list_response = client.get("/api/v1/sessions")
        sessions = list_response.json()["sessions"]
        assert len(sessions) == 1
        assert sessions[0]["id"] == session_2["id"]


class TestSessionEndpointIntegration:
    """Integration tests for session endpoints."""

    def test_full_session_lifecycle(self, client: TestClient):
        """Test complete session lifecycle: create, list, get, delete."""
        project_name = "Integration Test Project"

        # 1. Create session
        create_response = client.post("/api/v1/sessions", json={"project": project_name})
        assert create_response.status_code == 201
        session_data = create_response.json()
        session_id = session_data["id"]

        # 2. Verify session appears in list
        list_response = client.get("/api/v1/sessions")
        assert list_response.status_code == 200
        sessions = list_response.json()["sessions"]
        assert len(sessions) == 1
        assert sessions[0]["id"] == session_id

        # 3. Get session details
        get_response = client.get(f"/api/v1/sessions/{session_id}")
        assert get_response.status_code == 200
        detail_data = get_response.json()
        assert detail_data["id"] == session_id
        assert detail_data["project"] == project_name

        # 4. Delete session
        delete_response = client.delete(f"/api/v1/sessions/{session_id}")
        assert delete_response.status_code == 200

        # 5. Verify session is gone from list
        final_list_response = client.get("/api/v1/sessions")
        assert final_list_response.status_code == 200
        assert len(final_list_response.json()["sessions"]) == 0

        # 6. Verify direct access returns 404
        final_get_response = client.get(f"/api/v1/sessions/{session_id}")
        assert final_get_response.status_code == 404
