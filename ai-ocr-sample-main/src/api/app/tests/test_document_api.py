"""
Tests for document management API endpoints.
"""
import os
import pytest
import json
import tempfile
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, ANY

from app.main import app
from app.db.session import get_db

client = TestClient(app)


# Replace database with test database
async def override_get_db():
    """Mock database session for testing."""
    return MagicMock()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def test_document():
    """Sample document data for testing."""
    return {
        "id": "12345678-1234-5678-1234-567812345678",
        "filename": "test_document.xlsx",
        "file_type": "xlsx",
        "file_size": 1024,
        "file_path": "test_path/test_document.xlsx",
        "status": "uploaded",
        "metadata": None,
        "uploaded_at": "2025-03-26T12:00:00.000Z",
        "updated_at": "2025-03-26T12:00:00.000Z",
        "error": None
    }


@pytest.fixture
def test_parsed_data():
    """Sample parsed data for testing."""
    return {
        "file_name": "test_document.xlsx",
        "file_type": "xlsx",
        "sheets": {
            "Sheet1": {
                "data": [
                    {"A": "value1", "B": "value2"},
                    {"A": "value3", "B": "value4"}
                ],
                "columns": [
                    {"name": "A", "type": "object"},
                    {"name": "B", "type": "object"}
                ],
                "shape": {
                    "rows": 2,
                    "columns": 2
                }
            }
        },
        "sheet_names": ["Sheet1"]
    }


@pytest.fixture
def test_extracted_data():
    """Sample extracted data for testing."""
    return {
        "tables": [
            {
                "sheet_name": "Sheet1",
                "headers": ["A", "B"],
                "data": [
                    {"A": "value1", "B": "value2"},
                    {"A": "value3", "B": "value4"}
                ]
            }
        ],
        "metadata": {
            "document_type": "excel_table",
            "extraction_mode": "standard",
            "confidence_score": 0.85
        }
    }


@pytest.fixture
def test_validation_results():
    """Sample validation results for testing."""
    return {
        "valid": True,
        "level": "standard",
        "errors": [],
        "warnings": []
    }


class TestDocumentAPI:
    """Test document management API endpoints."""

    @patch("app.services.document_service.create_document")
    @patch("app.services.storage_service.store_document")
    def test_upload_document(self, mock_store, mock_create, test_document):
        """Test document upload endpoint."""
        # Setup mocks
        mock_store.return_value = "test_path/test_document.xlsx"
        mock_create.return_value = MagicMock(**test_document)
        
        # Test uploading with sample file
        with open("README.md", "rb") as f:
            response = client.post(
                "/api/v1/documents/",
                files={"file": ("test_document.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
            )
        
        # Verify response
        assert response.status_code == 201
        assert "document_id" in response.json()
        assert response.json()["status"] == "uploaded"
        
        # Verify mocks called
        mock_store.assert_called_once()
        mock_create.assert_called_once()

    @patch("app.services.document_service.get_document")
    def test_get_document(self, mock_get, test_document):
        """Test get document endpoint."""
        # Setup mock
        mock_get.return_value = MagicMock(**test_document)
        
        # Test get document
        response = client.get(f"/api/v1/documents/{test_document['id']}")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_document["id"]
        assert data["filename"] == test_document["filename"]
        assert data["status"] == test_document["status"]
        
        # Verify mock called
        mock_get.assert_called_once()

    @patch("app.services.document_service.get_document")
    def test_get_nonexistent_document(self, mock_get):
        """Test get nonexistent document."""
        # Setup mock
        mock_get.return_value = None
        
        # Test get nonexistent document
        response = client.get("/api/v1/documents/00000000-0000-0000-0000-000000000000")
        
        # Verify response
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch("app.services.document_service.get_documents")
    def test_list_documents(self, mock_get_all, test_document):
        """Test list documents endpoint."""
        # Setup mock
        mock_get_all.return_value = [MagicMock(**test_document)]
        
        # Test list documents
        response = client.get("/api/v1/documents/")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == test_document["id"]
        
        # Verify mock called
        mock_get_all.assert_called_once()

    @patch("app.services.document_service.delete_document")
    @patch("app.services.document_service.get_document")
    def test_delete_document(self, mock_get, mock_delete, test_document):
        """Test delete document endpoint."""
        # Setup mocks
        mock_get.return_value = MagicMock(**test_document)
        mock_delete.return_value = None
        
        # Test delete document
        response = client.delete(f"/api/v1/documents/{test_document['id']}")
        
        # Verify response
        assert response.status_code == 204
        
        # Verify mocks called
        mock_get.assert_called_once()
        mock_delete.assert_called_once()

    @patch("app.services.document_service.get_document")
    def test_delete_nonexistent_document(self, mock_get):
        """Test delete nonexistent document."""
        # Setup mock
        mock_get.return_value = None
        
        # Test delete nonexistent document
        response = client.delete("/api/v1/documents/00000000-0000-0000-0000-000000000000")
        
        # Verify response
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower() 
        
    @patch("app.services.document_service.parse_document")
    def test_parse_document(self, mock_parse, test_parsed_data):
        """Test document parsing endpoint."""
        # Setup mock
        mock_parse.return_value = test_parsed_data
        
        # Create a temporary test file
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as temp_file:
            temp_file.write(b"test content")
            temp_file_path = temp_file.name
        
        try:
            # Test parsing with sample file
            with open(temp_file_path, "rb") as f:
                response = client.post(
                    "/api/v1/documents/parse",
                    files={"file": ("test_document.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
                )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["file_name"] == "test_document.xlsx"
            assert data["file_type"] == "xlsx"
            assert "parsed_data" in data
            
            # Verify mock called
            mock_parse.assert_called_once()
        
        finally:
            # Clean up
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    @patch("app.services.extraction_service.create_extraction")
    @patch("app.services.document_service.process_document")
    @patch("app.services.storage_service.get_document_url")
    @patch("app.services.document_service.get_document")
    @patch("httpx.AsyncClient.get")
    def test_process_document(
        self, 
        mock_httpx_get, 
        mock_get_document, 
        mock_get_url, 
        mock_process, 
        mock_create_extraction,
        test_document,
        test_extracted_data,
        test_validation_results
    ):
        """Test document processing endpoint."""
        # Setup mocks
        document = MagicMock(**test_document)
        document.jobs = [MagicMock(id="job-123")]
        mock_get_document.return_value = document
        
        mock_get_url.return_value = "https://example.com/test_document.xlsx"
        
        # Mock httpx response
        mock_http_response = MagicMock()
        mock_http_response.raise_for_status = MagicMock()
        mock_http_response.content = b"test content"
        mock_httpx_get.return_value = mock_http_response
        
        # Mock process_document
        mock_process.return_value = (test_extracted_data, 0.85, test_validation_results)
        
        # Mock create_extraction
        extraction = MagicMock(id="extraction-123")
        mock_create_extraction.return_value = extraction
        
        # Test processing
        response = client.post(
            f"/api/v1/documents/{test_document['id']}/process",
            data={"validation_level": "standard"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == test_document["id"]
        assert data["extraction_id"] == "extraction-123"
        assert data["confidence"] == 0.85
        assert data["is_valid"] == True
        
        # Verify mocks called
        mock_get_document.assert_called_once()
        mock_get_url.assert_called_once()
        mock_httpx_get.assert_called_once()
        mock_process.assert_called_once()
        mock_create_extraction.assert_called_once() 