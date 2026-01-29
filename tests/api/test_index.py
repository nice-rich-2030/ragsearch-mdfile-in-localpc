"""Tests for index management API endpoints."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def mock_app_state():
    """Create a mock AppState."""
    mock_state = MagicMock()
    mock_state.vector_store.count.return_value = 150
    mock_state.file_db.get_all_files.return_value = {
        "file1.md": MagicMock(),
        "file2.md": MagicMock(),
        "file3.txt": MagicMock()
    }

    # Mock indexer.update() return value
    mock_summary = MagicMock()
    mock_summary.added = 3
    mock_summary.updated = 1
    mock_summary.deleted = 0
    mock_summary.unchanged = 45
    mock_summary.total_chunks = 150
    mock_summary.api_call_count = 2
    mock_state.indexer.update.return_value = mock_summary

    return mock_state


@pytest.fixture
def client(mock_app_state):
    """Create a test client with mocked dependencies."""
    with patch('src.api.dependencies.get_app_state', return_value=mock_app_state):
        from src.api.app import app
        app.state.app_state = mock_app_state
        yield TestClient(app)


class TestIndexRebuildEndpoint:
    """Tests for POST /api/v1/index/rebuild endpoint."""

    def test_rebuild_index_success(self, client, mock_app_state):
        """Test successful index rebuild."""
        response = client.post(
            "/api/v1/index/rebuild",
            json={}
        )

        assert response.status_code == 200
        data = response.json()

        assert "added" in data
        assert "updated" in data
        assert "deleted" in data
        assert "unchanged" in data
        assert "total_chunks" in data
        assert "api_call_count" in data
        assert "execution_time_ms" in data

        assert data["added"] == 3
        assert data["updated"] == 1
        assert data["deleted"] == 0
        assert data["unchanged"] == 45
        assert data["total_chunks"] == 150
        assert data["api_call_count"] == 2
        assert data["execution_time_ms"] >= 0

    def test_rebuild_index_calls_indexer(self, client, mock_app_state):
        """Test that rebuild calls indexer.update()."""
        response = client.post(
            "/api/v1/index/rebuild",
            json={}
        )

        assert response.status_code == 200
        mock_app_state.indexer.update.assert_called_once()


class TestIndexStatusEndpoint:
    """Tests for GET /api/v1/index/status endpoint."""

    def test_index_status_success(self, client, mock_app_state):
        """Test successful index status retrieval."""
        response = client.get("/api/v1/index/status")

        assert response.status_code == 200
        data = response.json()

        assert "total_chunks" in data
        assert "total_files" in data

        assert data["total_chunks"] == 150
        assert data["total_files"] == 3

    def test_index_status_calls_correct_methods(self, client, mock_app_state):
        """Test that status endpoint calls correct methods."""
        response = client.get("/api/v1/index/status")

        assert response.status_code == 200
        mock_app_state.vector_store.count.assert_called()
        mock_app_state.file_db.get_all_files.assert_called()
