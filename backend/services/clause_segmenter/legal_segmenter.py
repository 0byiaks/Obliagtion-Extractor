"""
Legal Document Clause Segmenter using spaCy NLP
"""
import re
import spacy
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class LegalClause:
    """Represents a legal clause with NLP-extracted information"""
    clause_id: str
    clause_number: Optional[str]
    text: str
    heading: Optional[str]
    level: int
    section_id: str
    section_heading: str
    
    # NLP-extracted information
    entities: List[Dict[str, Any]]
    obligation_verbs: List[str]
    legal_patterns: List[Dict[str, Any]]
    confidence: float
    
    # Position information
    start_char: int = 0
    end_char: int = 0
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class LegalDocumentSegmenter:
    """Legal document segmenter using spaCy NLP"""
    
    def __init__(self):
        """Initialize the legal document segmenter"""
        try:
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("✅ spaCy English model loaded successfully")
        except OSError:
            logger.error("❌ spaCy English model not found. Please run: python -m spacy download en_core_web_sm")
            raise
        
        # Legal-specific patterns
        self.legal_patterns = {
            # Obligation patterns
            'obligation': re.compile(r'(\w+(?:\s+\w+)*)\s+(?:shall|must|agrees to|required to|undertakes to)\s+(.+?)(?:\.|$)', re.IGNORECASE),
            
            # Prohibition patterns  
            'prohibition': re.compile(r'(\w+(?:\s+\w+)*)\s+(?:shall not|must not|agrees not to|prohibited from)\s+(.+?)(?:\.|$)', re.IGNORECASE),
            
            # Time-bound obligations
            'time_bound': re.compile(r'within\s+(\d+\s+\w+)\s+of\s+(.+?)(?:\.|$)', re.IGNORECASE),
            
            # Monetary obligations
            'monetary': re.compile(r'[\$£€]\d+(?:,\d{3})*(?:\.\d{2})?', re.IGNORECASE),
            
            # Legal definitions
            'definition': re.compile(r'"([^"]+)"\s+means\s+(.+?)(?:\.|$)', re.IGNORECASE),
            
            # Section headings (more flexible pattern)
            'section_heading': re.compile(r'^(\d+)\.\s+([A-Z][A-Za-z\s]+)$', re.MULTILINE),
            
            # Subsection headings
            'subsection_heading': re.compile(r'^(\d+)\.(\d+)\s+(.+)$', re.MULTILINE),
        }
        
        # Legal obligation verbs
        self.obligation_verbs = {
            'positive': ['shall', 'must', 'agrees to', 'required to', 'undertakes to', 'warrants', 'covenants'],
            'negative': ['shall not', 'must not', 'agrees not to', 'prohibited from', 'forbidden to']
        }
        
        logger.info("🔧 Legal Document Segmenter initialized with spaCy")
    
    def segment_document(self, text: str, document_id: str = "document") -> List[LegalClause]:
        """
        Segment a legal document into clauses using NLP
        
        Args:
            text: The legal document text
            document_id: Unique identifier for the document
            
        Returns:
            List of LegalClause objects
        """
        try:
            logger.info(f"📄 Segmenting legal document: {document_id}")
            
            # Use comprehensive clause detection
            clauses = self._detect_all_clauses(text, document_id)
            
            logger.info(f"✅ Document segmented into {len(clauses)} legal clauses")
            return clauses
            
        except Exception as e:
            logger.error(f"❌ Error segmenting document: {e}")
            # Return single clause with entire document
            return [self._create_fallback_clause(text, document_id)]
    
    def _detect_sections(self, text: str) -> List[Dict[str, Any]]:
        """Detect document sections using regex patterns"""
        sections = []
        
        # Find main sections
        section_matches = self.legal_patterns['section_heading'].findall(text)
        
        for i, (num, title) in enumerate(section_matches):
            # Find content until next section or end
            start_pattern = rf'^{num}\.\s+{re.escape(title)}$'
            next_pattern = rf'^{int(num)+1}\.\s+'
            
            start_match = re.search(start_pattern, text, re.MULTILINE)
            next_match = re.search(next_pattern, text, re.MULTILINE)
            
            if start_match:
                start_pos = start_match.start()
                end_pos = next_match.start() if next_match else len(text)
                content = text[start_pos:end_pos].strip()
                
                sections.append({
                    'id': f"s{num}",
                    'number': num,
                    'title': title.strip(),
                    'content': content,
                    'level': 1
                })
        
        return sections
    
    def _process_section(self, section: Dict[str, Any], full_text: str, document_id: str, offset: int) -> List[LegalClause]:
        """Process a section into clauses"""
        clauses = []
        section_text = section['content']
        
        # Find subsections within this section (1.1, 2.1, etc.)
        subsection_matches = self.legal_patterns['subsection_heading'].findall(section_text)
        
        for num, sub_num, content in subsection_matches:
            clause_text = f"{num}.{sub_num} {content}"
            
            # Process with spaCy
            doc = self.nlp(clause_text)
            
            # Extract NLP information
            entities = self._extract_entities(doc)
            obligation_verbs = self._extract_obligation_verbs(doc)
            legal_patterns = self._extract_legal_patterns(doc)
            confidence = self._calculate_confidence(doc, obligation_verbs, legal_patterns)
            
            clause = LegalClause(
                clause_id=f"{document_id}.s{num}.c{sub_num}",
                clause_number=f"{num}.{sub_num}",
                text=clause_text,
                heading=content.split(':')[0] if ':' in content else content[:50],
                level=2,
                section_id=section['id'],
                section_heading=section['title'],
                entities=entities,
                obligation_verbs=obligation_verbs,
                legal_patterns=legal_patterns,
                confidence=confidence,
                start_char=offset,
                end_char=offset + len(clause_text),
                metadata={
                    'extracted_with': 'spacy_nlp',
                    'section_level': section['level']
                }
            )
            
            clauses.append(clause)
        
        # Also process the section heading itself as a clause
        section_heading_clause = LegalClause(
            clause_id=f"{document_id}.s{section['id']}.heading",
            clause_number=section['id'],
            text=section['title'],
            heading=section['title'],
            level=1,
            section_id=section['id'],
            section_heading=section['title'],
            entities=[],
            obligation_verbs=[],
            legal_patterns=[],
            confidence=0.1,  # Low confidence for headings
            start_char=offset,
            end_char=offset + len(section['title']),
            metadata={
                'extracted_with': 'section_heading',
                'section_level': section['level']
            }
        )
        clauses.append(section_heading_clause)
        
        return clauses
    
    def _process_single_document(self, text: str, document_id: str) -> List[LegalClause]:
        """Process document as single unit when no clear sections found"""
        clauses = []
        
        # Split by sentences (remove length filter to catch short clauses)
        doc = self.nlp(text)
        sentences = [sent.text for sent in doc.sents if len(sent.text.strip()) > 5]  # Reduced from 20 to 5
        
        for i, sentence in enumerate(sentences):
            sent_doc = self.nlp(sentence)
            
            entities = self._extract_entities(sent_doc)
            obligation_verbs = self._extract_obligation_verbs(sent_doc)
            legal_patterns = self._extract_legal_patterns(sent_doc)
            confidence = self._calculate_confidence(sent_doc, obligation_verbs, legal_patterns)
            
            clause = LegalClause(
                clause_id=f"{document_id}.sentence_{i+1}",
                clause_number=None,
                text=sentence,
                heading=None,
                level=1,
                section_id="main",
                section_heading="Main Document",
                entities=entities,
                obligation_verbs=obligation_verbs,
                legal_patterns=legal_patterns,
                confidence=confidence,
                start_char=0,
                end_char=len(sentence),
                metadata={
                    'extracted_with': 'spacy_sentence',
                    'sentence_index': i
                }
            )
            
            clauses.append(clause)
        
        return clauses
    
    def _detect_all_clauses(self, text: str, document_id: str) -> List[LegalClause]:
        """Detect all types of clauses comprehensively"""
        clauses = []
        
        # Split text into lines
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        for i, line in enumerate(lines):
            # Determine clause type and level
            clause_info = self._classify_clause(line)
            
            if clause_info['type'] == 'section_heading':
                clause = LegalClause(
                    clause_id=f"{document_id}.s{clause_info['number']}.heading",
                    clause_number=clause_info['number'],
                    text=line,
                    heading=clause_info['title'],
                    level=1,
                    section_id=f"s{clause_info['number']}",
                    section_heading=clause_info['title'],
                    entities=[],
                    obligation_verbs=[],
                    legal_patterns=[],
                    confidence=0.1,
                    start_char=0,
                    end_char=len(line),
                    metadata={'extracted_with': 'comprehensive_detection', 'clause_type': 'section_heading'}
                )
                clauses.append(clause)
                
            elif clause_info['type'] == 'subsection':
                clause = LegalClause(
                    clause_id=f"{document_id}.s{clause_info['section']}.c{clause_info['subsection']}",
                    clause_number=f"{clause_info['section']}.{clause_info['subsection']}",
                    text=line,
                    heading=clause_info['title'],
                    level=2,
                    section_id=f"s{clause_info['section']}",
                    section_heading=self._get_section_heading(clauses, clause_info['section']),
                    entities=self._extract_entities(self.nlp(line)),
                    obligation_verbs=self._extract_obligation_verbs(self.nlp(line)),
                    legal_patterns=self._extract_legal_patterns(self.nlp(line)),
                    confidence=self._calculate_confidence(self.nlp(line), [], []),
                    start_char=0,
                    end_char=len(line),
                    metadata={'extracted_with': 'comprehensive_detection', 'clause_type': 'subsection'}
                )
                clauses.append(clause)
                
            elif clause_info['type'] == 'definition':
                clause = LegalClause(
                    clause_id=f"{document_id}.def_{i}",
                    clause_number=clause_info.get('number', f"def_{i}"),
                    text=line,
                    heading=clause_info.get('term', 'Definition'),
                    level=3,
                    section_id=self._get_current_section_id(clauses),
                    section_heading=self._get_current_section_heading(clauses),
                    entities=self._extract_entities(self.nlp(line)),
                    obligation_verbs=self._extract_obligation_verbs(self.nlp(line)),
                    legal_patterns=self._extract_legal_patterns(self.nlp(line)),
                    confidence=0.2,  # Low confidence for definitions
                    start_char=0,
                    end_char=len(line),
                    metadata={'extracted_with': 'comprehensive_detection', 'clause_type': 'definition'}
                )
                clauses.append(clause)
                
            elif clause_info['type'] == 'regular_clause':
                clause = LegalClause(
                    clause_id=f"{document_id}.clause_{i}",
                    clause_number=clause_info.get('number', f"clause_{i}"),
                    text=line,
                    heading=clause_info.get('title', line[:50]),
                    level=2,
                    section_id=self._get_current_section_id(clauses),
                    section_heading=self._get_current_section_heading(clauses),
                    entities=self._extract_entities(self.nlp(line)),
                    obligation_verbs=self._extract_obligation_verbs(self.nlp(line)),
                    legal_patterns=self._extract_legal_patterns(self.nlp(line)),
                    confidence=self._calculate_confidence(self.nlp(line), [], []),
                    start_char=0,
                    end_char=len(line),
                    metadata={'extracted_with': 'comprehensive_detection', 'clause_type': 'regular_clause'}
                )
                clauses.append(clause)
        
        return clauses
    
    def _classify_clause(self, line: str) -> Dict[str, Any]:
        """Classify a line as a specific type of clause"""
        
        # Check for section headings (1. INTERPRETATION)
        section_match = re.match(r'^(\d+)\.\s+([A-Z][A-Za-z\s]+)$', line)
        if section_match:
            return {
                'type': 'section_heading',
                'number': section_match.group(1),
                'title': section_match.group(2).strip()
            }
        
        # Check for subsections (1.1, 2.1, etc.)
        subsection_match = re.match(r'^(\d+)\.(\d+)\s+(.+)$', line)
        if subsection_match:
            return {
                'type': 'subsection',
                'section': subsection_match.group(1),
                'subsection': subsection_match.group(2),
                'title': subsection_match.group(3).strip()
            }
        
        # Check for definitions (1.1.1, 1.1.2, etc.)
        definition_match = re.match(r'^(\d+)\.(\d+)\.(\d+)\s+(.+)$', line)
        if definition_match:
            return {
                'type': 'definition',
                'number': f"{definition_match.group(1)}.{definition_match.group(2)}.{definition_match.group(3)}",
                'term': definition_match.group(4).split('"')[1] if '"' in definition_match.group(4) else definition_match.group(4)[:30]
            }
        
        # Check for regular clauses with numbering
        regular_match = re.match(r'^(\d+)\.(\d+)\s+(.+)$', line)
        if regular_match:
            return {
                'type': 'regular_clause',
                'number': f"{regular_match.group(1)}.{regular_match.group(2)}",
                'title': regular_match.group(3).strip()
            }
        
        # Default to regular clause
        return {
            'type': 'regular_clause',
            'title': line[:50]
        }
    
    def _get_section_heading(self, clauses: List[LegalClause], section_num: str) -> str:
        """Get the section heading for a given section number"""
        for clause in reversed(clauses):
            if clause.section_id == f"s{section_num}" and clause.metadata.get('clause_type') == 'section_heading':
                return clause.heading
        return f"Section {section_num}"
    
    def _get_current_section_id(self, clauses: List[LegalClause]) -> str:
        """Get the current section ID based on previous clauses"""
        for clause in reversed(clauses):
            if clause.metadata.get('clause_type') == 'section_heading':
                return clause.section_id
        return "s1"
    
    def _get_current_section_heading(self, clauses: List[LegalClause]) -> str:
        """Get the current section heading based on previous clauses"""
        for clause in reversed(clauses):
            if clause.metadata.get('clause_type') == 'section_heading':
                return clause.heading
        return "Main Document"
    
    def _extract_entities(self, doc) -> List[Dict[str, Any]]:
        """Extract named entities from spaCy doc"""
        entities = []
        
        for ent in doc.ents:
            entities.append({
                'text': ent.text,
                'label': ent.label_,
                'start': ent.start_char,
                'end': ent.end_char,
                'confidence': 0.8  # spaCy doesn't provide confidence scores
            })
        
        return entities
    
    def _extract_obligation_verbs(self, doc) -> List[str]:
        """Extract obligation verbs from text"""
        obligation_verbs = []
        
        for token in doc:
            token_lower = token.text.lower()
            
            # Check for positive obligation verbs
            for verb in self.obligation_verbs['positive']:
                if verb in token_lower:
                    obligation_verbs.append(token.text)
            
            # Check for negative obligation verbs
            for verb in self.obligation_verbs['negative']:
                if verb in token_lower:
                    obligation_verbs.append(token.text)
        
        return list(set(obligation_verbs))  # Remove duplicates
    
    def _extract_legal_patterns(self, doc) -> List[Dict[str, Any]]:
        """Extract legal patterns from text"""
        patterns = []
        text = doc.text
        
        # Check for obligation patterns
        obligation_match = self.legal_patterns['obligation'].search(text)
        if obligation_match:
            patterns.append({
                'pattern_type': 'obligation',
                'party': obligation_match.group(1),
                'action': obligation_match.group(2),
                'confidence': 0.9
            })
        
        # Check for prohibition patterns
        prohibition_match = self.legal_patterns['prohibition'].search(text)
        if prohibition_match:
            patterns.append({
                'pattern_type': 'prohibition',
                'party': prohibition_match.group(1),
                'action': prohibition_match.group(2),
                'confidence': 0.9
            })
        
        # Check for monetary amounts
        monetary_matches = self.legal_patterns['monetary'].findall(text)
        for amount in monetary_matches:
            patterns.append({
                'pattern_type': 'monetary',
                'amount': amount,
                'confidence': 0.95
            })
        
        # Check for definitions
        definition_match = self.legal_patterns['definition'].search(text)
        if definition_match:
            patterns.append({
                'pattern_type': 'definition',
                'term': definition_match.group(1),
                'definition': definition_match.group(2),
                'confidence': 0.85
            })
        
        return patterns
    
    def _calculate_confidence(self, doc, obligation_verbs: List[str], legal_patterns: List[Dict[str, Any]]) -> float:
        """Calculate confidence score for clause"""
        confidence = 0.5  # Base confidence
        
        # Boost confidence for obligation verbs
        if obligation_verbs:
            confidence += 0.2
        
        # Boost confidence for legal patterns
        if legal_patterns:
            confidence += 0.2
        
        # Boost confidence for legal entities
        legal_entities = [ent for ent in doc.ents if ent.label_ in ['PERSON', 'ORG', 'MONEY', 'DATE']]
        if legal_entities:
            confidence += 0.1
        
        return min(confidence, 1.0)  # Cap at 1.0
    
    def _create_fallback_clause(self, text: str, document_id: str) -> LegalClause:
        """Create fallback clause when processing fails"""
        doc = self.nlp(text)
        
        return LegalClause(
            clause_id=f"{document_id}.fallback",
            clause_number=None,
            text=text,
            heading=None,
            level=1,
            section_id="main",
            section_heading="Main Document",
            entities=self._extract_entities(doc),
            obligation_verbs=self._extract_obligation_verbs(doc),
            legal_patterns=self._extract_legal_patterns(doc),
            confidence=0.3,
            start_char=0,
            end_char=len(text),
            metadata={'extracted_with': 'fallback'}
        )


def test_legal_segmenter():
    """Test the legal document segmenter"""
    segmenter = LegalDocumentSegmenter()
    
    # Sample legal document
    legal_text = """
1. INTERPRETATION
1.1 Definitions: In this Agreement, unless the context otherwise requires:
1.1.1 "Business Day" means any day other than a Saturday, Sunday or public holiday in England when banks in London are open for business.
1.1.2 "Confidential Information" means all confidential information relating to the Purpose which the Discloser discloses to the Recipient.

2. CONFIDENTIALITY OBLIGATIONS
2.1 The Recipient shall keep all Confidential Information secret and confidential.
2.2 The Recipient shall not disclose Confidential Information to any third party without prior written consent.
2.3 The Recipient shall return all Confidential Information within 30 days of termination.

3. PAYMENT TERMS
3.1 Party A shall pay Party B the sum of $50,000 within 14 Business Days of execution.
3.2 Payment shall be made by wire transfer to the account specified in Schedule A.
3.3 Late payments shall incur interest at the rate of 5% per annum.
"""
    
    clauses = segmenter.segment_document(legal_text, "test_doc")
    
    print(f"\n🔍 LEGAL DOCUMENT SEGMENTATION RESULTS:")
    print(f"Total clauses found: {len(clauses)}")
    print()
    
    for clause in clauses:
        print(f"CLAUSE {clause.clause_number or clause.clause_id}:")
        print(f"  📝 Text: {clause.text[:100]}...")
        print(f"  🏷️ Heading: {clause.heading}")
        print(f"  📊 Level: {clause.level}")
        print(f"  🎯 Confidence: {clause.confidence:.2f}")
        print(f"  ⚖️ Obligation Verbs: {clause.obligation_verbs}")
        print(f"  🔍 Legal Patterns: {len(clause.legal_patterns)} found")
        print(f"  🏢 Entities: {len(clause.entities)} found")
        print()


if __name__ == "__main__":
    test_legal_segmenter()
