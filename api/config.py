"""Application configuration — loaded from environment variables."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# ── Server ──
API_HOST: str = os.getenv("AI_INTEL_API_HOST", "127.0.0.1")
API_PORT: int = int(os.getenv("AI_INTEL_API_PORT", "8001"))
CORS_ORIGINS: list[str] = os.getenv(
    "AI_INTEL_CORS_ORIGINS", "https://ai.hjhai.xyz"
).split(",")

# ── Database ──
DB_PATH: Path = Path(
    os.getenv("AI_INTEL_DB_PATH",
              str(Path(__file__).resolve().parent.parent / "data" / "ai_intel.db"))
)

# ── API Keys ──
API_KEY_PREFIX: str = os.getenv("AI_INTEL_API_KEY_PREFIX", "crn_")
API_KEY_LENGTH: int = int(os.getenv("AI_INTEL_API_KEY_LENGTH", "32"))

# ── Limits ──
MAX_ARTICLES_PER_BATCH: int = int(os.getenv("AI_INTEL_MAX_ARTICLES_PER_BATCH", "100"))

# ── Logging ──
LOG_DIR: Path = Path(os.getenv("AI_INTEL_LOG_DIR", "/var/log/ai-intel"))
