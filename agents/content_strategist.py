"""Content Strategist: Organizes research into structured, readable formats."""

import logging
from typing import Dict, Any, Optional, List
from integrations.fallback_clients import LLMOrchestrator

logger = logging.getLogger(__name__)


class ContentStrategist:
    """Organizes research into structured, readable formats."""
    
    def __init__(self):
        self.llm = LLMOrchestrator()
    
    def create_content_outline(
        self,
        topic: str,
        research_data: Optional[Dict[str, Any]] = None,
        content_type: str = "blog",
        **kwargs
    ) -> Dict[str, Any]:
        """Create a structured content outline from research."""
        research_context = ""
        if research_data and research_data.get("success"):
            research_context = research_data.get("research_summary", "")
        
        system_prompt = f"""You are a content strategist. Create a simple, step-by-step outline for a {content_type} so a student can follow it easily. Use clear headings and a logical flow.

The outline must include:
1. Main sections with clear, descriptive headings (what each part is about).
2. Key points under each section — short bullets, one idea per line.
3. Where to add examples or data (note "example here" or "statistic here").
4. A clear order: Step 1 → Step 2 → Step 3 so the reader never gets lost.
5. A defined ending: conclusion and/or call-to-action.

Format as a simple hierarchical outline:
- Main sections (I, II, III... or Step 1, Step 2...)
- Subsections (A, B, C...)
- Key points (short bullet list)

Keep language simple and avoid jargon."""
        
        research_section = ""
        if research_context:
            research_section = f"\n\nResearch Summary:\n{research_context}\n\nUse this research to inform the outline structure."
        
        prompt = f"""Topic: {topic}
Content Type: {content_type}
{research_section}

Create a comprehensive content outline:"""
        
        result = self.llm.generate_with_fallback(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.6,
            max_tokens=2000
        )
        result = result or {}
        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error", "outline_failed"),
                "message": result.get("message", "Failed to create outline")
            }
        return {
            "success": True,
            "outline": result.get("content") or "",
            "topic": topic,
            "content_type": content_type,
            "provider": result.get("provider", "Unknown")
        }
    
    def organize_research(
        self,
        research_data: Dict[str, Any],
        format: str = "structured"
    ) -> Dict[str, Any]:
        """Organize raw research into a structured format."""
        research_data = research_data or {}
        if not research_data.get("success"):
            return {
                "success": False,
                "error": "invalid_research",
                "message": "Invalid research data provided"
            }
        
        research_summary = research_data.get("research_summary", "")
        sources = research_data.get("sources", [])
        
        if format == "structured":
            system_prompt = """Organize research into a clear, structured format with:
1. Executive Summary
2. Key Findings (bullet points)
3. Data and Statistics
4. Expert Insights
5. Sources and Citations

Make it easy to scan and reference."""
            
            prompt = f"""Research Data:

{research_summary}

Organize this research into a structured format:"""
            
            result = self.llm.generate_with_fallback(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.5,
                max_tokens=2000
            )
            result = result or {}
            if result.get("success"):
                organized_content = result.get("content") or research_summary
            else:
                organized_content = research_summary
        else:
            organized_content = research_summary
            result = {}
        return {
            "success": True,
            "organized_content": organized_content,
            "sources": sources,
            "format": format,
            "provider": result.get("provider", "Unknown") if format == "structured" else None
        }
    
    def create_content_brief(
        self,
        topic: str,
        requirements: Optional[Dict[str, Any]] = None,
        research_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a comprehensive content brief for content creation."""
        requirements = requirements or {}
        research_context = ""
        
        if research_data and research_data.get("success"):
            research_context = research_data.get("research_summary", "")[:500]
        
        system_prompt = """Create a simple, step-by-step content brief that a student or newcomer can follow. Use clear headings and short sentences. Base it on current content and SEO trends (E-E-A-T, clarity, structure).

The brief must include:
1. **Objective** — In one sentence: what we want this content to achieve.
2. **Target Audience** — Who is it for? (simple description).
3. **Key Messages** — 3–5 main points, each in one line.
4. **Tone and Style** — How it should sound (e.g. friendly, professional, educational).
5. **Content Structure** — Step-by-step outline: what comes first, second, third (like a simple roadmap).
6. **SEO Considerations** — Main keywords and where to use them (title, headings, first paragraph).
7. **Success Metrics** — How we’ll know it worked (e.g. reads, shares, time on page).

Keep language simple and avoid jargon. Use bullet points and short paragraphs."""
        
        prompt = f"""Topic: {topic}

Requirements:
- Tone: {requirements.get('tone', 'professional')}
- Audience: {requirements.get('target_audience', 'general')}
- Keywords: {requirements.get('keywords', [])}

{f'Research Context: {research_context}' if research_context else ''}

Create a comprehensive content brief:"""
        
        result = self.llm.generate_with_fallback(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.6,
            max_tokens=2000
        )
        
        result = result or {}
        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error", "brief_failed"),
                "message": result.get("message", "Failed to create content brief")
            }
        return {
            "success": True,
            "brief": result.get("content") or "",
            "topic": topic,
            "requirements": requirements,
            "provider": result.get("provider", "Unknown")
        }

    def refine_brief(
        self,
        brief: str,
        feedback: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Refine the content strategy brief based on user feedback (modify, rectify, expand, etc.)."""
        brief = brief or ""
        if not brief.strip():
            return {
                "success": False,
                "error": "empty_brief",
                "message": "No brief content to refine."
            }
        system_prompt = """You are a content strategist. Revise the content brief based on the user's feedback. Apply the requested changes (modify, rectify, add, remove, reorder, simplify, expand) while keeping the brief clear and actionable. Return the full revised brief."""
        prompt = f"""Current content brief:

{brief}

User feedback / requested changes: {feedback}

Revise the brief according to the feedback. Return the complete revised brief:"""
        result = self.llm.generate_with_fallback(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.6,
            max_tokens=2000
        )
        result = result or {}
        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error", "refinement_failed"),
                "message": result.get("message", "Failed to refine brief")
            }
        return {
            "success": True,
            "brief": result.get("content") or brief,
            "refinements": feedback,
            "provider": result.get("provider", "Unknown")
        }
    
    def analyze_content_quality(
        self,
        content: str,
        requirements: Optional[Dict[str, Any]] = None,
        content_type: str = "blog"
    ) -> Dict[str, Any]:
        """Analyze content quality and provide scoring."""
        requirements = requirements if isinstance(requirements, dict) else {}
        content = content or ""

        system_prompt = """Analyze content quality based on:
1. Clarity and readability
2. Structure and organization
3. SEO optimization
4. Engagement potential
5. Brand voice alignment

Provide scores (0-10) and brief feedback for each category."""
        
        prompt = f"""Content Type: {content_type}
Requirements: {requirements}

Content to Analyze:

{content[:3000]}

Analyze the content quality:"""
        
        result = self.llm.generate_with_fallback(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.5,
            max_tokens=1000
        )
        result = result if (result is not None and isinstance(result, dict)) else {}
        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error", "analysis_failed"),
                "message": result.get("message", "Failed to analyze content")
            }
        analysis_text = (result.get("content") or "").lower()
        scores = {
            "clarity": 7.0,
            "structure": 7.0,
            "seo": 7.0,
            "engagement": 7.0,
            "brand_voice": 7.0
        }
        
        # Simple scoring extraction (can be improved)
        for key in scores.keys():
            if key in analysis_text:
                # Try to find score near the keyword
                import re
                pattern = rf"{key}.*?(\d+\.?\d*)"
                match = re.search(pattern, analysis_text)
                if match:
                    try:
                        scores[key] = float(match.group(1))
                    except:
                        pass
        
        overall_score = sum(scores.values()) / len(scores)
        
        return {
            "success": True,
            "scores": scores,
            "overall_score": overall_score,
            "analysis": result.get("content") or "",
            "provider": result.get("provider", "Unknown")
        }
