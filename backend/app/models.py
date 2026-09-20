"""Database models using SQLModel."""
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, JSON


class Campaign(SQLModel, table=True):
    """Campaign model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    product_name: str
    factual_product_description: str
    target_audience: str
    campaign_objective: str
    tone: str
    call_to_action: str
    verified_claims: str  # JSON string
    reference_image_path: Optional[str] = None
    selected_angle_id: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_mock: bool = False
    
    # Relationships
    stage_runs: list["StageRun"] = Relationship(back_populates="campaign")
    assets: list["Asset"] = Relationship(back_populates="campaign")


class StageRun(SQLModel, table=True):
    """Stage execution run model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    campaign_id: int = Field(foreign_key="campaign.id")
    stage: str
    status: str  # pending/running/succeeded/failed/interrupted
    attempt: int = 1
    input_hash: str  # For reuse detection
    output_json: Optional[str] = None  # JSON string
    output_ref: Optional[str] = None  # Reference to stored output
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    heartbeat_at: Optional[datetime] = None
    provider_usage: Optional[str] = None  # JSON string with cost/tokens
    
    # Idempotency
    idempotency_key: Optional[str] = Field(default=None, index=True)
    
    # Relationships
    campaign: Campaign = Relationship(back_populates="stage_runs")


class Asset(SQLModel, table=True):
    """Generated asset model."""
    id: Optional[int] = Field(default=None, primary_key=True)
    campaign_id: int = Field(foreign_key="campaign.id")
    asset_id: str
    asset_type: str  # image_1x1, image_9x16, video
    spec_id: str
    file_path: str
    width: int
    height: int
    duration_seconds: Optional[float] = None
    prompt_params: Optional[str] = None  # JSON string
    scene_source: Optional[str] = None  # cloudflare, procedural
    fallback_reason: Optional[str] = None  # Why fallback was used
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    campaign: Campaign = Relationship(back_populates="assets")
