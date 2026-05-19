"""Integration tests for app.db.repositories against a real Supabase project.

These tests HIT THE LIVE DATABASE configured in backend/.env. They are
marked `@pytest.mark.db` so they're excluded by default. Run explicitly:

    PYTHONPATH=. pytest -m db -v

Prerequisites (matches WEEK1-06 task description):
    - Supabase project exists with `001_initial_schema.sql` applied
    - A test store with id '00000000-0000-0000-0000-000000000001' exists
    - That store has a corresponding row in `policies`
    - `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` set in backend/.env

The tests insert audit_log rows tagged with `pytest_marker` prefixes in
the request_id so manual cleanup is easy:

    delete from audit_logs where id::text like 'aaaaaaaa-%';
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime

import pytest

from app.core.decision import (
    Decision,
    DecisionReason,
    DecisionResult,
)
from app.db.repositories import audit_repo, policy_repo
from app.schemas.api import AuditQuery


TEST_STORE_ID = "00000000-0000-0000-0000-000000000001"


def _ensure_live_db() -> None:
    if os.environ.get("USE_FAKE_DB", "").lower() in ("1", "true", "yes"):
        pytest.skip("USE_FAKE_DB is set; live DB tests skipped")
    # Clear the supabase client cache so it picks up fresh settings.
    from app.db.client import get_supabase

    get_supabase.cache_clear()


@pytest.fixture(scope="module", autouse=True)
def _live_db_guard():
    _ensure_live_db()
    yield


@pytest.mark.db
@pytest.mark.asyncio
async def test_policy_get_for_demo_store_returns_seeded_row() -> None:
    """The Demo Store policy we seeded by hand must come back unchanged."""
    p = await policy_repo.get_for_store(TEST_STORE_ID)
    assert p is not None, (
        f"No policy row for {TEST_STORE_ID}. Did you run the seed inserts in Step 4?"
    )
    assert p.store_id == TEST_STORE_ID
    assert p.threshold_age == 18
    assert p.buffer_years == 3
    assert abs(p.min_face_confidence - 0.7) < 1e-6


@pytest.mark.db
@pytest.mark.asyncio
async def test_policy_upsert_round_trip() -> None:
    """Upserting the same store_id with new values reads back identical."""
    updated = await policy_repo.upsert(
        store_id=TEST_STORE_ID,
        threshold_age=18,
        buffer_years=3,
        min_face_confidence=0.7,
    )
    assert updated.threshold_age == 18
    assert updated.buffer_years == 3

    reread = await policy_repo.get_for_store(TEST_STORE_ID)
    assert reread is not None
    assert reread.threshold_age == 18


@pytest.mark.db
@pytest.mark.asyncio
async def test_audit_write_and_query_round_trip() -> None:
    """Write an audit row, query it back, confirm fields survive."""
    # Use a deterministic UUID prefix so cleanup is easy: 'aaaaaaaa-...'
    request_id = str(uuid.UUID(int=(0xAAAAAAAA00000000 << 64) | uuid.uuid4().int & ((1 << 64) - 1)))
    result = DecisionResult(
        decision=Decision.MANUAL_CHECK,
        reason=DecisionReason.AMBIGUOUS_RANGE,
        age_low=17,
        age_high=22,
        threshold_used=18,
        buffer_used=3,
        face_confidence=0.91,
    )
    await audit_repo.write_log(
        request_id=request_id,
        store_id=TEST_STORE_ID,
        result=result,
    )

    found = await audit_repo.query(
        AuditQuery(store_id=TEST_STORE_ID, limit=10, offset=0)
    )
    matches = [r for r in found if r.id == request_id]
    assert matches, (
        f"Audit log written but query did not find id={request_id}. "
        "Likely RLS misconfiguration or service_role key issue."
    )
    row = matches[0]
    assert row.decision == "manual_check"
    assert row.reason == "range_straddles_threshold"
    assert row.age_low == 17
    assert row.age_high == 22


@pytest.mark.db
@pytest.mark.asyncio
async def test_audit_attach_override() -> None:
    """Operator override should land on the existing row, not create a new one."""
    request_id = str(uuid.UUID(int=(0xAAAAAAAA00000000 << 64) | uuid.uuid4().int & ((1 << 64) - 1)))
    base = DecisionResult(
        decision=Decision.MANUAL_CHECK,
        reason=DecisionReason.AMBIGUOUS_RANGE,
        age_low=17,
        age_high=22,
        threshold_used=18,
        buffer_used=3,
        face_confidence=0.91,
    )
    await audit_repo.write_log(
        request_id=request_id, store_id=TEST_STORE_ID, result=base
    )

    ok = await audit_repo.attach_override(
        request_id=request_id,
        final_decision="pass",
        note="ID verified: 1995-04-12",
    )
    assert ok, "attach_override returned False — request_id not found?"

    rows = await audit_repo.query(
        AuditQuery(store_id=TEST_STORE_ID, limit=20, offset=0)
    )
    target = next((r for r in rows if r.id == request_id), None)
    assert target is not None
    assert target.operator_override == "pass"
    assert target.operator_note == "ID verified: 1995-04-12"
