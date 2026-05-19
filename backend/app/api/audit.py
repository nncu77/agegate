"""Audit endpoints.

GET  /audit          — list audit log entries with filters
POST /audit/override — operator records the outcome of manual ID check
"""
import logging

from fastapi import APIRouter, HTTPException, status

from app.db.repositories import audit_repo
from app.schemas.api import AuditLogEntry, AuditQuery, OperatorOverrideRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/audit/query", response_model=list[AuditLogEntry])
async def query_audit(query: AuditQuery) -> list[AuditLogEntry]:
    """Query audit logs for a store.

    Using POST instead of GET because the filter set is rich and we
    don't want store_id (which is operationally sensitive) in URLs /
    server logs.
    """
    rows = await audit_repo.query(query)
    return rows


@router.post("/audit/override", status_code=status.HTTP_204_NO_CONTENT)
async def operator_override(payload: OperatorOverrideRequest) -> None:
    """Record the operator's final decision after a MANUAL_CHECK.

    This is the human-in-the-loop completion. Without this, a manual_check
    entry in the audit log is incomplete: we know the AI deferred, but
    we don't know what the human decided. Recording the override closes
    that loop and produces a defensible compliance trail.
    """
    updated = await audit_repo.attach_override(
        request_id=payload.request_id,
        final_decision=payload.final_decision,
        note=payload.operator_note,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit entry not found",
        )
