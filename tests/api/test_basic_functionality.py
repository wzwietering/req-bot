"""Basic functionality tests to verify API works."""

from fastapi.testclient import TestClient


class TestBasicAPI:
    """Test basic API functionality without complex database interactions."""

    def test_root_endpoint(self, client: TestClient):
        """Test the root endpoint returns expected response."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert data["message"] == "Requirements Bot API"
        assert data["version"] == "0.1.0"

    def test_health_check_endpoint(self, client: TestClient):
        """Test the health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_simple_session_creation(self, client: TestClient):
        """Test basic session creation to verify database connectivity."""
        response = client.post("/api/v1/sessions", json={"project": "Simple Test"})

        # Log the response for debugging
        print(f"Response status: {response.status_code}")
        print(f"Response data: {response.json()}")

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert "project" in data
        assert data["project"] == "Simple Test"
