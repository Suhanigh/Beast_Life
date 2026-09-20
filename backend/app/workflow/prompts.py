"""Workflow prompts for creative spec generation."""

# Creative spec generation prompt
CREATIVE_SPEC_PROMPT = """
You are a creative director for marketing campaigns. Convert the selected research angle into a detailed creative specification.

## Input
- Angle: {angle}
- Product: {product_name}
- Description: {product_description}
- CTA: {cta}
- Verified Claims: {verified_claims}
- Tone: {tone}

## Output Requirements
Generate a CreativeSpec with:
- hook: Compelling opening hook from the angle
- approved_headline: Clear headline for ads
- approved_body_copy: Optional supporting copy
- call_to_action: The provided CTA
- product_identity: Product name, allowed claims from verified_claims only
- scene_description: Visual scene based on angle's visual_direction
- palette: 3-5 hex colors matching the tone
- composition_1x1: Layout guidance for 1:1 format (safe zones, text placement)
- composition_9x16: Layout guidance for 9:16 format (safe zones, text placement, keep clear of top/bottom ~250px)
- video_outline: Beats with timings totaling 6-10s (target 8s):
  * 0-2.5s: Opening hook
  * 2.5-6s: Motion on scene + product
  * 6-8s: Ending CTA card

## Validation Rules
- Only use facts from the brief or verified_claims
- Do not invent numbers, percentages, discounts, or certification words
- Headline and body copy must be factual
- Video timing must total 6-10 seconds
"""

# Scene generation prompt
SCENE_GENERATION_PROMPT = """
Generate a scene description for creative assets based on the creative spec.

## Input
- Creative Spec: {spec}

## Output
Generate a detailed scene description that can be used for both images and video:
- Background description
- Lighting
- Product placement
- Key visual elements
- Color usage from the palette
"""

# Image generation prompt for 1:1 format
IMAGE_1X1_PROMPT = """
Generate layout instructions for a 1:1 square image ad.

## Input
- Creative Spec: {spec}
- Scene: {scene}

## Output
Detailed layout instructions:
- Product placement coordinates
- Text placement (headline, CTA)
- Safe zones
- Visual hierarchy
- Background treatment
"""

# Image generation prompt for 9:16 format
IMAGE_9X16_PROMPT = """
Generate layout instructions for a 9:16 vertical image ad.

## Input
- Creative Spec: {spec}
- Scene: {scene}

## Output
Detailed layout instructions:
- Product placement coordinates
- Text placement (headline, CTA) - keep clear of top/bottom ~250px
- Safe zones
- Visual hierarchy
- Background treatment
- Vertical composition guidance
"""

# Video generation prompt
VIDEO_GENERATION_PROMPT = """
Generate FFmpeg instructions for a 6-10s vertical video ad.

## Input
- Creative Spec: {spec}
- Scene: {scene}

## Output
FFmpeg command structure:
- Input parameters
- Video filters (fade, zoom, pan)
- Text overlays (headline, CTA with timing)
- Output parameters (1080x1920, 30fps, H.264 yuv420p, +faststart)
- Timing breakdown
"""
