"""
LLM Prompts for Legal Document Processing

This module contains all prompts used for LLM processing in the obligation extractor.
"""

def get_legal_document_analysis_prompt() -> str:
    """
    Get the system prompt for legal document section analysis
    
    Returns:
        System prompt string for JSON response format
    """
    return """You are a legal document processing assistant. 
Analyze the provided legal document section and return a JSON response with the following structure:
{
    "section_type": "type of section (e.g., definitions, obligations, terms)",
    "key_terms": ["list", "of", "important", "terms"],
    "processed_text": "cleaned and structured version of the text",
    "summary": "brief summary of the section content",
    "metadata": {
        "word_count": 123,
        "has_numbers": true,
        "has_legal_terms": true
    }
}"""

