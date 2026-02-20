"""SERP API client for web research with source attribution."""

import os
import logging
from typing import Optional, Dict, Any, List
import requests

logger = logging.getLogger(__name__)


class SERPClient:
    """Client for SERP API to conduct web research."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SERP_API_KEY")
        if not self.api_key:
            logger.warning("SERP_API_KEY not found. Research functionality will be limited.")
        self.base_url = "https://serpapi.com/search"
    
    def search(
        self,
        query: str,
        num_results: int = 10,
        engine: str = "google",
        **kwargs
    ) -> Dict[str, Any]:
        """Perform web search and return results with source attribution."""
        if not self.api_key:
            return {
                "success": False,
                "error": "api_key_missing",
                "message": "SERP_API_KEY not configured",
                "results": []
            }
        
        try:
            params = {
                "q": query,
                "api_key": self.api_key,
                "engine": engine,
                "num": num_results,
                **kwargs
            }
            
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            data = data if isinstance(data, dict) else {}

            results = []
            for item in (data.get("organic_results") or [])[:num_results]:
                if not isinstance(item, dict):
                    continue
                results.append({
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "source": item.get("displayed_link", ""),
                    "position": item.get("position", 0)
                })
            
            return {
                "success": True,
                "query": query,
                "results": results,
                "total_results": len(results)
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"SERP API error: {e}")
            return {
                "success": False,
                "error": "request_error",
                "message": str(e),
                "results": []
            }
        except Exception as e:
            logger.error(f"Unexpected SERP error: {e}")
            return {
                "success": False,
                "error": "unknown",
                "message": str(e),
                "results": []
            }
    
    def format_results_for_prompt(self, results: List[Dict[str, Any]]) -> str:
        """Format search results into a prompt-friendly string with citations."""
        results = results or []
        if not results:
            return "No search results available."
        formatted = "Research Results:\n\n"
        for i, result in enumerate(results, 1):
            if not isinstance(result, dict):
                continue
            formatted += f"[{i}] {result.get('title', '')}\n"
            formatted += f"    Source: {result.get('source', '')} ({result.get('link', '')})\n"
            formatted += f"    {result.get('snippet', '')}\n\n"
        return formatted
