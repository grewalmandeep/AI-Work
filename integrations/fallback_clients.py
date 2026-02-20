"""Fallback LLM clients for Anthropic Claude and Google Gemini."""

import os
import logging
from typing import Optional, Dict, Any
import requests

logger = logging.getLogger(__name__)


class ClaudeClient:
    """LLM client using Anthropic Claude (default: Sonnet 4.6 for strong code/content generation)."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.base_url = "https://api.anthropic.com/v1/messages"
        self.model = model or os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        self.enabled = bool(self.api_key)
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate text completion using Claude."""
        if not self.enabled:
            return {
                "success": False,
                "error": "api_key_missing",
                "message": "ANTHROPIC_API_KEY not configured"
            }
        
        try:
            headers = {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            
            payload = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}]
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            data = data if isinstance(data, dict) else {}
            content_list = data.get("content")
            content_list = content_list if isinstance(content_list, list) else []
            first_block = content_list[0] if len(content_list) else None
            content = ""
            if first_block is not None and isinstance(first_block, dict):
                content = first_block.get("text", "") or ""
            return {
                "success": True,
                "content": content,
                "model": self.model,
                "usage": data.get("usage", {}) if isinstance(data.get("usage"), dict) else {}
            }
        except Exception as e:
            try:
                from utils.traceback_capture import write_traceback
                write_traceback(e)
            except Exception:
                pass
            logger.error(f"Claude API error: {e}")
            raise


class GeminiClient:
    """Fallback LLM client using Google Gemini 2.0 Flash (configurable model)."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        # Allow model to be configured via environment variable, default to gemini-2.0-flash-exp
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.0-flash-exp")
        # Use v1beta API for newer models like gemini-2.0-flash-exp
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        self.enabled = bool(self.api_key)
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate text completion using Gemini."""
        if not self.enabled:
            return {
                "success": False,
                "error": "api_key_missing",
                "message": "GOOGLE_API_KEY not configured"
            }
        
        try:
            url = f"{self.base_url}?key={self.api_key}"
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                    "topP": 0.95,
                    "topK": 40
                }
            }
            
            # Add system instruction if provided (supported in Gemini 2.0+)
            if system_prompt:
                payload["systemInstruction"] = {
                    "parts": [{"text": system_prompt}]
                }
            
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
            data = data if isinstance(data, dict) else {}
            content = ""
            candidates = data.get("candidates")
            candidates = candidates if isinstance(candidates, list) else []
            if candidates and len(candidates):
                first = candidates[0]
                if first is not None and isinstance(first, dict):
                    c = first.get("content")
                    c = c if isinstance(c, dict) else {}
                    parts = c.get("parts")
                    parts = parts if isinstance(parts, list) else []
                    if parts and len(parts):
                        part = parts[0]
                        if part is not None and isinstance(part, dict):
                            content = part.get("text", "") or ""
            usage = data.get("usageMetadata")
            usage = usage if isinstance(usage, dict) else {}
            return {
                "success": True,
                "content": content,
                "model": self.model,
                "usage": usage
            }
        except Exception as e:
            try:
                from utils.traceback_capture import write_traceback
                write_traceback(e)
            except Exception:
                pass
            logger.error(f"Gemini API error: {e}")
            raise


class LLMOrchestrator:
    """Orchestrates LLM calls with automatic fallback. Use Claude as primary when USE_CLAUDE_AS_PRIMARY=true."""
    
    def __init__(self):
        from integrations.openai_client import OpenAIClient
        
        use_claude_primary = os.getenv("USE_CLAUDE_AS_PRIMARY", "").strip().lower() in ("1", "true", "yes")
        claude = ClaudeClient()
        openai_client = None
        try:
            openai_client = OpenAIClient()
        except Exception:
            pass
        
        self.fallbacks = []
        if use_claude_primary and claude.enabled:
            self.primary = claude
            self._primary_name = "Claude"
            if openai_client:
                self.fallbacks.append(("OpenAI", openai_client))
            gemini = GeminiClient()
            if gemini.enabled:
                self.fallbacks.append(("Gemini", gemini))
        elif openai_client:
            self.primary = openai_client
            self._primary_name = "OpenAI"
            if claude.enabled:
                self.fallbacks.append(("Claude", claude))
            gemini = GeminiClient()
            if gemini.enabled:
                self.fallbacks.append(("Gemini", gemini))
        elif claude.enabled:
            self.primary = claude
            self._primary_name = "Claude"
            gemini = GeminiClient()
            if gemini.enabled:
                self.fallbacks.append(("Gemini", gemini))
        else:
            raise ValueError(
                "No LLM available. Set OPENAI_API_KEY or ANTHROPIC_API_KEY (and optionally USE_CLAUDE_AS_PRIMARY=true) in .env"
            )
    
    def generate_with_fallback(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate with automatic fallback to secondary providers."""
        try:
            result = self.primary.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
        except Exception as e:
            try:
                from utils.traceback_capture import write_traceback
                write_traceback(e)
            except Exception:
                pass
            raise
        result = result if (result is not None and isinstance(result, dict)) else {}
        if result.get("success"):
            result["provider"] = self._primary_name
            return result

        for name, client in self.fallbacks:
            logger.info(f"Falling back to {name}")
            try:
                result = client.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
            except Exception as e:
                try:
                    from utils.traceback_capture import write_traceback
                    write_traceback(e)
                except Exception:
                    pass
                raise
            result = result if (result is not None and isinstance(result, dict)) else {}
            if result.get("success"):
                result["provider"] = name
                return result

        # All failed
        return {
            "success": False,
            "error": "all_providers_failed",
            "message": "All LLM providers failed. Please check API keys and network connection."
        }
