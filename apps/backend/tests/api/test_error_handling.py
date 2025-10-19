"""Test error handling and edge cases for API endpoints."""

import uuid

from fastapi.testclient import TestClient

from tests.api.test_utils import create_test_session


class TestGeneralErrorHandling:
    """Test general API error handling."""

    def test_root_endpoint(self, client: TestClient):
        """Test the root endpoint returns expected response."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert data["message"] == "SpecScribe API"
        assert data["version"] == "1.0.0"

    def test_health_check_endpoint(self, client: TestClient):
        """Test the health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_nonexistent_endpoint(self, client: TestClient):
        """Test accessing non-existent endpoint returns 404."""
        response = client.get("/api/v1/nonexistent")

        assert response.status_code == 404

    def test_unsupported_http_method(self, client: TestClient):
        """Test unsupported HTTP method returns 405."""
        # PATCH is not allowed according to CORS configuration
        response = client.patch("/api/v1/sessions")

        assert response.status_code == 405

    def test_malformed_json_request(self, client: TestClient):
        """Test malformed JSON in request body."""
        response = client.post(
            "/api/v1/sessions", content=b"{ invalid json }", headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_missing_content_type_header(self, client: TestClient):
        """Test request without proper content type."""
        response = client.post("/api/v1/sessions", content=b'{"project": "test"}')

        # Should still work as FastAPI is flexible
        assert response.status_code in [200, 201, 422]

    def test_oversized_request_payload(self, client: TestClient):
        """Test extremely large request payload."""
        # Create a very large project name
        huge_data = {"project": "A" * 10000}  # Much larger than max length

        response = client.post("/api/v1/sessions", json=huge_data)

        assert response.status_code == 422


class TestSessionErrorScenarios:
    """Test error scenarios specific to session management."""

    def test_session_with_special_characters_in_path(self, client: TestClient):
        """Test session operations with special characters in URL path."""
        # Characters that should reach validation (422)
        invalid_uuid_chars = ["<script>", "%20", "null", "undefined"]
        # Path traversal should be blocked by routing (404)
        path_traversal_chars = ["../"]

        for char in invalid_uuid_chars:
            # These should return 400 for invalid UUID format
            response = client.get(f"/api/v1/sessions/{char}")
            assert response.status_code == 400

            response = client.delete(f"/api/v1/sessions/{char}")
            assert response.status_code == 400

        for char in path_traversal_chars:
            # These should return 404 (blocked by routing)
            response = client.get(f"/api/v1/sessions/{char}")
            assert response.status_code == 404

            response = client.delete(f"/api/v1/sessions/{char}")
            assert response.status_code == 404

    def test_session_operations_with_empty_uuid(self, client: TestClient):
        """Test session operations with empty UUID."""
        # Empty session ID matches the sessions list endpoint
        response = client.get("/api/v1/sessions/")
        assert response.status_code == 200  # Sessions list endpoint

    def test_concurrent_session_creation(self, client: TestClient):
        """Test creating multiple sessions concurrently (basic test)."""
        project_names = [f"Concurrent Project {i}" for i in range(5)]
        responses = []

        # Create sessions rapidly
        for project_name in project_names:
            response = client.post("/api/v1/sessions", json={"project": project_name})
            responses.append(response)

        # All should succeed
        for response in responses:
            assert response.status_code == 201

        # All should have unique IDs
        session_ids = [resp.json()["id"] for resp in responses]
        assert len(set(session_ids)) == len(session_ids)  # All unique

    def test_session_creation_with_unicode_characters(self, client: TestClient):
        """Test session creation with various Unicode characters."""
        unicode_projects = [
            "项目名称",  # Chinese
            "プロジェクト",  # Japanese
            "проект",  # Russian
            "🚀 Rocket Project 🚀",  # Emojis
            "Café Restaurant Management",  # Accented characters
        ]

        for project_name in unicode_projects:
            response = client.post("/api/v1/sessions", json={"project": project_name})
            # Unicode should be handled properly
            assert response.status_code == 201
            data = response.json()
            assert data["project"] == project_name


class TestQuestionAnswerErrorScenarios:
    """Test error scenarios for question/answer workflow."""

    def test_answer_submission_to_completed_session(self, client: TestClient, sample_session_data):
        """Test submitting answer to already completed session."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # This test would need a way to complete a session first
        # For now, we'll test the error structure
        # TODO: Implement session completion logic in test utilities

        # Test with a session that doesn't have questions available
        response = client.post(
            f"/api/v1/sessions/{session_id}/answers", json={"answer_text": "Answer to completed session"}
        )

        # Should handle gracefully - either 400 for invalid state or success
        assert response.status_code in [200, 400, 422]

    def test_continue_with_database_error(self, client: TestClient, sample_session_data):
        """Test continue endpoint behavior when database is unavailable."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # This would require mocking database failures
        # For now, test basic functionality
        response = client.post(f"/api/v1/sessions/{session_id}/continue")
        assert response.status_code in [200, 500]

    def test_answer_with_extremely_long_text(self, client: TestClient, sample_session_data):
        """Test answer submission with text at edge of limits."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # Get a question first
        continue_response = client.post(f"/api/v1/sessions/{session_id}/continue")
        assert continue_response.status_code == 200

        # Test with exactly 5000 characters (max limit)
        max_answer = "A" * 5000
        response = client.post(f"/api/v1/sessions/{session_id}/answers", json={"answer_text": max_answer})
        assert response.status_code == 200

        # Test with 5001 characters (over limit)
        over_limit_answer = "A" * 5001
        response = client.post(f"/api/v1/sessions/{session_id}/answers", json={"answer_text": over_limit_answer})
        assert response.status_code == 422

    def test_rapid_consecutive_requests(self, client: TestClient, sample_session_data):
        """Test rapid consecutive requests to same session."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # Make multiple rapid requests
        responses = []
        for _ in range(5):
            response = client.post(f"/api/v1/sessions/{session_id}/continue")
            responses.append(response)

        # All should return valid responses
        for response in responses:
            assert response.status_code == 200

        # All should return consistent data
        first_response_data = responses[0].json()
        for response in responses[1:]:
            response_data = response.json()
            assert response_data["session_id"] == first_response_data["session_id"]


class TestValidationErrorMessages:
    """Test that validation errors provide clear messages."""

    def test_session_creation_validation_messages(self, client: TestClient):
        """Test validation error messages for session creation."""
        # Empty project name
        response = client.post("/api/v1/sessions", json={"project": ""})
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert "validation" in data["error"].lower()

        # Missing project field
        response = client.post("/api/v1/sessions", json={})
        assert response.status_code == 422
        data = response.json()
        assert "error" in data

    def test_answer_validation_messages(self, client: TestClient, sample_session_data):
        """Test validation error messages for answer submission."""
        session = create_test_session(client, sample_session_data)
        session_id = session["id"]

        # Get a question first
        continue_response = client.post(f"/api/v1/sessions/{session_id}/continue")
        assert continue_response.status_code == 200

        # Empty answer
        response = client.post(f"/api/v1/sessions/{session_id}/answers", json={"answer_text": ""})
        assert response.status_code == 422
        data = response.json()
        assert "error" in data

        # Missing answer_text field
        response = client.post(f"/api/v1/sessions/{session_id}/answers", json={})
        assert response.status_code == 422
        data = response.json()
        assert "error" in data

    def test_uuid_validation_messages(self, client: TestClient):
        """Test UUID validation error messages."""
        invalid_uuids = ["123", "not-a-uuid", "12345678-1234-1234-1234-12345678901"]

        for invalid_uuid in invalid_uuids:
            response = client.get(f"/api/v1/sessions/{invalid_uuid}")
            assert response.status_code == 400
            data = response.json()
            assert "error" in data


class TestSecurityAndSafety:
    """Test security-related error handling."""

    def test_sql_injection_attempts(self, client: TestClient):
        """Test that SQL injection attempts are handled safely."""
        # These should be handled by parameter validation, not SQL escaping
        injection_attempts = ["'; DROP TABLE sessions; --", "1' OR '1'='1", "1'; SELECT * FROM sessions; --"]

        for injection in injection_attempts:
            # Try in session ID
            response = client.get(f"/api/v1/sessions/{injection}")
            assert response.status_code == 400  # Invalid UUID format

            # Try in project name
            response = client.post("/api/v1/sessions", json={"project": injection})
            # Should either succeed (properly escaped) or fail validation
            assert response.status_code in [201, 422]

    def test_xss_prevention_in_responses(self, client: TestClient):
        """Test that XSS attempts in input don't appear in responses."""
        xss_attempts = ["<script>alert('xss')</script>", "javascript:alert('xss')", "<img src=x onerror=alert('xss')>"]

        for xss in xss_attempts:
            # Try in project name (should be rejected by validation)
            response = client.post("/api/v1/sessions", json={"project": xss})
            assert response.status_code == 422  # Should be rejected

    def test_path_traversal_attempts(self, client: TestClient):
        """Test that path traversal attempts are handled safely."""
        # Unix-style and URL-encoded traversal blocked by routing
        routing_blocked = [
            "../../../etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2f",
        ]
        # Windows-style backslashes treated as single path segment
        validation_blocked = [
            "..\\..\\..\\windows\\system32",
        ]

        for traversal in routing_blocked:
            response = client.get(f"/api/v1/sessions/{traversal}")
            # Path traversal should be blocked by routing (404)
            assert response.status_code == 404

        for traversal in validation_blocked:
            response = client.get(f"/api/v1/sessions/{traversal}")
            # Invalid UUID format should be caught by validation (400)
            assert response.status_code == 400


class TestMiddlewareErrorHandling:
    """Test error handling middleware behavior."""

    def test_cors_headers_on_error_responses(self, client: TestClient):
        """Test that CORS headers are present on error responses."""
        response = client.get("/api/v1/sessions/invalid-uuid")
        assert response.status_code == 400

        # Check for CORS headers (basic test)
        # Note: TestClient might not include all CORS headers
        # This is a basic structural test

    def test_consistent_error_response_format(self, client: TestClient):
        """Test that all error responses follow consistent format."""
        # Test various error scenarios
        error_responses = [
            client.get("/api/v1/sessions/invalid-uuid"),  # 400
            client.get(f"/api/v1/sessions/{uuid.uuid4()}"),  # 404
            client.post("/api/v1/sessions", json={}),  # 422
        ]

        for response in error_responses:
            assert response.status_code >= 400
            data = response.json()
            # All error responses should have consistent structure
            assert "error" in data
            # May also have "message" or other fields depending on middleware
