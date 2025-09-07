from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime

# ---- Obligation internals (structured) ----

class Amount(BaseModel):
    raw: Optional[str] = None              # "$10,000", "ten thousand US dollars"
    value: Optional[Decimal] = None        # 10000.00 if confidently parsed
    currency: Optional[str] = None         # "USD", "GBP", etc.

class Deadline(BaseModel):
    raw: Optional[str] = None              # "within 30 days of Delivery"
    normalized: Optional[str] = None       # "2026-03-15" or "RELATIVE:P30D_AFTER_DELIVERY"

class Ambiguity(BaseModel):
    field: str                              # "party" | "action" | "trigger" | "deadline" | "amount"
    reason: str

class ObligationItem(BaseModel):
    id: Optional[str] = None                # server-assigned or model-provided
    party: Optional[str] = None
    action: Optional[str] = None
    trigger: Optional[str] = None
    deadline: Deadline = Field(default_factory=Deadline)
    amount: Amount = Field(default_factory=Amount)
    clause_id: Optional[str] = None         # canonical id for source clause
    clause_reference: Optional[str] = None  # "Section 2.1" if present in text
    confidence_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    ambiguities: List[Ambiguity] = Field(default_factory=list)

# ---- Per-clause grouping ----

class ClauseResult(BaseModel):
    clause_id: str
    obligations: List[ObligationItem]

# ---- Request/Response (document-level wrapper) ----

class ExtractRequest(BaseModel):
    # transport/input hints
    document_type: Optional[str] = Field(default="auto", description="pdf, docx, txt, auto")
    text: Optional[str] = None             # for paste mode
    known_parties: Optional[List[str]] = None
    extract_confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    include_implicit_obligations: bool = True
    max_tokens_per_batch: int = 1800

class ObligationResponse(BaseModel):
    document_name: Optional[str] = None
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    processing_time: Optional[float] = None
    extraction_success: bool = True

    # results
    results: List[ClauseResult]
    counts: Dict[str, int]                  # {"total_obligations": n, "with_deadline": m, "with_amount": k}

# ---- Exports & utilities ----

class ExportRequest(BaseModel):
    format: str = Field(default="csv", description="csv, json, xlsx")
    include_metadata: bool = True

class ProcessingStatus(BaseModel):
    status: str
    progress_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    current_step: str = ""
    estimated_completion: Optional[datetime] = None

class FileValidation(BaseModel):
    is_valid: bool
    file_type: str
    file_size: int
    error_message: Optional[str] = None

class ConfidenceMetrics(BaseModel):
    overall_confidence: Optional[float] = None
    high_confidence_count: int = 0
    medium_confidence_count: int = 0
    low_confidence_count: int = 0
    avg_confidence: Optional[float] = None