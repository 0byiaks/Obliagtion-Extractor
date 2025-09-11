import os
import json
from openai import OpenAI
from typing import Dict, Any, Optional, List
import logging
from dataclasses import dataclass
from dotenv import load_dotenv
from .prompts import get_legal_document_analysis_prompt

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

@dataclass
class LLMConfig:
    """Configuration for LLM client"""
    api_key: str
    model: str = "gpt-4o-mini"
    max_tokens: int = 1200
    temperature: float = 0.1
    timeout: int = 30

class LLMClient:
    """Modern OpenAI ChatGPT client for document segmentation with JSON responses"""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """
        Initialize LLM client with configuration
        
        Args:
            config: LLM configuration. If None, loads from environment variables
        """
        if config is None:
            config = self._load_config_from_env()
        
        self.config = config
        self.client = OpenAI(api_key=config.api_key)
        
        logger.info(f"LLM Client initialized with model: {config.model}, max_tokens: {config.max_tokens}")
    
    def _load_config_from_env(self) -> LLMConfig:
        """Load configuration from environment variables"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        return LLMConfig(
            api_key=api_key,
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "1200")),
            temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.1")),
            timeout=int(os.getenv("OPENAI_TIMEOUT", "30"))
        )
    
    def process_section(self, text: str, section_context: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a single section of text with LLM using JSON response format
        
        Args:
            text: The text content to process (should be within token limit)
            section_context: Optional context about the section (heading, etc.)
        
        Returns:
            Dictionary with processed results
        """
        try:
            # Create system prompt for JSON response
            system_prompt = get_legal_document_analysis_prompt()
            
            # Create user prompt
            user_prompt = f"Process this legal document section:\n\n{text}"
            if section_context:
                user_prompt = f"Context: {section_context}\n\n{user_prompt}"
            
            # Call OpenAI with JSON response format
            response = self.client.chat.completions.create(
                model=self.config.model,
                temperature=self.config.temperature,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=self.config.max_tokens,
                timeout=self.config.timeout
            )
            
            # Parse JSON response
            json_response = json.loads(response.choices[0].message.content)
            
            result = {
                "success": True,
                "processed_data": json_response,
                "processed_text": json_response.get("processed_text", text),
                "usage": {
                    "total_tokens": response.usage.total_tokens,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens
                },
                "model": response.model
            }
            
            logger.info(f"LLM processed section successfully. Tokens used: {response.usage.total_tokens}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return {
                "success": False,
                "error": f"JSON parsing error: {str(e)}",
                "error_type": "json_error",
                "processed_text": text  # Fallback to original text
            }
        except Exception as e:
            logger.error(f"Unexpected error in LLM processing: {e}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "error_type": "unknown",
                "processed_text": text  # Fallback to original text
            }
    
    def test_connection(self) -> bool:
        """
        Test the LLM connection with a simple request
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "user", "content": "Hello, this is a test message."}
                ],
                max_tokens=10,
                temperature=0
            )
            
            logger.info("LLM connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"LLM connection test failed: {e}")
            return False
    
    def get_token_count(self, text: str) -> int:
        """
        Estimate token count for text (rough approximation)
        
        Args:
            text: Text to count tokens for
        
        Returns:
            Estimated token count
        """
        # Rough approximation: 1 token ≈ 4 characters for English text
        return len(text) // 4
    
    def is_within_token_limit(self, text: str) -> bool:
        """
        Check if text is within the configured token limit (1200 tokens)
        
        Args:
            text: Text to check
        
        Returns:
            True if within limit, False otherwise
        """
        estimated_tokens = self.get_token_count(text)
        return estimated_tokens <= self.config.max_tokens
