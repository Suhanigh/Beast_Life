"""Cloudflare AI image generation provider."""
import os
import requests
from typing import Optional
from app.config import config


class CloudflareImageGenerator:
    """Cloudflare AI image generation using Workers AI."""
    
    def __init__(self):
        """Initialize Cloudflare image generator."""
        self.account_id = config.CLOUDFLARE_ACCOUNT_ID
        self.api_key = config.CLOUDFLARE_API_KEY
        self.base_url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/ai/run"
        
        if not self.account_id or not self.api_key:
            raise ValueError("Cloudflare credentials not configured")
    
    def generate_image(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        model: str = "@cf/stabilityai/stable-diffusion-xl-base-1.0"
    ) -> bytes:
        """
        Generate an image using Cloudflare AI.
        
        Args:
            prompt: Text prompt for image generation
            width: Image width in pixels
            height: Image height in pixels
            model: Cloudflare AI model to use
            
        Returns:
            Image data as bytes
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "prompt": prompt,
            "width": width,
            "height": height
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/{model}",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code != 200:
                error_msg = f"Cloudflare API error: {response.status_code} - {response.text}"
                print(f"✗ {error_msg}")
                raise Exception(error_msg)
            
            # Check content type to determine response format
            content_type = response.headers.get('content-type', '')
            
            if content_type.startswith('image/'):
                # Direct image response
                print("✓ Cloudflare returned direct image response")
                return response.content
            else:
                # Try to parse as JSON
                try:
                    result = response.json()
                    if "result" in result and "image" in result["result"]:
                        import base64
                        return base64.b64decode(result["result"]["image"])
                    else:
                        raise Exception(f"Unexpected response format: {result}")
                except ValueError as e:
                    raise Exception(f"JSON parsing failed: {e}")
                
        except requests.Timeout:
            raise Exception("Cloudflare API timeout")
        except Exception as e:
            raise Exception(f"Cloudflare image generation failed: {str(e)}")
    
    def is_available(self) -> bool:
        """Check if Cloudflare credentials are configured."""
        return bool(self.account_id and self.api_key)


def get_image_generator():
    """Factory function to get image generator."""
    try:
        return CloudflareImageGenerator()
    except ValueError:
        return None