"""Application configuration loaded from environment variables."""
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Override via environment or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- API ---
    api_env: str = Field(default="development", description="development | production")
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"],
        description="Allowed origins for the operator UI",
    )

    # --- Supabase ---
    supabase_url: str = ""
    supabase_service_key: str = ""  # Server-side only. Never expose to client.
    supabase_jwt_secret: str = ""

    # --- ML ---
    # Where InsightFace / MiVOLO weights are mounted. In Railway/Render,
    # mount a volume here so models are not re-downloaded on every deploy.
    model_cache_dir: str = "/var/cache/agegate/models"

    # Model identifiers. We default to the standard buffalo_l pack for
    # InsightFace (good accuracy/size tradeoff). MiVOLO is loaded from a
    # checkpoint path; see docs/ml-models.md.
    insightface_pack: str = "buffalo_l"
    mivolo_checkpoint: str = "mivolo_d1.pth"

    # Inference device. "cpu" for cheap deployment, "cuda" if GPU available.
    inference_device: str = "cpu"

    # Confidence threshold for face detection. Below this, we refuse to
    # produce an age estimate at all and ask the operator to retake.
    face_detection_min_confidence: float = 0.7

    # --- Decision policy defaults ---
    # These are policy defaults; per-store overrides live in the DB.
    default_threshold_age: int = 18
    default_buffer_years: int = 3


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance. Safe across the process."""
    return Settings()


settings = get_settings()
