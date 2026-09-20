"""Background worker that polls and executes pending stages."""
import time
import threading
import json
import uuid
from typing import Dict, Any, Optional
from sqlmodel import Session, select

from app.db import engine
from app.models import Campaign, StageRun, Asset
from app.workflow.runner import (
    mark_stage_running,
    mark_stage_success,
    mark_stage_failed,
    update_heartbeat,
    recover_stale_running_stages
)
from app.config import config
from app.agents.research.agent import ResearchAgent
from app.workflow.stages.spec import generate_spec
from app.workflow.stages.scene import generate_scene
from app.rendering.compositor import get_compositor
from app.rendering.video import get_video_generator


class StageExecutor:
    """Executes individual stages."""
    
    def __init__(self):
        self._stages = {}
    
    def register_stage(self, stage_name: str, handler):
        """Register a stage handler function."""
        self._stages[stage_name] = handler
    
    def execute_stage(self, session: Session, stage_run: StageRun) -> Dict[str, Any]:
        """Execute a stage by name."""
        handler = self._stages.get(stage_run.stage)
        if not handler:
            raise ValueError(f"No handler registered for stage: {stage_run.stage}")
        
        return handler(session, stage_run)


# Global stage executor
executor = StageExecutor()


# Register research stage with actual agent
def execute_research_stage(session: Session, stage_run: StageRun) -> Dict[str, Any]:
    """Execute research stage using the research agent."""
    # Get campaign
    campaign = session.get(Campaign, stage_run.campaign_id)
    if not campaign:
        raise ValueError(f"Campaign {stage_run.campaign_id} not found")
    
    # Parse verified claims
    try:
        verified_claims = json.loads(campaign.verified_claims)
    except json.JSONDecodeError:
        verified_claims = []
    
    # Create research agent
    agent = ResearchAgent()
    
    try:
        # Execute research
        result = agent.research(
            product_name=campaign.product_name,
            product_description=campaign.factual_product_description,
            target_audience=campaign.target_audience,
            campaign_objective=campaign.campaign_objective,
            tone=campaign.tone
        )
        
        return result
        
    finally:
        agent.close()

executor.register_stage("research", execute_research_stage)


def execute_spec_stage(session: Session, stage_run: StageRun) -> Dict[str, Any]:
    """Execute spec stage using the spec generator."""
    # Get campaign
    campaign = session.get(Campaign, stage_run.campaign_id)
    if not campaign:
        raise ValueError(f"Campaign {stage_run.campaign_id} not found")
    
    if campaign.selected_angle_id is None:
        raise ValueError("Must select an angle before generating spec")
    
    # Generate spec
    spec = generate_spec(session, campaign, campaign.selected_angle_id)
    
    return spec

executor.register_stage("spec", execute_spec_stage)


def execute_scene_stage(session: Session, stage_run: StageRun) -> Dict[str, Any]:
    """Execute scene stage using the scene generator."""
    # Get campaign
    campaign = session.get(Campaign, stage_run.campaign_id)
    if not campaign:
        raise ValueError(f"Campaign {stage_run.campaign_id} not found")
    
    # Get spec from previous stage
    from app.models import StageRun
    spec_run = session.exec(
        select(StageRun).where(
            StageRun.campaign_id == campaign.id,
            StageRun.stage == "spec",
            StageRun.status == "succeeded"
        ).order_by(StageRun.id.desc())
    ).first()
    
    if not spec_run or not spec_run.output_json:
        raise ValueError("Spec output not found")
    
    spec = json.loads(spec_run.output_json)
    
    # Generate scene
    scene = generate_scene(session, campaign, spec)
    
    return {"spec": spec, "scene": scene}

executor.register_stage("scene", execute_scene_stage)


def execute_image_1x1_stage(session: Session, stage_run: StageRun) -> Dict[str, Any]:
    """Execute image_1x1 stage using the compositor."""
    # Get campaign
    campaign = session.get(Campaign, stage_run.campaign_id)
    if not campaign:
        raise ValueError(f"Campaign {stage_run.campaign_id} not found")
    
    # Get spec and scene
    from app.models import StageRun
    scene_run = session.exec(
        select(StageRun).where(
            StageRun.campaign_id == campaign.id,
            StageRun.stage == "scene",
            StageRun.status == "succeeded"
        ).order_by(StageRun.id.desc())
    ).first()
    
    if not scene_run or not scene_run.output_json:
        raise ValueError("Scene output not found")
    
    scene_data = json.loads(scene_run.output_json)
    spec = scene_data["spec"]
    scene = scene_data["scene"]
    
    # Generate image
    compositor = get_compositor()
    output_path, scene_source, fallback_reason = compositor.generate_image_1x1(spec, scene)
    
    return {
        "asset_type": "image_1x1",
        "file_path": output_path,
        "width": 1080,
        "height": 1080,
        "spec_id": spec["spec_id"],
        "scene_source": scene_source,
        "fallback_reason": fallback_reason
    }

executor.register_stage("image_1x1", execute_image_1x1_stage)


def execute_image_9x16_stage(session: Session, stage_run: StageRun) -> Dict[str, Any]:
    """Execute image_9x16 stage using the compositor."""
    # Get campaign
    campaign = session.get(Campaign, stage_run.campaign_id)
    if not campaign:
        raise ValueError(f"Campaign {stage_run.campaign_id} not found")
    
    # Get spec and scene
    from app.models import StageRun
    scene_run = session.exec(
        select(StageRun).where(
            StageRun.campaign_id == campaign.id,
            StageRun.stage == "scene",
            StageRun.status == "succeeded"
        ).order_by(StageRun.id.desc())
    ).first()
    
    if not scene_run or not scene_run.output_json:
        raise ValueError("Scene output not found")
    
    scene_data = json.loads(scene_run.output_json)
    spec = scene_data["spec"]
    scene = scene_data["scene"]
    
    # Generate image
    compositor = get_compositor()
    output_path, scene_source, fallback_reason = compositor.generate_image_9x16(spec, scene)
    
    return {
        "asset_type": "image_9x16",
        "file_path": output_path,
        "width": 1080,
        "height": 1920,
        "spec_id": spec["spec_id"],
        "scene_source": scene_source,
        "fallback_reason": fallback_reason
    }

executor.register_stage("image_9x16", execute_image_9x16_stage)


def execute_video_stage(session: Session, stage_run: StageRun) -> Dict[str, Any]:
    """Execute video stage using the video generator."""
    # Get campaign
    campaign = session.get(Campaign, stage_run.campaign_id)
    if not campaign:
        raise ValueError(f"Campaign {stage_run.campaign_id} not found")
    
    # Get spec and scene
    from app.models import StageRun
    scene_run = session.exec(
        select(StageRun).where(
            StageRun.campaign_id == campaign.id,
            StageRun.stage == "scene",
            StageRun.status == "succeeded"
        ).order_by(StageRun.id.desc())
    ).first()
    
    if not scene_run or not scene_run.output_json:
        raise ValueError("Scene output not found")
    
    scene_data = json.loads(scene_run.output_json)
    spec = scene_data["spec"]
    scene = scene_data["scene"]
    
    # Find the 9x16 image to use as video background
    from app.models import Asset
    from app.config import config
    import os
    
    # Get the most recent 9x16 image for this campaign
    image_9x16 = session.query(Asset).filter(
        Asset.campaign_id == campaign.id,
        Asset.asset_type == "image_9x16"
    ).order_by(Asset.created_at.desc()).first()
    
    image_path = None
    if image_9x16 and image_9x16.file_path:
        raw_path = image_9x16.file_path
        
        # Handle different path formats
        if raw_path.startswith('./'):
            # Remove ./ and join with asset dir
            clean_path = raw_path[2:]
            image_path = os.path.join(config.ASSET_DIR, clean_path)
        elif raw_path.startswith('/'):
            # Remove leading / and join with asset dir
            clean_path = raw_path[1:]
            image_path = os.path.join(config.ASSET_DIR, clean_path)
        else:
            # Use as-is, join with asset dir
            image_path = os.path.join(config.ASSET_DIR, raw_path)
        
        # Prevent double paths
        if 'data/campaigns/data/campaigns' in image_path:
            # Fix double path issue
            image_path = image_path.replace('data/campaigns/data/campaigns', 'data/campaigns')
        
        print(f"Using 9x16 image as video background: {image_path}")
        
        # Verify file exists
        if not os.path.exists(image_path):
            print(f"⚠ Image file not found: {image_path}")
            image_path = None
    
    # Generate video
    video_generator = get_video_generator()
    output_path = video_generator.generate_video(spec, scene, image_path=image_path)
    
    return {
        "asset_type": "video",
        "file_path": output_path,
        "width": 1080,
        "height": 1920,
        "duration_seconds": 8.0,
        "spec_id": spec["spec_id"]
    }

executor.register_stage("video", execute_video_stage)


def _create_asset_record(session: Session, campaign_id: int, asset_data: Dict[str, Any]):
    """Create asset record in database."""
    from app.models import Asset
    import uuid
    
    asset = Asset(
        campaign_id=campaign_id,
        asset_id=str(uuid.uuid4()),
        asset_type=asset_data.get("asset_type"),
        spec_id=asset_data.get("spec_id"),
        file_path=asset_data.get("file_path"),
        width=asset_data.get("width"),
        height=asset_data.get("height"),
        duration_seconds=asset_data.get("duration_seconds"),
        prompt_params=json.dumps(asset_data),
        scene_source=asset_data.get("scene_source"),
        fallback_reason=asset_data.get("fallback_reason")
    )
    
    session.add(asset)
    session.commit()


def worker_loop(stop_event: threading.Event):
    """Main worker loop that polls for pending stages."""
    print("Worker started, polling for pending stages...")
    
    while not stop_event.is_set():
        try:
            with Session(engine) as session:
                # Recover stale running stages
                recovered = recover_stale_running_stages(session)
                if recovered > 0:
                    print(f"Recovered {recovered} stale running stages")
                
                # Fetch pending stages
                pending_stages = session.exec(
                    select(StageRun).where(
                        StageRun.status == "pending"
                    ).order_by(StageRun.id).limit(10)
                ).all()
                
                for stage_run in pending_stages:
                    try:
                        # Get campaign for asset creation
                        campaign = session.get(Campaign, stage_run.campaign_id)
                        if not campaign:
                            raise ValueError(f"Campaign {stage_run.campaign_id} not found")
                        
                        # Mark as running
                        mark_stage_running(session, stage_run)
                        
                        # Execute stage
                        output = executor.execute_stage(session, stage_run)
                        
                        # Mark as success (JSON for spec/research/scene, string for others)
                        if stage_run.stage in ["research", "spec", "scene"]:
                            output_json = json.dumps(output)
                        else:
                            # For image/video stages, create asset record
                            if stage_run.stage in ["image_1x1", "image_9x16", "video"]:
                                _create_asset_record(session, campaign.id, output)
                            output_json = json.dumps(output)
                        
                        mark_stage_success(
                            session,
                            stage_run,
                            output_json=output_json
                        )
                        
                        print(f"Completed stage {stage_run.stage} for campaign {stage_run.campaign_id}")
                        
                    except Exception as e:
                        # Mark as failed
                        mark_stage_failed(session, stage_run, str(e))
                        print(f"Failed stage {stage_run.stage} for campaign {stage_run.campaign_id}: {e}")
        
        except Exception as e:
            print(f"Worker loop error: {e}")
        
        # Wait before next poll
        stop_event.wait(config.WORKER_POLL_INTERVAL)
    
    print("Worker stopped")


# Global worker thread control
_worker_thread: Optional[threading.Thread] = None
_worker_stop_event: Optional[threading.Event] = None


def start_worker():
    """Start the background worker thread."""
    global _worker_thread, _worker_stop_event
    
    if _worker_thread and _worker_thread.is_alive():
        print("Worker already running")
        return
    
    _worker_stop_event = threading.Event()
    _worker_thread = threading.Thread(
        target=worker_loop,
        args=(_worker_stop_event,),
        daemon=True
    )
    _worker_thread.start()
    print("Worker thread started")


def stop_worker():
    """Stop the background worker thread."""
    global _worker_stop_event, _worker_thread
    
    if _worker_stop_event:
        _worker_stop_event.set()
    
    if _worker_thread:
        _worker_thread.join(timeout=5)
        print("Worker thread stopped")
