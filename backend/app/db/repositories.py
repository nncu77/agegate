"""Database repositories.

Thin wrappers around the Supabase Python client. Kept separate from the
API layer so that:
    - swapping DB implementations later (raw asyncpg, SQLAlchemy) only
      touches this file
    - tests can substitute fakes via dependency injection
    - the API code doesn't deal with SQL or table names directly

USE_FAKE_DB
-----------
When the env var `USE_FAKE_DB=true` is set, every method returns
hardcoded scaffold data and writes/updates are no-ops. This lets the
ML-integration test suite (`pytest -m ml`) run without a Supabase
connection — handy in CI and on dev machines without credentials.
The flag is read fresh on each call so tests can monkey-patch it.

Error policy
------------
`write_log` is fire-and-forget: failures are logged but never raised,
because losing a single audit row must not break the user-facing
request (the verification result still goes back to the operator).
Read methods, in contrast, return None / [] on failure so callers can
decide explicitly how to react.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Optional

from app.core.decision import DecisionResult
from app.db.client import get_supabase
from app.schemas.api import AuditLogEntry, AuditQuery, PolicyResponse

logger = logging.getLogger(__name__)


def _use_fake() -> bool:
    return os.environ.get("USE_FAKE_DB", "").lower() in ("1", "true", "yes")


class PolicyRepository:
    async def get_for_store(self, store_id: str) -> Optional[PolicyResponse]:
        """Return the active policy for a store, or None if not configured."""
        if _use_fake():
            return PolicyResponse(
                store_id=store_id,
                threshold_age=18,
                buffer_years=3,
                min_face_confidence=0.7,
                updated_at=datetime.utcnow(),
            )
        try:
            sb = get_supabase()
            res = (
                sb.table("policies")
                .select("*")
                .eq("store_id", store_id)
                .maybe_single()
                .execute()
            )
            if res is None or res.data is None:
                return None
            return PolicyResponse(**res.data)
        except Exception:
            logger.exception("policy_repo.get_for_store failed store_id=%s", store_id)
            return None

    async def upsert(
        self,
        store_id: str,
        threshold_age: int,
        buffer_years: int,
        min_face_confidence: float,
    ) -> PolicyResponse:
        if _use_fake():
            return PolicyResponse(
                store_id=store_id,
                threshold_age=threshold_age,
                buffer_years=buffer_years,
                min_face_confidence=min_face_confidence,
                updated_at=datetime.utcnow(),
            )
        sb = get_supabase()
        res = (
            sb.table("policies")
            .upsert(
                {
                    "store_id": store_id,
                    "threshold_age": threshold_age,
                    "buffer_years": buffer_years,
                    "min_face_confidence": min_face_confidence,
                },
                on_conflict="store_id",
            )
            .execute()
        )
        if not res.data:
            raise RuntimeError("policy upsert returned no rows")
        return PolicyResponse(**res.data[0])


class AuditRepository:
    async def write_log(
        self,
        request_id: str,
        store_id: str,
        result: DecisionResult,
    ) -> None:
        """Persist a single audit entry. Failures are logged but swallowed."""
        if _use_fake():
            return
        try:
            sb = get_supabase()
            sb.table("audit_logs").insert(
                {
                    "id": request_id,
                    "store_id": store_id,
                    "decision": result.decision.value,
                    "reason": result.reason.value,
                    "age_low": result.age_low,
                    "age_high": result.age_high,
                    "face_confidence": result.face_confidence,
                    "threshold_used": result.threshold_used,
                    "buffer_used": result.buffer_used,
                }
            ).execute()
        except Exception:
            # NEVER raise: a verify call has already committed to a decision;
            # losing the audit row is bad but not fatal to the user response.
            logger.exception(
                "audit_repo.write_log failed request_id=%s store_id=%s",
                request_id,
                store_id,
            )

    async def attach_override(
        self,
        request_id: str,
        final_decision: str,
        note: Optional[str],
    ) -> bool:
        """Update an existing audit row with the operator's verdict.

        Returns True if a row was found and updated, False otherwise.
        """
        if _use_fake():
            return True
        try:
            sb = get_supabase()
            res = (
                sb.table("audit_logs")
                .update(
                    {
                        "operator_override": final_decision,
                        "operator_note": note,
                        "operator_acted_at": datetime.utcnow().isoformat(),
                    }
                )
                .eq("id", request_id)
                .execute()
            )
            return bool(res.data)
        except Exception:
            logger.exception(
                "audit_repo.attach_override failed request_id=%s", request_id
            )
            return False

    async def query(self, query: AuditQuery) -> list[AuditLogEntry]:
        if _use_fake():
            return []
        try:
            sb = get_supabase()
            q = sb.table("audit_logs").select("*").eq("store_id", query.store_id)
            if query.from_date:
                q = q.gte("timestamp", query.from_date.isoformat())
            if query.to_date:
                q = q.lte("timestamp", query.to_date.isoformat())
            if query.decision:
                q = q.eq("decision", query.decision)
            q = q.order("timestamp", desc=True).range(
                query.offset, query.offset + query.limit - 1
            )
            res = q.execute()
            return [AuditLogEntry(**row) for row in (res.data or [])]
        except Exception:
            logger.exception("audit_repo.query failed store_id=%s", query.store_id)
            return []


policy_repo = PolicyRepository()
audit_repo = AuditRepository()
