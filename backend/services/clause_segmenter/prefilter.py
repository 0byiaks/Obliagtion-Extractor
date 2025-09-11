"""
Pre-filtering service for legal document clauses
Uses cheap heuristics to identify clauses likely to contain obligations
"""
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PrefilterResult:
    """Result of pre-filtering a clause"""
    keep: bool
    score: float
    reasons: List[str]
    confidence: str
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class PreFilter:
    """Pre-filter service for legal document clauses"""
    
    def __init__(self, threshold: float = 0.35):
        """
        Initialize pre-filter with configurable threshold
        
        Args:
            threshold: Score threshold for keeping clauses (0.0-1.0)
        """
        self.threshold = threshold
        
        # Positive signals (increase score)
        self.obligation_verbs = [
            'shall', 'must', 'agrees to', 'required to', 'undertakes to',
            'warrants', 'covenants', 'promises', 'commits to', 'may',
            'agrees not to', 'prohibited from', 'forbidden to'
        ]
        
        self.action_verbs = [
            'pay', 'deliver', 'keep', 'return', 'provide', 'ensure',
            'notify', 'maintain', 'comply', 'perform', 'execute',
            'supply', 'inspect', 'report', 'submit', 'complete',
            'terminate', 'work', 'compete', 'serve', 'assign'
        ]
        
        self.obligation_sections = [
            'payment', 'delivery', 'confidentiality', 'indemnity',
            'warranty', 'sla', 'service level', 'performance',
            'obligations', 'duties', 'responsibilities', 'liability',
            'compensation', 'employment', 'termination', 'benefits',
            'non-compete', 'position', 'agreement'
        ]
        
        # Negative signals (decrease score)
        self.definition_patterns = [
            r'"([^"]+)"\s+means\s+',
            r'is\s+defined\s+as',
            r'for\s+purposes\s+of',
            r'as\s+used\s+herein',
            r'refers\s+to',
            r'shall\s+mean'
        ]
        
        self.skip_sections = [
            'recitals', 'whereas', 'background', 'miscellaneous',
            'governing law', 'notices', 'severability', 'interpretation',
            'definitions', 'terminology', 'abbreviations'
        ]
        
        # Compile regex patterns
        self.money_pattern = re.compile(r'[\$£€]\d+(?:,\d{3})*(?:\.\d{2})?')
        self.deadline_patterns = [
            re.compile(r'within\s+\d+\s+(?:days?|weeks?|months?|years?)', re.IGNORECASE),
            re.compile(r'by\s+\d{1,2}/\d{1,2}/\d{4}', re.IGNORECASE),
            re.compile(r'within\s+\d+\s+Business\s+Days', re.IGNORECASE),
            re.compile(r'no\s+later\s+than', re.IGNORECASE),
            re.compile(r'prior\s+to', re.IGNORECASE)
        ]
        
        logger.info(f"🔧 PreFilter initialized with threshold: {self.threshold}")
    
    def filter_clauses(self, clauses: List[Any]) -> List[Any]:
        """
        Filter clauses likely to contain obligations
        
        Args:
            clauses: List of LegalClause objects
            
        Returns:
            List of filtered LegalClause objects
        """
        logger.info(f"🔍 Pre-filtering {len(clauses)} clauses...")
        
        kept_clauses = []
        filtered_count = 0
        
        for clause in clauses:
            # Extract clause metadata
            clause_metadata = {
                'section_heading': getattr(clause, 'section_heading', ''),
                'clause_number': getattr(clause, 'clause_number', ''),
                'level': getattr(clause, 'level', 1)
            }
            
            # Pre-filter the clause
            result = self.prefilter_clause(clause.text, clause_metadata)
            
            if result.keep:
                # Add prefilter metadata to clause
                clause.metadata = clause.metadata or {}
                clause.metadata['prefilter'] = {
                    'keep': result.keep,
                    'score': result.score,
                    'reasons': result.reasons,
                    'confidence': result.confidence
                }
                kept_clauses.append(clause)
            else:
                filtered_count += 1
        
        logger.info(f"✅ Pre-filtering complete: {len(kept_clauses)} kept, {filtered_count} filtered")
        logger.info(f"📊 Filter rate: {filtered_count/len(clauses)*100:.1f}% filtered out")
        
        return kept_clauses
    
    def prefilter_clause(self, clause_text: str, metadata: Dict[str, Any]) -> PrefilterResult:
        """
        Pre-filter a single clause to determine if it likely contains obligations
        
        Args:
            clause_text: The text content of the clause
            metadata: Metadata about the clause (section, level, etc.)
            
        Returns:
            PrefilterResult with keep/skip decision and reasoning
        """
        score = 0.0
        reasons = []
        
        # 1. Check for obligation verbs (HIGH WEIGHT)
        obligation_found = False
        for verb in self.obligation_verbs:
            if verb.lower() in clause_text.lower():
                score += 0.4
                reasons.append(f"Contains obligation verb: '{verb}'")
                obligation_found = True
                break
        
        # 2. Check for monetary amounts (HIGH WEIGHT)
        if self.money_pattern.search(clause_text):
            score += 0.3
            reasons.append("Contains monetary amount")
        
        # 3. Check for deadlines/timeframes (MEDIUM WEIGHT)
        deadline_found = False
        for pattern in self.deadline_patterns:
            if pattern.search(clause_text):
                score += 0.2
                reasons.append("Contains deadline/timeframe")
                deadline_found = True
                break
        
        # 4. Check for obligation sections (MEDIUM WEIGHT)
        section_heading = metadata.get('section_heading', '').lower()
        for section in self.obligation_sections:
            if section in section_heading:
                score += 0.2
                reasons.append(f"From obligation section: '{section}'")
                break
        
        # 5. Check for action verbs (MEDIUM WEIGHT)
        action_found = False
        for verb in self.action_verbs:
            if verb.lower() in clause_text.lower():
                score += 0.1
                reasons.append(f"Contains action verb: '{verb}'")
                action_found = True
                break
        
        # 6. NEGATIVE SIGNALS (REDUCE SCORE)
        
        # Skip definitions
        for pattern in self.definition_patterns:
            if re.search(pattern, clause_text, re.IGNORECASE):
                score -= 0.3
                reasons.append("Appears to be a definition")
                break
        
        # Skip recitals/miscellaneous sections (but keep clauses with 'shall')
        for section in self.skip_sections:
            if section in section_heading:
                # If clause contains 'shall', don't penalize as much
                if 'shall' in clause_text.lower():
                    score -= 0.05  # Minimal penalty for 'shall' clauses
                    reasons.append(f"From non-obligation section: '{section}' (but contains 'shall')")
                else:
                    score -= 0.2
                    reasons.append(f"From non-obligation section: '{section}'")
                break
        
        # Skip very short clauses
        if len(clause_text.strip()) < 20:
            score -= 0.4
            reasons.append("Too short to contain meaningful obligation")
        
        # Skip clauses with only numbers/letters (likely numbering)
        if re.match(r'^[\d\.\s]+$', clause_text.strip()):
            score -= 0.5
            reasons.append("Appears to be clause numbering only")
        
        # 7. Determine final decision
        score = max(0.0, min(score, 1.0))  # Clamp between 0-1
        
        if score >= self.threshold:
            keep = True
            if score >= 0.7:
                confidence = "high"
            elif score >= 0.5:
                confidence = "medium"
            else:
                confidence = "low"
        else:
            keep = False
            confidence = "low"
        
        return PrefilterResult(
            keep=keep,
            score=score,
            reasons=reasons,
            confidence=confidence,
            metadata={
                'threshold': self.threshold,
                'obligation_found': obligation_found,
                'deadline_found': deadline_found,
                'action_found': action_found
            }
        )
    
    def get_filter_statistics(self, clauses: List[Any]) -> Dict[str, Any]:
        """
        Get statistics about pre-filtering performance
        
        Args:
            clauses: List of LegalClause objects
            
        Returns:
            Dictionary with filtering statistics
        """
        total_clauses = len(clauses)
        kept_clauses = 0
        high_confidence = 0
        medium_confidence = 0
        low_confidence = 0
        
        for clause in clauses:
            prefilter_data = getattr(clause, 'metadata', {}).get('prefilter', {})
            if prefilter_data.get('keep', False):
                kept_clauses += 1
                confidence = prefilter_data.get('confidence', 'low')
                if confidence == 'high':
                    high_confidence += 1
                elif confidence == 'medium':
                    medium_confidence += 1
                else:
                    low_confidence += 1
        
        return {
            'total_clauses': total_clauses,
            'kept_clauses': kept_clauses,
            'filtered_clauses': total_clauses - kept_clauses,
            'filter_rate': (total_clauses - kept_clauses) / total_clauses if total_clauses > 0 else 0,
            'high_confidence': high_confidence,
            'medium_confidence': medium_confidence,
            'low_confidence': low_confidence,
            'threshold': self.threshold
        }


def test_prefilter():
    """Test the pre-filter service"""
    prefilter = PreFilter(threshold=0.35)
    
    # Test clauses
    test_clauses = [
        {
            'text': 'Party A shall pay Party B the sum of $50,000 within 30 days',
            'metadata': {'section_heading': 'Payment Terms', 'clause_number': '3.1'}
        },
        {
            'text': 'Supplier shall deliver the Goods within 14 Business Days',
            'metadata': {'section_heading': 'Delivery Obligations', 'clause_number': '4.1'}
        },
        {
            'text': '"Business Day" means any day other than a Saturday',
            'metadata': {'section_heading': 'Definitions', 'clause_number': '1.1'}
        },
        {
            'text': 'This Agreement shall be governed by English law',
            'metadata': {'section_heading': 'Governing Law', 'clause_number': '8.1'}
        },
        {
            'text': 'The Recipient shall keep all Confidential Information secret',
            'metadata': {'section_heading': 'Confidentiality', 'clause_number': '2.1'}
        }
    ]
    
    print("🔍 Testing PreFilter Service")
    print("=" * 50)
    
    for i, test_case in enumerate(test_clauses):
        result = prefilter.prefilter_clause(test_case['text'], test_case['metadata'])
        
        print(f"\nCLAUSE {i+1}: {test_case['metadata']['clause_number']}")
        print(f"  📝 Text: {test_case['text']}")
        print(f"  🎯 Decision: {'KEEP' if result.keep else 'SKIP'}")
        print(f"  📊 Score: {result.score:.2f}")
        print(f"  🔍 Confidence: {result.confidence}")
        print(f"  📋 Reasons: {', '.join(result.reasons)}")
    
    print(f"\n📈 Summary:")
    print(f"  Threshold: {prefilter.threshold}")
    print(f"  Test completed successfully!")


if __name__ == "__main__":
    test_prefilter()
