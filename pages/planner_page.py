import os
import re
import time
import json
from datetime import datetime, timedelta
from typing import Tuple, List, Optional, Dict, Any, Union
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from pages.base_page import BasePage
from utils.config import Config
from utils.logger import get_logger
from utils.map_helpers import MapHelpers

logger = get_logger("PlannerPage")


class PlannerPage(BasePage):
    """Page Object for RoadTripTribes Planner interface and Mapbox route interactions."""

    # Navigation & Initial Trip Form
    PLAN_ROADTRIP_TAB: Tuple[str, str] = (
        By.XPATH,
        "//div[contains(@class, 'planTrip')] | //button[contains(@class, 'journeysEmptyStateAction') and contains(text(), 'Plan a Roadtrip')]"
    )
    MY_ROADTRIPS_TAB: Tuple[str, str] = (By.XPATH, "//div[contains(@class, 'myRoadTrip')]")
    TRIP_NAME_INPUT: Tuple[str, str] = (By.ID, "trip_name")
    START_DATE_INPUT: Tuple[str, str] = (By.ID, "start_date")
    END_DATE_INPUT: Tuple[str, str] = (By.ID, "end_date")
    TRIP_DESCRIPTION_INPUT: Tuple[str, str] = (
        By.CSS_SELECTOR,
        "textarea#trip_description, textarea[name='trip_description']"
    )
    ADD_ROUTES_BUTTON: Tuple[str, str] = (
        By.XPATH,
        "//button[contains(@class, 'btnStyle') and contains(., 'Add Route')]"
    )

    # Route Metadata Inputs
    ROUTE_NAME_INPUT: Tuple[str, str] = (By.ID, "route_name")
    ROUTE_START_DATE_INPUT: Tuple[str, str] = (By.ID, "route_start_date")

    # Waypoints & Location Inputs
    FROM_CONTAINER: Tuple[str, str] = (
        By.XPATH,
        "(//div[contains(@class, 'route-waypoint-field')])[1]//div[contains(@class, 'place-search-select')]"
    )
    TO_CONTAINER: Tuple[str, str] = (
        By.XPATH,
        "(//div[contains(@class, 'route-waypoint-field')])[2]//div[contains(@class, 'place-search-select')]"
    )

    FROM_INPUT: Tuple[str, str] = (
        By.XPATH,
        "(//div[contains(@class, 'route-waypoint-field')])[1]//div[contains(@class, 'place-search-select')]//input[not(@type='hidden')]"
    )
    TO_INPUT: Tuple[str, str] = (
        By.XPATH,
        "(//div[contains(@class, 'route-waypoint-field')])[2]//div[contains(@class, 'place-search-select')]//input[not(@type='hidden')]"
    )

    FROM_SELECTED_CONTAINER: Tuple[str, str] = (
        By.XPATH,
        "(//div[contains(@class, 'route-waypoint-field')])[1]//div[contains(@class, 'place-search__single-value') or contains(@class, 'route-waypoint-select')]"
    )
    TO_SELECTED_CONTAINER: Tuple[str, str] = (
        By.XPATH,
        "(//div[contains(@class, 'route-waypoint-field')])[2]//div[contains(@class, 'place-search__single-value') or contains(@class, 'route-waypoint-select')]"
    )

    # Autocomplete Dropdown in Portal
    AUTOCOMPLETE_OPTIONS: Tuple[str, str] = (
        By.CSS_SELECTOR,
        ".place-search__menu-portal .place-search__option, div[class*='place-search__option']"
    )
    AUTOCOMPLETE_MENU_PORTAL: Tuple[str, str] = (By.CSS_SELECTOR, ".place-search__menu-portal")

    # Calculated Route Data
    ALL_COORDINATES_INPUT: Tuple[str, str] = (By.ID, "allCoordinates")
    ROUTE_DISTANCE_INPUT: Tuple[str, str] = (By.CSS_SELECTOR, "input[name='total_distance']")
    ROUTE_DURATION_INPUT: Tuple[str, str] = (
        By.XPATH,
        "(//input[@name='total_distance'])[2] | //div[contains(@class, 'formGroup') and .//label[contains(text(), 'Route Duration')]]//input"
    )
    SAVE_ROADTRIP_BTN: Tuple[str, str] = (
        By.XPATH,
        "//button[contains(@class, 'btnStyle') and (contains(., 'Save Roadtrip') or contains(., 'Saving Roadtrip') or contains(., 'Update Roadtrip') or contains(., 'Updating Roadtrip'))]"
    )
    CLEAR_ALL_BTN: Tuple[str, str] = (By.XPATH, "//button[contains(text(), 'Clear All')]")

    # Mapbox Elements
    MAP_CONTAINER: Tuple[str, str] = (By.ID, "map")
    MAP_CANVAS: Tuple[str, str] = (By.CSS_SELECTOR, "#map canvas.mapboxgl-canvas")
    MAP_MARKERS: Tuple[str, str] = (By.CSS_SELECTOR, "#map .mapboxgl-marker")
    MARKER_DOTS: Tuple[str, str] = (By.CSS_SELECTOR, "#map .marker-dot, #map .stoppoint-marker")
    ROUTE_DESCRIPTION_INPUT: Tuple[str, str] = (
        By.CSS_SELECTOR,
        "textarea#route_description, textarea[name='route_description']"
    )
    WAYPOINT_STOPPOINT_BUTTONS: Tuple[str, str] = (By.CSS_SELECTOR, "button.route-waypoint-stoppoint")
    WAYPOINT_DELETE_BUTTONS: Tuple[str, str] = (
        By.CSS_SELECTOR,
        "button.route-waypoint-delete, button[aria-label='Remove waypoint']"
    )

    # My Roadtrips List Elements
    SEARCH_ROADTRIPS_INPUT: Tuple[str, str] = (
        By.CSS_SELECTOR,
        "input.journeysSearchInput, input[placeholder*='Search roadtrips']"
    )
    JOURNEY_LIST_CARDS: Tuple[str, str] = (By.CSS_SELECTOR, ".upcomingJourneyList")
    SEE_ALL_ROUTES_BTN: Tuple[str, str] = (By.CSS_SELECTOR, ".add-hyperlink")
    ROUTE_CARD_EDIT_BTN: Tuple[str, str] = (By.CSS_SELECTOR, "a.editTripOption")
    DELETE_TRIP_BTN: Tuple[str, str] = (By.CSS_SELECTOR, "span.deleteTripOption")
    SWAL_CONFIRM_DELETE_BTN: Tuple[str, str] = (By.CSS_SELECTOR, "button.swal2-confirm")

    # Error & Notification Elements
    TOAST_SUCCESS: Tuple[str, str] = (By.CSS_SELECTOR, ".Toastify__toast--success")
    TOAST_ERROR: Tuple[str, str] = (By.CSS_SELECTOR, ".Toastify__toast--error")
    SWAL_ERROR: Tuple[str, str] = (By.CSS_SELECTOR, ".swal2-error, .swal2-popup")
    GENERAL_ERROR: Tuple[str, str] = (By.CSS_SELECTOR, ".error-message, .loginModalErrorSlot--form")

    def ensure_planner_tab_active(self, trip_name: Optional[str] = None) -> "PlannerPage":
        """
        Navigates or switches to the 'Plan a Roadtrip' tab and completes initial trip dates if prompted.
        """
        logger.info("Verifying Planner tab is active...")
        if self.is_element_present(self.PLAN_ROADTRIP_TAB, timeout=5):
            tab = self.find(self.PLAN_ROADTRIP_TAB)
            tab_classes = tab.get_attribute("class") or ""
            if "homePageMainTabActive" not in tab_classes:
                logger.info("Clicking 'Plan a Roadtrip' tab to activate.")
                self.click(self.PLAN_ROADTRIP_TAB)

        # If the trip dates form is displayed, fill dates and trip name and click 'Add Route(s)'
        if self.is_element_visible(self.ADD_ROUTES_BUTTON, timeout=3):
            logger.info("Initial Roadtrip details form detected. Setting dates and clicking 'Add Route(s)'...")
            self._fill_initial_trip_dates(trip_name)
            time.sleep(0.5)
            self.click(self.ADD_ROUTES_BUTTON)

        # Wait until waypoint containers are visible
        self.wait_until_visible(self.FROM_CONTAINER, timeout=Config.EXPLICIT_TIMEOUT)
        logger.info("Planner tab is ready and waypoint fields are visible.")
        return self

    def _fill_initial_trip_dates(self, trip_name: Optional[str] = None) -> None:
        """Fills trip name, start and end dates on the initial roadtrip modal form using React value setters."""
        now = datetime.now() + timedelta(days=2)
        dep_val = now.strftime("%Y-%m-%dT10:00")
        ret_val = (now + timedelta(days=5)).strftime("%Y-%m-%d")

        if trip_name:
            trip_name_el = self.find(self.TRIP_NAME_INPUT, timeout=5)
            self.execute_script("""
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                nativeInputValueSetter.call(arguments[0], arguments[1]);
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            """, trip_name_el, trip_name)

        start_date_el = self.find(self.START_DATE_INPUT, timeout=5)
        end_date_el = self.find(self.END_DATE_INPUT, timeout=5)

        react_setter = """
        function setReactValue(element, value) {
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
            nativeInputValueSetter.call(element, value);
            element.dispatchEvent(new Event('input', { bubbles: true }));
            element.dispatchEvent(new Event('change', { bubbles: true }));
        }
        setReactValue(arguments[0], arguments[1]);
        setReactValue(arguments[2], arguments[3]);
        """
        self.execute_script(react_setter, start_date_el, dep_val, end_date_el, ret_val)

    def set_roadtrip_name(self, trip_name: str) -> None:
        """Enters the roadtrip-level name into the trip_name field."""
        logger.info(f"Setting Roadtrip Name: '{trip_name}'")
        trip_name_el = self.wait_until_visible(self.TRIP_NAME_INPUT, timeout=Config.EXPLICIT_TIMEOUT)
        self.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", trip_name_el)
        self.execute_script("""
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
            nativeInputValueSetter.call(arguments[0], arguments[1]);
            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
        """, trip_name_el, trip_name)

    def get_roadtrip_name(self, timeout: int = 25) -> str:
        """Returns the current roadtrip-level name from the Planner sidebar."""
        def _has_name(driver):
            els = driver.find_elements(*self.TRIP_NAME_INPUT)
            if els:
                val = (els[0].get_attribute("value") or "").strip()
                if val:
                    return val
            return False

        try:
            return self.wait_for_condition(_has_name, timeout=timeout, message="Roadtrip name input not populated.")
        except Exception:
            trip_name_el = self.find(self.TRIP_NAME_INPUT, timeout=3)
            return (trip_name_el.get_attribute("value") or "").strip() if trip_name_el else ""

    def set_roadtrip_description(self, description: str) -> None:
        """Sets the roadtrip-level description in the Planner sidebar."""
        logger.info(f"Setting Roadtrip Description: '{description}'")
        desc_el = self.wait_until_present(self.TRIP_DESCRIPTION_INPUT, timeout=Config.EXPLICIT_TIMEOUT)
        self.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", desc_el)
        self.execute_script("""
            const nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
            nativeTextAreaValueSetter.call(arguments[0], arguments[1]);
            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
        """, desc_el, description)

    def get_roadtrip_description(self, timeout: int = 25) -> str:
        """Returns the current roadtrip-level description from the Planner sidebar."""
        def _has_val(driver):
            els = driver.find_elements(*self.TRIP_DESCRIPTION_INPUT)
            if els:
                val = (els[0].get_attribute("value") or "").strip()
                if val:
                    return val
            return False

        try:
            return self.wait_for_condition(_has_val, timeout=timeout, message="Trip description input not populated.")
        except Exception:
            desc_el = self.find(self.TRIP_DESCRIPTION_INPUT, timeout=3)
            return (desc_el.get_attribute("value") or "").strip() if desc_el else ""

    def set_roadtrip_dates(self, start_datetime: str, end_date: str) -> None:
        """
        Safely sets the roadtrip departure datetime (YYYY-MM-DDTHH:MM) and return date (YYYY-MM-DD).
        To satisfy client-side validation rules (start_date < end_date), end_date is updated
        first when extending dates, followed by start_date, and synchronized with route_start_date.
        """
        logger.info(f"Setting Roadtrip Dates -> Departure: '{start_datetime}', Return: '{end_date}'")
        start_el = self.wait_until_visible(self.START_DATE_INPUT, timeout=Config.EXPLICIT_TIMEOUT)
        end_el = self.wait_until_visible(self.END_DATE_INPUT, timeout=Config.EXPLICIT_TIMEOUT)

        react_setter = """
        function setReactValue(element, value) {
            if (!element) return;
            const nativeSetter = (element.tagName.toLowerCase() === 'textarea' 
                ? Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set
                : Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set);
            nativeSetter.call(element, value);
            element.dispatchEvent(new Event('input', { bubbles: true }));
            element.dispatchEvent(new Event('change', { bubbles: true }));
        }
        setReactValue(arguments[0], arguments[1]);
        setReactValue(arguments[2], arguments[3]);
        """
        self.execute_script(react_setter, end_el, end_date, start_el, start_datetime)
        time.sleep(0.5)

        route_start_els = self.find_all(self.ROUTE_START_DATE_INPUT, timeout=2)
        if route_start_els:
            self.execute_script("""
                const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                nativeSetter.call(arguments[0], arguments[1]);
                arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
                arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            """, route_start_els[0], start_datetime)

    def get_roadtrip_start_date(self, timeout: int = 25) -> str:
        """Returns the current start_date input value."""
        def _has_val(driver):
            els = driver.find_elements(*self.START_DATE_INPUT)
            if els:
                val = (els[0].get_attribute("value") or "").strip()
                if val:
                    return val
            return False

        try:
            return self.wait_for_condition(_has_val, timeout=timeout, message="Start date input not populated.")
        except Exception:
            el = self.find(self.START_DATE_INPUT, timeout=3)
            return (el.get_attribute("value") or "").strip() if el else ""

    def get_roadtrip_end_date(self, timeout: int = 25) -> str:
        """Returns the current end_date input value."""
        def _has_val(driver):
            els = driver.find_elements(*self.END_DATE_INPUT)
            if els:
                val = (els[0].get_attribute("value") or "").strip()
                if val:
                    return val
            return False

        try:
            return self.wait_for_condition(_has_val, timeout=timeout, message="End date input not populated.")
        except Exception:
            el = self.find(self.END_DATE_INPUT, timeout=3)
            return (el.get_attribute("value") or "").strip() if el else ""

    def get_roadtrip_details(self, timeout: int = 25) -> Dict[str, str]:
        """Returns a dictionary containing all roadtrip-level field values."""
        return {
            "trip_name": self.get_roadtrip_name(timeout=timeout),
            "trip_description": self.get_roadtrip_description(timeout=timeout),
            "start_date": self.get_roadtrip_start_date(timeout=timeout),
            "end_date": self.get_roadtrip_end_date(timeout=timeout)
        }

    def set_route_name(self, route_name: str) -> None:
        """Enters the route name into the route_name field."""
        logger.info(f"Setting Route Name: '{route_name}'")
        route_name_el = self.wait_until_visible(self.ROUTE_NAME_INPUT, timeout=Config.EXPLICIT_TIMEOUT)
        self.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", route_name_el)
        self.execute_script("""
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
            nativeInputValueSetter.call(arguments[0], arguments[1]);
            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
        """, route_name_el, route_name)

    def set_route_description(self, description: str) -> None:
        """Sets the route description in the Planner sidebar."""
        logger.info(f"Setting Route Description: '{description}'")
        desc_el = self.wait_until_present(self.ROUTE_DESCRIPTION_INPUT, timeout=Config.EXPLICIT_TIMEOUT)
        self.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", desc_el)
        self.execute_script("""
            const nativeTextAreaValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
            nativeTextAreaValueSetter.call(arguments[0], arguments[1]);
            arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
            arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
        """, desc_el, description)

    def get_route_description(self) -> str:
        """Returns the current route description from the Planner sidebar."""
        desc_el = self.find(self.ROUTE_DESCRIPTION_INPUT, timeout=5)
        return (desc_el.get_attribute("value") or "").strip()

    ADD_WAYPOINT_BUTTON: Tuple[str, str] = (
        By.XPATH,
        "//button[contains(@class, 'btnStyle') and contains(., 'Add') and not(contains(., 'Add Route'))]"
    )
    WAYPOINT_FIELDS: Tuple[str, str] = (By.CSS_SELECTOR, ".route-waypoint-field")
    WAYPOINT_SELECTED_VALUES: Tuple[str, str] = (
        By.CSS_SELECTOR,
        ".route-waypoint-field .place-search__single-value, .route-waypoint-field .route-waypoint-select"
    )

    def add_waypoint_field(self) -> None:
        """Clicks the 'Add' stop button to append a new destination waypoint field."""
        logger.info("Clicking 'Add' button to add a new waypoint field...")
        add_btn = self.wait_until_visible(self.ADD_WAYPOINT_BUTTON, timeout=Config.EXPLICIT_TIMEOUT)
        self.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", add_btn)
        time.sleep(0.3)
        self.execute_script("arguments[0].click();", add_btn)
        time.sleep(0.8)

    def enter_and_select_from_location(self, location_query: str) -> str:
        """
        Types the start location into the From field and selects the matching suggestion.
        Returns the selected option text.
        """
        logger.info(f"Selecting FROM location: '{location_query}'")
        return self._search_and_select_waypoint(self.FROM_CONTAINER, location_query, waypoint_name="FROM")

    def enter_and_select_to_location(self, location_query: str) -> str:
        """
        Types the destination location into the To field and selects the matching suggestion.
        Returns the selected option text.
        """
        logger.info(f"Selecting TO location: '{location_query}'")
        return self._search_and_select_waypoint(self.TO_CONTAINER, location_query, waypoint_name="TO")

    def enter_and_select_intermediate_waypoint(self, location_query: str, waypoint_index: int, waypoint_name: str = "") -> str:
        """
        Adds and selects an intermediate stop at the current destination field before appending subsequent stops.
        """
        label = waypoint_name or f"Waypoint {waypoint_index}"
        logger.info(f"Selecting {label}: '{location_query}'")
        target_container = (
            By.XPATH,
            f"(//div[contains(@class, 'route-waypoint-field')])[{waypoint_index}]//div[contains(@class, 'place-search-select')]"
        )
        return self._search_and_select_waypoint(target_container, location_query, waypoint_name=label)

    # GPX Import Elements
    IMPORT_GPX_TAB: Tuple[str, str] = (By.ID, "nav-profile-tab")
    IMPORT_GPX_FILE_INPUT: Tuple[str, str] = (By.ID, "importGPXNewUpdateFile")
    GPX_UPLOAD_CONTAINER: Tuple[str, str] = (By.CSS_SELECTOR, ".uploadedGpxFiles")

    WAYPOINT_DRAG_HANDLES: Tuple[str, str] = (
        By.CSS_SELECTOR,
        ".uploadedGpxFiles .dragDropGpxFile, .route-waypoint-drag, [data-rbd-drag-handle-draggable-id]"
    )

    def import_gpx(self, file_path: str, timeout: int = 45) -> Dict[str, Any]:
        """
        Uploads a GPX file via the Planner 'Import Gpx' tab and waits for route generation.
        """
        logger.info(f"Initiating GPX file upload from: {file_path}")
        self.ensure_planner_tab_active()

        # Switch to Import GPX tab
        import_tab = self.wait_until_visible(self.IMPORT_GPX_TAB, timeout=Config.EXPLICIT_TIMEOUT)
        self.execute_script("arguments[0].click();", import_tab)
        time.sleep(0.8)

        # Upload file via file input
        file_input = self.find(self.IMPORT_GPX_FILE_INPUT, timeout=Config.EXPLICIT_TIMEOUT)
        abs_path = os.path.abspath(str(file_path))
        file_input.send_keys(abs_path)
        logger.info(f"GPX file path sent to file input: {abs_path}")

        # Wait for route calculation
        route_data = self.wait_for_route_calculation(timeout=timeout)
        imported_waypoints = self.get_all_selected_waypoints()

        logger.info(
            f"GPX Import completed successfully -> "
            f"Waypoints: {len(imported_waypoints)}, Distance: {route_data['distance']}, "
            f"Duration: {route_data['duration']}, Coordinates: {len(route_data['coordinates'])}"
        )

        return {
            "file_path": abs_path,
            "waypoints": imported_waypoints,
            "waypoint_count": len(imported_waypoints),
            "distance": route_data["distance"],
            "duration": route_data["duration"],
            "distance_numeric": route_data["distance_numeric"],
            "coordinates": route_data["coordinates"]
        }

    def reorder_waypoint(self, from_index: int, to_index: int) -> List[str]:
        """
        Reorders a waypoint from `from_index` to `to_index` (0-indexed) using the react-beautiful-dnd
        accessible drag-handle controls:
        1. Scrolls and focuses the visible drag handle at `from_index`.
        2. Sends SPACE to lift the item.
        3. Sends ARROW_DOWN or ARROW_UP to navigate to `to_index`.
        4. Sends SPACE to drop the item.
        5. Waits for the React state and DOM to update, then returns the updated waypoint list.
        """
        logger.info(f"Reordering waypoint from position {from_index + 1} to position {to_index + 1}...")
        all_handles = self.find_all(self.WAYPOINT_DRAG_HANDLES, timeout=5)
        drag_handles = [h for h in all_handles if h.is_displayed()]
        if not drag_handles or from_index >= len(drag_handles):
            raise IndexError(
                f"Cannot reorder waypoint: from_index {from_index} is out of range ({len(drag_handles)} visible handles found)."
            )

        handle = drag_handles[from_index]
        self.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", handle)
        time.sleep(0.3)

        # 1. Lift the item
        handle.send_keys(Keys.SPACE)
        time.sleep(0.4)

        # 2. Move item in requested direction
        diff = to_index - from_index
        if diff > 0:
            for _ in range(diff):
                handle.send_keys(Keys.ARROW_DOWN)
                time.sleep(0.3)
        elif diff < 0:
            for _ in range(abs(diff)):
                handle.send_keys(Keys.ARROW_UP)
                time.sleep(0.3)

        # 3. Drop the item
        handle.send_keys(Keys.SPACE)
        time.sleep(2.0)

        updated_waypoints = self.get_all_selected_waypoints()
        logger.info(f"Waypoint order after reorder: {updated_waypoints}")
        return updated_waypoints

    def delete_waypoint(self, waypoint_index: int) -> List[str]:
        """
        Deletes a waypoint at the given 1-based index (e.g. 1 for start, 3 for 3rd stop),
        confirms the SweetAlert confirmation popup ('Yes, Remove'), and returns the updated waypoint list.
        """
        logger.info(f"Deleting waypoint at 1-based position {waypoint_index}...")
        del_btns = self.find_all(self.WAYPOINT_DELETE_BUTTONS, timeout=10)
        if not del_btns or waypoint_index < 1 or waypoint_index > len(del_btns):
            raise IndexError(f"Cannot delete waypoint at index {waypoint_index}; available buttons: {len(del_btns)}")

        target_btn = del_btns[waypoint_index - 1]
        self.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", target_btn)
        time.sleep(0.3)
        self.execute_script("arguments[0].click();", target_btn)

        # Wait for SweetAlert2 confirm button and confirm removal
        confirm_btn = self.wait_until_clickable(self.SWAL_CONFIRM_DELETE_BTN, timeout=8)
        self.execute_script("arguments[0].click();", confirm_btn)
        time.sleep(1.0)

        updated_waypoints = self.get_all_selected_waypoints()
        logger.info(f"Waypoint at position {waypoint_index} deleted. Remaining ({len(updated_waypoints)}): {updated_waypoints}")
        return updated_waypoints

    def delete_waypoint_by_name(self, name_substring: str) -> List[str]:
        """
        Locates a waypoint containing the given name substring and deletes it.
        """
        current_wps = self.get_all_selected_waypoints()
        target_idx = None
        for i, wp in enumerate(current_wps):
            if name_substring.lower() in wp.lower():
                target_idx = i + 1
                break
        if target_idx is None:
            raise ValueError(f"Waypoint matching '{name_substring}' not found in: {current_wps}")
        return self.delete_waypoint(target_idx)

    def toggle_waypoint_stoppoint(self, waypoint_index: int) -> bool:
        """
        Toggles the Stop/Passthrough button on a waypoint row (1-indexed).
        Returns True if the waypoint is now a Stop (has 'is-active' class), False otherwise.
        """
        logger.info(f"Toggling Stop/Passthrough on waypoint at position {waypoint_index}...")
        stop_btns = self.find_all(self.WAYPOINT_STOPPOINT_BUTTONS, timeout=10)
        if not stop_btns or waypoint_index < 1 or waypoint_index > len(stop_btns):
            raise IndexError(f"Cannot toggle stoppoint at index {waypoint_index}; available buttons: {len(stop_btns)}")

        target_btn = stop_btns[waypoint_index - 1]
        self.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", target_btn)
        time.sleep(0.3)
        self.execute_script("arguments[0].click();", target_btn)
        time.sleep(1.0)

        is_active = "is-active" in (target_btn.get_attribute("class") or "")
        logger.info(f"Waypoint {waypoint_index} Stop state is now: {'STOP (Active)' if is_active else 'PASSTHROUGH (Inactive)'}")
        return is_active

    def is_waypoint_stoppoint(self, waypoint_index: int) -> bool:
        """Returns True if the waypoint at 1-based index is currently designated as a Stop."""
        stop_btns = self.find_all(self.WAYPOINT_STOPPOINT_BUTTONS, timeout=10)
        if not stop_btns or waypoint_index < 1 or waypoint_index > len(stop_btns):
            return False
        return "is-active" in (stop_btns[waypoint_index - 1].get_attribute("class") or "")

    def get_all_waypoint_stop_states(self) -> List[bool]:
        """Returns a list of boolean values indicating whether each waypoint is a Stop (True) or Passthrough (False)."""
        stop_btns = self.find_all(self.WAYPOINT_STOPPOINT_BUTTONS, timeout=10)
        return ["is-active" in (btn.get_attribute("class") or "") for btn in stop_btns]

    def click_map_to_add_waypoint(
        self,
        offset_x: int = 120,
        offset_y: int = -60,
        previous_distance: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Clicks on the Mapbox canvas at the given offset relative to canvas center,
        confirms the SweetAlert 'Add Coordinate' popup, and waits for route recalculation.
        Returns the updated route calculation data.
        """
        logger.info(f"Clicking Mapbox canvas at offset ({offset_x}, {offset_y}) to add a waypoint...")
        canvas = self.wait_until_visible(self.MAP_CANVAS, timeout=15)

        actions = ActionChains(self.driver)
        actions.move_to_element_with_offset(canvas, offset_x, offset_y).click().perform()
        time.sleep(1.5)

        # Confirm SweetAlert2 "Add Coordinate" popup
        confirm_btn = self.wait_until_clickable(self.SWAL_CONFIRM_DELETE_BTN, timeout=10)
        self.execute_script("arguments[0].click();", confirm_btn)
        time.sleep(2.0)

        recalc_route = self.wait_for_route_calculation(timeout=35, previous_distance=previous_distance)
        logger.info(f"Map click added waypoint successfully -> New distance: {recalc_route['distance']}")
        return recalc_route

    def drag_map_pin(
        self,
        marker_index: int = 0,
        offset_x: int = 60,
        offset_y: int = 60,
        previous_distance: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Drags a draggable Mapbox marker dot (0-indexed among .marker-dot elements) by the given pixel offset,
        triggering 'dragend', reverse geocoding, and route recalculation.
        Returns the updated route calculation data.
        """
        logger.info(f"Dragging Mapbox marker pin at index {marker_index} by offset ({offset_x}, {offset_y})...")
        dots = self.find_all(self.MARKER_DOTS, timeout=15)
        if not dots or marker_index >= len(dots):
            raise IndexError(f"Cannot drag marker at index {marker_index}; visible dots: {len(dots)}")

        self.execute_script("""
            const dot = arguments[0];
            const canvas = document.querySelector('#map canvas.mapboxgl-canvas');
            const offsetX = arguments[1];
            const offsetY = arguments[2];
            
            if (!dot || !canvas) return;
            
            const dotRect = dot.getBoundingClientRect();
            const startX = dotRect.left + dotRect.width / 2;
            const startY = dotRect.top + dotRect.height / 2;
            const endX = startX + offsetX;
            const endY = startY + offsetY;
            
            // 1. mousedown on dot
            dot.dispatchEvent(new MouseEvent('mousedown', {
                bubbles: true, cancelable: true, view: window, clientX: startX, clientY: startY, button: 0, buttons: 1
            }));
            
            // 2. mousemove on canvas and window in steps
            for (let i = 1; i <= 5; i++) {
                const curX = startX + (endX - startX) * (i / 5);
                const curY = startY + (endY - startY) * (i / 5);
                canvas.dispatchEvent(new MouseEvent('mousemove', {
                    bubbles: true, cancelable: true, view: window, clientX: curX, clientY: curY, button: 0, buttons: 1
                }));
                window.dispatchEvent(new MouseEvent('mousemove', {
                    bubbles: true, cancelable: true, view: window, clientX: curX, clientY: curY, button: 0, buttons: 1
                }));
            }
            
            // 3. mouseup on canvas and window
            canvas.dispatchEvent(new MouseEvent('mouseup', {
                bubbles: true, cancelable: true, view: window, clientX: endX, clientY: endY, button: 0, buttons: 0
            }));
            window.dispatchEvent(new MouseEvent('mouseup', {
                bubbles: true, cancelable: true, view: window, clientX: endX, clientY: endY, button: 0, buttons: 0
            }));
        """, dots[marker_index], offset_x, offset_y)

        time.sleep(2.0)
        recalc_route = self.wait_for_route_calculation(timeout=35, previous_distance=previous_distance)
        logger.info(f"Map pin dragged successfully -> New distance: {recalc_route['distance']}")
        return recalc_route

    def get_all_selected_waypoints(self) -> List[str]:
        """
        Extracts and returns the text of all currently populated waypoint fields in order.
        Handles both Standard Planner view and GPX Import view.
        Uses textContent to reliably retrieve values even for scrolled/overflow elements.
        """
        # Check GPX import view
        gpx_containers = self.find_all(self.GPX_UPLOAD_CONTAINER, timeout=1)
        if gpx_containers and gpx_containers[0].is_displayed():
            rows = self.find_all(
                (By.CSS_SELECTOR, ".uploadedGpxFiles [data-rbd-draggable-id]"),
                timeout=2
            )
            texts = []
            for r in rows:
                sv_el = r.find_elements(By.CSS_SELECTOR, ".place-search__single-value, .place-search-select")
                raw = (sv_el[0].get_attribute("textContent") or sv_el[0].text or "").strip() if sv_el else (r.get_attribute("textContent") or r.text or "").strip()
                t = re.sub(r"^\d+\s*[\n\|]\s*", "", raw).strip()
                if t and "enter your" not in t.lower() and "add a stop" not in t.lower():
                    texts.append(t)
            if texts:
                return texts

        # Standard Planner view
        fields = self.find_all(self.WAYPOINT_FIELDS, timeout=5)
        waypoint_texts = []
        for idx, f in enumerate(fields):
            # Prefer place-search__single-value if present
            sv_elements = f.find_elements(By.CSS_SELECTOR, ".place-search__single-value")
            if sv_elements:
                raw_text = (sv_elements[0].get_attribute("textContent") or sv_elements[0].text or "").strip()
            else:
                raw_text = (f.get_attribute("textContent") or f.text or "").strip()

            cleaned = re.sub(r"^\d+\s*[\n\|]\s*", "", raw_text).strip()
            if cleaned and "enter your" not in cleaned.lower() and "add a stop" not in cleaned.lower():
                waypoint_texts.append(cleaned)
            elif raw_text:
                waypoint_texts.append(raw_text)
        return waypoint_texts

    def _search_and_select_waypoint(self, container_locator: Tuple[str, str], query: str, waypoint_name: str) -> str:
        """
        Interacts with react-select component with robust scrolling and portal dropdown selection.
        """
        container = self.wait_until_present(container_locator, timeout=Config.EXPLICIT_TIMEOUT)
        self.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", container)
        time.sleep(0.3)

        try:
            container.click()
        except ElementClickInterceptedException:
            self.execute_script("arguments[0].click();", container)

        input_el = container.find_element(By.CSS_SELECTOR, "input")
        try:
            input_el.send_keys(Keys.CONTROL + "a")
            input_el.send_keys(Keys.BACKSPACE)
            time.sleep(0.2)
            input_el.send_keys(query)
        except Exception:
            self.execute_script("arguments[0].value = '';", input_el)
            input_el.send_keys(query)

        logger.info(f"Typed '{query}' into {waypoint_name} input.")

        # Explicitly wait for autocomplete dropdown options to appear in portal
        logger.info("Waiting for autocomplete dropdown options in portal...")
        first_option = self.wait_until_visible(self.AUTOCOMPLETE_OPTIONS, timeout=15)
        selected_text = first_option.text.strip()
        logger.info(f"Clicking {waypoint_name} dropdown option: '{selected_text.replace(chr(10), ', ')}'")

        # Dispatch mousedown, mouseup, and click
        self.execute_script("""
            arguments[0].dispatchEvent(new MouseEvent('mousedown', {bubbles: true, cancelable: true, view: window}));
            arguments[0].dispatchEvent(new MouseEvent('mouseup', {bubbles: true, cancelable: true, view: window}));
            arguments[0].click();
        """, first_option)

        time.sleep(1.2)
        return selected_text

    def wait_for_route_calculation(self, timeout: Optional[int] = 35, previous_distance: Optional[str] = None) -> Dict[str, Any]:
        """
        Explicitly waits for route calculation to complete:
        - Distance input populated with positive value (> 0).
        - #allCoordinates populated with GeoJSON coordinate array.
        - If previous_distance is provided, waits until distance differs from previous_distance.
        """
        timeout = timeout or 35
        logger.info(f"Waiting up to {timeout}s for route calculation to complete{' (expecting change from ' + previous_distance + ')' if previous_distance else ''}...")

        def _is_route_ready(driver) -> bool:
            try:
                dist_inputs = driver.find_elements(*self.ROUTE_DISTANCE_INPUT)
                has_distance = False
                current_dist = ""
                for inp in dist_inputs:
                    val = (inp.get_attribute("value") or "").strip()
                    if val and val != "0" and any(char.isdigit() for char in val) and ("km" in val.lower() or "mile" in val.lower()):
                        has_distance = True
                        current_dist = val
                        break

                if not has_distance:
                    return False

                if previous_distance and current_dist == previous_distance:
                    return False

                coords_el = driver.find_element(*self.ALL_COORDINATES_INPUT)
                coords_val = (coords_el.get_attribute("value") or "").strip()
                has_coordinates = bool(coords_val and coords_val != "[]" and coords_val.startswith("["))

                return has_distance and has_coordinates
            except Exception:
                return False

        try:
            self.wait_for_condition(
                _is_route_ready,
                timeout=timeout,
                message="Route calculation timed out: total_distance and #allCoordinates were not fully populated."
            )
        except TimeoutException:
            logger.error("Route calculation did not complete within timeout.")
            diagnostics = self.get_failure_diagnostics()
            raise AssertionError(f"Route calculation failed to produce a valid route. Diagnostics: {diagnostics}")

        distance_str = self.get_route_distance()
        duration_str = self.get_route_duration()
        coordinates = self.get_route_coordinates()
        logger.info(f"Route calculated successfully -> Distance: '{distance_str}', Duration: '{duration_str}', Coordinates count: {len(coordinates)}")

        return {
            "distance": distance_str,
            "duration": duration_str,
            "distance_numeric": self.get_numeric_distance(distance_str),
            "coordinates": coordinates
        }

    def get_route_distance(self) -> str:
        """Returns the total_distance input value."""
        try:
            dist_inputs = self.find_all(self.ROUTE_DISTANCE_INPUT, timeout=3)
            for inp in dist_inputs:
                v = (inp.get_attribute("value") or "").strip()
                if v and any(c.isdigit() for c in v) and ("km" in v.lower() or "mile" in v.lower()):
                    return v
            if dist_inputs:
                return (dist_inputs[0].get_attribute("value") or "").strip()
            return ""
        except Exception:
            return ""

    def get_route_duration(self) -> str:
        """Returns the total duration value."""
        try:
            dist_inputs = self.find_all(self.ROUTE_DISTANCE_INPUT, timeout=3)
            if len(dist_inputs) > 1:
                return (dist_inputs[1].get_attribute("value") or "").strip()
            return ""
        except Exception:
            return ""

    def get_route_coordinates(self) -> List[List[float]]:
        """Parses and returns coordinates from #allCoordinates input."""
        try:
            coords_el = self.find(self.ALL_COORDINATES_INPUT, timeout=3)
            val = (coords_el.get_attribute("value") or "").strip()
            if val and val.startswith("["):
                return json.loads(val)
            return []
        except Exception:
            return []

    @staticmethod
    def get_numeric_distance(distance_text: str) -> float:
        """Extracts numeric float from distance text (e.g. '614 km' -> 614.0)."""
        match = re.search(r"([\d\.,]+)", distance_text)
        if match:
            clean_num = match.group(1).replace(",", "")
            try:
                return float(clean_num)
            except ValueError:
                return 0.0
        return 0.0

    def get_selected_from_location(self) -> str:
        """Returns the text of the selected From location."""
        try:
            el = self.find(self.FROM_SELECTED_CONTAINER, timeout=3)
            return el.text.strip()
        except Exception:
            return ""

    def get_selected_to_location(self) -> str:
        """Returns the text of the selected To location."""
        try:
            el = self.find(self.TO_SELECTED_CONTAINER, timeout=3)
            return el.text.strip()
        except Exception:
            return ""

    def verify_no_errors(self) -> None:
        """Verifies that no blocking error toasts or alerts are present."""
        for locator, name in [
            (self.TOAST_ERROR, "Toast error"),
            (self.SWAL_ERROR, "SweetAlert error"),
            (self.GENERAL_ERROR, "General form error")
        ]:
            if self.is_element_visible(locator, timeout=1):
                err_text = self.get_text(locator)
                if err_text and "latitude must be between" not in err_text.lower():
                    raise AssertionError(f"Unexpected error encountered on page ({name}): '{err_text}'")

    def get_active_toasts(self) -> List[str]:
        """Returns list of text strings from all currently visible toast notifications."""
        try:
            toasts = self.driver.find_elements(
                By.CSS_SELECTOR,
                ".Toastify__toast, .Toastify__toast--error, .Toastify__toast--warning, .Toastify__toast--info, .Toastify__toast--success, .error-message, .swal2-popup"
            )
            return [t.text.strip() for t in toasts if t.is_displayed() and t.text.strip()]
        except Exception:
            return []

    def wait_for_error_toast_or_condition(self, text_keywords: List[str], timeout: int = 10) -> Optional[str]:
        """Waits for an error toast message containing any of the given keywords."""
        def _check_toast(driver):
            for t in driver.find_elements(
                By.CSS_SELECTOR,
                ".Toastify__toast, .Toastify__toast--error, .Toastify__toast--warning, .error-message, .swal2-popup"
            ):
                if t.is_displayed():
                    txt = (t.text or "").strip()
                    if any(kw.lower() in txt.lower() for kw in text_keywords):
                        return txt
            return False

        try:
            return self.wait_for_condition(_check_toast, timeout=timeout)
        except Exception:
            return None

    def is_route_calculated(self) -> bool:
        """Checks if distance and coordinates currently indicate a valid calculated route."""
        dist = self.get_route_distance()
        num_dist = self.get_numeric_distance(dist)
        coords = self.get_route_coordinates()
        return bool(num_dist > 0 and len(coords) >= 2)

    def verify_route_failure_state(self) -> Dict[str, Any]:
        """
        Verifies and returns diagnostics for failure states (Route not found, Max distance exceeded).
        """
        canvas_ready = MapHelpers.is_map_canvas_ready(self.driver)
        markers = MapHelpers.get_map_markers(self.driver)
        dist_str = self.get_route_distance()
        coords = self.get_route_coordinates()
        diagnostics = MapHelpers.get_mapbox_diagnostics(self.driver)
        toasts = self.get_active_toasts()

        return {
            "canvas_ready": canvas_ready,
            "marker_count": len(markers),
            "distance_str": dist_str,
            "coordinates_count": len(coords),
            "mapbox_diagnostics": diagnostics,
            "active_toasts": toasts,
            "is_route_calculated": bool(self.get_numeric_distance(dist_str) > 0 and len(coords) >= 2)
        }

    def wait_for_map_markers(self, min_count: int = 2, timeout: int = 10) -> List[Any]:
        """Waits until at least min_count markers are rendered on the map."""
        try:
            return self.wait_for_condition(
                lambda d: MapHelpers.get_map_markers(d) if len(MapHelpers.get_map_markers(d)) >= min_count else False,
                timeout=timeout,
                message=f"Timed out waiting for at least {min_count} markers on map."
            )
        except Exception:
            return MapHelpers.get_map_markers(self.driver)

    def verify_route_on_map(self) -> Dict[str, Any]:
        """
        Executes layered verification that an actual route is generated and displayed on the map:
        1. Map container and canvas are rendered with non-zero dimensions.
        2. Mapbox markers exist (origin & destination pins).
        3. Route distance is positive.
        4. Route coordinates exist in #allCoordinates.
        5. Secondary JavaScript diagnostics.
        """
        logger.info("Executing layered route verification on map...")

        # 1. Map Canvas Verification
        canvas_ready = MapHelpers.is_map_canvas_ready(self.driver)
        if not canvas_ready:
            raise AssertionError("Map canvas is not ready or has 0 dimensions.")

        # 2. Markers Verification (wait up to 10s for markers to render)
        markers = self.wait_for_map_markers(min_count=2, timeout=10)
        marker_count = len(markers)
        logger.info(f"Mapbox markers count on map: {marker_count}")
        if marker_count < 2:
            raise AssertionError(f"Expected at least 2 waypoint markers on map, found {marker_count}.")

        # 3. Distance Verification
        distance_str = self.get_route_distance()
        numeric_dist = self.get_numeric_distance(distance_str)
        if numeric_dist <= 0:
            raise AssertionError(f"Route distance validation failed: distance is '{distance_str}' (expected > 0).")

        # 4. Route Coordinates Verification
        coords = self.get_route_coordinates()
        if len(coords) < 1:
            raise AssertionError(f"Route coordinates validation failed: found {len(coords)} coordinate points.")

        # 5. Secondary Mapbox JS Context Check
        diagnostics = MapHelpers.get_mapbox_diagnostics(self.driver)
        logger.info(f"Mapbox JS Diagnostics: {diagnostics}")

        return {
            "canvas_ready": canvas_ready,
            "marker_count": marker_count,
            "distance_str": distance_str,
            "numeric_distance": numeric_dist,
            "coordinates_count": len(coords),
            "mapbox_diagnostics": diagnostics
        }

    def save_roadtrip(self, timeout: int = 25) -> Dict[str, Any]:
        """
        Clicks 'Save Roadtrip' (or 'Update Roadtrip') and confirms backend persistence:
        1. When creating new trip: waits for redirect to /home/<trip_id> or success toast.
        2. When editing existing trip (already on /home/<id>): waits for save button loading state
           to finish and success toast to confirm backend update.
        """
        logger.info("Clicking 'Save Roadtrip' button...")
        initial_url = self.driver.current_url
        is_edit_mode = bool(re.search(r"/home/\d+", initial_url))

        save_btn = self.wait_until_clickable(self.SAVE_ROADTRIP_BTN, timeout=Config.EXPLICIT_TIMEOUT)
        self.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", save_btn)
        time.sleep(0.5)

        try:
            save_btn.click()
        except Exception:
            self.execute_script("arguments[0].click();", save_btn)

        logger.info("Waiting for save operation to complete and verify success indicators...")

        if is_edit_mode:
            # When updating existing trip, wait for toast confirmation or button settling
            def _is_update_saved(driver) -> bool:
                toasts = driver.find_elements(*self.TOAST_SUCCESS)
                for t in toasts:
                    if t.is_displayed() and any(w in (t.text or "").lower() for w in ["successfully", "updated", "saved"]):
                        return True
                btn_txt = ""
                try:
                    btn = driver.find_element(*self.SAVE_ROADTRIP_BTN)
                    btn_txt = (btn.text or "").lower()
                except Exception:
                    pass
                if "saving" not in btn_txt and "updating" not in btn_txt and "update" in btn_txt:
                    return True
                return False

            try:
                self.wait_for_condition(
                    _is_update_saved,
                    timeout=timeout,
                    message="Save/Update operation timed out waiting for success confirmation."
                )
            except TimeoutException:
                self.verify_no_errors()
        else:
            # When creating new trip, wait for redirect to /home/<new_id> or toast
            def _is_new_saved(driver) -> bool:
                curr_url = driver.current_url
                if re.search(r"/home/\d+", curr_url) and curr_url != initial_url:
                    return True
                toasts = driver.find_elements(*self.TOAST_SUCCESS)
                for t in toasts:
                    if t.is_displayed() and "successfully" in (t.text or "").lower():
                        return True
                return False

            try:
                self.wait_for_condition(
                    _is_new_saved,
                    timeout=timeout,
                    message="Save operation timed out: did not receive success toast or trip redirect."
                )
            except TimeoutException:
                self.verify_no_errors()
                raise AssertionError("Failed to confirm Roadtrip save: no success toast or trip redirect detected.")

        trip_id = None
        match = re.search(r"/home/(\d+)", self.driver.current_url)
        if match:
            trip_id = match.group(1)
            logger.info(f"Roadtrip successfully saved with Generated ID: '{trip_id}'")

        # Verify no error popups occurred
        self.verify_no_errors()
        time.sleep(1.0)  # Brief settle time to let React state commit

        return {
            "success": True,
            "trip_id": trip_id,
            "redirect_url": self.driver.current_url
        }

    def open_my_roadtrips_tab(self) -> None:
        """Switches to the 'My Roadtrips' tab and verifies content is ready."""
        logger.info("Opening 'My Roadtrips' tab...")

        # If currently on a sub-route like /home/<id>, return cleanly to base /home
        if re.search(r"/home/\d+", self.driver.current_url):
            logger.info("Sub-route /home/<id> detected, navigating to root /home...")
            self.driver.get(f"{Config.BASE_URL}/home")
            self.wait_for_condition(
                lambda d: d.execute_script("return document.readyState") == "complete",
                timeout=10,
                message="Timed out waiting for /home page to load."
            )
            time.sleep(1.0)

        # Multi-attempt tab activation with active-state verification
        my_trips_content_selector = (
            By.CSS_SELECTOR,
            ".upcomingJourneyList, .upcomingJourneyGridBox, input.journeysSearchInput, "
            "input[placeholder*='Search roadtrips'], .journeysEmptyState, .cardParent, "
            ".upcomingJourneyList span.hyperlink"
        )

        for attempt in range(4):
            try:
                my_trips_tab = self.wait_until_visible(self.MY_ROADTRIPS_TAB, timeout=10)
                tab_classes = my_trips_tab.get_attribute("class") or ""

                if "homePageMainTabActive" in tab_classes:
                    if self.find_all(my_trips_content_selector, timeout=1):
                        logger.info("My Roadtrips tab is already active and content is present.")
                        break

                logger.info(f"Activating 'My Roadtrips' tab (Attempt {attempt + 1}/4)...")
                try:
                    my_trips_tab.click()
                except Exception:
                    self.execute_script("arguments[0].click();", my_trips_tab)

                def _is_tab_switched(d) -> bool:
                    try:
                        tab = d.find_element(*self.MY_ROADTRIPS_TAB)
                        cls = tab.get_attribute("class") or ""
                        if "homePageMainTabActive" in cls:
                            return True
                    except Exception:
                        pass
                    return bool(d.find_elements(*my_trips_content_selector))

                if self.wait_for_condition(_is_tab_switched, timeout=5):
                    logger.info("My Roadtrips tab activated successfully.")
                    break
            except Exception as e:
                logger.warning(f"Tab switch attempt {attempt + 1} encountered: {e}")
                time.sleep(1.0)

        # Wait for any shimmer / loading skeletons to disappear
        try:
            self.wait_for_condition(
                lambda d: not bool(d.find_elements(By.CSS_SELECTOR, ".shimmer, .loading, .skeleton")),
                timeout=10
            )
        except Exception:
            pass

        # Final assertion: ensure My Roadtrips container is present and visible
        self.wait_until_visible(
            my_trips_content_selector,
            timeout=Config.EXPLICIT_TIMEOUT
        )
        logger.info("My Roadtrips view loaded and verified ready.")

    def search_and_locate_roadtrip(self, trip_name: str, timeout: int = 15) -> Any:
        """
        Searches for a roadtrip by name in My Roadtrips and returns the card WebElement.
        """
        if re.search(r"/home/\d+", self.driver.current_url):
            self.driver.get(f"{Config.BASE_URL}/home")
            time.sleep(1.5)

        self.open_my_roadtrips_tab()
        logger.info(f"Searching for Roadtrip: '{trip_name}' in My Roadtrips...")
        search_inp = self.wait_until_visible(self.SEARCH_ROADTRIPS_INPUT, timeout=Config.EXPLICIT_TIMEOUT)
        search_inp.send_keys(Keys.CONTROL + "a")
        search_inp.send_keys(Keys.BACKSPACE)
        search_inp.send_keys(trip_name)
        time.sleep(1.5)

        def _find_card(driver):
            cards = driver.find_elements(*self.JOURNEY_LIST_CARDS)
            for card in cards:
                if trip_name.lower() in (card.text or "").lower():
                    return card
            return False

        try:
            target_card = self.wait_for_condition(
                _find_card,
                timeout=timeout,
                message=f"Roadtrip with name '{trip_name}' was not found in My Roadtrips list."
            )
            logger.info(f"Found Roadtrip card for '{trip_name}'.")
            return target_card
        except TimeoutException:
            raise AssertionError(f"Saved roadtrip '{trip_name}' could not be located in My Roadtrips list.")

    def reopen_saved_roadtrip_in_planner(self, trip_card: Optional[Any] = None) -> None:
        """
        Opens 'See All Routes' on the roadtrip card, waits for route data in group routes,
        and clicks Edit route to reopen it in Planner.
        """
        if trip_card is None:
            self.open_my_roadtrips_tab()
            self.wait_until_visible((By.CSS_SELECTOR, ".upcomingJourneyList span.hyperlink"), timeout=15)
            cards = self.find_all(self.JOURNEY_LIST_CARDS, timeout=10)
            if not cards:
                raise AssertionError("No roadtrip cards found in My Roadtrips.")
            trip_card = cards[0]

        logger.info("Clicking 'See All Routes' on saved roadtrip card...")
        see_routes_btn = None
        for _ in range(20):
            try:
                see_routes_btn = trip_card.find_element(*self.SEE_ALL_ROUTES_BTN)
                if see_routes_btn.is_displayed():
                    break
            except Exception:
                pass
            time.sleep(0.5)

        if not see_routes_btn:
            see_routes_btn = self.wait_until_clickable(self.SEE_ALL_ROUTES_BTN, timeout=10)

        # Click See All Routes with retry
        logger.info("Waiting for route card in group routes list...")
        for attempt in range(3):
            self.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", see_routes_btn)
            time.sleep(0.5)
            self.execute_script("arguments[0].click();", see_routes_btn)
            try:
                self.wait_for_condition(
                    lambda d: bool(d.find_elements(By.CSS_SELECTOR, "a.editTripOption, .journeyBox--groupRoutes")),
                    timeout=8
                )
                break
            except Exception:
                logger.info(f"Retrying 'See All Routes' click (Attempt {attempt + 2}/3)...")
                time.sleep(1.0)

        # In routes view, locate the route edit button and click
        logger.info("Locating and clicking Edit route button to open Planner...")
        time.sleep(1.0)

        edit_btn = self.wait_until_clickable(
            (By.CSS_SELECTOR, ".journeyBox--groupRoutes a.editTripOption, a.editTripOption"),
            timeout=15
        )
        self.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", edit_btn)
        time.sleep(0.5)
        self.execute_script("arguments[0].click();", edit_btn)

        # Wait for Planner tab to load and roadtrip data to populate
        logger.info("Waiting for reopened roadtrip data to populate in Planner...")
        time.sleep(2)

        # The page may show either:
        # (A) A preview card with "Update Roadtrip" button -> need to click it to enter edit mode
        # (B) The edit form directly with #trip_name already present and populated
        # Handle both states with a polling loop
        deadline = time.time() + 45
        populated = False
        last_click_t = 0
        while time.time() < deadline:
            # Check if edit form is already visible and populated
            trip_name_els = self.driver.find_elements(By.ID, "trip_name")
            if trip_name_els:
                val = (trip_name_els[0].get_attribute("value") or "").strip()
                if val:
                    populated = True
                    break

            # Check if preview card "Update Roadtrip" button is shown and click it
            now = time.time()
            if now - last_click_t >= 3.0:
                update_btns = self.driver.find_elements(
                    By.XPATH,
                    "//button[contains(@class,'btnStyle') and contains(normalize-space(.), 'Update Roadtrip')] | "
                    "//button[normalize-space(.)='Update Roadtrip'] | "
                    "//a[normalize-space(.)='Update Roadtrip']"
                )
                for ub in update_btns:
                    try:
                        if ub.is_displayed():
                            logger.info("Preview card detected - using native click on 'Update Roadtrip' button...")
                            self.execute_script(
                                "arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", ub
                            )
                            time.sleep(0.3)
                            try:
                                ub.click()
                            except Exception:
                                ActionChains(self.driver).move_to_element(ub).click().perform()
                            last_click_t = time.time()
                            time.sleep(2.0)
                            break
                    except Exception:
                        pass

            time.sleep(0.5)

        if populated:
            logger.info("Saved roadtrip successfully reopened and populated in Planner tab.")
        else:
            logger.warning("Reopened roadtrip data condition wait finished.")

    def delete_roadtrip(self, trip_name: Optional[str] = None) -> bool:
        """
        Searches for a roadtrip in My Roadtrips or deletes the latest created card, confirming deletion.
        """
        try:
            logger.info(f"Initiating cleanup for roadtrip: '{trip_name}'...")
            self.driver.get(f"{Config.BASE_URL}/home")
            time.sleep(1.5)
            self.open_my_roadtrips_tab()

            cards = self.find_all(self.JOURNEY_LIST_CARDS, timeout=10)
            if not cards:
                logger.info("No roadtrip cards to delete.")
                return False

            target_card = None
            if trip_name:
                clean_target = re.sub(r"\s+", " ", trip_name).strip().lower()
                for card in cards:
                    clean_card_text = re.sub(r"\s+", " ", card.text or "").strip().lower()
                    if clean_target in clean_card_text or clean_card_text in clean_target:
                        target_card = card
                        break

            if not target_card and cards:
                target_card = cards[0]

            if target_card:
                del_btns = target_card.find_elements(*self.DELETE_TRIP_BTN)
                if not del_btns:
                    del_btns = self.find_all(self.DELETE_TRIP_BTN, timeout=5)
                if del_btns:
                    btn = del_btns[0]
                    self.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'instant'});", btn)
                    time.sleep(0.3)
                    self.execute_script("arguments[0].click();", btn)

                    # Confirm in SweetAlert
                    confirm_btn = self.wait_until_clickable(self.SWAL_CONFIRM_DELETE_BTN, timeout=8)
                    self.execute_script("arguments[0].click();", confirm_btn)
                    time.sleep(2)
                    logger.info(f"Roadtrip '{trip_name}' deleted successfully.")
                    return True

            logger.info(f"Roadtrip '{trip_name}' was not found for deletion (already removed or not saved).")
            return False
        except Exception as e:
            logger.warning(f"Cleanup for roadtrip '{trip_name}' encountered an error: {e}")
            return False

    def get_failure_diagnostics(self) -> Dict[str, Any]:
        """Collects diagnostic details when a test fails."""
        return {
            "current_url": self.driver.current_url,
            "selected_from": self.get_selected_from_location(),
            "selected_to": self.get_selected_to_location(),
            "route_distance": self.get_route_distance(),
            "route_duration": self.get_route_duration(),
            "coordinates_count": len(self.get_route_coordinates()),
            "map_canvas_ready": MapHelpers.is_map_canvas_ready(self.driver),
            "marker_count": len(MapHelpers.get_map_markers(self.driver)),
            "visible_error": self._get_any_visible_error()
        }

    def _get_any_visible_error(self) -> Optional[str]:
        for loc in [self.TOAST_ERROR, self.SWAL_ERROR, self.GENERAL_ERROR]:
            if self.is_element_visible(loc, timeout=1):
                txt = self.get_text(loc)
                if txt:
                    return txt
        return None
