"""Image compositor using Pillow for deterministic image generation."""
import os
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Any, Tuple, Optional
import json
import requests
import io
import textwrap


class ImageCompositor:
    """Deterministic image compositor using Pillow."""
    
    def __init__(self, asset_dir: str = None):
        """Initialize compositor with asset directory."""
        from app.config import config
        self.asset_dir = asset_dir or config.ASSET_DIR
        os.makedirs(self.asset_dir, exist_ok=True)
        
        # Load bundled fonts (simulated for now)
        self.fonts = {
            "headline": self._get_default_font(48),
            "body": self._get_default_font(24),
            "cta": self._get_default_font(32)
        }
        
        # Try to load AI image generator
        self.image_generator = None
        self.scene_source = "procedural"  # Default to procedural
        self.fallback_reason = None
        try:
            from app.providers.image_generator import get_image_generator
            self.image_generator = get_image_generator()
            if self.image_generator and self.image_generator.is_available():
                print("✓ Cloudflare AI image generator loaded successfully")
                self.scene_source = "cloudflare"
            else:
                print("✗ Cloudflare AI generator not available - will use procedural fallback")
                self.fallback_reason = "AI generator not available"
        except Exception as e:
            print(f"✗ AI image generator initialization failed: {e}")
            self.fallback_reason = f"Initialization error: {str(e)}"
    
    def _get_default_font(self, size: int) -> ImageFont.ImageFont:
        """Get default font (using system font for now)."""
        try:
            # Try common system fonts
            font_paths = [
                "/System/Library/Fonts/Helvetica.ttc",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "arial.ttf",
                "/Windows/Fonts/arial.ttf"
            ]
            for font_path in font_paths:
                if os.path.exists(font_path):
                    return ImageFont.truetype(font_path, size)
        except:
            pass
        return ImageFont.load_default()
    
    def _generate_ai_image(self, prompt: str, width: int, height: int) -> Optional[Image.Image]:
        """Generate image using Cloudflare AI if available."""
        if not self.image_generator:
            print(f"✗ AI generation skipped: No image generator available")
            return None
        
        try:
            print(f"→ Attempting Cloudflare AI generation for {width}x{height} image")
            print(f"  Prompt: {prompt[:100]}...")
            
            # Add delay to avoid rate limiting
            import time
            time.sleep(2)
            
            image_data = self.image_generator.generate_image(prompt, width, height)
            img = Image.open(io.BytesIO(image_data))
            print(f"✓ Cloudflare AI generation successful")
            return img
        except Exception as e:
            print(f"✗ AI image generation failed: {e}")
            self.fallback_reason = f"AI generation failed: {str(e)}"
            return None
    
    def generate_image_1x1(
        self,
        spec: Dict[str, Any],
        scene: Dict[str, Any],
        packshot_path: str = None,
        output_path: str = None
    ) -> Tuple[str, str, Optional[str]]:  # Returns (path, scene_source, fallback_reason)
        """Generate 1080x1080 square image."""
        scene_source = self.scene_source
        fallback_reason = self.fallback_reason
        
        # Try AI generation first with highly product-specific prompt
        product_name = spec.get('product_identity', {}).get('name', 'product')
        headline = spec.get('approved_headline', '')
        scene_desc = spec.get('scene_description', '')
        body_copy = spec.get('approved_body_copy', '')
        objective = spec.get('product_identity', {}).get('name', '')
        
        # Extract verified claims for product-specific details
        product_claims = spec.get('product_identity', {}).get('allowed_claims', [])
        claims_text = ' '.join(product_claims) if product_claims else ''
        
        # Build highly specific product prompt with industry cues
        if 'protein' in product_name.lower() or 'supplement' in product_name.lower():
            industry_style = "fitness product photography, gym setting, athletic lifestyle, protein powder container, nutritional supplement packaging, sports nutrition branding"
        elif 'food' in product_name.lower() or 'beverage' in product_name.lower():
            industry_style = "food product photography, appetizing presentation, food styling, culinary packaging, restaurant quality lighting"
        elif 'tech' in product_name.lower() or 'software' in product_name.lower():
            industry_style = "technology product photography, modern tech aesthetic, clean UI, device photography, software branding"
        else:
            industry_style = "professional product photography, commercial lighting, studio setup, advertising photography"
        
        ai_prompt = f"Professional product advertisement for {product_name}. {headline}. {scene_desc}. {body_copy}. {claims_text}. {industry_style}. Show the actual product package/container clearly. Product-focused composition. High-quality commercial photography with studio lighting. Professional advertising photography. Branded product shot."
        
        ai_image = self._generate_ai_image(ai_prompt, 1080, 1080)
        
        if ai_image:
            # Use AI-generated image
            img = ai_image
            scene_source = "cloudflare"
            fallback_reason = None
        else:
            # Fallback to improved procedural generation
            print("→ Using procedural fallback generation")
            img = self._generate_procedural_image_1x1(spec, scene, packshot_path)
            scene_source = "procedural"
            if not fallback_reason:
                fallback_reason = "AI generation unavailable"
        
        # Save
        if not output_path:
            output_path = os.path.join(self.asset_dir, f"image_1x1_{spec['spec_id']}.png")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        img.save(output_path, 'PNG')
        print(f"✓ Saved image to {output_path} (source: {scene_source})")
        return output_path, scene_source, fallback_reason
    
    def _generate_procedural_image_1x1(self, spec: Dict[str, Any], scene: Dict[str, Any], packshot_path: str = None) -> Image.Image:
        """Generate improved procedural 1x1 image."""
        img = Image.new('RGB', (1080, 1080), color=spec['palette'][0])
        draw = ImageDraw.Draw(img)
        
        # Draw gradient background
        self._draw_gradient(draw, img.size, spec['palette'])
        
        # Generate product packshot
        packshot = self._generate_product_packshot(spec['product_identity']['name'], (400, 400))
        img.paste(packshot, (340, 340), packshot)
        
        # Draw headline with shadow
        headline = spec.get('approved_headline', '')
        if headline:
            self._draw_text_with_shadow(draw, headline, self.fonts['headline'], 
                                      (50, 50, 1030, 300), spec['palette'][4], spec['palette'][0])
        
        # Draw CTA as filled pill
        cta = spec.get('call_to_action', '')
        if cta:
            self._draw_cta_pill(draw, cta, self.fonts['cta'], 
                              (50, 850, 1030, 950), spec['palette'][3], spec['palette'][0])
        
        return img
    
    def _generate_product_packshot(self, product_name: str, size: Tuple[int, int]) -> Image.Image:
        """Generate a product packshot with transparent background."""
        img = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Draw rounded rectangle background
        margin = 20
        rect = [
            margin, margin, 
            size[0] - margin, size[1] - margin
        ]
        
        # Draw semi-transparent white background
        draw.rounded_rectangle(rect, radius=20, fill=(255, 255, 255, 200))
        
        # Draw product name
        font = self._get_default_font(24)
        text_bbox = draw.textbbox((0, 0), product_name, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        # Center text
        x = (size[0] - text_width) // 2
        y = (size[1] - text_height) // 2
        draw.text((x, y), product_name, font=font, fill=(50, 50, 50, 255))
        
        return img
    
    def _draw_text_with_shadow(self, draw, text: str, font, bbox: Tuple[int, int, int, int], 
                            text_color: str, shadow_color: str):
        """Draw text with shadow for better contrast."""
        # Draw shadow offset
        shadow_offset = 3
        shadow_bbox = (bbox[0] + shadow_offset, bbox[1] + shadow_offset, 
                      bbox[2] + shadow_offset, bbox[3] + shadow_offset)
        self._draw_text_centered(draw, text, font, shadow_bbox, shadow_color)
        
        # Draw main text
        self._draw_text_centered(draw, text, font, bbox, text_color)
    
    def _draw_cta_pill(self, draw, text: str, font, bbox: Tuple[int, int, int, int],
                      bg_color: str, text_color: str):
        """Draw CTA as a filled pill shape."""
        # Draw pill background
        pill_height = bbox[3] - bbox[1]
        pill_radius = pill_height // 2
        draw.rounded_rectangle(bbox, radius=pill_radius, fill=bg_color)
        
        # Draw centered text
        self._draw_text_centered(draw, text, font, bbox, text_color)
    
    def generate_image_9x16(
        self,
        spec: Dict[str, Any],
        scene: Dict[str, Any],
        packshot_path: str = None,
        output_path: str = None
    ) -> Tuple[str, str, Optional[str]]:  # Returns (path, scene_source, fallback_reason)
        """Generate 1080x1920 vertical image."""
        scene_source = self.scene_source
        fallback_reason = self.fallback_reason
        
        # Try AI generation first with highly product-specific prompt
        product_name = spec.get('product_identity', {}).get('name', 'product')
        headline = spec.get('approved_headline', '')
        scene_desc = spec.get('scene_description', '')
        body_copy = spec.get('approved_body_copy', '')
        
        # Extract verified claims for product-specific details
        product_claims = spec.get('product_identity', {}).get('allowed_claims', [])
        claims_text = ' '.join(product_claims) if product_claims else ''
        
        # Build highly specific product prompt with industry cues
        if 'protein' in product_name.lower() or 'supplement' in product_name.lower():
            industry_style = "fitness product photography, gym setting, athletic lifestyle, protein powder container, nutritional supplement packaging, sports nutrition branding"
        elif 'food' in product_name.lower() or 'beverage' in product_name.lower():
            industry_style = "food product photography, appetizing presentation, food styling, culinary packaging, restaurant quality lighting"
        elif 'tech' in product_name.lower() or 'software' in product_name.lower():
            industry_style = "technology product photography, modern tech aesthetic, clean UI, device photography, software branding"
        else:
            industry_style = "professional product photography, commercial lighting, studio setup, advertising photography"
        
        # Create more product-specific prompt for vertical format
        ai_prompt = f"Professional product advertisement for {product_name}. {headline}. {scene_desc}. {body_copy}. {claims_text}. {industry_style}. Show the actual product package/container clearly. Product-focused composition. Vertical format for social media, mobile-first design. High-quality commercial photography with studio lighting. Professional advertising photography. Branded product shot."
        
        ai_image = self._generate_ai_image(ai_prompt, 1080, 1920)
        
        if ai_image:
            # Use AI-generated image
            img = ai_image
            scene_source = "cloudflare"
            fallback_reason = None
        else:
            # Fallback to improved procedural generation
            print("→ Using procedural fallback generation for 9x16")
            img = self._generate_procedural_image_9x16(spec, scene, packshot_path)
            scene_source = "procedural"
            if not fallback_reason:
                fallback_reason = "AI generation unavailable"
        
        # Save
        if not output_path:
            output_path = os.path.join(self.asset_dir, f"image_9x16_{spec['spec_id']}.png")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        img.save(output_path, 'PNG')
        print(f"✓ Saved 9x16 image to {output_path} (source: {scene_source})")
        return output_path, scene_source, fallback_reason
    
    def _generate_procedural_image_9x16(self, spec: Dict[str, Any], scene: Dict[str, Any], packshot_path: str = None) -> Image.Image:
        """Generate improved procedural 9x16 image with safe zones."""
        img = Image.new('RGB', (1080, 1920), color=spec['palette'][0])
        draw = ImageDraw.Draw(img)
        
        # Draw gradient background
        self._draw_gradient(draw, img.size, spec['palette'])
        
        # Safe zones (250px from top/bottom)
        safe_top = 250
        safe_bottom = 1920 - 250
        
        # Generate and place product packshot
        packshot = self._generate_product_packshot(spec['product_identity']['name'], (500, 500))
        img.paste(packshot, (290, 710), packshot)
        
        # Draw headline with shadow (below top safe zone)
        headline = spec.get('approved_headline', '')
        if headline:
            self._draw_text_with_shadow(draw, headline, self.fonts['headline'], 
                                      (50, safe_top, 1030, safe_top + 200), spec['palette'][4], spec['palette'][0])
        
        # Draw CTA as filled pill (above bottom safe zone)
        cta = spec.get('call_to_action', '')
        if cta:
            self._draw_cta_pill(draw, cta, self.fonts['cta'], 
                              (50, safe_bottom - 100, 1030, safe_bottom), spec['palette'][3], spec['palette'][0])
        
        return img
    
    def _draw_gradient(self, draw, size, colors):
        """Draw simple gradient background."""
        # Simplified gradient (just top-to-bottom fade)
        for i in range(size[1]):
            ratio = i / size[1]
            if len(colors) >= 2:
                r = int(int(colors[0][1:3], 16) * (1 - ratio) + int(colors[1][1:3], 16) * ratio)
                g = int(int(colors[0][3:5], 16) * (1 - ratio) + int(colors[1][3:5], 16) * ratio)
                b = int(int(colors[0][5:7], 16) * (1 - ratio) + int(colors[1][5:7], 16) * ratio)
                draw.rectangle([(0, i), (size[0], i + 1)], fill=(r, g, b))
    
    def _draw_placeholder_product(self, draw, coords):
        """Draw placeholder product box."""
        draw.rectangle(coords, outline=(255, 255, 255), width=3)
        draw.text((coords[0] + 10, coords[1] + 10), "PRODUCT", fill=(255, 255, 255))
    
    def _draw_text_centered(self, draw, text, font, coords, color):
        """Draw centered text within coordinates with automatic wrapping."""
        # Calculate max width
        max_width = coords[2] - coords[0] - 40  # 20px padding on each side
        
        # Wrap text if too long
        wrapped_lines = textwrap.wrap(text, width=20)  # Approximate character limit
        
        if not wrapped_lines:
            return
        
        # If text fits without wrapping, draw single line
        if len(wrapped_lines) == 1 and len(text) <= 30:
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            x = coords[0] + (coords[2] - coords[0] - text_width) // 2
            y = coords[1] + (coords[3] - coords[1] - text_height) // 2
            
            draw.text((x, y), text, font=font, fill=color)
        else:
            # Draw wrapped text, centered
            line_height = font.size * 1.2
            total_height = len(wrapped_lines) * line_height
            
            start_y = coords[1] + (coords[3] - coords[1] - total_height) // 2
            
            for i, line in enumerate(wrapped_lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                
                x = coords[0] + (coords[2] - coords[0] - text_width) // 2
                y = start_y + i * line_height
                
                draw.text((x, y), line, font=font, fill=color)


def get_compositor() -> ImageCompositor:
    """Factory function to get image compositor."""
    return ImageCompositor()
