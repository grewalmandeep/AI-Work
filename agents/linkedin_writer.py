"""LinkedIn Post Writer: Creates engaging professional social media posts with hashtag strategies."""

import logging
import re
from typing import Dict, Any, Optional, List
from integrations.fallback_clients import LLMOrchestrator

logger = logging.getLogger(__name__)


class LinkedInPostWriter:
    """Creates engaging LinkedIn posts with hashtag strategies."""
    
    def __init__(self):
        self.llm = LLMOrchestrator()
    
    def generate_post(
        self,
        topic: str,
        research_data: Optional[Dict[str, Any]] = None,
        requirements: Optional[Dict[str, Any]] = None,
        tone: str = "professional",
        post_type: str = "standard",
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a LinkedIn post with hashtags."""
        requirements = requirements or {}
        
        # LinkedIn post length guidelines
        post_lengths = {
            "short": 150,  # Quick thoughts
            "medium": 300,  # Standard post
            "long": 1300   # Article-style post
        }
        
        # Build context from research
        research_context = ""
        if research_data and research_data.get("success"):
            research_context = research_data.get("research_summary", "")
        
        system_prompt = f"""You are an expert LinkedIn content creator. Write in simple, human language so any professional or student can follow. Follow current trends: authenticity, storytelling, and clear value.

Your posts must:
1. Start with a strong, simple hook (one line that makes people stop scrolling).
2. Tell a short story or share one clear idea — keep it human and relatable, not corporate.
3. Use a simple step-by-step or list format when helpful (e.g. "Here are 3 things…", "Step 1… Step 2…").
4. Give one clear takeaway or call-to-action (e.g. "What would you add?" or "Try this first.").
5. Use line breaks every 1–2 sentences for mobile readability.
6. Include 5–10 relevant, trending hashtags at the end (on a new line).
7. Keep a {tone} tone and length suitable for {post_type} posts.
8. Sound like a real person, not a bot — avoid buzzwords and filler.

Format:
- Hook (first line)
- 2–4 short paragraphs or bullet points
- One clear CTA or question
- Hashtags on the last line"""
        
        research_section = ""
        if research_context:
            research_section = f"\n\nResearch Context:\n{research_context}\n\nUse insights from this research to inform your post."
        
        prompt = f"""Topic: {topic}

Post Type: {post_type}
Tone: {tone}
Target Audience: {requirements.get('target_audience', 'professional network')}
{research_section}

Create a compelling LinkedIn post:"""
        
        result = self.llm.generate_with_fallback(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.8,
            max_tokens=1500
        )
        if not result or not isinstance(result, dict):
            result = {}
        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error", "generation_failed"),
                "message": result.get("message", "Failed to generate LinkedIn post"),
                "content": None
            }
        content = result.get("content") or ""
        
        # Extract hashtags
        hashtags = self._extract_hashtags(content)
        
        # Ensure hashtags are present
        if not hashtags:
            hashtags = self._generate_hashtags(topic, content)
            content += f"\n\n{' '.join(hashtags)}"
        else:
            # Ensure hashtags are on a new line
            content_without_hashtags = re.sub(r'#\w+\s*', '', content).strip()
            content = f"{content_without_hashtags}\n\n{' '.join(hashtags)}"
        
        # Calculate engagement score (simple heuristic)
        engagement_score = self._calculate_engagement_score(content)
        
        return {
            "success": True,
            "content": content,
            "hashtags": hashtags,
            "character_count": len(content),
            "engagement_score": engagement_score,
            "post_type": post_type,
            "provider": result.get("provider", "Unknown")
        }
    
    def _extract_hashtags(self, content: str) -> List[str]:
        """Extract hashtags from content."""
        content = content or ""
        hashtags = re.findall(r'#\w+', content)
        # Remove duplicates while preserving order
        seen = set()
        unique_hashtags = []
        for tag in hashtags:
            if tag.lower() not in seen:
                seen.add(tag.lower())
                unique_hashtags.append(tag)
        return unique_hashtags[:10]  # Limit to 10
    
    def _generate_hashtags(
        self,
        topic: str,
        content: str,
        num_hashtags: int = 8
    ) -> List[str]:
        """Generate relevant hashtags for the post."""
        system_prompt = """Generate relevant LinkedIn hashtags for a post. Return hashtags separated by spaces, starting with #. Include a mix of:
- Broad industry tags
- Specific topic tags
- Trending professional tags

Return ONLY the hashtags, no explanation."""
        
        prompt = f"""Topic: {topic}

Post Content:
{content[:500]}

Generate {num_hashtags} relevant LinkedIn hashtags:"""
        
        result = self.llm.generate_with_fallback(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=100
        )
        
        if result["success"]:
            hashtags = self._extract_hashtags(result["content"])
            if hashtags:
                return hashtags[:num_hashtags]
        
        # Fallback hashtags
        return ["#LinkedIn", "#ProfessionalDevelopment", "#Business", "#Leadership", "#Networking"]
    
    def _calculate_engagement_score(self, content: str) -> float:
        """Calculate a simple engagement score based on content characteristics."""
        score = 5.0  # Base score
        
        # Bonus for questions
        if "?" in content:
            score += 1.0
        
        # Bonus for call-to-action words
        cta_words = ["share", "comment", "thoughts", "agree", "discuss", "learn"]
        if any(word.lower() in content.lower() for word in cta_words):
            score += 1.0
        
        # Bonus for numbers/statistics
        if re.search(r'\d+', content):
            score += 0.5
        
        # Bonus for proper length (250-1300 chars is sweet spot)
        char_count = len(content)
        if 250 <= char_count <= 1300:
            score += 1.0
        
        # Penalty for too long
        if char_count > 3000:
            score -= 1.0
        
        return min(10.0, max(0.0, score))
    
    def refine_post(
        self,
        content: str,
        feedback: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Refine LinkedIn post based on user feedback."""
        system_prompt = """You are a LinkedIn content editor. Refine the post based on feedback. Keep the tone human and simple, with a clear hook, short paragraphs, and one clear takeaway or CTA. Maintain engagement and professional tone."""
        
        prompt = f"""Original LinkedIn Post:

{content}

User Feedback: {feedback}

Refine the post according to the feedback:"""
        
        result = self.llm.generate_with_fallback(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.8,
            max_tokens=1500
        )
        result = result or {}
        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error", "refinement_failed"),
                "message": result.get("message", "Failed to refine post")
            }
        refined_content = result.get("content") or ""
        hashtags = self._extract_hashtags(refined_content)
        
        if not hashtags:
            hashtags = self._extract_hashtags(content)
            refined_content += f"\n\n{' '.join(hashtags)}"
        
        return {
            "success": True,
            "content": refined_content,
            "hashtags": hashtags,
            "refinements": feedback,
            "provider": result.get("provider", "Unknown")
        }
