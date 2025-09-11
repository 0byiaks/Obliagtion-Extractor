"""
Data models for legal document processing
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum


class ClauseLevel(Enum):
    """Hierarchical levels for legal document clauses"""
    MAIN_SECTION = "main_section"
    PRIMARY_SUBSECTION = "primary_subsection" 
    SECONDARY_SUBSECTION = "secondary_subsection"
    TERTIARY_SUBSECTION = "tertiary_subsection"
    ALPHABETICAL = "alphabetical"
    ROMAN_NUMERAL = "roman_numeral"


@dataclass
class Clause:
    """Represents a legal document clause with metadata"""
    clause_id: str
    clause_number: Optional[str]
    text: str
    heading: Optional[str]
    level: ClauseLevel
    section_id: str
    section_heading: str
    start_char: int = 0
    end_char: int = 0
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}