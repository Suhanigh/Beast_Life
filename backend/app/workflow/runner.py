"""Stage runner with input hash reuse and idempotency."""
import hashlib
import json
from datetime import datetime
from typing import Optional, Dict, Any
from sqlmodel import Session, select

from app.models import StageRun
from app.config import config


def compute_input_hash(input_data: Dict[str, Any]) -> str:
    """Compute hash of input data for reuse detection."""
    input_str = json.dumps(input_data, sort_keys=True)
    return hashlib.sha256(input_str.encode()).hexdigest()


def get_or_create_stage_run(
    session: Session,
    campaign_id: int,
    stage: str,
    input_data: Dict[str, Any],
    idempotency_key: Optional[str] = None
) -> StageRun:
    """
    Get existing successful run with same input hash, or create new run.
    Enforces idempotency via unique idempotency_key for in-flight stages.
    """
    input_hash = compute_input_hash(input_data)
    
    # Check for existing successful run with same input hash (reuse)
    existing = session.exec(
        select(StageRun).where(
            StageRun.campaign_id == campaign_id,
            StageRun.stage == stage,
            StageRun.input_hash == input_hash,
            StageRun.status == "succeeded"
        )
    ).first()
    
    if existing:
        return existing
    
    # Check for in-flight run with same idempotency key
    if idempotency_key:
        in_flight = session.exec(
            select(StageRun).where(
                StageRun.campaign_id == campaign_id,
                StageRun.stage == stage,
                StageRun.idempotency_key == idempotency_key,
                StageRun.status.in_(["pending", "running"])
            )
        ).first()
        
        if in_flight:
            return in_flight
    
    # Create new stage run
    stage_run = StageRun(
        campaign_id=campaign_id,
        stage=stage,
        status="pending",
        input_hash=input_hash,
        idempotency_key=idempotency_key
    )
    session.add(stage_run)
    session.commit()
    session.refresh(stage_run)
    
    return stage_run


def mark_stage_running(session: Session, stage_run: StageRun) -> None:
    """Mark stage as running with heartbeat."""
    stage_run.status = "running"
    stage_run.started_at = datetime.utcnow()
    stage_run.heartbeat_at = datetime.utcnow()
    session.add(stage_run)
    session.commit()


def mark_stage_success(
    session: Session,
    stage_run: StageRun,
    output_json: Optional[str] = None,
    output_ref: Optional[str] = None,
    provider_usage: Optional[Dict[str, Any]] = None
) -> None:
    """Mark stage as succeeded."""
    stage_run.status = "succeeded"
    stage_run.finished_at = datetime.utcnow()
    stage_run.heartbeat_at = datetime.utcnow()
    
    if output_json:
        stage_run.output_json = output_json
    if output_ref:
        stage_run.output_ref = output_ref
    if provider_usage:
        stage_run.provider_usage = json.dumps(provider_usage)
    
    session.add(stage_run)
    session.commit()


def mark_stage_failed(
    session: Session,
    stage_run: StageRun,
    error: str,
    provider_usage: Optional[Dict[str, Any]] = None
) -> None:
    """Mark stage as failed."""
    stage_run.status = "failed"
    stage_run.finished_at = datetime.utcnow()
    stage_run.heartbeat_at = datetime.utcnow()
    stage_run.error = error
    
    if provider_usage:
        stage_run.provider_usage = json.dumps(provider_usage)
    
    session.add(stage_run)
    session.commit()


def update_heartbeat(session: Session, stage_run: StageRun) -> None:
    """Update heartbeat for running stage."""
    stage_run.heartbeat_at = datetime.utcnow()
    session.add(stage_run)
    session.commit()


def recover_stale_running_stages(session: Session) -> int:
    """
    Mark stages as interrupted if heartbeat is stale.
    Returns count of recovered stages.
    """
    cutoff = datetime.utcnow()
    # Subtract heartbeat timeout from current time
    from datetime import timedelta
    cutoff = cutoff - timedelta(seconds=config.WORKER_HEARTBEAT_TIMEOUT)
    
    stale_stages = session.exec(
        select(StageRun).where(
            StageRun.status == "running",
            StageRun.heartbeat_at < cutoff
        )
    ).all()
    
    count = 0
    for stage in stale_stages:
        stage.status = "interrupted"
        stage.error = "Stage interrupted due to stale heartbeat"
        session.add(stage)
        count += 1
    
    session.commit()
    return count
