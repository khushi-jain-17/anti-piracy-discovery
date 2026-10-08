import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # API Keys
    SERPAPI_API_KEY: str = os.getenv("SERPAPI_API_KEY", "")

    # Pipeline Limits
    MAX_RESULTS_PER_QUERY: int = 10
    CONCURRENCY: int = 3
    
    # Playwright Settings
    HEADLESS: bool = True
    BROWSER_TIMEOUT_MS: int = 30000
    PLAYER_DETECTION_WAIT_SEC: int = 5
    USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )

    # Directories
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    OUTPUT_DIR: Path = BASE_DIR / "outputs"
    SCREENSHOT_DIR: Path = OUTPUT_DIR / "screenshots"
    TAKEDOWN_DIR: Path = OUTPUT_DIR / "takedown_notices"
    LOGO_REFERENCE_DIR: Path = BASE_DIR / "assets" / "reference_logos"
    LOGO_DHASH_THRESHOLD: int = 10   # max Hamming distance (of 64 bits) for dHash match
    LOGO_AHASH_THRESHOLD: int = 16   # max Hamming distance (of 64 bits) for aHash confirmation
    # Redis & Celery Distributed Task Queue Settings
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", "redis://localhost:6379/1"))
    REDIS_CACHE_TTL_SEC: int = 86400  # 24-hour domain classification cache TTL
    CELERY_WORKER_CONCURRENCY: int = 3
    USE_DISTRIBUTED_QUEUE: bool = False
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()

# Ensure directories exist
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
settings.SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
settings.TAKEDOWN_DIR.mkdir(parents=True, exist_ok=True)
