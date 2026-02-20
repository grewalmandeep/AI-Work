"""Deep Research Agent: Uses SERP API and GPT to conduct web research with source attribution."""

import logging
from typing import Dict, Any, List, Optional
from integrations.serp_client import SERPClient
from integrations.fallback_clients import LLMOrchestrator

logger = logging.getLogger(__name__)


class DeepResearchAgent:
    """Conducts web research with source attribution."""
    
    def __init__(self):
        self.serp_client = SERPClient()
        self.llm = LLMOrchestrator()
    
    def conduct_research(
        self,
        topic: str,
        query: Optional[str] = None,
        num_results: int = 10,
        depth: str = "deep"
    ) -> Dict[str, Any]:
        """Conduct comprehensive research on a topic."""
        search_query = query or topic
        
        logger.info(f"Conducting research on: {search_query}")
        
        # Perform SERP search
        search_results = self.serp_client.search(
            query=search_query,
            num_results=num_results
        )
        search_results = search_results or {}
        if not search_results.get("success") or not search_results.get("results"):
            return {
                "success": False,
                "error": "search_failed",
                "message": "Failed to retrieve search results",
                "research_data": None,
                "sources": []
            }
        
        # Synthesize research using LLM
        formatted_results = self.serp_client.format_results_for_prompt(search_results.get("results") or [])
        
        system_prompt = """You are a research synthesis expert. Analyze the provided search results and create a comprehensive research summary with:
1. Key findings and insights
2. Important statistics and data points
3. Expert opinions and quotes
4. Trends and patterns
5. Gaps or areas needing more research

Always maintain source attribution. Format your response with clear sections and cite sources using [Source N] notation."""
        
        prompt = f"""Topic: {topic}

{formatted_results}

Synthesize this research into a comprehensive summary with source attribution:"""
        
        synthesis_result = self.llm.generate_with_fallback(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.5,
            max_tokens=2000
        )
        
        synthesis_result = synthesis_result or {}
        search_results = search_results or {}
        if not synthesis_result.get("success"):
            return {
                "success": False,
                "error": "synthesis_failed",
                "message": "Failed to synthesize research",
                "research_data": None,
                "sources": (search_results.get("results") or [])
            }
        raw_results = search_results.get("results") or []
        sources = [
            {"title": r.get("title", ""), "url": r.get("link", ""), "source": r.get("source", ""), "snippet": r.get("snippet", "")}
            for r in raw_results if isinstance(r, dict)
        ]
        return {
            "success": True,
            "topic": topic,
            "research_summary": synthesis_result.get("content") or "",
            "sources": sources,
            "raw_results": raw_results,
            "provider": synthesis_result.get("provider", "Unknown")
        }
    
    def generate_research_queries(self, topic: str, num_queries: int = 3) -> List[str]:
        """Generate multiple research queries for comprehensive coverage."""
        system_prompt = """Generate diverse search queries to comprehensively research a topic. Create queries that cover:
- Main topic overview
- Recent developments and trends
- Statistics and data
- Expert opinions

Return one query per line, no numbering."""
        
        prompt = f"""Topic: {topic}

Generate {num_queries} diverse research queries:"""
        
        result = self.llm.generate_with_fallback(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=200
        )
        
        result = result or {}
        if result.get("success"):
            raw = (result.get("content") or "").strip()
            if raw:
                queries = [q.strip() for q in raw.split("\n") if q.strip()]
                return queries[:num_queries]
        
        # Fallback to simple variations
        return [
            topic,
            f"{topic} trends 2024",
            f"{topic} statistics data"
        ]
    
    def multi_query_research(
        self,
        topic: str,
        num_queries: int = 3,
        results_per_query: int = 5
    ) -> Dict[str, Any]:
        """Conduct research using multiple queries for comprehensive coverage."""
        queries = self.generate_research_queries(topic, num_queries)
        
        all_results = []
        all_sources = []
        
        for query in queries:
            search_result = self.serp_client.search(
                query=query,
                num_results=results_per_query
            )
            
            if search_result["success"]:
                all_results.extend(search_result["results"])
                all_sources.extend([
                    {
                        "title": r["title"],
                        "url": r["link"],
                        "source": r["source"],
                        "snippet": r["snippet"]
                    }
                    for r in search_result["results"]
                ])
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_sources = []
        for source in all_sources:
            if source["url"] not in seen_urls:
                seen_urls.add(source["url"])
                unique_sources.append(source)
        
        # Synthesize all results
        if all_results:
            formatted_results = self.serp_client.format_results_for_prompt(all_results[:20])
            
            system_prompt = """You are a research synthesis expert. Create a comprehensive research summary from multiple search queries covering the same topic. Organize findings by themes and always cite sources using [Source N] notation."""
            
            prompt = f"""Topic: {topic}

Research results from multiple queries:

{formatted_results}

Create a comprehensive synthesis:"""
            
            synthesis_result = self.llm.generate_with_fallback(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.5,
                max_tokens=2500
            )
            synthesis_result = synthesis_result or {}
            if synthesis_result.get("success"):
                return {
                    "success": True,
                    "topic": topic,
                    "research_summary": synthesis_result.get("content") or "",
                    "sources": unique_sources,
                    "queries_used": queries,
                    "provider": synthesis_result.get("provider", "Unknown")
                }
        
        return {
            "success": False,
            "error": "research_failed",
            "message": "Failed to conduct multi-query research",
            "sources": unique_sources
        }
