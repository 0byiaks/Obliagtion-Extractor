from typing import List, Dict, Any, Optional
from .client import LLMClient, LLMConfig
from ..chunking.prechunk import Section, create_toc_based_chunks
import logging

logger = logging.getLogger(__name__)

class LLMSegmentationService:
    """LLM-based document segmentation service"""
    
    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize segmentation service
        
        Args:
            llm_client: Optional LLM client. If None, creates default client
        """
        self.llm_client = llm_client or LLMClient()
        logger.info("LLM Segmentation Service initialized")
    
    def segment_document(self, text: str, max_section_length: int = 1500) -> List[Dict[str, Any]]:
        """
        Segment document using LLM processing
        
        Args:
            text: Document text to segment
            max_section_length: Maximum characters per section
        
        Returns:
            List of segmented sections with LLM processing results
        """
        try:
            # First, get basic sections using TOC-based approach
            sections = self._get_basic_sections(text)
            logger.info(f"Found {len(sections)} basic sections")
            
            # Process each section with LLM
            processed_sections = []
            
            for i, section in enumerate(sections):
                logger.info(f"Processing section {i+1}/{len(sections)}: {section.heading[:50]}...")
                
                # Check if section is within token limit
                section_text = f"{section.heading}\n\n{section.body}"
                
                if self.llm_client.is_within_token_limit(section_text):
                    # Process entire section
                    result = self.llm_client.process_section(
                        text=section.body,
                        section_context=section.heading
                    )
                    
                    processed_sections.append({
                        "section_index": i,
                        "heading": section.heading,
                        "original_body": section.body,
                        "processed_body": result.get("processed_text", section.body),
                        "processed_data": result.get("processed_data", {}),
                        "llm_success": result.get("success", False),
                        "llm_error": result.get("error") if not result.get("success") else None,
                        "tokens_used": result.get("usage", {}).get("total_tokens", 0),
                        "is_complete_section": True
                    })
                else:
                    # Section too long, split it
                    logger.info(f"Section too long, splitting into smaller parts")
                    sub_sections = self._split_long_section(section, max_section_length)
                    
                    for j, sub_section in enumerate(sub_sections):
                        result = self.llm_client.process_section(
                            text=sub_section["body"],
                            section_context=f"{section.heading} (Part {j+1})"
                        )
                        
                        processed_sections.append({
                            "section_index": i,
                            "sub_section_index": j,
                            "heading": f"{section.heading} (Part {j+1})",
                            "original_body": sub_section["body"],
                            "processed_body": result.get("processed_text", sub_section["body"]),
                            "processed_data": result.get("processed_data", {}),
                            "llm_success": result.get("success", False),
                            "llm_error": result.get("error") if not result.get("success") else None,
                            "tokens_used": result.get("usage", {}).get("total_tokens", 0),
                            "is_complete_section": False
                        })
            
            logger.info(f"LLM segmentation completed. Processed {len(processed_sections)} sections")
            return processed_sections
            
        except Exception as e:
            logger.error(f"Error in LLM segmentation: {e}")
            # Fallback to basic TOC-based chunking
            logger.info("Falling back to TOC-based chunking")
            chunks = create_toc_based_chunks(text)
            return [{
                "section_index": i,
                "heading": chunk.metadata.get("heading", f"Section {i+1}"),
                "original_body": chunk.text,
                "processed_body": chunk.text,
                "llm_success": False,
                "llm_error": f"Segmentation failed: {str(e)}",
                "tokens_used": 0,
                "is_complete_section": True
            } for i, chunk in enumerate(chunks)]
    
    def _get_basic_sections(self, text: str) -> List[Section]:
        """Get basic sections using TOC-based approach"""
        from ..chunking.prechunk import split_by_table_of_contents
        return split_by_table_of_contents(text)
    
    def _split_long_section(self, section: Section, max_length: int) -> List[Dict[str, str]]:
        """Split a long section into smaller parts"""
        words = section.body.split()
        sub_sections = []
        current_words = []
        
        for word in words:
            current_words.append(word)
            current_text = " ".join(current_words)
            
            if len(current_text) >= max_length:
                sub_sections.append({
                    "body": current_text,
                    "word_count": len(current_words)
                })
                current_words = []
        
        # Add remaining words
        if current_words:
            sub_sections.append({
                "body": " ".join(current_words),
                "word_count": len(current_words)
            })
        
        return sub_sections
    
    def test_llm_connection(self) -> bool:
        """Test if LLM connection is working"""
        return self.llm_client.test_connection()
