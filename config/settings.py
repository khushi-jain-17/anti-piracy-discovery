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
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()

# Ensure directories exist
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
settings.SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
settings.TAKEDOWN_DIR.mkdir(parents=True, exist_ok=True)
