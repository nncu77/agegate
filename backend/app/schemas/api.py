"""Pydantic schemas for API requests and responses."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class VerifyRequest(BaseModel):
    """Image(s) submitted for age verification.

    Send either a single `image_base64` (legacy single-frame mode) or
    `image_base64_frames` (a short burst of frames captured within ~0.5s).
    Multi-frame mode aggregates per-frame age estimates via median and
    derives the uncertainty interval from inter-frame standard deviation
    — tighter when the model is consistent, wider when it disagrees with
    itself. This honestly surfaces model uncertainty while reducing the
    "single bad frame" noise that plagues single-shot estimation.
    """

    image_base64: Optional[str] = Field(
        default=None,
        description="Single base64-encoded JPEG/PNG (legacy single-frame mode)",
    )
    image_base64_frames: Optional[list[str]] = Field(
        default=None,
        description="Burst of base64 frames (multi-frame mode); 2–10 frames recommended",
    )
    store_id: str = Field(..., description="UUID of the store making the request")
    operator_face_index: Optional[int] = Field(
        default=None,
        description="If multiple faces detected, operator can pick one by index",
    )


class VerifyResponse(BaseModel):
    """Decision returned to the operator UI."""

    request_id: str
    decision: str  # 'pass' | 'reject' | 'manual_check'
    reason: str
    age_low: int
    age_high: int
    threshold_used: int
    buffer_used: int
    face_confidence: float
    multiple_faces_detected: bool = False


class OperatorOverrideRequest(BaseModel):
    """Operator records the result of their manual ID check."""

    request_id: str
    final_decision: str = Field(..., pattern="^(pass|reject)$")
    operator_note: Optional[str] = Field(default=None, max_length=500)


class AuditLogEntry(BaseModel):
    """One row of the audit trail."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    store_id: str
    timestamp: datetime
    decision: str
    reason: str
    age_low: int
    age_high: int
    face_confidence: float
    threshold_used: int
    buffer_used: int
    operator_override: Optional[str] = None
    operator_note: Optional[str] = None


class AuditQuery(BaseModel):
    """Filters for audit log queries."""

    store_id: str
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    decision: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class PolicyUpdate(BaseModel):
    """Update a store's verification policy."""

    threshold_age: int = Field(..., ge=0, le=100)
    buffer_years: int = Field(..., ge=0, le=20)
    min_face_confidence: float = Field(..., ge=0.0, le=1.0)


class PolicyResponse(BaseModel):
    """Current policy for a store."""

    store_id: str
    threshold_age: int
    buffer_years: int
    min_face_confidence: float
    updated_at: datetime
