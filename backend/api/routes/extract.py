from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from typing import Dict, Any, Optional
from services.ingest.parsers import to_text, IngestError
from services.clause_segmenter.legal_segmenter import LegalDocumentSegmenter
from services.clause_segmenter.prefilter import PreFilter
from core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.post("/extract")
async def extract_obligations(
    file: Optional[UploadFile] = File(None),
    text: Optional[str] = Form(None)
) -> Dict[str, Any]:
    """
    Extract obligations from legal documents using NLP-based segmentation.
    
    This endpoint processes legal documents (PDF, DOCX, TXT) or plain text input
    and extracts obligation clauses with intelligent pre-filtering to reduce LLM costs.
    
    Args:
        file: Optional file upload (PDF, DOCX, TXT)
        text: Optional text input of legal document
    
    Returns:
        - mode: processing mode (file type or "text")
        - filename: original filename or "text_input"
        - char_count: character count of content
        - preview: first 200 characters of content
        - text: full extracted/input text
        - clauses: list of legal clauses with NLP analysis and pre-filtering
        - stats: processing statistics including filter rates and confidence scores
    """
    try:
        # Validate that exactly one input is provided
        if (file is None and text is None) or (file is not None and text is not None):
            raise HTTPException(
                status_code=400, 
                detail="Exactly one of 'file' or 'text' must be provided"
            )
        
        # Initialize legal document segmenter and pre-filter
        segmenter = LegalDocumentSegmenter()
        prefilter = PreFilter(threshold=0.35)
        
        if file is not None:
            logger.info(f"Ingesting file: {file.filename}")
            
            # Parse the file to extract text
            file_bytes = await file.read()
            extracted_text = to_text(file_bytes, file.filename)
            
            # Calculate character count
            char_count = len(extracted_text)
            
            # Create preview (first 200 characters)
            preview = extracted_text[:200] + "..." if len(extracted_text) > 200 else extracted_text
            
            # Apply NLP-based legal segmentation
            logger.info("Applying NLP-based legal document segmentation")
            legal_clauses = segmenter.segment_document(extracted_text, file.filename)
            
            # Apply pre-filtering to identify obligation clauses
            logger.info("Applying pre-filtering to identify obligation clauses")
            filtered_clauses = prefilter.filter_clauses(legal_clauses)
            
            # Convert filtered clauses to serializable format
            clauses_data = []
            for clause in filtered_clauses:
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
                "mode": "file",
                "filename": file.filename,
                "char_count": char_count,
                "preview": preview,
                "text": extracted_text,
                "clauses": clauses_data,
                "stats": {
                    "total_clauses": len(legal_clauses),
                    "filtered_clauses": len(filtered_clauses),
                    "filter_rate": (len(legal_clauses) - len(filtered_clauses)) / len(legal_clauses) if legal_clauses else 0,
                    "high_confidence_clauses": len([c for c in filtered_clauses if c.confidence > 0.8]),
                    "obligation_clauses": len([c for c in filtered_clauses if c.obligation_verbs]),
                    "processing_method": "spacy_nlp_legal_segmentation_with_prefilter"
                }
            }
            
            logger.info(f"Processing completed - {len(legal_clauses)} total clauses, {len(filtered_clauses)} obligation clauses")
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
            
            # Apply pre-filtering to identify obligation clauses
            logger.info("Applying pre-filtering to identify obligation clauses")
            filtered_clauses = prefilter.filter_clauses(legal_clauses)
            
            # Convert filtered clauses to serializable format
            clauses_data = []
            for clause in filtered_clauses:
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
                    "filtered_clauses": len(filtered_clauses),
                    "filter_rate": (len(legal_clauses) - len(filtered_clauses)) / len(legal_clauses) if legal_clauses else 0,
                    "high_confidence_clauses": len([c for c in filtered_clauses if c.confidence > 0.8]),
                    "obligation_clauses": len([c for c in filtered_clauses if c.obligation_verbs]),
                    "processing_method": "spacy_nlp_legal_segmentation_with_prefilter"
                }
            }
            
            logger.info(f"Processing completed - {len(legal_clauses)} total clauses, {len(filtered_clauses)} obligation clauses")
            logger.info(f"Text ingestion completed - {char_count} characters processed")
            return result
        
    except IngestError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during document processing: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during document processing")