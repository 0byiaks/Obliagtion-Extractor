"""
Data models for legal document processing
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class Obligation:
    """Represents an extracted obligation from a legal document"""
    party: str
    action: str
    trigger: Optional[str] = None
    deadline: Optional[str] = None
    amount: Optional[str] = None
    confidence: float = 0.0
    source_text: str = ""
    section_id: str = ""
    clause_id: str = ""
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ExtractionStats:
    """Statistics about the extraction process"""
    total_clauses: int = 0
    prefilter_kept: int = 0
    classifier_positive: int = 0
    obligations_found: int = 0
    processing_time_ms: int = 0
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}