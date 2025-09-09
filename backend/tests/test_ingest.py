import pytest
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app import app
import io

client = TestClient(app)

def test_ping():
    """Test the ping endpoint."""
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_ingest_file_docx():
    """Test ingesting a docx file."""
    # Create a simple test docx content (this is a simplified test)
    # In a real test, you'd create an actual .docx file
    test_content = b"PK\x03\x04"  # Minimal ZIP header for docx
    test_file = io.BytesIO(test_content)
    
    response = client.post(
        "/ingest/file",
        files={"file": ("test.docx", test_file, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    
    # This will fail because it's not a real docx file, but tests the endpoint structure
    assert response.status_code in [200, 400]  # Either success or expected failure

def test_ingest_file_no_file():
    """Test ingesting without a file."""
    response = client.post("/ingest/file")
    assert response.status_code == 422  # Validation error

def test_ingest_file_empty():
    """Test ingesting an empty file."""
    test_file = io.BytesIO(b"")
    
    response = client.post(
        "/ingest/file",
        files={"file": ("empty.docx", test_file, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    )
    
    # Empty file should fail parsing
    assert response.status_code == 400

def test_ingest_file_unsupported():
    """Test ingesting an unsupported file type."""
    test_content = "This is a test contract with obligations."
    test_file = io.BytesIO(test_content.encode())
    
    response = client.post(
        "/ingest/file",
        files={"file": ("test.txt", test_file, "text/plain")}
    )
    
    # Unsupported file type should return 400
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]
