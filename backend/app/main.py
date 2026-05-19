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


@app.get("/_diag/db")
async def diag_db():
    """Temporary diagnostic: exposes whether Supabase wiring works.

    Returns env-var presence (NOT values), config hash prefixes for
    fingerprinting, and the actual exception text if the policies
    query fails. Safe to leave open: doesn't leak secrets.

    REMOVE THIS ENDPOINT before any non-portfolio use.
    """
    import os

    info: dict = {
        "env_SUPABASE_URL_present": bool(os.environ.get("SUPABASE_URL")),
        "env_SUPABASE_URL_length": len(os.environ.get("SUPABASE_URL", "")),
        "env_SUPABASE_SERVICE_KEY_present": bool(
            os.environ.get("SUPABASE_SERVICE_KEY")
        ),
        "env_SUPABASE_SERVICE_KEY_length": len(
            os.environ.get("SUPABASE_SERVICE_KEY", "")
        ),
        "env_SUPABASE_SERVICE_KEY_prefix": os.environ.get(
            "SUPABASE_SERVICE_KEY", ""
        )[:4],
        "settings_url_length": len(settings.supabase_url),
        "settings_key_length": len(settings.supabase_service_key),
        "settings_key_prefix": settings.supabase_service_key[:4],
        "env_USE_FAKE_DB": os.environ.get("USE_FAKE_DB", "<unset>"),
    }

    try:
        from app.db.client import get_supabase

        sb = get_supabase()
        res = sb.table("policies").select("store_id").limit(1).execute()
        info["query_ok"] = True
        info["query_rows_returned"] = len(res.data or [])
    except Exception as e:
        info["query_ok"] = False
        info["query_error_type"] = type(e).__name__
        info["query_error_msg"] = str(e)[:500]

    return info
