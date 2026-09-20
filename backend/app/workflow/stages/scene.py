"""Scene generation stage."""
import json
from typing import Dict, Any
from sqlmodel import Session

from app.models import Campaign
from app.workflow.prompts import SCENE_GENERATION_PROMPT


def generate_scene(session: Session, campaign: Campaign, spec: Dict[str, Any]) -> Dict[str, Any]:
    """Generate scene description from creative spec."""
    # Build prompt
    prompt = SCENE_GENERATION_PROMPT.format(
        spec=json.dumps(spec)
    )
    
    # Mock scene generation
    scene = {
        "background": spec.get("scene_description", ""),
        "lighting": "Bright, energetic lighting matching practical tone",
        "product_placement": "Center stage, prominent but natural",
        "key_elements": ["Protein powder container", "Active lifestyle elements", "Clean aesthetic"],
        "color_usage": spec.get("palette", ["#ffffff", "#000000"]),
        "mood": "Energetic and practical"
    }
    
    return scene
