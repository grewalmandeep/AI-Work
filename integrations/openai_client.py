"""OpenAI API client with error handling and fallback support."""

import os
import logging
from typing import Optional, Dict, Any, List
from openai import OpenAI, APIError, RateLimitError, APIConnectionError

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Primary LLM client using OpenAI GPT-4."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        self.client = OpenAI(api_key=self.api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o")
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate text completion with error handling."""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            return {
                "success": True,
                "content": response.choices[0].message.content,
                "model": self.model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
        except RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {e}")
            return {"success": False, "error": "rate_limit", "message": str(e)}
        except APIConnectionError as e:
            logger.error(f"OpenAI connection error: {e}")
            return {"success": False, "error": "connection", "message": str(e)}
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            return {"success": False, "error": "api_error", "message": str(e)}
        except Exception as e:
            try:
                from utils.traceback_capture import write_traceback
                write_traceback(e)
            except Exception:
                pass
            logger.error(f"Unexpected OpenAI error: {e}")
            raise
    
    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        **kwargs
    ):
        """Generate streaming text completion."""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                stream=True,
                **kwargs
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            yield f"Error: {str(e)}"
