from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import Dict, Any, Optional
from services.ingest.parsers import to_text, IngestError
from services.chunking.legal_segmenter import LegalDocumentSegmenter
from core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.post("/ingest")
async def ingest(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None)
) -> Dict[str, Any]:
    """
    Ingest either a file upload or text input and return metadata and content.
    Applies NLP-based legal document segmentation.
    
    Args:
        file: Optional file upload
        text: Optional text input
    
    Returns:
        - mode: processing mode (file type or "text")
        - filename: original filename or "text_input"
        - char_count: character count of content
        - preview: first 200 characters of content
        - text: full extracted/input text
        - clauses: list of legal clauses with NLP analysis
        - stats: processing statistics
    """
    try:
        # Validate that exactly one input is provided
        if (file is None and text is None) or (file is not None and text is not None):
            raise HTTPException(
                status_code=400, 
                detail="Exactly one of 'file' or 'text' must be provided"
            )
        
        # Initialize legal document segmenter
        segmenter = LegalDocumentSegmenter()
        
        if file is not None:
            logger.info(f"Ingesting file: {file.filename}")
            
            # Parse the file to extract text
            file_bytes = await file.read()
            extracted_text, detected_type = to_text(file_bytes, file.filename)
            
            # Calculate character count
            char_count = len(extracted_text)
            
            # Create preview (first 200 characters)
            preview = extracted_text[:200] + "..." if len(extracted_text) > 200 else extracted_text
            
            # Apply NLP-based legal segmentation
            logger.info("Applying NLP-based legal document segmentation")
            legal_clauses = segmenter.segment_document(extracted_text, file.filename)
            
            # Convert clauses to serializable format
            clauses_data = []
            for clause in legal_clauses:
                clauses_data.append({
                    "clause_id": clause.clause_id,
                    "clause_number": clause.clause_number,
                    "text": clause.text,
                    "heading": clause.heading,
                    "level": clause.level,
                    "section_id": clause.section_id,
                    "section_heading": clause.section_heading,
                    "entities": clause.entities,
                    "obligation_verbs": clause.obligation_verbs,
                    "legal_patterns": clause.legal_patterns,
                    "confidence": clause.confidence,
                    "start_char": clause.start_char,
                    "end_char": clause.end_char,
                    "metadata": clause.metadata
                })
            
            result = {
                "mode": detected_type,
                "filename": file.filename,
                "char_count": char_count,
                "preview": preview,
                "text": extracted_text,
                "clauses": clauses_data,
                "stats": {
                    "total_clauses": len(legal_clauses),
                    "high_confidence_clauses": len([c for c in legal_clauses if c.confidence > 0.8]),
                    "obligation_clauses": len([c for c in legal_clauses if c.obligation_verbs]),
                    "processing_method": "spacy_nlp_legal_segmentation"
                }
            }
            
            logger.info(f"Processing completed - {len(legal_clauses)} legal clauses found")
            logger.info(f"File ingestion completed - {char_count} characters extracted")
            return result
            
        else:  # Process text input
            logger.info(f"Ingesting text input - {len(text)} characters")
            
            # Calculate character count
            char_count = len(text)
            
            # Create preview (first 200 characters)
            preview = text[:200] + "..." if len(text) > 200 else text
            
            # Apply NLP-based legal segmentation
            logger.info("Applying NLP-based legal document segmentation")
            legal_clauses = segmenter.segment_document(text, "text_input")
            
            # Convert clauses to serializable format
            clauses_data = []
            for clause in legal_clauses:
                clauses_data.append({
                    "clause_id": clause.clause_id,
                    "clause_number": clause.clause_number,
                    "text": clause.text,
                    "heading": clause.heading,
                    "level": clause.level,
                    "section_id": clause.section_id,
                    "section_heading": clause.section_heading,
                    "entities": clause.entities,
                    "obligation_verbs": clause.obligation_verbs,
                    "legal_patterns": clause.legal_patterns,
                    "confidence": clause.confidence,
                    "start_char": clause.start_char,
                    "end_char": clause.end_char,
                    "metadata": clause.metadata
                })
            
            result = {
                "mode": "text",
                "filename": "text_input",
                "char_count": char_count,
                "preview": preview,
                "text": text,
                "clauses": clauses_data,
                "stats": {
                    "total_clauses": len(legal_clauses),
                    "high_confidence_clauses": len([c for c in legal_clauses if c.confidence > 0.8]),
                    "obligation_clauses": len([c for c in legal_clauses if c.obligation_verbs]),
                    "processing_method": "spacy_nlp_legal_segmentation"
                }
            }
            
            logger.info(f"Processing completed - {len(legal_clauses)} legal clauses found")
            logger.info(f"Text ingestion completed - {char_count} characters processed")
            return result
        
    except IngestError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        # Re-raise HTTPExceptions without modification
        raise
    except Exception as e:
        logger.error(f"Ingestion failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ingest failed: {e}")
