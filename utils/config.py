import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load local .env file if present (without overriding explicit environment variables)
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
else:
    load_dotenv()


class Config:
    """Central configuration class for test settings, credentials, and controlled geolocation."""

    BASE_URL: str = os.getenv("BASE_URL", "https://staging.roadtriptribes.com").rstrip("/")
    LOGIN_URL: str = f"{BASE_URL}/login"
    PLANNER_URL: str = f"{BASE_URL}/home"

    # Credentials (Must be provided via environment variables or local .env)
    TEST_EMAIL: str = os.getenv("RTT_TEST_EMAIL", os.getenv("TEST_EMAIL", "")).strip()
    TEST_PASSWORD: str = os.getenv("RTT_TEST_PASSWORD", os.getenv("TEST_PASSWORD", "")).strip()

    # Browser execution settings
    BROWSER: str = os.getenv("BROWSER", "chrome").lower().strip()
    HEADLESS: bool = os.getenv("HEADLESS", "false").lower() in ("true", "1", "yes")
    EXPLICIT_TIMEOUT: int = int(os.getenv("EXPLICIT_TIMEOUT", "20"))
    IMPLICIT_TIMEOUT: int = int(os.getenv("IMPLICIT_TIMEOUT", "10"))

    # Controlled Geolocation Settings (Optional for deterministic location testing)
    _raw_lat = os.getenv("RTT_GEO_LATITUDE", "").strip()
    _raw_lon = os.getenv("RTT_GEO_LONGITUDE", "").strip()
    _raw_acc = os.getenv("RTT_GEO_ACCURACY", "10").strip()

    GEO_LATITUDE: Optional[float] = float(_raw_lat) if _raw_lat else None
    GEO_LONGITUDE: Optional[float] = float(_raw_lon) if _raw_lon else None
    GEO_ACCURACY: float = float(_raw_acc) if _raw_acc else 10.0

    # Project directories
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
    REPORTS_DIR: Path = PROJECT_ROOT / "reports"
    SCREENSHOTS_DIR: Path = REPORTS_DIR / "screenshots"

    @classmethod
    def is_geolocation_configured(cls) -> bool:
        """Returns True if both latitude and longitude are defined in config."""
        return cls.GEO_LATITUDE is not None and cls.GEO_LONGITUDE is not None

    @classmethod
    def validate_geolocation(cls) -> None:
        """
        Validates that configured geolocation values fall within valid geographic bounds:
        - Latitude: -90.0 to 90.0
        - Longitude: -180.0 to 180.0
        - Accuracy: > 0.0
        """
        if cls.is_geolocation_configured():
            lat = cls.GEO_LATITUDE
            lon = cls.GEO_LONGITUDE
            acc = cls.GEO_ACCURACY

            if lat is not None and not (-90.0 <= lat <= 90.0):
                raise ValueError(f"Invalid RTT_GEO_LATITUDE '{lat}': must be between -90.0 and 90.0 degrees.")
            if lon is not None and not (-180.0 <= lon <= 180.0):
                raise ValueError(f"Invalid RTT_GEO_LONGITUDE '{lon}': must be between -180.0 and 180.0 degrees.")
            if acc is not None and acc <= 0:
                raise ValueError(f"Invalid RTT_GEO_ACCURACY '{acc}': must be greater than 0 meters.")

    @classmethod
    def validate_credentials(cls) -> None:
        """
        Validates that required test credentials are set.
        Raises RuntimeError with helpful diagnostic message if credentials are missing.
        """
        missing = []
        if not cls.TEST_EMAIL:
            missing.append("RTT_TEST_EMAIL")
        if not cls.TEST_PASSWORD:
            missing.append("RTT_TEST_PASSWORD")

        if missing:
            raise RuntimeError(
                f"\n[CONFIG ERROR] Missing required test credentials: {', '.join(missing)}.\n"
                f"Please set them in your local .env file (copy from .env.example) or pass them as environment variables.\n"
                f"Example: set RTT_TEST_EMAIL=user@example.com && set RTT_TEST_PASSWORD=secret"
            )


# Automatically validate geolocation values if provided on import
Config.validate_geolocation()
