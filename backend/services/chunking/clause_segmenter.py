"""
Complete ClauseSegmenter with all required methods
"""
import re
import logging
from typing import List, Tuple, Optional, Dict, Any
from models.schema import Clause, ClauseLevel

logger = logging.getLogger(__name__)


class ClauseSegmenter:
    """Service for segmenting legal documents by section headings"""
    
    def __init__(self):
        """Initialize with patterns for section heading documents"""
        # These are the actual section headings from your document
        self.section_headings = [
            "Interpretation",
            "Confidential Information", 
            "Confidentiality obligations",
            "Mandatory disclosure",
            "Return or destruction of Confidential Information",
            "Reservation of rights and acknowledgement",
            "indemnity",
            "Inadequacy of damages",
            "No obligation to continue discussions",
            "Ending discussions and duration of confidentiality obligations",
            "No partnership or agency",
            "General"
        ]
        
        logger.info("Clause segmenter initialized for section heading documents")
    
    def segment_section(self, section_text: str, section_id: str, section_heading: str) -> List[Clause]:
        """
        Segment document by section headings - THE REAL FIX
        """
        try:
            # Clean the text
            cleaned_text = self._clean_text(section_text)
            
            # Find section boundaries
            section_positions = self._find_section_positions(cleaned_text)
            
            if not section_positions:
                # No sections found, return entire text as one clause
                return [self._create_single_clause(cleaned_text, section_id, section_heading)]
            
            # Extract clauses for each section
            clauses = []
            for i, (heading, start_pos) in enumerate(section_positions):
                # Determine end position
                if i + 1 < len(section_positions):
                    end_pos = section_positions[i + 1][1]
                else:
                    end_pos = len(cleaned_text)
                
                # Extract section content
                section_content = cleaned_text[start_pos:end_pos].strip()
                
                # Skip very short sections
                if len(section_content) < 20:
                    continue
                
                # Create clause
                clause = Clause(
                    clause_id=f"{section_id}_{i+1}",
                    clause_number=str(i + 1),
                    text=section_content,
                    heading=heading,
                    level=ClauseLevel.MAIN_SECTION,
                    section_id=section_id,
                    section_heading=section_heading,
                    start_char=start_pos,
                    end_char=end_pos,
                    metadata={
                        'extracted_with': 'section_heading_split',
                        'section_index': i,
                        'original_heading': heading
                    }
                )
                
                clauses.append(clause)
            
            logger.info(f"Segmented document into {len(clauses)} sections")
            return clauses
            
        except Exception as e:
            logger.error(f"Error segmenting document: {e}")
            return [self._create_single_clause(section_text, section_id, section_heading)]
    
    def _clean_text(self, text: str) -> str:
        """Clean the input text"""
        # Remove table of contents and headers
        lines = text.split('\n')
        cleaned_lines = []
        
        skip_until_agreed = True
        for line in lines:
            line = line.strip()
            
            
            # Skip everything until "IT IS HEREBY AGREED"
            if "IT IS HEREBY AGREED" in line:
                skip_until_agreed = False
                continue
                
            if skip_until_agreed:
                continue
                
            # Skip signatures and other end matter
            if any(phrase in line for phrase in [
                "THIS AGREEMENT HAS BEEN ENTERED",
                "Signed by",
                "Director",
                "Intern",
                "for and on behalf of"
            ]):
                break
                
            if line:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _find_section_positions(self, text: str) -> List[Tuple[str, int]]:
        """Find positions of section headings in the text"""
        positions = []
        
        for heading in self.section_headings:
            # Look for the heading as a standalone line
            pattern = rf'^{re.escape(heading)}$'
            match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
            
            if match:
                positions.append((heading, match.start()))
            else:
                # Try without exact match (for slight variations)
                pattern = rf'^{re.escape(heading)}'
                match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
                if match:
                    positions.append((heading, match.start()))
        
        # Sort by position in text
        positions.sort(key=lambda x: x[1])
        
        return positions
    
    def _create_single_clause(self, text: str, section_id: str, section_heading: str) -> Clause:
        """Create a single clause from entire text"""
        return Clause(
            clause_id=f"{section_id}_1",
            clause_number="1",
            text=text,
            heading=section_heading,
            level=ClauseLevel.MAIN_SECTION,
            section_id=section_id,
            section_heading=section_heading,
            start_char=0,
            end_char=len(text),
            metadata={'extracted_with': 'single_clause_fallback'}
        )
    
    def segment_multiple_sections(self, sections: List[dict]) -> List[Clause]:
        """Segment multiple sections"""
        all_clauses = []
        
        for section in sections:
            section_clauses = self.segment_section(
                section['text'],
                section['id'], 
                section['heading']
            )
            all_clauses.extend(section_clauses)
        
        return all_clauses
    
    # MISSING METHODS - THESE ARE REQUIRED FOR YOUR FASTAPI
    
    def segment_to_structured_dict(self, text: str, doc_id: str, doc_title: str) -> List[Dict[str, Any]]:
        """
        Return clauses in the exact JSON structure needed by the API.
        This is where ALL parsing, regex, and text processing logic should live.
        
        Args:
            text: Document text to process
            doc_id: Document identifier
            doc_title: Document title
            
        Returns:
            List of structured clause dictionaries ready for API response
        """
        clauses = self.segment_section(text, doc_id, doc_title)
        
        # Convert to structured format directly here
        structured_clauses = []
        
        for clause in clauses:
            structured_clause = {
                'id': clause.clause_number or clause.clause_id,
                'title': clause.heading or f"Section {clause.clause_number}",
                'content': clause.text,
                'sub_clauses': self._extract_sub_clauses_from_text(clause.text, clause.clause_number or clause.clause_id)
            }
            structured_clauses.append(structured_clause)
        
        return structured_clauses
    
    def _extract_sub_clauses_from_text(self, text: str, section_id: str) -> List[Dict[str, Any]]:
        """
        Extract sub-clauses from text using regex patterns to find numbered sub-clauses.
        """
        sub_clauses = []
        
        # First, try to find numbered sub-clauses (2.1, 2.2, etc.)
        # Pattern to match: "2.1" followed by content until next "2.2" or end
        pattern = rf'{section_id}\.(\d+)\s+(.+?)(?=\n{section_id}\.\d+\s+|\Z)'
        matches = re.findall(pattern, text, re.DOTALL)
        
        if matches:
            # Found numbered sub-clauses
            for match in matches:
                sub_number, content = match
                content = content.strip()
                
                # Extract title from first line
                lines = content.split('\n')
                title = lines[0] if lines else f"Sub-clause {section_id}.{sub_number}"
                
                sub_clauses.append({
                    'id': f"{section_id}.{sub_number}",
                    'title': title,
                    'content': f"{section_id}.{sub_number} {content}",
                    'items': self._extract_definition_items(content, f"{section_id}.{sub_number}")
                })
        
        # If no numbered sub-clauses found, try specific patterns for known sections
        elif "Definitions:" in text and "Interpretation." in text:
            # Section 1 (Interpretation) - has clear "Definitions:" and "Interpretation." parts
            parts = text.split("Interpretation.", 1)
            
            if len(parts) == 2:
                definitions_part = parts[0].strip()
                interpretation_part = parts[1].strip()
                
                # Definitions sub-clause
                sub_clauses.append({
                    'id': f"{section_id}.1",
                    'title': "Definitions",
                    'content': f"{section_id}.1 {definitions_part}",
                    'items': self._extract_definition_items(definitions_part, f"{section_id}.1")
                })
                
                # Interpretation sub-clause
                sub_clauses.append({
                    'id': f"{section_id}.2", 
                    'title': "Interpretation",
                    'content': f"{section_id}.2 Interpretation.\n{interpretation_part}",
                    'items': []
                })
        
        elif "Information is not Confidential Information if:" in text:
            # Section 2 has two clear parts
            parts = text.split("Information is not Confidential Information if:", 1)
            
            if len(parts) == 2:
                definition_part = parts[0].strip()
                exclusion_part = "Information is not Confidential Information if:" + parts[1].strip()
                
                sub_clauses.append({
                    'id': f"{section_id}.1",
                    'title': "Confidential Information Definition",
                    'content': f"{section_id}.1 {definition_part}",
                    'items': []
                })
                
                sub_clauses.append({
                    'id': f"{section_id}.2",
                    'title': "Information Not Considered Confidential",
                    'content': f"{section_id}.2 {exclusion_part}",
                    'items': []
                })
            else:
                # Fallback
                sub_clauses.append({
                    'id': f"{section_id}.1",
                    'title': "Content",
                    'content': text,
                    'items': []
                })
        
        # For sections with clear obligation lists (like Confidentiality obligations)
        elif "shall:" in text or "undertakes" in text:
            # Split on numbered sub-clauses (3.1, 3.2, etc.)
            pattern = r'(\d+\.\d+)\s+(.+?)(?=\n\d+\.\d+|\Z)'
            matches = re.findall(pattern, text, re.DOTALL)
            
            if matches:
                for match in matches:
                    clause_number, clause_text = match
                    clause_text = clause_text.strip()
                    
                    # Extract a clean title from the first line
                    lines = clause_text.split('\n')
                    first_line = lines[0].strip()
                    
                    # Create a shorter title
                    if len(first_line) > 80:
                        title = first_line[:80] + "..."
                    else:
                        title = first_line
                    
                    sub_clauses.append({
                        'id': clause_number,
                        'title': title,
                        'content': f"{clause_number} {clause_text}",
                        'items': []
                    })
            else:
                # Fallback - create single sub-clause
                sub_clauses.append({
                    'id': f"{section_id}.1",
                    'title': "Content",
                    'content': text,
                    'items': []
                })
        
        # Default fallback for all other sections
        else:
            sub_clauses.append({
                'id': f"{section_id}.1",
                'title': "Content",
                'content': f"{section_id}.1 {text}",
                'items': []
            })
        
        return sub_clauses
    
    def _extract_title_from_content(self, content: str) -> str:
        """Extract a meaningful title from content"""
        lines = content.split('\n')
        if not lines:
            return "Content"
            
        first_line = lines[0].strip()
        if len(first_line) > 80:
            # Take first few words if line is too long
            words = first_line.split()[:8]
            return ' '.join(words)
        else:
            return first_line
    
    def _extract_definition_items(self, text: str, clause_number: str) -> List[Dict[str, str]]:
        """
        Extract individual definition items from clause text.
        FIXED to handle your document's specific definition format.
        """
        items = []
        
        # Pattern for definitions like: "Business Day" means any day other than...
        definition_pattern = r'"([^"]+)"\s+(means|has|is)\s+(.+?)(?=\n"|$)'
        matches = re.findall(definition_pattern, text, re.MULTILINE | re.DOTALL)
        
        for i, (term, connector, definition) in enumerate(matches):
            definition = definition.strip()
            # Clean up definition text
            if definition.endswith('.'):
                definition = definition[:-1]
            
            # Remove extra whitespace and line breaks
            definition = ' '.join(definition.split())
            
            items.append({
                'id': f"{clause_number}.{i+1}",
                'term': term,
                'definition': f"{connector} {definition}"
            })
        
        return items


def test_with_your_data():
    """Test with your actual document text"""
    
    # Your actual document text
    document_text = """DEFEYENE LEGAL SOLUTIONS LIMITED
and
Otitodilichukwu Vincent Obiokala
Confidentiality Agreement
Table Of Contents
Interpretation 3
Confidential Information 4
Confidentiality obligations 5
Mandatory disclosure 5
Return or destruction of Confidential Information 6
Reservation of rights and acknowledgement 6
indemnity 7
Inadequacy of damages 7
No obligation to continue discussions 7
Ending discussions and duration of confidentiality obligations 7
No partnership or agency 7
General 8
This Agreement is made on the 20th day of August 2025
BETWEEN
Defeyene Legal Solutions Limited, a company incorporated and registered in England and Wales with company number 10721979 whose registered office is at 2 Leman Street, Beyond, Aldgate Tower, E1 8FA London ("Definely")
Otitodilichukwu Vincent Obiokala , a United Kingdom resident whose primary place of residence is at 130 fairlawn court SE77DU, London (the "Individual")
RECITALS
The parties intend to enter into discussions relating to the Purpose which will involve the disclosure of confidential information from Definely to the Recipient.
The parties have agreed to comply with this Agreement in connection with the disclosure and use of Confidential Information.
IT IS HEREBY AGREED
Interpretation
Definitions:
"Business Day" means any day other than a Saturday, Sunday or public holiday in England when banks in London are open for business.
"Confidential Information" has the meaning given in clause 2.
"Discloser" means Definely, being the party that discloses its Confidential Information, directly or indirectly, to the Recipient.
"Purpose" means the summer internship run by Definely for the period commencing on 01/09/2025 and ending on 26/09/2025
"Recipient" means the Individual, being the party that receives Confidential Information, directly or indirectly, from the Discloser.
"Representative(s)" means in relation to each party (to the extent applicable):
its officers and employees that need to know the Confidential Information for the Purpose;
its professional advisers or consultants who are engaged to advise that party: in connection with the Purpose;
its contractors and sub-contractors engaged by that party: in connection with the Purpose; and
any other person to whom the other party agrees in writing that Confidential Information may be disclosed in connection with the Purpose.
Interpretation.
A reference to a statute or statutory provision is a reference to it as amended or re-enacted. A reference to a statute or statutory provision includes any subordinate legislation made under that statute or statutory provision, as amended or re-enacted.
Any words following the terms including, include, in particular, for example or any similar expression shall be construed as illustrative and shall not limit the sense of the words, description, definition, phrase or term preceding those terms.
A reference to writing or written includes email.
A reference to a company shall include any company, corporation or other body corporate, wherever and however incorporated or established.
A reference to a holding company or a subsidiary means a holding company or a subsidiary (as the case may be) as defined in section 1159 of the Companies Act 2006.
Any obligation on a party not to do something includes an obligation not to allow that thing to be done.
Confidential Information
Confidential Information means all confidential information relating to the Purpose which the Discloser or its Representatives directly or indirectly discloses, or makes available, to the Recipient or its Representatives, before, on or after the date of this Agreement. This includes:
the terms of this Agreement;
all confidential or proprietary information relating to:
the business, affairs, customers, clients, suppliers plans, intentions, or market opportunities of the Discloser; and
the operations, processes, product information, know-how, technical information, designs, trade secrets or software of the Discloser;
any information, findings, data or analysis derived from Confidential Information; and
any other information that is identified as being of a confidential or proprietary nature.
but excludes any information referred to in clause 2.2.
Information is not Confidential Information if:
it is, or becomes, generally available to the public other than as a direct or indirect result of the information being disclosed by the Recipient or its Representatives in breach of this Agreement (except that any compilation of otherwise public information in a form not publicly known shall still be treated as Confidential Information);
it was available to the Recipient on a non-confidential basis prior to disclosure by the Discloser;
it was, is, or becomes available to the Recipient on a non-confidential basis from a person who, to the Recipient's knowledge, is not under any confidentiality obligation in respect of that information;
it was lawfully in the possession of the Recipient before the information was disclosed by the Discloser;
it is developed by or for the Recipient independently of the information disclosed by the Discloser; and
the parties agree in writing that the information is not confidential."""
    
    segmenter = ClauseSegmenter()
    
    # Test the structured output method
    structured_clauses = segmenter.segment_to_structured_dict(document_text, "doc", "Confidentiality Agreement")
    
    print(f"Found {len(structured_clauses)} structured clauses:")
    for clause in structured_clauses:
        print(f"\nClause {clause['id']}: {clause['title']}")
        print(f"Sub-clauses: {len(clause['sub_clauses'])}")
        for sub_clause in clause['sub_clauses']:
            print(f"  - {sub_clause['id']}: {sub_clause['title']}")
            if sub_clause['items']:
                print(f"    Items: {len(sub_clause['items'])}")
        print("="*50)
    
    return structured_clauses


if __name__ == "__main__":
    test_with_your_data()
