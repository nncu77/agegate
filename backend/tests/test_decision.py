"""Unit tests for the conservative decision policy.

These tests document the policy as much as they verify it. If you're
trying to understand AgeGate's decision behavior, read this file.
"""
import pytest

from app.core.decision import (
    AgeEstimate,
    Decision,
    DecisionReason,
    PolicyConfig,
    decide,
    multiple_faces_result,
    no_face_result,
)


@pytest.fixture
def policy_18() -> PolicyConfig:
    """Standard tobacco/alcohol policy: 18+ with 3-year buffer."""
    return PolicyConfig(
        threshold_age=18,
        buffer_years=3,
        min_face_confidence=0.7,
    )


@pytest.fixture
def policy_20() -> PolicyConfig:
    """E-cigarette policy: 20+ with 3-year buffer."""
    return PolicyConfig(
        threshold_age=20,
        buffer_years=3,
        min_face_confidence=0.7,
    )


def _est(low: int, high: int, conf: float = 0.95) -> AgeEstimate:
    """Helper: build an AgeEstimate with a reasonable point estimate."""
    return AgeEstimate(
        age_low=low,
        age_high=high,
        point_estimate=(low + high) / 2,
        face_confidence=conf,
    )


class TestClearlyOver:
    """Cases that should PASS without manual check."""

    def test_clearly_adult(self, policy_18: PolicyConfig) -> None:
        # 25-32: well above 18+3=21
        result = decide(_est(25, 32), policy_18)
        assert result.decision == Decision.PASS
        assert result.reason == DecisionReason.CLEARLY_OVER

    def test_exactly_at_safe_floor(self, policy_18: PolicyConfig) -> None:
        # age_low == threshold + buffer == 21. Should still pass.
        result = decide(_est(21, 28), policy_18)
        assert result.decision == Decision.PASS

    def test_one_below_safe_floor_is_ambiguous(self, policy_18: PolicyConfig) -> None:
        # age_low = 20: just below the 21 safe floor. Manual.
        result = decide(_est(20, 27), policy_18)
        assert result.decision == Decision.MANUAL_CHECK
        assert result.reason == DecisionReason.AMBIGUOUS_RANGE


class TestClearlyUnder:
    """Cases that should REJECT."""

    def test_clearly_minor(self, policy_18: PolicyConfig) -> None:
        # 10-15: entire range below 18
        result = decide(_est(10, 15), policy_18)
        assert result.decision == Decision.REJECT
        assert result.reason == DecisionReason.CLEARLY_UNDER

    def test_high_equals_threshold_minus_one(self, policy_18: PolicyConfig) -> None:
        # age_high = 17: still entirely below 18
        result = decide(_est(13, 17), policy_18)
        assert result.decision == Decision.REJECT

    def test_high_equals_threshold_is_ambiguous(self, policy_18: PolicyConfig) -> None:
        # age_high = 18: touches the threshold from below. NOT a reject.
        # The estimate might include an 18-year-old; we must verify.
        result = decide(_est(14, 18), policy_18)
        assert result.decision == Decision.MANUAL_CHECK
        assert result.reason == DecisionReason.AMBIGUOUS_RANGE


class TestAmbiguousZone:
    """The interesting cases — where the policy earns its keep."""

    def test_range_straddles_threshold(self, policy_18: PolicyConfig) -> None:
        # 16-22: half below, half above threshold. Must verify.
        result = decide(_est(16, 22), policy_18)
        assert result.decision == Decision.MANUAL_CHECK
        assert result.reason == DecisionReason.AMBIGUOUS_RANGE

    def test_just_above_threshold_in_buffer(self, policy_18: PolicyConfig) -> None:
        # 19-24: above threshold but age_low (19) below safe floor (21).
        # Model thinks they're adult, but with margin too thin to trust.
        result = decide(_est(19, 24), policy_18)
        assert result.decision == Decision.MANUAL_CHECK

    def test_narrow_range_in_buffer_zone(self, policy_18: PolicyConfig) -> None:
        # 18-19: tight range, but right at threshold. Verify.
        result = decide(_est(18, 19), policy_18)
        assert result.decision == Decision.MANUAL_CHECK


class TestLowConfidence:
    """If we can't see the face well, we can't decide."""

    def test_low_confidence_overrides_clear_estimate(
        self, policy_18: PolicyConfig
    ) -> None:
        # Even with an estimate that *looks* clear, low confidence → manual.
        result = decide(_est(25, 32, conf=0.5), policy_18)
        assert result.decision == Decision.MANUAL_CHECK
        assert result.reason == DecisionReason.LOW_CONFIDENCE

    def test_confidence_at_threshold_passes(self, policy_18: PolicyConfig) -> None:
        # Exactly at min_face_confidence → not low confidence
        result = decide(_est(25, 32, conf=0.7), policy_18)
        assert result.decision == Decision.PASS


class TestTwentyThreshold:
    """Same logic with a higher threshold (e-cigarette case)."""

    def test_19_year_old_estimate_rejects(self, policy_20: PolicyConfig) -> None:
        # 17-19: entirely below 20
        result = decide(_est(17, 19), policy_20)
        assert result.decision == Decision.REJECT

    def test_safe_floor_is_23(self, policy_20: PolicyConfig) -> None:
        # threshold 20 + buffer 3 = 23
        result = decide(_est(23, 30), policy_20)
        assert result.decision == Decision.PASS

        result = decide(_est(22, 30), policy_20)
        assert result.decision == Decision.MANUAL_CHECK


class TestSpecialCases:
    def test_no_face(self, policy_18: PolicyConfig) -> None:
        result = no_face_result(policy_18)
        assert result.decision == Decision.MANUAL_CHECK
        assert result.reason == DecisionReason.NO_FACE
        assert result.age_low == 0

    def test_multiple_faces(self, policy_18: PolicyConfig) -> None:
        result = multiple_faces_result(policy_18)
        assert result.decision == Decision.MANUAL_CHECK
        assert result.reason == DecisionReason.MULTIPLE_FACES


class TestPolicyValidation:
    def test_rejects_invalid_threshold(self) -> None:
        with pytest.raises(ValueError):
            PolicyConfig(threshold_age=-1, buffer_years=3, min_face_confidence=0.7)
        with pytest.raises(ValueError):
            PolicyConfig(threshold_age=200, buffer_years=3, min_face_confidence=0.7)

    def test_rejects_invalid_buffer(self) -> None:
        with pytest.raises(ValueError):
            PolicyConfig(threshold_age=18, buffer_years=-1, min_face_confidence=0.7)

    def test_rejects_invalid_confidence(self) -> None:
        with pytest.raises(ValueError):
            PolicyConfig(threshold_age=18, buffer_years=3, min_face_confidence=1.5)


class TestSerialization:
    """Pin the audit-log JSON shape — downstream readers depend on it."""

    def test_to_dict_shape_and_confidence_rounding(self, policy_18: PolicyConfig) -> None:
        result = decide(_est(25, 32, conf=0.95123), policy_18)
        assert result.to_dict() == {
            "decision": "pass",
            "reason": "clearly_over_threshold",
            "age_low": 25,
            "age_high": 32,
            "threshold_used": 18,
            "buffer_used": 3,
            "face_confidence": 0.951,
        }
