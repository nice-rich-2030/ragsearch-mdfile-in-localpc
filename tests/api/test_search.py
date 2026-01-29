"""Tests for search API endpoints."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


# Mock the app state before importing the app
@pytest.fixture
def mock_app_state():
    """Create a mock AppState."""
    mock_state = MagicMock()
    mock_state.vector_store.count.return_value = 100
    mock_state.searcher.search.return_value = [
        MagicMock(
            file_path="test.md",
            heading="## Test Heading",
            content="Test content",
            score=0.95,
            chunk_index=0
        )
    ]
    return mock_state


@pytest.fixture
def client(mock_app_state):
    """Create a test client with mocked dependencies."""
    with patch('src.api.dependencies.get_app_state', return_value=mock_app_state):
        from src.api.app import app
        app.state.app_state = mock_app_state
        yield TestClient(app)


class TestSearchEndpoint:
    """Tests for POST /api/v1/search endpoint."""

    def test_search_success(self, client, mock_app_state):
        """Test successful search request."""
        response = client.post(
            "/api/v1/search",
            json={"query": "Python", "top_k": 3}
        )

        assert response.status_code == 200
        data = response.json()

        assert "results" in data
        assert "total_chunks" in data
        assert "query" in data
        assert "execution_time_ms" in data
        assert data["query"] == "Python"
        assert data["total_chunks"] == 100
        assert len(data["results"]) == 1

    def test_search_default_top_k(self, client, mock_app_state):
        """Test search with default top_k value."""
        response = client.post(
            "/api/v1/search",
            json={"query": "test query"}
        )

        assert response.status_code == 200
        # Verify default top_k (5) was used
        mock_app_state.searcher.search.assert_called_with("test query", 5)

    def test_search_empty_query(self, client):
        """Test search with empty query (should fail validation)."""
        response = client.post(
            "/api/v1/search",
            json={"query": ""}
        )

        assert response.status_code == 422

    def test_search_missing_query(self, client):
        """Test search without query parameter (should fail validation)."""
        response = client.post(
            "/api/v1/search",
            json={}
        )

        assert response.status_code == 422

    def test_search_invalid_top_k(self, client):
        """Test search with invalid top_k value."""
        # top_k = 0 (below minimum)
        response = client.post(
            "/api/v1/search",
            json={"query": "test", "top_k": 0}
        )
        assert response.status_code == 422

        # top_k = 101 (above maximum)
        response = client.post(
            "/api/v1/search",
            json={"query": "test", "top_k": 101}
        )
        assert response.status_code == 422

    def test_search_result_structure(self, client, mock_app_state):
        """Test that search result has correct structure."""
        response = client.post(
            "/api/v1/search",
            json={"query": "test"}
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["results"]) > 0
        result = data["results"][0]

        assert "file_path" in result
        assert "heading" in result
        assert "content" in result
        assert "score" in result
        assert "chunk_index" in result


class TestHealthEndpoint:
    """Tests for GET /health endpoint."""

    def test_health_check(self, client, mock_app_state):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert data["status"] == "healthy"
        assert "index_size" in data
        assert data["index_size"] == 100
