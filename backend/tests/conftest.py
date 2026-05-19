"""Shared pytest fixtures.

ML-heavy imports are deferred into fixture bodies so `pytest -m "not ml"`
stays fast at collection time (no torch / onnxruntime / insightface load).
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from app.ml.pipeline import AgePipeline


FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def ml_pipeline() -> "AgePipeline":
    """Warm-loaded AgePipeline, shared across the session.

    Uses ~/.insightface as the model cache so the buffalo_l pack
    (~280MB) is downloaded at most once per developer machine.
    """
    cache = str(Path.home() / ".insightface")

    from app.core.config import settings as _settings

    _settings.model_cache_dir = cache

    from app.ml.pipeline import AgePipeline

    pipeline = AgePipeline()
    asyncio.run(pipeline.warmup())
    return pipeline


@pytest.fixture(scope="session")
def has_face_image_path() -> Path:
    """Path to a real-face fixture image. Skips dependent tests if absent.

    Drop a public-domain face photo (JPG or PNG, <500 KB) at
    `backend/tests/fixtures/has_face.jpg`. See fixtures/README.md.
    """
    candidates = [FIXTURES_DIR / "has_face.jpg", FIXTURES_DIR / "has_face.png"]
    for p in candidates:
        if p.exists():
            return p
    pytest.skip(
        "No has_face.{jpg,png} fixture present. "
        "See backend/tests/fixtures/README.md for instructions."
    )
