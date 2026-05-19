"""End-to-end integration tests for the /api/v1/verify endpoint.

Covers the full request flow:
    base64 image -> decode -> detect -> select -> estimate -> decide
    -> audit log (no-op in current fake repo) -> JSON response

Uses FastAPI's TestClient with `with ... as client:` to trigger the
lifespan handler so the ML pipeline is loaded once for the test session.

The current `app.db.repositories` module returns hardcoded values for
`policy_repo.get_for_store()` (always policy 18/3/0.7) and is a no-op
for `audit_repo.write_log()`. That makes these tests run without a
Supabase connection — when WEEK1-06 wires real Supabase, a USE_FAKE_DB
toggle will be needed so these tests can opt out of the live DB.
"""
from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


FIXTURES_DIR = Path(__file__).parent / "fixtures"
DEMO_STORE_ID = "00000000-0000-0000-0000-000000000001"


def _b64_image_bytes(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _blank_png_b64() -> str:
    """A 320x240 all-black PNG, base64 encoded. No face will be found."""
    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (320, 240), color=(0, 0, 0)).save(buf, format="PNG")
    return _b64_image_bytes(buf.getvalue())


@pytest.fixture(scope="session")
def test_client():
    """Boot the FastAPI app once per session (lifespan loads the pipeline)."""
    from fastapi.testclient import TestClient

    # Force the pipeline cache dir to ~/.insightface so warmup() finds
    # the buffalo_l pack that WEEK1-03 downloaded (default
    # `/var/cache/agegate/models` is not writable on Windows).
    from app.core.config import settings

    settings.model_cache_dir = str(Path.home() / ".insightface")

    from app.main import app

    with TestClient(app) as client:
        yield client


@pytest.mark.ml
def test_verify_with_real_face_returns_valid_decision(
    test_client: "TestClient",
) -> None:
    """Posting a real face fixture returns a 200 with a sensible decision."""
    fixture = FIXTURES_DIR / "has_face.jpg"
    assert fixture.exists(), (
        f"{fixture} missing — run scripts/download_test_fixtures.py first"
    )

    payload = {
        "image_base64": _b64_image_bytes(fixture.read_bytes()),
        "store_id": DEMO_STORE_ID,
    }
    res = test_client.post("/api/v1/verify", json=payload)
    assert res.status_code == 200, res.text

    data = res.json()
    # Either model estimates the subject as clearly adult (PASS) or
    # the range straddles the 18+3=21 safe floor (MANUAL_CHECK).
    # REJECT would mean the model thinks the historical figure is < 18,
    # which would be a regression — flag if it happens.
    assert data["decision"] in ("pass", "manual_check"), data
    assert data["reason"] in (
        "clearly_over_threshold",
        "range_straddles_threshold",
        "face_detection_confidence_too_low",
    )
    assert data["age_low"] >= 0
    assert data["age_high"] >= data["age_low"]
    assert data["threshold_used"] == 18
    assert data["buffer_used"] == 3
    assert "request_id" in data


@pytest.mark.ml
def test_verify_with_blank_image_returns_no_face_manual_check(
    test_client: "TestClient",
) -> None:
    """A blank (no face) image must produce MANUAL_CHECK / NO_FACE."""
    payload = {
        "image_base64": _blank_png_b64(),
        "store_id": DEMO_STORE_ID,
    }
    res = test_client.post("/api/v1/verify", json=payload)
    assert res.status_code == 200, res.text

    data = res.json()
    assert data["decision"] == "manual_check"
    assert data["reason"] == "no_face_detected"
    assert data["multiple_faces_detected"] is False


@pytest.mark.ml
def test_verify_rejects_invalid_base64(test_client: "TestClient") -> None:
    """Garbage base64 yields 400, not 500 — input validation lives at the edge.

    Marked ml because it uses the session-scoped `test_client` fixture
    (which triggers the FastAPI lifespan + ML warmup). The validation
    itself runs before any pipeline call, but loading the client costs
    pipeline init.
    """
    payload = {
        "image_base64": "this!is!not!base64!!!",
        "store_id": DEMO_STORE_ID,
    }
    res = test_client.post("/api/v1/verify", json=payload)
    assert res.status_code == 400
    assert "Invalid base64" in res.text or "Cannot decode" in res.text


@pytest.mark.ml
def test_verify_rejects_oversized_image(test_client: "TestClient") -> None:
    """Image exceeding MAX_IMAGE_BYTES (5MB) is rejected with 413."""
    # 6MB of zeros — when base64-encoded it's larger, but the server
    # decodes first and checks raw byte size.
    big = b"\x00" * (6 * 1024 * 1024)
    payload = {
        "image_base64": _b64_image_bytes(big),
        "store_id": DEMO_STORE_ID,
    }
    res = test_client.post("/api/v1/verify", json=payload)
    assert res.status_code == 413
