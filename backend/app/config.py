"""Application configuration with environment variable overrides."""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Application configuration."""
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./data/campaigns.db")
    
    # Research agent limits
    MAX_TOOL_CALLS: int = int(os.getenv("MAX_TOOL_CALLS", "8"))
    MAX_FOLLOWUP_SEARCHES: int = int(os.getenv("MAX_FOLLOWUP_SEARCHES", "2"))
    PAGE_FETCH_TIMEOUT: int = int(os.getenv("PAGE_FETCH_TIMEOUT", "10"))
    RESEARCH_WALL_CLOCK: int = int(os.getenv("RESEARCH_WALL_CLOCK", "90"))
    PAGE_TEXT_CAP: int = int(os.getenv("PAGE_TEXT_CAP", "20000"))  # 20KB
    LLM_RETRIES: int = int(os.getenv("LLM_RETRIES", "1"))
    
    # Worker polling
    WORKER_POLL_INTERVAL: int = int(os.getenv("WORKER_POLL_INTERVAL", "2"))
    WORKER_HEARTBEAT_TIMEOUT: int = int(os.getenv("WORKER_HEARTBEAT_TIMEOUT", "30"))
    
    # Mock mode
    MOCK_MODE: bool = os.getenv("MOCK_MODE", "0") == "1"
    
    # Failure injection for testing
    FAIL_STAGE: Optional[str] = os.getenv("FAIL_STAGE")
    FAIL_ONCE: Optional[str] = os.getenv("FAIL_ONCE")
    
    # Asset storage
    ASSET_DIR: str = os.getenv("ASSET_DIR", "./data/campaigns")
    
    # API keys (server-side only)
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    TAVILY_API_KEY: Optional[str] = os.getenv("TAVILY_API_KEY")
    CLOUDFLARE_ACCOUNT_ID: Optional[str] = os.getenv("CLOUDFLARE_ACCOUNT_ID")
    CLOUDFLARE_API_KEY: Optional[str] = os.getenv("CLOUDFLARE_API_KEY")
    
    # Upload limits
    MAX_UPLOAD_SIZE: int = int(os.getenv("MAX_UPLOAD_SIZE", "5")) * 1024 * 1024  # 5MB
    ALLOWED_UPLOAD_TYPES: list = ["image/png", "image/jpeg", "image/webp"]


config = Config()
