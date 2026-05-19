"""Smoke tests for InsightFace wiring in app/ml/pipeline.py.

ML imports are deferred to function bodies — collection of this module
must not trigger torch / onnxruntime load (see tests/conftest.py).
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING

import numpy as np
import pytest

if TYPE_CHECKING:
    from app.ml.pipeline import AgePipeline


@pytest.mark.ml
def test_warmup_initializes_face_analyzer(ml_pipeline: "AgePipeline") -> None:
    """After warmup() the pipeline is ready and the analyzer is loaded."""
    assert ml_pipeline.is_ready() is True
    assert ml_pipeline._face_analyzer is not None


@pytest.mark.ml
def test_detect_faces_returns_empty_on_blank_image(
    ml_pipeline: "AgePipeline",
) -> None:
    """A pure-black 640x640 frame has no face — must return [], not None."""
    blank = np.zeros((640, 640, 3), dtype=np.uint8)
    result = ml_pipeline.detect_faces(blank)
    assert result == []
    assert isinstance(result, list)


@pytest.mark.ml
def test_detect_faces_finds_face_in_fixture(
    ml_pipeline: "AgePipeline",
    has_face_image_path: Path,
) -> None:
    """A real face image should yield at least one DetectedFace."""
    import cv2

    img = cv2.imread(str(has_face_image_path))
    assert img is not None, f"Failed to load {has_face_image_path}"
    result = ml_pipeline.detect_faces(img)
    assert len(result) >= 1
    face = result[0]
    # 112x112 aligned crop per InsightFace norm_crop default
    assert face.aligned_crop.shape == (112, 112, 3)
    assert 0.0 <= face.detection_confidence <= 1.0
    # point_age comes from InsightFace's genderage head, populated
    # during detection. Used by estimate_age() without a second
    # inference pass.
    assert 0 < face.point_age < 120


def test_detect_faces_filters_below_min_confidence(monkeypatch) -> None:
    """Faces with det_score < min_confidence are dropped before alignment.

    Pure unit test: the analyzer is mocked so this is fast and doesn't
    require the ml fixture / model download.
    """
    from app.core.config import settings
    from app.ml.pipeline import AgePipeline

    monkeypatch.setattr(settings, "face_detection_min_confidence", 0.7)

    pipeline = AgePipeline()
    pipeline._ready = True
    fake_low = SimpleNamespace(
        det_score=0.4,
        kps=np.zeros((5, 2), dtype=np.float32),
        bbox=np.array([0, 0, 10, 10], dtype=np.float32),
    )
    pipeline._face_analyzer = SimpleNamespace(get=lambda _img: [fake_low])

    out = pipeline.detect_faces(np.zeros((100, 100, 3), dtype=np.uint8))
    assert out == []


def test_detect_faces_raises_when_not_ready() -> None:
    """Calling detect_faces before warmup() must fail loudly, not silently."""
    from app.ml.pipeline import AgePipeline

    pipeline = AgePipeline()
    with pytest.raises(RuntimeError, match="warmup"):
        pipeline.detect_faces(np.zeros((100, 100, 3), dtype=np.uint8))
