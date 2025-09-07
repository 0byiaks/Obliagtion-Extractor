import fitz  # PyMuPDF
from docx import Document
from fastapi import UploadFile, HTTPException
import io
import re
from typing import Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TextExtractor:
    """
    Service for extracting text from various document formats
    Supports: PDF, DOCX, TXT files
    """
    
    def __init__(self):
        self.supported_types = {
            "application/pdf": self._extract_pdf,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": self._extract_docx,
            "text/plain": self._extract_txt
        }
    
    async def extract_text(self, file: UploadFile) -> str:
        """
        Main method to extract text from uploaded file
        """
        try:
            # Read file content
            content = await file.read()
            logger.info(f"Processing file: {file.filename} ({file.content_type})")
            
            # Get appropriate extraction method
            if file.content_type not in self.supported_types:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Unsupported file type: {file.content_type}"
                )
            
            # Extract text using appropriate method
            extractor = self.supported_types[file.content_type]
            raw_text = extractor(content)
            
            # Clean and process text
            cleaned_text = self._clean_text(raw_text)
            
            # Validate extraction
            if not cleaned_text.strip():
                raise HTTPException(
                    status_code=400, 
                    detail="No text could be extracted from the document"
                )
            
            logger.info(f"Successfully extracted {len(cleaned_text)} characters")
            return cleaned_text
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Text extraction failed: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"Text extraction failed: {str(e)}"
            )
    
    def _extract_pdf(self, content: bytes) -> str:
        """
        Extract text from PDF using PyMuPDF
        """
        try:
            # Create PDF document from bytes
            doc = fitz.open(stream=content, filetype="pdf")
            
            text_parts = []
            page_count = len(doc)
            
            logger.info(f"Processing PDF with {page_count} pages")
            
            for page_num in range(page_count):
                page = doc[page_num]
                
                # Extract text from page
                page_text = page.get_text()
                
                # Add page separator for multi-page documents
                if page_text.strip():
                    text_parts.append(f"\n--- Page {page_num + 1} ---\n")
                    text_parts.append(page_text)
            
            doc.close()
            
            full_text = "".join(text_parts)
            logger.info(f"PDF extraction complete: {len(full_text)} characters extracted")
            
            return full_text
            
        except Exception as e:
            logger.error(f"PDF extraction error: {str(e)}")
            raise Exception(f"Failed to extract text from PDF: {str(e)}")
    
    def _extract_docx(self, content: bytes) -> str:
        """
        Extract text from DOCX using python-docx
        """
        try:
            # Create document from bytes
            doc = Document(io.BytesIO(content))
            
            text_parts = []
            
            # Extract paragraphs
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_parts.append(paragraph.text)
            
            # Extract tables
            for table in doc.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        if cell.text.strip():
                            row_text.append(cell.text.strip())
                    if row_text:
                        text_parts.append(" | ".join(row_text))
            
            full_text = "\n".join(text_parts)
            logger.info(f"DOCX extraction complete: {len(full_text)} characters extracted")
            
            return full_text
            
        except Exception as e:
            logger.error(f"DOCX extraction error: {str(e)}")
            raise Exception(f"Failed to extract text from DOCX: {str(e)}")
    
    def _extract_txt(self, content: bytes) -> str:
        """
        Extract text from plain text file
        """
        try:
            # Try different encodings
            encodings = ['utf-8', 'utf-16', 'latin1', 'cp1252']
            
            for encoding in encodings:
                try:
                    text = content.decode(encoding)
                    logger.info(f"TXT extraction complete using {encoding}: {len(text)} characters")
                    return text
                except UnicodeDecodeError:
                    continue
            
            # If all encodings fail, use utf-8 with error handling
            text = content.decode('utf-8', errors='replace')
            logger.warning("Used UTF-8 with error replacement for text extraction")
            return text
            
        except Exception as e:
            logger.error(f"TXT extraction error: {str(e)}")
            raise Exception(f"Failed to extract text from TXT: {str(e)}")
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize extracted text
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page breaks and form feeds
        text = re.sub(r'[\f\v]', '\n', text)
        
        # Normalize line breaks
        text = re.sub(r'\r\n', '\n', text)
        text = re.sub(r'\r', '\n', text)
        
        # Remove excessive line breaks (more than 2 consecutive)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Clean up special characters that might interfere
        text = re.sub(r'[^\w\s\.,;:!?()[\]{}"\'-/\\@#$%^&*+=<>~`|]', '', text)
        
        # Trim whitespace
        text = text.strip()
        
        return text
    
    def get_document_info(self, file: UploadFile, content: bytes) -> dict:
        """
        Get basic information about the document
        """
        info = {
            "filename": file.filename,
            "content_type": file.content_type,
            "size_bytes": len(content),
            "size_readable": self._format_file_size(len(content))
        }
        
        # Add format-specific info
        if file.content_type == "application/pdf":
            try:
                doc = fitz.open(stream=content, filetype="pdf")
                info["page_count"] = len(doc)
                info["has_images"] = any(len(page.get_images()) > 0 for page in doc)
                doc.close()
            except:
                info["page_count"] = "unknown"
                info["has_images"] = "unknown"
                
        elif file.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            try:
                doc = Document(io.BytesIO(content))
                info["paragraph_count"] = len(doc.paragraphs)
                info["table_count"] = len(doc.tables)
            except:
                info["paragraph_count"] = "unknown"
                info["table_count"] = "unknown"
        
        return info
    
    def _format_file_size(self, size_bytes: int) -> str:
        """
        Format file size in human readable format
        """
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024**2:
            return f"{size_bytes/1024:.1f} KB"
        elif size_bytes < 1024**3:
            return f"{size_bytes/(1024**2):.1f} MB"
        else:
            return f"{size_bytes/(1024**3):.1f} GB"
    
    def validate_file(self, file: UploadFile) -> dict:
        """
        Validate uploaded file before processing
        """
        errors = []
        warnings = []
        
        # Check file type
        if file.content_type not in self.supported_types:
            errors.append(f"Unsupported file type: {file.content_type}")
        
        # Check filename
        if not file.filename:
            errors.append("Filename is missing")
        
        # File size limits (adjust as needed)
        MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
        if hasattr(file, 'size') and file.size > MAX_FILE_SIZE:
            errors.append(f"File size too large. Maximum allowed: {self._format_file_size(MAX_FILE_SIZE)}")
        
        # Check file extension matches content type
        if file.filename:
            extension = file.filename.lower().split('.')[-1]
            expected_extensions = {
                "application/pdf": ["pdf"],
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ["docx"],
                "text/plain": ["txt"]
            }
            
            if file.content_type in expected_extensions:
                if extension not in expected_extensions[file.content_type]:
                    warnings.append(f"File extension '{extension}' doesn't match content type")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }