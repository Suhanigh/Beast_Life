"""Pydantic schemas for API contracts and validation."""
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class CampaignObjective(str, Enum):
    """Campaign objective options."""
    INTRODUCE = "introduce"
    DRIVE_CONVERSION = "drive_conversion"
    BRAND_AWARENESS = "brand_awareness"
    LAUNCH = "launch"


class Tone(str, Enum):
    """Tone options."""
    PRACTICAL_ENERGETIC = "practical_energetic"
    SOPHISTICATED = "sophisticated"
    PLAYFUL = "playful"
    AUTHENTIC = "authentic"


class BriefCreate(BaseModel):
    """Request schema for creating a campaign brief."""
    product_name: str = Field(..., min_length=1, max_length=200)
    factual_product_description: str = Field(..., min_length=10, max_length=2000)
    target_audience: str = Field(..., min_length=10, max_length=500)
    campaign_objective: CampaignObjective
    tone: Tone
    call_to_action: str = Field(..., min_length=1, max_length=100)
    verified_claims: List[str] = Field(default_factory=list, max_length=10)
    
    @field_validator('verified_claims')
    @classmethod
    def validate_claims(cls, v):
        """Validate verified claims length."""
        for claim in v:
            if len(claim) > 200:
                raise ValueError("Each verified claim must be at most 200 characters")
        return v


class Source(BaseModel):
    """Research source reference."""
    title: str
    url: str
    accessed_at: datetime
    excerpt: str


class AngleStatement(BaseModel):
    """Single statement within an angle with evidence label."""
    text: str
    label: str = Field(..., pattern="^(sourced_observation|creative_interpretation)$")


class Angle(BaseModel):
    """Creative angle from research."""
    audience_insight: str
    hook: str
    visual_direction: str
    rationale: str
    source_ids: List[int]
    statements: List[AngleStatement]


class ResearchOutput(BaseModel):
    """Research agent output contract."""
    angles: List[Angle] = Field(..., min_length=3, max_length=3)
    sources: List[Source]
    tool_calls: List[dict]
    source_gap: Optional[str] = None


class CreativeSpec(BaseModel):
    """Shared creative specification."""
    spec_id: str
    version: int
    hook: str
    approved_headline: str
    approved_body_copy: Optional[str] = None
    call_to_action: str
    product_identity: dict
    scene_description: str
    palette: List[str]  # Hex colors
    composition_1x1: dict
    composition_9x16: dict
    video_outline: dict


class Asset(BaseModel):
    """Generated asset metadata."""
    asset_id: str
    asset_type: str  # "image_1x1", "image_9x16", "video"
    spec_id: str
    file_path: str
    width: int
    height: int
    duration_seconds: Optional[float] = None
    prompt_params: Optional[dict] = None


class StageStatus(str, Enum):
    """Stage execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class StageType(str, Enum):
    """Workflow stage types."""
    RESEARCH = "research"
    SPEC = "spec"
    SCENE = "scene"
    IMAGE_1X1 = "image_1x1"
    IMAGE_9X16 = "image_9x16"
    VIDEO = "video"


class CampaignResponse(BaseModel):
    """Campaign response with full state."""
    id: int
    brief: BriefCreate
    selected_angle_id: Optional[int] = None
    created_at: datetime
    is_mock: bool
    
    # Nested research output (raw JSON string)
    research_output: Optional[str] = None
    
    # Nested creative spec (raw JSON string)
    creative_spec: Optional[str] = None
    
    # Generated assets
    assets: List[Asset] = []
    
    # Stage runs
    stage_runs: List[dict] = []


class CampaignListResponse(BaseModel):
    """Simplified campaign for history list."""
    id: int
    product_name: str
    created_at: datetime
    status: str
    is_mock: bool


class StageRunResponse(BaseModel):
    """Stage run response."""
    id: int
    campaign_id: int
    stage: StageType
    status: StageStatus
    attempt: int
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
