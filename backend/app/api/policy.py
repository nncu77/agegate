"""Policy endpoints: per-store age threshold configuration."""
import logging

from fastapi import APIRouter, HTTPException, status

from app.db.repositories import policy_repo
from app.schemas.api import PolicyResponse, PolicyUpdate

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/policy/{store_id}", response_model=PolicyResponse)
async def get_policy(store_id: str) -> PolicyResponse:
    row = await policy_repo.get_for_store(store_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No policy configured for this store",
        )
    return row


@router.put("/policy/{store_id}", response_model=PolicyResponse)
async def update_policy(store_id: str, payload: PolicyUpdate) -> PolicyResponse:
    """Upsert a store's policy.

    Note: changing a policy is logged separately (see audit_repo.log_policy_change)
    so that any post-incident review can correlate the policy in effect
    at the time of a given verification.
    """
    updated = await policy_repo.upsert(
        store_id=store_id,
        threshold_age=payload.threshold_age,
        buffer_years=payload.buffer_years,
        min_face_confidence=payload.min_face_confidence,
    )
    logger.info(
        "policy updated store_id=%s threshold=%s buffer=%s",
        store_id,
        payload.threshold_age,
        payload.buffer_years,
    )
    return updated
