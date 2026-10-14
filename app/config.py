
import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    app_name: str = os.getenv(
        "APP_NAME",
        "FitBuddy - AI Fitness Plan Generator",
    )
    database_url: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./fitbuddy.db",
    )
    gemini_api_key: str | None = (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
    )
    workout_model: str = os.getenv(
        "GEMINI_WORKOUT_MODEL",
        "gemini-2.5-flash",
    )
    nutrition_model: str = os.getenv(
        "GEMINI_NUTRITION_MODEL",
        "gemini-2.5-flash",
    )
    gemini_fallback_model: str | None = os.getenv(
        "GEMINI_FALLBACK_MODEL"
    )
    use_demo_fallback: bool = (
        os.getenv("USE_DEMO_FALLBACK", "true").lower()
        == "true"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
