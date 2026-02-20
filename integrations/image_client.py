"""DALL-E 3 client for image generation."""

import os
import logging
from typing import Optional, Dict, Any
from openai import OpenAI, APIError

logger = logging.getLogger(__name__)


class ImageGenerationClient:
    """Client for DALL-E 3 image generation."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found for image generation")
        self.client = OpenAI(api_key=self.api_key)
        self.model = "dall-e-3"
    
    def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        style: str = "vivid",
        n: int = 1
    ) -> Dict[str, Any]:
        """Generate image using DALL-E 3. Supports HD (quality='hd') and sizes 1024x1024, 1792x1024, 1024x1792."""
        try:
            prompt = (prompt or "").strip()
            if not prompt:
                return {
                    "success": False,
                    "error": "empty_prompt",
                    "message": "Image prompt cannot be empty. Please provide a topic or description."
                }
            # DALL-E 3 prompt length limit is 4000 chars
            if len(prompt) > 4000:
                prompt = prompt[:3997] + "..."
            # DALL-E 3: quality 'hd' for high-definition; sizes 1024x1024, 1792x1024, 1024x1792
            if size not in ("1024x1024", "1792x1024", "1024x1792"):
                size = "1024x1024"
            if quality not in ("standard", "hd"):
                quality = "standard"
            response = self.client.images.generate(
                model=self.model,
                prompt=prompt,
                size=size,
                quality=quality,
                style=style,
                n=n
            )
            
            image_url = response.data[0].url if response.data else None
            
            return {
                "success": True,
                "image_url": image_url,
                "revised_prompt": response.data[0].revised_prompt if response.data else None,
                "model": self.model
            }
        except APIError as e:
            logger.error(f"DALL-E API error: {e}")
            return {
                "success": False,
                "error": "api_error",
                "message": str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected image generation error: {e}")
            return {
                "success": False,
                "error": "unknown",
                "message": str(e)
            }
