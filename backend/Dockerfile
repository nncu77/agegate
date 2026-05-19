# Multi-stage build to keep the runtime image small.
# Stage 1 installs Python deps (heavy: torch + onnxruntime).
# Stage 2 copies the venv + app code + pre-downloads ML weights so
# the first request after a cold start doesn't pay model-download cost.
#
# Targets: Hugging Face Spaces (default port 7860, runs as uid 1000),
# Railway, Render, local `docker run`. PORT env var overrides default.

FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements.txt

# Pre-download InsightFace buffalo_l so the image is self-contained.
# Without this, first cold start downloads ~280MB which is slow and
# subject to upstream availability.
RUN mkdir -p /opt/models && \
    /opt/venv/bin/python -c "import os; os.environ['INSIGHTFACE_HOME']='/opt/models'; from insightface.app import FaceAnalysis; fa = FaceAnalysis(name='buffalo_l', root='/opt/models', providers=['CPUExecutionProvider']); fa.prepare(ctx_id=-1, det_size=(640,640))"

# ---

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# HF Spaces and most container hosts run as a non-root user. Create
# one with uid 1000 (HF's default) and own the writable dirs.
RUN useradd -m -u 1000 appuser

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder --chown=appuser:appuser /opt/models /home/appuser/.insightface

WORKDIR /app
COPY --chown=appuser:appuser app ./app

USER appuser

# HF Spaces defaults to 7860; honor whatever PORT the host sets.
ENV PORT=7860 \
    MODEL_CACHE_DIR=/home/appuser/.insightface
EXPOSE 7860

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
