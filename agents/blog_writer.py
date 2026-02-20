"""SEO Blog Writer: Generates long-form content optimized for search engines."""

import logging
from typing import Dict, Any, Optional, List
from integrations.fallback_clients import LLMOrchestrator

logger = logging.getLogger(__name__)


class SEOBlogWriter:
    """Generates long-form SEO-optimized blog content."""
    
    def __init__(self):
        self.llm = LLMOrchestrator()
    
    def generate_blog_post(
        self,
        topic: str,
        research_data: Optional[Dict[str, Any]] = None,
        requirements: Optional[Dict[str, Any]] = None,
        tone: str = "professional",
        length: str = "medium",
        target_keywords: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a complete SEO-optimized blog post."""
        requirements = requirements or {}
        target_keywords = target_keywords or []
        
        # Determine word count based on length
        word_counts = {
            "short": 800,
            "medium": 1500,
            "long": 2500
        }
        target_words = word_counts.get(length, 1500)
        
        # Build context from research
        research_context = ""
        sources = []
        if research_data and research_data.get("success"):
            research_context = research_data.get("research_summary", "")
            sources = research_data.get("sources", [])
        
        system_prompt = f"""You are an expert SEO content writer. Follow current best practices (E-E-A-T, featured snippets, clear structure) and write in simple, human language so even a student can understand. Use a step-by-step flow.

Your writing must:
1. Be simple and clear — short sentences, everyday words, no jargon unless explained.
2. Follow a clear step-by-step structure: Step 1, Step 2, etc., or numbered lists where it helps.
3. Include proper headings (H2, H3) so readers and search engines can scan easily.
4. Naturally use target keywords in titles and first paragraphs; aim for featured-snippet style answers.
5. Show experience and expertise (E-E-A-T) with concrete examples or brief explanations.
6. Use bullet points and short paragraphs (2–4 sentences) for readability.
7. Have a short introduction that states what the reader will learn, and a brief conclusion with one clear takeaway or call-to-action.
8. Be approximately {target_words} words and keep a {tone} tone throughout.

Format:
- One clear title (H1)
- Meta description (150–160 characters)
- Introduction (what we’ll cover)
- Sections with H2/H3 and step-by-step or numbered content
- Conclusion (summary + one next step)"""
        
        keyword_section = ""
        if target_keywords:
            keyword_section = f"\n\nTarget Keywords to naturally incorporate: {', '.join(target_keywords)}"
        
        research_section = ""
        if research_context:
            research_section = f"\n\nResearch Context:\n{research_context}\n\nUse this research to inform your content, but write in your own voice. Cite sources when using specific data or statistics."
        
        prompt = f"""Topic: {topic}

Audience: {requirements.get('target_audience', 'general audience')}
Tone: {tone}
Length: {length} (~{target_words} words)
{keyword_section}
{research_section}

Write a comprehensive, SEO-optimized blog post:"""
        
        result = self.llm.generate_with_fallback(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=4000
        )
        if not result or not isinstance(result, dict):
            result = {}
        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error", "generation_failed"),
                "message": result.get("message", "Failed to generate blog post"),
                "content": None
            }
        content = result.get("content") or ""
        title = self._extract_title(content)
        meta_description = self._extract_meta_description(content)
        
        return {
            "success": True,
            "title": title,
            "meta_description": meta_description,
            "content": content,
            "word_count": len((content or "").split()),
            "sources": sources,
            "keywords_used": target_keywords,
            "provider": result.get("provider", "Unknown")
        }
    
    def _extract_title(self, content: str) -> str:
        """Extract title from blog post content."""
        content = content or ""
        lines = content.split("\n")
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if line and (line.startswith("# ") or len(line) < 100):
                return line.replace("# ", "").strip()
        return "Blog Post Title"
    
    def _extract_meta_description(self, content: str) -> str:
        """Extract or generate meta description."""
        content = content or ""
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "meta description" in line.lower():
                if i + 1 < len(lines):
                    return lines[i + 1].strip()[:160]
        
        # Generate from first paragraph
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip() and not p.startswith("#")]
        if paragraphs:
            first_para = paragraphs[0][:160]
            return first_para
        
        return "A comprehensive guide on the topic."
    
    def refine_content(
        self,
        content: str,
        feedback: str,
        original_requirements: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Refine existing blog content based on user feedback."""
        system_prompt = """You are an expert content editor. Refine the blog post based on user feedback. Keep the content simple and human, with clear step-by-step structure and SEO best practices. Preserve readability so a student can understand it easily."""
        
        prompt = f"""Original Blog Post:

{content}

User Feedback: {feedback}

Refine the blog post according to the feedback:"""
        
        result = self.llm.generate_with_fallback(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=4000
        )
        result = result or {}
        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error", "refinement_failed"),
                "message": result.get("message", "Failed to refine content")
            }
        return {
            "success": True,
            "content": result.get("content") or "",
            "refinements": feedback,
            "provider": result.get("provider", "Unknown")
        }
