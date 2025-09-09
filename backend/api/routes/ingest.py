from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import Dict, Any, Optional
from services.ingest.parsers import to_text, IngestError
from core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.post("/ingest/file")
async def ingest_file(file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    Ingest a single file and return metadata and text content.
    
    Returns:
        - mode: file processing mode
        - filename: original filename
        - char_count: character count of extracted text
        - preview: first 200 characters of text
        - text: full extracted text
    """
    try:
        logger.info(f"Ingesting file: {file.filename}")
        
        # Parse the file to extract text
        file_bytes = await file.read()
        text, detected_type = to_text(file_bytes, file.filename)
        
        # Calculate character count
        char_count = len(text)
        
        # Create preview (first 200 characters)
        preview = text[:200] + "..." if len(text) > 200 else text
        
        # Use detected type as mode
        mode = detected_type
        
        result = {
            "mode": mode,
            "filename": file.filename,
            "char_count": char_count,
            "preview": preview,
            "text": text
        }
        
        logger.info(f"File ingestion completed - {char_count} characters extracted")
        return result
        
    except IngestError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingest failed: {e}")

@router.post("/ingest/text")
async def ingest_text(text: str = Form(...)) -> Dict[str, Any]:
    """
    Ingest text directly and return metadata and content.
    
    Returns:
        - mode: text processing mode
        - filename: "text_input"
        - char_count: character count of input text
        - preview: first 200 characters of text
        - text: full input text
    """
    try:
        logger.info(f"Ingesting text input - {len(text)} characters")
        
        # Calculate character count
        char_count = len(text)
        
        # Create preview (first 200 characters)
        preview = text[:200] + "..." if len(text) > 200 else text
        
        result = {
            "mode": "text",
            "filename": "text_input",
            "char_count": char_count,
            "preview": preview,
            "text": text
        }
        
        logger.info(f"Text ingestion completed - {char_count} characters processed")
        return result
        
    except Exception as e:
        logger.error(f"Text ingestion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Text ingest failed: {e}")
