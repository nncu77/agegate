"""Verify endpoint: the main entry point for age checks.

Request flow:
    1. Decode image
    2. Detect faces
    3. Select target face
    4. Estimate age
    5. Apply decision policy
    6. Write audit log
    7. Return decision

Important: the original image is NEVER persisted. It exists only in
process memory during this request.
"""
import base64
import logging
import uuid
from io import BytesIO

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Request, status
from PIL import Image

from app.core.decision import (
    AgeEstimate,
    PolicyConfig,
    decide,
    multiple_faces_result,
    no_face_result,
)
from app.db.repositories import audit_repo, policy_repo
from app.ml.pipeline import AgePipeline
from app.schemas.api import VerifyRequest, VerifyResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# Sanity ceiling for incoming images. Operators are uploading webcam
# frames; anything bigger is either malicious or a misconfigured client.
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB decoded


def get_pipeline(request: Request) -> AgePipeline:
    """FastAPI dependency: pull the shared pipeline off app.state."""
    return request.app.state.pipeline


def _decode_image(b64: str) -> np.ndarray:
    """Decode base64 image into a BGR numpy array.

    Accepts data-URL prefixes (data:image/jpeg;base64,...) or raw base64.
    """
    if "," in b64:
        b64 = b64.split(",", 1)[1]

    try:
        raw = base64.b64decode(b64, validate=True)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid base64: {e}",
        )

    if len(raw) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image exceeds {MAX_IMAGE_BYTES} bytes",
        )

    try:
        img = Image.open(BytesIO(raw)).convert("RGB")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot decode image: {e}",
        )

    # InsightFace expects BGR (OpenCV convention)
    arr = np.array(img)[:, :, ::-1].copy()
    return arr


@router.post("/verify", response_model=VerifyResponse)
async def verify(
    payload: VerifyRequest,
    pipeline: AgePipeline = Depends(get_pipeline),
) -> VerifyResponse:
    request_id = str(uuid.uuid4())
    logger.info(
        "verify request_id=%s store_id=%s", request_id, payload.store_id
    )

    # 1. Load this store's policy. If the store doesn't exist or the
    #    policy is missing, refuse — don't fall back to defaults silently.
    policy_row = await policy_repo.get_for_store(payload.store_id)
    if policy_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No policy configured for this store",
        )
    policy = PolicyConfig(
        threshold_age=policy_row.threshold_age,
        buffer_years=policy_row.buffer_years,
        min_face_confidence=policy_row.min_face_confidence,
    )

    # 2. Decode image(s). Multi-frame mode: each frame is decoded and a
    #    per-frame target face is picked. Single-frame mode: same as before.
    frames_b64 = payload.image_base64_frames or (
        [payload.image_base64] if payload.image_base64 else []
    )
    if not frames_b64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either image_base64 or image_base64_frames is required",
        )

    images = [_decode_image(b) for b in frames_b64]

    # 3. Detect faces per frame, collect target faces from each frame.
    per_frame_faces = [pipeline.detect_faces(img) for img in images]
    multiple_detected = any(len(f) > 1 for f in per_frame_faces)

    # All frames found no face → MANUAL_CHECK (NO_FACE).
    if not any(per_frame_faces):
        result = no_face_result(policy)
        await audit_repo.write_log(
            request_id=request_id, store_id=payload.store_id, result=result
        )
        return VerifyResponse(
            request_id=request_id,
            **result.to_dict(),
            multiple_faces_detected=False,
        )

    # 4. Pick a target face per frame (drop frames where selection is ambiguous).
    targets = []
    for f in per_frame_faces:
        if not f:
            continue
        t = pipeline.select_target_face(
            f, operator_selection=payload.operator_face_index
        )
        if t is not None:
            targets.append(t)

    if not targets:
        result = multiple_faces_result(policy)
        await audit_repo.write_log(
            request_id=request_id, store_id=payload.store_id, result=result
        )
        return VerifyResponse(
            request_id=request_id,
            **result.to_dict(),
            multiple_faces_detected=True,
        )

    # 5. Aggregate-estimate when burst mode; single-frame path otherwise.
    if len(targets) > 1:
        estimate: AgeEstimate = pipeline.estimate_age_multi(targets)
    else:
        estimate = pipeline.estimate_age(targets[0])

    # 6. Decide
    result = decide(estimate, policy)

    # 7. Audit log (image is discarded here — only the result is kept)
    await audit_repo.write_log(
        request_id=request_id,
        store_id=payload.store_id,
        result=result,
    )

    # 8. Images go out of scope. GC will collect them. No persistence.
    del images, per_frame_faces, targets

    return VerifyResponse(
        request_id=request_id,
        **result.to_dict(),
        multiple_faces_detected=multiple_detected,
    )
