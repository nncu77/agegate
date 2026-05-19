"""ML pipeline: face detection + alignment + age estimation.

This module wraps InsightFace and MiVOLO behind a clean interface.
The pipeline is **stateful** (models are loaded once at startup) and
**thread-safe for read** (inference can be called from multiple
request handlers concurrently, with the GIL serializing the actual
PyTorch calls).

Why not async I/O for inference?
--------------------------------
Inference is CPU/GPU bound, not I/O bound. Wrapping it in async gives
no concurrency benefit and complicates the code. We run inference
synchronously inside a thread executor (FastAPI handles that via
`run_in_threadpool`) so the event loop stays responsive.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

from app.core.config import settings
from app.core.decision import AgeEstimate

# `insightface` is imported lazily inside warmup()/detect_faces() so
# that `pytest -m "not ml"` (and any non-ML caller) does not pay the
# ~7s cost of loading the InsightFace package at module import time.

logger = logging.getLogger(__name__)


@dataclass
class DetectedFace:
    """A face found by the detector, with the data needed for age estimation.

    `point_age` is the raw age (in years) produced by the detector's
    age head. InsightFace's `buffalo_l` pack runs gender+age inference
    as part of `FaceAnalysis.get()`, so we capture it here rather than
    re-running a second model in `estimate_age()`.
    """

    bbox: tuple[int, int, int, int]  # x1, y1, x2, y2
    aligned_crop: np.ndarray  # the aligned face patch (112x112)
    detection_confidence: float
    point_age: float  # raw model output, before sigma-widening


class AgePipeline:
    """End-to-end pipeline. Lifecycle: instantiate once, call infer() per request.

    Wiring the real models in:
        - InsightFace `FaceAnalysis` for detection + alignment landmarks
        - MiVOLO checkpoint loaded via torch.load for age regression

    The current file is a structural scaffold. The model-loading code is
    intentionally placeholder; see TODO markers below. Wire these in
    during Week 1 once dependencies are pinned (see requirements.txt).
    """

    def __init__(self) -> None:
        self._face_analyzer = None  # InsightFace FaceAnalysis instance
        self._age_model = None  # MiVOLO model instance
        self._ready = False

    async def warmup(self) -> None:
        """Load models and run a dummy inference to JIT warm caches.

        Called at FastAPI startup. Failing here means the service is
        unhealthy — better to crash on boot than serve broken responses.
        """
        logger.info("Loading ML models...")
        from insightface.app import FaceAnalysis

        use_gpu = settings.inference_device != "cpu"
        providers = (
            ["CUDAExecutionProvider", "CPUExecutionProvider"]
            if use_gpu
            else ["CPUExecutionProvider"]
        )
        self._face_analyzer = FaceAnalysis(
            name=settings.insightface_pack,
            root=settings.model_cache_dir,
            providers=providers,
        )
        # ctx_id=-1 for CPU, 0 for GPU 0 per InsightFace docs.
        self._face_analyzer.prepare(
            ctx_id=0 if use_gpu else -1,
            det_size=(640, 640),
        )

        # MiVOLO age model is wired in WEEK1-04.

        # Warmup: a single inference allocates ONNX buffers so the first
        # real request doesn't pay the cold-start cost.
        dummy = np.zeros((640, 640, 3), dtype=np.uint8)
        _ = self._face_analyzer.get(dummy)

        self._ready = True
        logger.info("ML models ready")

    def is_ready(self) -> bool:
        return self._ready

    def detect_faces(self, image: np.ndarray) -> list[DetectedFace]:
        """Run face detection on a BGR image. Returns 0+ faces.

        Faces below `face_detection_min_confidence` are filtered out at
        this stage — we don't want them propagating to age estimation.
        """
        if not self._ready:
            raise RuntimeError("Pipeline not ready; call warmup() first")

        from insightface.utils.face_align import norm_crop

        raw_faces = self._face_analyzer.get(image)
        min_conf = settings.face_detection_min_confidence
        result: list[DetectedFace] = []
        kept_scores: list[float] = []
        for f in raw_faces:
            score = float(f.det_score)
            if score < min_conf:
                continue
            aligned = norm_crop(image, landmark=f.kps)
            result.append(
                DetectedFace(
                    bbox=tuple(int(x) for x in f.bbox),
                    aligned_crop=aligned,
                    detection_confidence=score,
                    point_age=float(f.age),
                )
            )
            kept_scores.append(score)
        logger.info(
            "detect_faces: raw=%d kept=%d min_conf=%.2f scores=%s",
            len(raw_faces),
            len(result),
            min_conf,
            [round(s, 3) for s in kept_scores],
        )
        return result

    def estimate_age_multi(self, faces: list[DetectedFace]) -> AgeEstimate:
        """Aggregate per-frame age estimates from a burst capture.

        Strategy
        --------
        - point_estimate = median of per-frame `point_age`
          (median rather than mean: one bad frame doesn't drag it)
        - sigma = max(MIN_SIGMA, ceil(1.5 * stdev))
          (data-driven uncertainty: tight band when frames agree,
          wide band when they don't — wider band → more MANUAL_CHECK)
        - face_confidence = max of per-frame detection confidence
          (best frame represents our actual evidence quality)

        Why median + std rather than fixed sigma=4 (single-frame mode)?
        ---------------------------------------------------------------
        Single-frame estimate_age() can only guess uncertainty from
        published model MAE. With multiple frames we have an *empirical*
        sample of the model's variance on THIS face, which is far more
        meaningful than a population-level prior.
        """
        if not self._ready:
            raise RuntimeError("Pipeline not ready; call warmup() first")
        if not faces:
            raise ValueError("estimate_age_multi requires at least one face")

        import math
        import statistics

        ages = [f.point_age for f in faces]
        confs = [f.detection_confidence for f in faces]
        point = statistics.median(ages)
        stdev = statistics.pstdev(ages) if len(ages) > 1 else 0.0
        sigma = max(2, math.ceil(1.5 * stdev))

        return AgeEstimate(
            age_low=max(0, int(round(point - sigma))),
            age_high=int(round(point + sigma)),
            point_estimate=point,
            face_confidence=max(confs),
        )

    def estimate_age(self, face: DetectedFace) -> AgeEstimate:
        """Convert the detector's raw age into a conservative [low, high] range.

        Source of point_age
        -------------------
        We use the genderage head bundled with the InsightFace `buffalo_l`
        pack (already loaded during `warmup()`). `FaceAnalysis.get()` runs
        it once per detected face, so the value is captured into
        `DetectedFace.point_age` during `detect_faces()` — this method
        does not run a second inference pass.

        Why InsightFace built-in rather than MiVOLO / DeepFace
        -------------------------------------------------------
        - MiVOLO: pretrained weights ship under research-only license
          (problematic for any deployment story). Pulled.
        - DeepFace: clean license but drags TensorFlow + keras + own
          model-weight downloads; one of the weight downloads failed
          on Windows during install. Pulled.
        - InsightFace genderage: already loaded, zero extra dependency,
          accuracy adequate for a *conservative* policy where the
          buffer absorbs estimator drift.

        Sigma choice
        ------------
        We widen the point estimate to `[point - sigma, point + sigma]`
        with `sigma_years = 4`. The genderage head's documented MAE on
        adults is ~4–5 years; ±4 is a 1-sigma window. The decision
        policy already adds its own `buffer_years` (default 3), so this
        sigma is intentionally *not* asking the model to be more
        confident than it is — it shifts borderline cases to
        MANUAL_CHECK rather than risking false PASS.

        Known limitations
        -----------------
        - Black-and-white / pre-WWII photographs read systematically
          older than ground truth (training distribution skew). See
          `tests/test_pipeline_age.py` tolerance comment.
        - Demographic bias is documented in `docs/decision-policy.md`
          Future Work section.
        """
        if not self._ready:
            raise RuntimeError("Pipeline not ready; call warmup() first")

        sigma_years = 4
        point_age = face.point_age
        age_low = max(0, int(round(point_age - sigma_years)))
        age_high = int(round(point_age + sigma_years))

        return AgeEstimate(
            age_low=age_low,
            age_high=age_high,
            point_estimate=point_age,
            face_confidence=face.detection_confidence,
        )

    def select_target_face(
        self,
        faces: list[DetectedFace],
        operator_selection: Optional[int] = None,
    ) -> Optional[DetectedFace]:
        """Choose which face to estimate when multiple are detected.

        Strategy:
            - If operator passed an explicit index, use that.
            - Otherwise return the face with the largest bbox area
              (closest to camera = the actual customer).
            - If multiple faces have similar size (within 20%), refuse
              to auto-select — return None so the caller can flag
              MULTIPLE_FACES and prompt the operator.
        """
        if not faces:
            return None
        if operator_selection is not None:
            if 0 <= operator_selection < len(faces):
                return faces[operator_selection]
            return None
        if len(faces) == 1:
            return faces[0]

        def area(f: DetectedFace) -> int:
            x1, y1, x2, y2 = f.bbox
            return (x2 - x1) * (y2 - y1)

        ranked = sorted(faces, key=area, reverse=True)
        largest, second = area(ranked[0]), area(ranked[1])
        if second / largest > 0.8:
            # Ambiguous; let the human pick.
            return None
        return ranked[0]
