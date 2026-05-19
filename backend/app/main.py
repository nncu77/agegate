"""AgeGate FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import audit, policy, verify
from app.core.config import settings
from app.core.logging import setup_logging
from app.ml.pipeline import AgePipeline

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML models at startup; release at shutdown.

    Models are heavy (~hundreds of MB). Loading them per-request would
    blow latency and memory. Hold a single shared pipeline for the
    lifetime of the process.
    """
    app.state.pipeline = AgePipeline()
    await app.state.pipeline.warmup()
    yield
    # Pipeline cleanup happens via GC; no explicit release needed for
    # InsightFace / MiVOLO models in a single-process deployment.


app = FastAPI(
    title="AgeGate API",
    version="0.1.0",
    description="AI-assisted age verification for age-gated retail",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(verify.router, prefix="/api/v1", tags=["verify"])
app.include_router(audit.router, prefix="/api/v1", tags=["audit"])
app.include_router(policy.router, prefix="/api/v1", tags=["policy"])


@app.get("/health")
async def health():
    """Liveness probe. Does not check ML model state."""
    return {"status": "ok", "version": app.version}


@app.get("/ready")
async def ready():
    """Readiness probe. Confirms ML pipeline is loaded."""
    ready = app.state.pipeline.is_ready() if hasattr(app.state, "pipeline") else False
    return {"ready": ready}


