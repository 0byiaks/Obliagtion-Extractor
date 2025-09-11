"""
Tests for document parsing functionality (Task 1: Upload → Parse)
"""
import pytest
import io
from services.ingest.parsers import to_text, IngestError


class TestDocumentParsing:
    """Test document parsing for different file types"""
    
    def test_docx_parsing(self):
        """Test DOCX file parsing"""
        # Create a simple DOCX content (this would be a real DOCX file in practice)
        # For now, we'll test the error handling
        with pytest.raises(IngestError):
            to_text(b"invalid docx content", "test.docx")
    
    def test_txt_parsing(self):
        """Test TXT file parsing"""
        text_content = "This is a test document with obligations.\nCompany shall pay $1000."
        text_bytes = text_content.encode('utf-8')
        
        result_text, detected_type = to_text(text_bytes, "test.txt")
        
        assert detected_type == "txt"
        assert "test document" in result_text
        assert "Company shall pay" in result_text
    
    def test_txt_parsing_latin1(self):
        """Test TXT file parsing with latin-1 encoding"""
        text_content = "Test with special chars: café, naïve"
        text_bytes = text_content.encode('latin-1')
        
        result_text, detected_type = to_text(text_bytes, "test.txt")
        
        assert detected_type == "txt"
        assert "café" in result_text
    
    def test_pdf_parsing_not_implemented(self):
        """Test PDF parsing raises appropriate error"""
        with pytest.raises(IngestError, match="PDF parsing not yet implemented"):
            to_text(b"fake pdf content", "test.pdf")
    
    def test_unsupported_file_type(self):
        """Test unsupported file type raises error"""
        with pytest.raises(IngestError, match="Unsupported file type"):
            to_text(b"content", "test.xyz")
    
    def test_empty_file(self):
        """Test empty file handling"""
        result_text, detected_type = to_text(b"", "test.txt")
        
        assert detected_type == "txt"
        assert result_text == ""
    
    def test_none_filename(self):
        """Test None filename handling"""
        with pytest.raises(AttributeError):
            to_text(b"content", None)