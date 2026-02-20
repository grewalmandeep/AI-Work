"""Query Handler: Routes user intent to the correct workflow."""

import logging
from typing import Dict, Any, List, Optional
from integrations.fallback_clients import LLMOrchestrator

logger = logging.getLogger(__name__)


class QueryHandler:
    """Routes user intent to the correct workflow."""
    
    def __init__(self):
        self.llm = LLMOrchestrator()
        self.intent_map = {
            "blog": ["blog", "article", "post", "long-form", "seo"],
            "linkedin": ["linkedin", "social", "post", "professional"],
            "research": ["research", "investigate", "find", "search", "study"],
            "image": ["image", "picture", "visual", "art", "illustration"],
            "strategy": ["strategy", "plan", "outline", "organize", "structure"]
        }
    
    def classify_intent(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Classify user intent and route to appropriate workflow."""
        system_prompt = """You are an intent classification system. Analyze the user's query and classify it into one of these categories (match ContentAlchemy's "What do you want to do?" options):
- blog: SEO-optimized blog posts, articles, long-form content
- linkedin: Engaging LinkedIn posts, professional social posts
- research: Research, find information, investigate a topic
- image: High-quality images, visuals, illustrations
- strategy: Content strategies, plans, outlines, organization

Respond with ONLY the category name in lowercase."""
        
        prompt = f"User query: {query}\n\nClassify the intent:"
        
        if context and isinstance(context, dict):
            prompt += f"\n\nContext: {context.get('previous_intent', 'N/A')}"
        
        result = self.llm.generate_with_fallback(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=50
        )
        result = result if (result is not None and isinstance(result, dict)) else {}
        if not result.get("success"):
            # Fallback to keyword matching
            intent = self._fallback_classify(query)
            return {
                "intent": intent,
                "confidence": 0.5,
                "method": "keyword_fallback"
            }
        intent = (result.get("content") or "").strip().lower()
        
        # Validate intent
        if intent not in ["blog", "linkedin", "research", "image", "strategy"]:
            intent = self._fallback_classify(query)
            return {
                "intent": intent,
                "confidence": 0.6,
                "method": "fallback_validation"
            }
        
        return {
            "intent": intent,
            "confidence": 0.9,
            "method": "llm_classification"
        }
    
    def _fallback_classify(self, query: str) -> str:
        """Fallback keyword-based classification."""
        query_lower = query.lower()
        
        # Count matches for each intent
        scores = {}
        for intent, keywords in self.intent_map.items():
            scores[intent] = sum(1 for keyword in keywords if keyword in query_lower)
        
        # Return intent with highest score, default to blog
        max_score = max(scores.values())
        if max_score == 0:
            return "blog"  # Default
        
        for intent, score in scores.items():
            if score == max_score:
                return intent
        
        return "blog"
    
    def should_conduct_research(self, query: str, intent: str) -> bool:
        """Determine if research should be conducted before content generation."""
        research_keywords = [
            "research", "find", "investigate", "learn about", "information about",
            "facts about", "statistics", "data", "latest", "current", "trends"
        ]
        
        query_lower = query.lower()
        has_research_keywords = any(keyword in query_lower for keyword in research_keywords)
        
        # Always conduct research for research intent
        if intent == "research":
            return True
        
        # For blog posts, research if keywords present
        if intent == "blog" and has_research_keywords:
            return True
        
        return False
    
    def extract_content_requirements(
        self,
        query: str,
        intent: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Extract specific requirements from user query."""
        requirements = {
            "topic": "",
            "tone": "professional",
            "length": "medium",
            "target_audience": "general",
            "keywords": [],
            "style": "informative"
        }
        
        system_prompt = """Extract content requirements from the user query. Return a JSON object with:
- topic: The main topic or subject
- tone: professional, casual, friendly, formal
- length: short, medium, long
- target_audience: general audience description
- keywords: list of important keywords
- style: informative, persuasive, educational, etc.

Return ONLY valid JSON, no additional text."""
        
        prompt = f"""Query: {query}
Intent: {intent}

Extract requirements:"""
        
        result = self.llm.generate_with_fallback(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=300
        )
        result = result if (result is not None and isinstance(result, dict)) else {}
        if result.get("success") and result.get("content"):
            try:
                import json
                raw = (result.get("content") or "").strip()
                if raw:
                    extracted = json.loads(raw)
                    if isinstance(extracted, dict):
                        requirements.update(extracted)
            except Exception:
                logger.warning("Failed to parse extracted requirements, using defaults")
        return requirements
