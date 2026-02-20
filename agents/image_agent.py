"""Image Generation Agent: Crafts high-quality DALL-E 3 prompts and manages visual creation."""

import logging
from typing import Dict, Any, Optional
from integrations.image_client import ImageGenerationClient
from integrations.fallback_clients import LLMOrchestrator

logger = logging.getLogger(__name__)


class ImageGenerationAgent:
    """Crafts high-quality DALL-E 3 prompts and manages visual creation."""
    
    def __init__(self):
        self.image_client = ImageGenerationClient()
        self.llm = LLMOrchestrator()
    
    def craft_prompt(
        self,
        topic: str,
        style: str = "professional",
        context: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Craft an optimized DALL-E 3 prompt for image generation."""
        system_prompt = """You are an expert at crafting DALL-E 3 prompts for high-definition, professional images. Your prompts must:
1. Define one clear subject or viewpoint so the image has a single, easy-to-understand focus.
2. Specify composition: e.g. "centered", "clean background", "professional setting" so the result is clear and not cluttered.
3. Include quality cues: "high resolution", "sharp focus", "professional lighting", "clear and readable".
4. Describe style and mood: e.g. "modern", "professional", "inspiring" — avoid vague or abstract wording.
5. Keep the scene appropriate and suitable for professional or educational use.

Goal: A high-definition image with a clear viewpoint on the topic that anyone (including students) can understand at a glance. Return ONLY the prompt text, no explanation."""
        
        style_guidelines = {
            "professional": "professional business style, clean and modern",
            "creative": "creative and artistic, vibrant colors",
            "minimalist": "minimalist design, clean lines, simple composition",
            "realistic": "photorealistic, high detail, natural lighting",
            "illustration": "illustration style, vibrant, engaging"
        }
        
        style_desc = style_guidelines.get(style.lower(), style_guidelines["professional"])
        
        prompt = f"""Topic: {topic}
Style: {style} ({style_desc})

{f'Context: {context}' if context else ''}

Create a detailed, effective DALL-E 3 prompt for generating an image:"""
        
        result = self.llm.generate_with_fallback(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=300
        )
        result = result or {}
        if not result.get("success"):
            crafted_prompt = f"A professional {style} illustration of {topic}, high quality, detailed, modern design"
            return {
                "success": True,
                "prompt": crafted_prompt,
                "method": "fallback"
            }
        crafted_prompt = (result.get("content") or "").strip().strip('"').strip("'")
        
        return {
            "success": True,
            "prompt": crafted_prompt,
            "method": "llm_generated",
            "provider": result.get("provider", "Unknown")
        }
    
    def generate_image(
        self,
        topic: str,
        style: str = "professional",
        size: str = "1024x1024",
        quality: str = "standard",
        context: Optional[str] = None,
        use_crafted_prompt: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate an image using DALL-E 3. Supports HD (quality='hd') and larger sizes for clear, high-definition visuals."""
        topic = (topic or "").strip()
        if not topic:
            return {
                "success": False,
                "error": "empty_topic",
                "message": "Image topic cannot be empty. Please provide a subject or description."
            }
        # Craft the prompt if requested
        if use_crafted_prompt:
            prompt_result = self.craft_prompt(
                topic=topic,
                style=style,
                context=context,
                **kwargs
            )
            
            prompt_result = prompt_result or {}
            if prompt_result.get("success"):
                prompt = (prompt_result.get("prompt") or topic).strip()
            else:
                # Fallback to simple prompt
                prompt = f"A professional {style} illustration of {topic}, high quality, detailed"
            if not prompt:
                prompt = f"A professional {style} illustration of {topic}, high quality, detailed"
        else:
            prompt = topic
        
        # Generate the image
        image_result = self.image_client.generate_image(
            prompt=prompt,
            size=size,
            quality=quality,
            style="vivid"  # DALL-E 3 style option
        )
        
        image_result = image_result or {}
        if not image_result.get("success"):
            return {
                "success": False,
                "error": image_result.get("error", "generation_failed"),
                "message": image_result.get("message", "Failed to generate image")
            }
        return {
            "success": True,
            "image_url": image_result.get("image_url") or "",
            "prompt_used": prompt,
            "revised_prompt": image_result.get("revised_prompt"),
            "size": size,
            "quality": quality,
            "style": style
        }
    
    def refine_image_prompt(
        self,
        original_prompt: str,
        feedback: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Refine an image generation prompt based on feedback."""
        system_prompt = """You are an expert at refining DALL-E 3 prompts. Improve the prompt based on feedback. Keep one clear subject or viewpoint, high-definition quality, and a composition that is easy to understand at a glance."""
        
        prompt = f"""Original Prompt: {original_prompt}

Feedback: {feedback}

Create an improved version of the prompt:"""
        
        result = self.llm.generate_with_fallback(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=300
        )
        result = result or {}
        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error", "refinement_failed"),
                "message": result.get("message", "Failed to refine prompt")
            }
        refined_prompt = (result.get("content") or "").strip().strip('"').strip("'")
        
        return {
            "success": True,
            "refined_prompt": refined_prompt,
            "original_prompt": original_prompt,
            "feedback": feedback,
            "provider": result.get("provider", "Unknown")
        }
