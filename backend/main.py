# main.py
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic_settings import BaseSettings
import logging
from typing import List, Optional
import uvicorn

# Services
from services.text_ectractor import TextExtractor
from services.ai_processor import AIProcessor
from services.export_service import ExportService

# Models (use your current ones; consider adding counts later)
from models.obligation import ObligationResponse, ObligationItem, ClauseResult

# ---------------- Settings ----------------

class Settings(BaseSettings):
    CORS_ORIGINS: str = "http://localhost:3000"
    MAX_UPLOAD_MB: int = 20
    # Add LLM keys etc. later
    class Config:
        env_file = ".env"

settings = Settings()

# ---------------- App & Middleware ----------------

app = FastAPI(
    title="Legal Document Obligation Extractor",
    description="Extract structured obligations from legal documents using AI",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("obligation-extractor")

# ---------------- Dependency helpers ----------------

def get_text_extractor() -> TextExtractor:
    return TextExtractor()

def get_ai_processor() -> AIProcessor:
    return AIProcessor()

def get_export_service() -> ExportService:
    return ExportService()

# ---------------- Common helpers ----------------

ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
}

def validate_upload(file: UploadFile):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Supported: PDF, DOCX, TXT",
        )

# Optional: limit very large uploads by Content-Length when reverse proxy doesn’t enforce it
def enforce_size_limit(content_length: Optional[int]):
    if content_length is not None:
        mb = content_length / (1024 * 1024)
        if mb > settings.MAX_UPLOAD_MB:
            raise HTTPException(status_code=413, detail="File too large")

# ---------------- Routes ----------------

@app.get("/")
async def root():
    return {"message": "Legal Document Obligation Extractor API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "obligation-extractor"}

@app.get("/supported-formats")
async def get_supported_formats():
    return {
        "supported_formats": [
            {"extension": "pdf", "mime_type": "application/pdf", "description": "PDF documents"},
            {"extension": "docx", "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "description": "Word documents"},
            {"extension": "txt", "mime_type": "text/plain", "description": "Plain text files"},
        ]
    }

# --- A) File upload path ---
@app.post("/extract-obligations", response_model=ObligationResponse)
async def extract_obligations_file(
    file: UploadFile = File(...),
    text_extractor: TextExtractor = Depends(get_text_extractor),
    ai_processor: AIProcessor = Depends(get_ai_processor),
):
    enforce_size_limit(None)  # pass request.headers.get("content-length") if you want
    validate_upload(file)

    try:
        log.info("Processing file: %s (%s)", file.filename, file.content_type)
        document_text = await text_extractor.extract_text(file)
        if not document_text or not document_text.strip():
            raise HTTPException(status_code=400, detail="No text could be extracted from the document")

        log.info("Extracting obligations with AI…")
        obligations: List[ObligationItem] = await ai_processor.extract_obligations(document_text)

        # Create clause results from obligations
        clause_results = [
            ClauseResult(
                clause_id=f"clause_{i+1}",
                obligations=[obligation]
            ) for i, obligation in enumerate(obligations)
        ]
        
        # Calculate counts
        counts = {
            "total_obligations": len(obligations),
            "with_deadline": sum(1 for o in obligations if getattr(o, "deadline", None) and getattr(o.deadline, "raw", None)),
            "with_amount": sum(1 for o in obligations if getattr(o, "amount", None) and getattr(o.amount, "raw", None)),
        }

        response = ObligationResponse(
            document_name=file.filename,
            results=clause_results,
            counts=counts,
            extraction_success=True,
        )
        # Optionally attach counts in a response header or extend your model
        return response

    except HTTPException:
        raise
    except Exception as e:
        log.exception("Error processing document")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# --- B) Paste-text path (great for dev + quick tests) ---
class TextExtractBody(JSONResponse):
    pass

@app.post("/extract-obligations-text", response_model=ObligationResponse)
async def extract_obligations_text(
    body: dict = Body(..., example={"text": "Seller shall deliver goods within 30 days; Buyer shall pay $10,000."}),
    ai_processor: AIProcessor = Depends(get_ai_processor),
):
    text = (body or {}).get("text", "")
    if not text or not text.strip():
        raise HTTPException(status_code=400, detail="Provide non-empty 'text'")

    try:
        log.info("Extracting obligations from pasted text (%d chars)…", len(text))
        obligations: List[ObligationItem] = await ai_processor.extract_obligations(text)

        # Create clause results from obligations
        clause_results = [
            ClauseResult(
                clause_id=f"clause_{i+1}",
                obligations=[obligation]
            ) for i, obligation in enumerate(obligations)
        ]
        
        # Calculate counts
        counts = {
            "total_obligations": len(obligations),
            "with_deadline": sum(1 for o in obligations if getattr(o, "deadline", None) and getattr(o.deadline, "raw", None)),
            "with_amount": sum(1 for o in obligations if getattr(o, "amount", None) and getattr(o.amount, "raw", None)),
        }

        response = ObligationResponse(
            document_name="pasted_text",
            results=clause_results,
            counts=counts,
            extraction_success=True,
        )
        return response
    except Exception as e:
        log.exception("Error processing pasted text")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# --- C) CSV export ---
@app.post("/export-csv")
async def export_obligations_csv(
    obligations_data: ObligationResponse,
    export_service: ExportService = Depends(get_export_service),
):
    try:
        csv_content = export_service.to_csv(obligations_data.obligations)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=obligations_{obligations_data.document_name}.csv"},
        )
    except Exception as e:
        log.exception("CSV export failed")
        raise HTTPException(status_code=500, detail=f"CSV export failed: {str(e)}")

# ---------------- Error handlers (optional polish) ----------------

@app.exception_handler(422)
async def validation_exception_handler(request, exc):
    # Uniform validation error shape
    return JSONResponse(status_code=422, content={"detail": "Validation failed", "errors": exc.errors()})

# ---------------- Main ----------------

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
