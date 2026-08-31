from typing import Dict, Any, List
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from utils.logger import get_logger

logger = get_logger("MapHelpers")


class MapHelpers:
    """Helper utilities for inspecting Mapbox GL elements, markers, and layers."""

    @staticmethod
    def is_map_canvas_ready(driver: WebDriver) -> bool:
        """
        Verifies that the Mapbox container and WebGL canvas are mounted and rendered.
        """
        try:
            map_container = driver.find_element(By.ID, "map")
            if not map_container.is_displayed():
                return False

            canvas = map_container.find_element(By.CSS_SELECTOR, "canvas.mapboxgl-canvas")
            width = int(canvas.get_attribute("width") or 0)
            height = int(canvas.get_attribute("height") or 0)
            return canvas.is_displayed() and width > 0 and height > 0
        except Exception as e:
            logger.debug(f"Map canvas check exception: {e}")
            return False

    @staticmethod
    def get_map_markers(driver: WebDriver) -> List[Any]:
        """
        Returns all Mapbox marker DOM elements currently rendered on the map.
        """
        try:
            return driver.find_elements(By.CSS_SELECTOR, "#map .mapboxgl-marker")
        except Exception:
            return []

    @staticmethod
    def get_mapbox_diagnostics(driver: WebDriver) -> Dict[str, Any]:
        """
        Performs safe JavaScript inspection of the Mapbox environment and layers.
        Returns a diagnostic dictionary without raising exceptions.
        """
        js_script = """
        const result = {
            hasMapContainer: !!document.getElementById('map'),
            hasCanvas: !!document.querySelector('#map canvas.mapboxgl-canvas'),
            markerCount: document.querySelectorAll('#map .mapboxgl-marker').length,
            mapboxLayers: [],
            hasRouteLayer: false,
            routeDetails: ''
        };

        // Try inspecting window.map if exposed
        try {
            if (window.map && typeof window.map.getStyle === 'function') {
                const style = window.map.getStyle();
                if (style && style.layers) {
                    result.mapboxLayers = style.layers.map(l => ({ id: l.id, type: l.type }));
                    result.hasRouteLayer = style.layers.some(l => 
                        l.id.startsWith('gpx-') || 
                        l.id.includes('route') || 
                        l.id.includes('directions') ||
                        l.type === 'line'
                    );
                }
            }
        } catch (e) {
            result.routeDetails = 'Map style query error: ' + e.message;
        }

        return result;
        """
        try:
            res = driver.execute_script(js_script)
            return res or {}
        except Exception as e:
            logger.debug(f"JavaScript map inspection failed: {e}")
            return {
                "hasMapContainer": False,
                "hasCanvas": False,
                "markerCount": 0,
                "mapboxLayers": [],
                "hasRouteLayer": False,
                "routeDetails": str(e)
            }
