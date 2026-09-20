"""Campaign CRUD and workflow endpoints."""
import json
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select

from app.db import get_session
from app.models import Campaign, StageRun, Asset
from app.schemas import (
    BriefCreate,
    CampaignResponse,
    CampaignListResponse,
    StageRunResponse,
    StageType,
    StageStatus
)
from app.workflow.runner import get_or_create_stage_run
from app.workflow.worker import start_worker
from app.config import config


router = APIRouter()

# Start worker on import
start_worker()


@router.post("", response_model=CampaignResponse)
def create_campaign(
    brief: BriefCreate,
    session: Session = Depends(get_session)
):
    """Create a new campaign from a brief."""
    from app.config import config
    
    campaign = Campaign(
        product_name=brief.product_name,
        factual_product_description=brief.factual_product_description,
        target_audience=brief.target_audience,
        campaign_objective=brief.campaign_objective.value,
        tone=brief.tone.value,
        call_to_action=brief.call_to_action,
        verified_claims=json.dumps(brief.verified_claims),
        is_mock=config.MOCK_MODE
    )
    
    session.add(campaign)
    session.commit()
    session.refresh(campaign)
    
    return build_campaign_response(session, campaign)


@router.get("", response_model=list[CampaignListResponse])
def list_campaigns(session: Session = Depends(get_session)):
    """List all campaigns (history)."""
    campaigns = session.exec(
        select(Campaign).order_by(Campaign.created_at.desc())
    ).all()
    
    return [
        CampaignListResponse(
            id=c.id,
            product_name=c.product_name,
            created_at=c.created_at,
            status=compute_campaign_status(session, c.id),
            is_mock=c.is_mock
        )
        for c in campaigns
    ]


@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(
    campaign_id: int,
    session: Session = Depends(get_session)
):
    """Get full campaign state including stages, research, spec, and assets."""
    campaign = session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    return build_campaign_response(session, campaign)


@router.post("/{campaign_id}/research/start")
def start_research(
    campaign_id: int,
    session: Session = Depends(get_session)
):
    """Start the research stage for a campaign."""
    campaign = session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Create or get stage run
    stage_run = get_or_create_stage_run(
        session,
        campaign_id,
        StageType.RESEARCH,
        {
            "product_name": campaign.product_name,
            "description": campaign.factual_product_description,
            "audience": campaign.target_audience
        },
        idempotency_key=str(uuid.uuid4())
    )
    
    return {"stage_run_id": stage_run.id, "status": stage_run.status}


@router.post("/{campaign_id}/angle")
def select_angle(
    campaign_id: int,
    angle_data: dict,
    session: Session = Depends(get_session)
):
    """Select an angle from research results."""
    campaign = session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    angle_id = angle_data.get("angle_id")
    if angle_id is None:
        raise HTTPException(status_code=400, detail="angle_id is required")
    
    campaign.selected_angle_id = angle_id
    session.add(campaign)
    session.commit()
    session.refresh(campaign)
    
    return {"status": "selected", "angle_id": angle_id}


@router.post("/{campaign_id}/generate")
def generate_creatives(
    campaign_id: int,
    session: Session = Depends(get_session)
):
    """Start creative generation (spec -> scene -> images -> video)."""
    campaign = session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign.selected_angle_id is None:
        raise HTTPException(
            status_code=400,
            detail="Must select an angle before generation"
        )
    
    # Create stage runs for generation pipeline
    stages = [
        StageType.SPEC,
        StageType.SCENE,
        StageType.IMAGE_1X1,
        StageType.IMAGE_9X16,
        StageType.VIDEO
    ]
    
    created_runs = []
    for stage in stages:
        stage_run = get_or_create_stage_run(
            session,
            campaign_id,
            stage,
            {"campaign_id": campaign_id, "angle_id": campaign.selected_angle_id},
            idempotency_key=str(uuid.uuid4())
        )
        created_runs.append({
            "stage": stage,
            "stage_run_id": stage_run.id,
            "status": stage_run.status
        })
    
    return {"stages": created_runs}


@router.post("/{campaign_id}/stages/{stage}/retry")
def retry_stage(
    campaign_id: int,
    stage: str,
    session: Session = Depends(get_session)
):
    """Retry a failed or interrupted stage."""
    campaign = session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Get the most recent run for this stage
    last_run = session.exec(
        select(StageRun).where(
            StageRun.campaign_id == campaign_id,
            StageRun.stage == stage
        ).order_by(StageRun.id.desc())
    ).first()
    
    if not last_run:
        raise HTTPException(status_code=404, detail="Stage run not found")
    
    if last_run.status == "succeeded":
        raise HTTPException(
            status_code=400,
            detail="Cannot retry a succeeded stage"
        )
    
    # Create new run with incremented attempt
    new_run = get_or_create_stage_run(
        session,
        campaign_id,
        stage,
        {"campaign_id": campaign_id, "retry_of": last_run.id},
        idempotency_key=str(uuid.uuid4())
    )
    new_run.attempt = last_run.attempt + 1
    session.add(new_run)
    session.commit()
    session.refresh(new_run)
    
    return {"stage_run_id": new_run.id, "attempt": new_run.attempt}


def build_campaign_response(
    session: Session,
    campaign: Campaign
) -> CampaignResponse:
    """Build full campaign response with nested data."""
    # Get stage runs
    stage_runs = session.exec(
        select(StageRun).where(
            StageRun.campaign_id == campaign.id
        ).order_by(StageRun.id)
    ).all()
    
    # Get assets
    assets = session.exec(
        select(Asset).where(Asset.campaign_id == campaign.id)
    ).all()
    
    # Extract research output from stage runs
    research_output = None
    for sr in stage_runs:
        if sr.stage == "research" and sr.status == "succeeded" and sr.output_json:
            research_output = sr.output_json  # Return raw JSON string
            break
    
    # Extract creative spec from stage runs
    creative_spec = None
    for sr in stage_runs:
        if sr.stage == "spec" and sr.status == "succeeded" and sr.output_json:
            creative_spec = sr.output_json  # Return as-is for now
            break
    
    return CampaignResponse(
        id=campaign.id,
        brief=BriefCreate(
            product_name=campaign.product_name,
            factual_product_description=campaign.factual_product_description,
            target_audience=campaign.target_audience,
            campaign_objective=campaign.campaign_objective,
            tone=campaign.tone,
            call_to_action=campaign.call_to_action,
            verified_claims=json.loads(campaign.verified_claims)
        ),
        selected_angle_id=campaign.selected_angle_id,
        created_at=campaign.created_at,
        is_mock=campaign.is_mock,
        research_output=research_output,
        creative_spec=creative_spec,
        stage_runs=[
            {
                "id": sr.id,
                "campaign_id": sr.campaign_id,
                "stage": sr.stage,
                "status": sr.status,
                "attempt": sr.attempt,
                "error": sr.error,
                "started_at": sr.started_at,
                "finished_at": sr.finished_at
            }
            for sr in stage_runs
        ],
        assets=[
            {
                "asset_id": a.asset_id,
                "asset_type": a.asset_type,
                "spec_id": a.spec_id,
                "file_path": a.file_path.replace('./', '/'),  # Convert to absolute path for static serving
                "width": a.width,
                "height": a.height,
                "duration_seconds": a.duration_seconds,
                "prompt_params": json.loads(a.prompt_params) if a.prompt_params else None,
                "scene_source": a.scene_source,
                "fallback_reason": a.fallback_reason
            }
            for a in assets
        ]
    )


def compute_campaign_status(session: Session, campaign_id: int) -> str:
    """Compute overall campaign status from stage runs."""
    stage_runs = session.exec(
        select(StageRun).where(StageRun.campaign_id == campaign_id)
    ).all()
    
    if not stage_runs:
        return "created"
    
    # Check for any failed stages
    if any(sr.status == "failed" for sr in stage_runs):
        return "failed"
    
    # Check for any running stages
    if any(sr.status in ["pending", "running"] for sr in stage_runs):
        return "in_progress"
    
    # All succeeded
    return "completed"
