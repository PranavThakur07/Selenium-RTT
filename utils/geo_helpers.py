from typing import Optional
from selenium.webdriver.remote.webdriver import WebDriver
from utils.logger import get_logger

logger = get_logger("GeoHelpers")


class GeoHelpers:
    """Helper utilities for CDP-based controlled browser geolocation override."""

    @staticmethod
    def configure_browser_geolocation(
        driver: WebDriver,
        latitude: float,
        longitude: float,
        accuracy: float = 10.0,
        origin: str = "https://staging.roadtriptribes.com"
    ) -> bool:
        """
        Grants geolocation permission and overrides the browser geolocation using
        Chrome DevTools Protocol (CDP) for deterministic location-based testing.
        """
        if not hasattr(driver, "execute_cdp_cmd"):
            logger.warning("Current WebDriver does not support CDP commands. Geolocation override skipped.")
            return False

        try:
            # 1. Grant geolocation permissions for target origin
            driver.execute_cdp_cmd(
                "Browser.grantPermissions",
                {
                    "origin": origin,
                    "permissions": ["geolocation"]
                }
            )

            # 2. Override geolocation coordinates and accuracy
            driver.execute_cdp_cmd(
                "Emulation.setGeolocationOverride",
                {
                    "latitude": latitude,
                    "longitude": longitude,
                    "accuracy": accuracy
                }
            )

            # Log required configuration format without credentials
            logger.info(
                f"Geolocation enabled:\n"
                f"Latitude: {latitude}\n"
                f"Longitude: {longitude}\n"
                f"Accuracy: {accuracy} meters"
            )
            return True

        except Exception as e:
            logger.warning(f"Failed to configure CDP geolocation override: {e}")
            return False

    @staticmethod
    def clear_browser_geolocation(driver: WebDriver) -> bool:
        """Clears any active CDP geolocation override."""
        if hasattr(driver, "execute_cdp_cmd"):
            try:
                driver.execute_cdp_cmd("Emulation.clearGeolocationOverride", {})
                logger.info("CDP Geolocation override cleared.")
                return True
            except Exception as e:
                logger.warning(f"Failed to clear CDP geolocation override: {e}")
        return False
