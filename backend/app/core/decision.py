"""Conservative decision policy for age verification.

This module is the heart of AgeGate. It translates the probabilistic output
of an age estimation model into a discrete operational decision.

Design principles
-----------------
1. **Asymmetric risk**: false-negatives (letting a minor through) carry
   legal liability for the merchant. False-positives (asking a 30-year-old
   for ID) cause minor inconvenience. The policy is deliberately biased
   toward MANUAL_CHECK rather than PASS.

2. **No point estimates**: we never collapse the age range into a single
   number for the decision. The full [low, high] interval drives the call.

3. **Operator override**: every MANUAL_CHECK can be resolved by the
   operator, and that resolution is what gets logged for audit. The model
   informs; the human decides.

4. **Explainability**: every decision returns the rule that fired, so the
   operator UI can show "why" — and so audit logs are interpretable years
   later.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Literal


class Decision(str, Enum):
    """Three possible outcomes of an age check."""

    PASS = "pass"  # Clearly above threshold — green light
    REJECT = "reject"  # Clearly below threshold — red light
    MANUAL_CHECK = "manual_check"  # Ambiguous — operator must verify ID


class DecisionReason(str, Enum):
    """Machine-readable explanation of which rule fired."""

    CLEARLY_OVER = "clearly_over_threshold"
    CLEARLY_UNDER = "clearly_under_threshold"
    AMBIGUOUS_RANGE = "range_straddles_threshold"
    LOW_CONFIDENCE = "face_detection_confidence_too_low"
    NO_FACE = "no_face_detected"
    MULTIPLE_FACES = "multiple_faces_no_target_selected"


@dataclass(frozen=True)
class AgeEstimate:
    """Output of the ML pipeline before policy is applied."""

    age_low: int
    age_high: int
    point_estimate: float  # for display/logging only, NEVER for decision
    face_confidence: float  # 0.0 – 1.0


@dataclass(frozen=True)
class PolicyConfig:
    """Per-store policy configuration.

    Stored in `policies` table, fetched per request based on store_id.
    """

    threshold_age: int  # Legal minimum age (18 or 20 in Taiwan)
    buffer_years: int  # Extra safety margin above threshold for PASS
    min_face_confidence: float  # Below this, refuse to decide

    def __post_init__(self) -> None:
        # Defensive validation — these come from DB and might be edited
        # by a store admin. We refuse to operate on nonsense.
        if self.threshold_age < 0 or self.threshold_age > 100:
            raise ValueError(f"Invalid threshold_age: {self.threshold_age}")
        if self.buffer_years < 0 or self.buffer_years > 20:
            raise ValueError(f"Invalid buffer_years: {self.buffer_years}")
        if not 0.0 <= self.min_face_confidence <= 1.0:
            raise ValueError(f"Invalid min_face_confidence: {self.min_face_confidence}")


@dataclass(frozen=True)
class DecisionResult:
    """Final output returned to the operator UI and audit log."""

    decision: Decision
    reason: DecisionReason
    age_low: int
    age_high: int
    threshold_used: int
    buffer_used: int
    face_confidence: float

    def to_dict(self) -> dict:
        return {
            "decision": self.decision.value,
            "reason": self.reason.value,
            "age_low": self.age_low,
            "age_high": self.age_high,
            "threshold_used": self.threshold_used,
            "buffer_used": self.buffer_used,
            "face_confidence": round(self.face_confidence, 3),
        }


def decide(estimate: AgeEstimate, policy: PolicyConfig) -> DecisionResult:
    """Apply the conservative decision policy.

    Decision table:

        face_confidence < min_face_confidence
            → MANUAL_CHECK (LOW_CONFIDENCE)
        age_high < threshold
            → REJECT (CLEARLY_UNDER)
        age_low >= threshold + buffer
            → PASS (CLEARLY_OVER)
        otherwise (range overlaps or sits in buffer zone)
            → MANUAL_CHECK (AMBIGUOUS_RANGE)

    Rationale: we only PASS when the *lower* bound of the estimate is
    comfortably above the legal threshold. Anything that touches or
    crosses the threshold gets escalated to a human — even if the point
    estimate "looks fine" — because age estimation models systematically
    underestimate or overestimate certain demographics, and we cannot
    afford that error at the threshold.
    """
    # Rule 1: Low face detection confidence — refuse to estimate.
    # The face might be occluded, angled, motion-blurred, or just not a
    # face. We won't pretend to know.
    if estimate.face_confidence < policy.min_face_confidence:
        return DecisionResult(
            decision=Decision.MANUAL_CHECK,
            reason=DecisionReason.LOW_CONFIDENCE,
            age_low=estimate.age_low,
            age_high=estimate.age_high,
            threshold_used=policy.threshold_age,
            buffer_used=policy.buffer_years,
            face_confidence=estimate.face_confidence,
        )

    # Rule 2: Clearly under. Even the upper bound of our estimate is
    # below the legal threshold. Reject with confidence — but the
    # operator can still override (this is logged separately).
    if estimate.age_high < policy.threshold_age:
        return DecisionResult(
            decision=Decision.REJECT,
            reason=DecisionReason.CLEARLY_UNDER,
            age_low=estimate.age_low,
            age_high=estimate.age_high,
            threshold_used=policy.threshold_age,
            buffer_used=policy.buffer_years,
            face_confidence=estimate.face_confidence,
        )

    # Rule 3: Clearly over. The lower bound exceeds threshold + buffer.
    # We are confident enough to pass without manual ID check.
    safe_floor = policy.threshold_age + policy.buffer_years
    if estimate.age_low >= safe_floor:
        return DecisionResult(
            decision=Decision.PASS,
            reason=DecisionReason.CLEARLY_OVER,
            age_low=estimate.age_low,
            age_high=estimate.age_high,
            threshold_used=policy.threshold_age,
            buffer_used=policy.buffer_years,
            face_confidence=estimate.face_confidence,
        )

    # Rule 4: Ambiguous. The range straddles either the threshold itself
    # or the buffer zone. Send to human verification.
    return DecisionResult(
        decision=Decision.MANUAL_CHECK,
        reason=DecisionReason.AMBIGUOUS_RANGE,
        age_low=estimate.age_low,
        age_high=estimate.age_high,
        threshold_used=policy.threshold_age,
        buffer_used=policy.buffer_years,
        face_confidence=estimate.face_confidence,
    )


def no_face_result(policy: PolicyConfig) -> DecisionResult:
    """Special case: no face detected in the frame."""
    return DecisionResult(
        decision=Decision.MANUAL_CHECK,
        reason=DecisionReason.NO_FACE,
        age_low=0,
        age_high=0,
        threshold_used=policy.threshold_age,
        buffer_used=policy.buffer_years,
        face_confidence=0.0,
    )


def multiple_faces_result(policy: PolicyConfig) -> DecisionResult:
    """Special case: multiple faces, no target selection from operator."""
    return DecisionResult(
        decision=Decision.MANUAL_CHECK,
        reason=DecisionReason.MULTIPLE_FACES,
        age_low=0,
        age_high=0,
        threshold_used=policy.threshold_age,
        buffer_used=policy.buffer_years,
        face_confidence=0.0,
    )
