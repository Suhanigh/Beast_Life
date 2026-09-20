"""Creative spec generation stage."""
import json
import uuid
from typing import Dict, Any
from sqlmodel import Session, select

from app.models import Campaign, StageRun
from app.providers.llm import get_llm_client, LLMMessage
from app.workflow.prompts import CREATIVE_SPEC_PROMPT


def generate_spec(session: Session, campaign: Campaign, angle_id: int) -> Dict[str, Any]:
    """Generate creative spec from selected angle."""
    # Get research output
    from app.models import StageRun
    stage_run = session.exec(
        select(StageRun).where(
            StageRun.campaign_id == campaign.id,
            StageRun.stage == "research",
            StageRun.status == "succeeded"
        ).order_by(StageRun.id.desc())
    ).first()
    
    if not stage_run or not stage_run.output_json:
        raise ValueError("Research output not found")
    
    research_output = json.loads(stage_run.output_json)
    
    # Get selected angle
    angles = research_output.get("angles", [])
    if angle_id < 1 or angle_id > len(angles):
        raise ValueError(f"Invalid angle_id: {angle_id}")
    
    selected_angle = angles[angle_id - 1]
    
    # Parse verified claims
    verified_claims = json.loads(campaign.verified_claims)
    
    # Build prompt
    prompt = CREATIVE_SPEC_PROMPT.format(
        angle=json.dumps(selected_angle),
        product_name=campaign.product_name,
        product_description=campaign.factual_product_description,
        cta=campaign.call_to_action,
        verified_claims=json.dumps(verified_claims),
        tone=campaign.tone
    )
    
    # Get LLM client (mock for now)
    llm_client = get_llm_client()
    
    # Generate spec
    response = llm_client.chat([
        LLMMessage(role="system", content="You are a creative director for marketing campaigns."),
        LLMMessage(role="user", content=prompt)
    ])
    
    # Generate spec_id and version
    spec_id = str(uuid.uuid4())
    version = 1
    
    # Mock spec response (in real implementation, parse LLM response)
    # Generate dynamic palette based on tone and product
    if campaign.tone == "practical_energetic":
        palette = ["#1a1a2e", "#16213e", "#0f3460", "#e94560", "#ffffff"]
    elif campaign.tone == "sophisticated":
        palette = ["#2c3e50", "#34495e", "#7f8c8d", "#c0392b", "#ecf0f1"]
    elif campaign.tone == "playful":
        palette = ["#ff6b6b", "#feca57", "#48dbfb", "#ff9ff3", "#ffffff"]
    elif campaign.tone == "authentic":
        palette = ["#2d3436", "#636e72", "#b2bec3", "#00b894", "#dfe6e9"]
    else:
        palette = ["#1a1a2e", "#16213e", "#0f3460", "#e94560", "#ffffff"]
    
    # Make scene description more specific to product
    product_specific_scene = f"{selected_angle.get('visual_direction', '')} featuring {campaign.product_name}"
    
    # Generate more dynamic headline based on angle and product
    hook = selected_angle.get("hook", "")
    if campaign.tone == "practical_energetic":
        approved_headline = f"{hook} - {campaign.product_name}"
    elif campaign.tone == "sophisticated":
        approved_headline = f"{campaign.product_name}: {hook}"
    elif campaign.tone == "playful":
        approved_headline = f"{hook} ✨ {campaign.product_name}"
    elif campaign.tone == "authentic":
        approved_headline = f"{campaign.product_name}. {hook}"
    else:
        approved_headline = hook
    
    spec = {
        "spec_id": spec_id,
        "version": version,
        "hook": selected_angle.get("hook", ""),
        "approved_headline": approved_headline,
        "approved_body_copy": selected_angle.get("rationale", ""),
        "call_to_action": campaign.call_to_action,
        "product_identity": {
            "name": campaign.product_name,
            "allowed_claims": verified_claims
        },
        "scene_description": product_specific_scene,
        "palette": palette,
        "composition_1x1": {
            "safe_zone": "50px margin",
            "headline_placement": "top center",
            "cta_placement": "bottom center",
            "product_placement": "center"
        },
        "composition_9x16": {
            "safe_zone": "250px from top/bottom",
            "headline_placement": "top center (below safe zone)",
            "cta_placement": "bottom center (above safe zone)",
            "product_placement": "center middle"
        },
        "video_outline": {
            "beats": [
                {"time": "0-2.5s", "action": "Opening hook with product reveal"},
                {"time": "2.5-6s", "action": "Motion on scene + product zoom"},
                {"time": "6-8s", "action": "Ending CTA card"}
            ],
            "total_duration": "8s"
        }
    }
    
    return spec
