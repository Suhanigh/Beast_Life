"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import config
from app.db import engine, create_db_and_tables
from app.api import campaigns


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    create_db_and_tables()
    yield
    # Shutdown
    pass


app = FastAPI(
    title="AI Campaign Creative Studio",
    description="AI-powered campaign creative generation for Beast Life",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for generated assets
data_dir = Path("data")
if data_dir.exists():
    app.mount("/data", StaticFiles(directory=str(data_dir)), name="data")

# Include routers
app.include_router(campaigns.router, prefix="/api/campaigns", tags=["campaigns"])


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "mock_mode": config.MOCK_MODE}
