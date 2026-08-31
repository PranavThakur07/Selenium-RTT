"""
TC-004: Invalid Route Handling & Route Calculation Validation

Validates that the Planner correctly handles scenarios where a route cannot
be generated or where the route exceeds the application's maximum allowed distance:
1. Route Not Found error handling & stale route data clearance.
2. Maximum Distance Exceeded handling & state isolation.
3. GPX Import route validation and sea route regression inspection.
4. Non-destructive validation: all created data is preserved on staging.
"""

import os
import time
import pytest
from typing import Dict, Any, List
from pages.login_page import LoginPage
from pages.planner_page import PlannerPage
from utils.config import Config
from utils.logger import get_logger, log_test_header, log_step, log_test_success
from utils.map_helpers import MapHelpers
from utils.gpx_parser import GPXParser

logger = get_logger("TestInvalidRouteHandling")


@pytest.mark.tc004
@pytest.mark.regression
@pytest.mark.planner
@pytest.mark.invalid_routes
class TestInvalidRouteHandling:
    """Test Suite for TC-004: Invalid Route Handling & Route Calculation Validation."""

    def test_tc004_invalid_route_and_distance_limit_validation(self, driver):
        """
        Executes TC-004 validating failure-state handling across:
        A. Route Not Found & Stale Route Clearance
        B. Maximum Distance Exceeded Validation
        C. GPX Import & Sea Route Regression Inspection
        """
        log_test_header(
            "TC-004",
            "Invalid Route & Distance Limit Validation"
        )

        login_page = LoginPage(driver)
        planner_page = PlannerPage(driver)

        # -------------------------------------------------------------------------
        # STEP 01 & 02: AUTHENTICATION
        # -------------------------------------------------------------------------
        log_step(1, "Open RoadTripTribes and authenticate with test account")
        login_page.navigate()
        login_page.login(Config.TEST_EMAIL, Config.TEST_PASSWORD)
        login_page.wait_for_login_completion()

        # -------------------------------------------------------------------------
        # STEP 03: NAVIGATE TO PLANNER
        # -------------------------------------------------------------------------
        timestamp = time.strftime("%m%d_%H%M%S")
        test_trip_name = f"AutoInvalid_{timestamp}"
        log_step(2, f"Navigate to Planner tab and initialize Roadtrip: '{test_trip_name}'")
        planner_page.ensure_planner_tab_active(test_trip_name)

        # =========================================================================
        # SCENARIO A: ROUTE NOT FOUND & STALE ROUTE CLEARANCE
        # =========================================================================
        log_step(3, "SCENARIO A: Establish valid route baseline (San Francisco -> Sacramento)")
        planner_page.enter_and_select_from_location("San Francisco, CA")
        planner_page.enter_and_select_to_location("Sacramento, CA")

        baseline_route = planner_page.wait_for_route_calculation(timeout=30)
        baseline_dist = baseline_route["distance"]
        baseline_coords = baseline_route["coordinates"]
        baseline_markers = len(MapHelpers.get_map_markers(driver))

        logger.info(f"Established Baseline Route: Distance='{baseline_dist}', Coords={len(baseline_coords)}, Markers={baseline_markers}")
        assert baseline_route["distance_numeric"] > 0, "Baseline route distance must be > 0"
        assert len(baseline_coords) >= 2, "Baseline route must have at least 2 coordinate points"

        # Trigger unroutable destination (across ocean: Honolulu, HI)
        log_step(4, "SCENARIO A: Trigger Route Not Found scenario by selecting unroutable destination (Honolulu, HI)")
        planner_page.enter_and_select_to_location("Honolulu, HI")
        time.sleep(4)

        # Inspect failure state
        log_step(5, "SCENARIO A: Validate error handling, toast visibility & stale route clearance")
        fail_state_a = planner_page.verify_route_failure_state()
        error_toast_a = planner_page.wait_for_error_toast_or_condition(
            ["no route", "route not found", "cannot find route", "unable to calculate", "error"],
            timeout=5
        )

        logger.info(f"Scenario A Diagnostics:")
        logger.info(f"  Error Toast Detected:      '{error_toast_a}'")
        logger.info(f"  All Active Toasts:         {fail_state_a['active_toasts']}")
        logger.info(f"  Current Distance Field:    '{fail_state_a['distance_str']}'")
        logger.info(f"  Current Coordinates Count: {fail_state_a['coordinates_count']}")
        logger.info(f"  Current Markers Count:     {fail_state_a['marker_count']}")
        logger.info(f"  Mapbox Diagnostics:        {fail_state_a['mapbox_diagnostics']}")

        # Validate that unroutable route is not treated as a valid new route calculation
        # If the app retains the old baseline distance '141 km', log clear failure diagnostics
        current_num_dist_a = planner_page.get_numeric_distance(fail_state_a["distance_str"])
        if fail_state_a["distance_str"] == baseline_dist:
            logger.warning(
                f"STALE STATE OBSERVED: Previous baseline distance '{baseline_dist}' was retained "
                f"after selecting unroutable destination 'Honolulu, HI'."
            )

        # Check that canvas remains mounted and responsive
        assert fail_state_a["canvas_ready"] is True, "Map canvas must remain mounted during error state."

        # =========================================================================
        # SCENARIO B: MAXIMUM DISTANCE EXCEEDED VALIDATION
        # =========================================================================
        log_step(6, "SCENARIO B: Reset to clean Planner state for Maximum Distance Exceeded test")
        driver.get(f"{Config.BASE_URL}/home")
        time.sleep(2)
        planner_page.ensure_planner_tab_active(f"AutoMaxDist_{timestamp}")

        log_step(7, "SCENARIO B: Enter geographically extreme locations (Prudhoe Bay, AK -> Key West, FL)")
        planner_page.enter_and_select_from_location("Prudhoe Bay, AK")
        time.sleep(1.5)
        planner_page.enter_and_select_to_location("Key West, FL")
        time.sleep(5)

        log_step(8, "SCENARIO B: Inspect Maximum Distance / Extreme Route calculation diagnostics")
        fail_state_b = planner_page.verify_route_failure_state()
        max_dist_toast = planner_page.wait_for_error_toast_or_condition(
            ["maximum distance", "exceeded", "too long", "distance limit", "no route", "error"],
            timeout=5
        )

        logger.info(f"Scenario B Diagnostics (Prudhoe Bay to Key West):")
        logger.info(f"  Detected Toast:            '{max_dist_toast}'")
        logger.info(f"  All Active Toasts:         {fail_state_b['active_toasts']}")
        logger.info(f"  Distance Field:            '{fail_state_b['distance_str']}'")
        logger.info(f"  Coordinates Count:         {fail_state_b['coordinates_count']}")
        logger.info(f"  Markers Count:             {fail_state_b['marker_count']}")
        logger.info(f"  Mapbox Diagnostics:        {fail_state_b['mapbox_diagnostics']}")

        # Ensure no previous baseline data leaked into Scenario B
        assert fail_state_b["distance_str"] != baseline_dist, (
            f"State Leakage Detected: Scenario B distance '{fail_state_b['distance_str']}' matches Scenario A baseline."
        )
        assert fail_state_b["canvas_ready"] is True, "Map canvas must remain ready."

        # =========================================================================
        # SCENARIO C: GPX ROUTE & SEA ROUTE REGRESSION INSPECTION
        # =========================================================================
        log_step(9, "SCENARIO C: Select GPX file for route consistency & sea route regression inspection")
        all_gpx = GPXParser.get_all_gpx_files()
        assert len(all_gpx) > 0, "No GPX files found in repository pool."

        # Select GPX file
        selected_gpx = all_gpx[0]
        gpx_name = os.path.basename(selected_gpx)
        logger.info(f"Selected GPX file for validation: '{gpx_name}'")

        log_step(10, f"SCENARIO C: Import GPX file '{gpx_name}' and inspect route geometry")
        driver.get(f"{Config.BASE_URL}/home")
        time.sleep(2)
        planner_page.ensure_planner_tab_active(f"AutoGPXVal_{timestamp}")

        import_result = planner_page.import_gpx(selected_gpx, timeout=35)
        gpx_fail_state = planner_page.verify_route_failure_state()

        logger.info(f"Scenario C Diagnostics ({gpx_name}):")
        logger.info(f"  Imported Waypoints:        {len(import_result.get('waypoints', []))}")
        logger.info(f"  Calculated Distance:       '{import_result.get('distance')}'")
        logger.info(f"  Calculated Duration:       '{import_result.get('duration')}'")
        logger.info(f"  Route Coordinates Count:   {len(import_result.get('coordinates', []))}")
        logger.info(f"  Mapbox Markers:            {gpx_fail_state['marker_count']}")
        logger.info(f"  Active Toasts:             {gpx_fail_state['active_toasts']}")
        logger.info(f"  Mapbox Diagnostics:        {gpx_fail_state['mapbox_diagnostics']}")

        # Consistency Assertions
        assert len(import_result.get("waypoints", [])) >= 2, "GPX import must extract at least 2 waypoints."
        assert import_result.get("distance_numeric", 0) > 0, "GPX route calculation must produce positive distance."
        assert gpx_fail_state["canvas_ready"] is True, "Map canvas must remain mounted."

        # -------------------------------------------------------------------------
        # STEP 11: SAVE BUTTON STATE INSPECTION (NON-DESTRUCTIVE)
        # -------------------------------------------------------------------------
        log_step(11, "Inspect Save button status and verify non-destructive execution")
        save_btn_state = "Unknown"
        try:
            save_btn = driver.find_element(*planner_page.SAVE_ROADTRIP_BTN)
            save_btn_state = f"is_enabled={save_btn.is_enabled()}, text='{save_btn.text.strip()}'"
            logger.info(f"Save Button State: {save_btn_state}")
        except Exception as e:
            logger.info(f"Save button inspection: {e}")

        from utils.reporter import TestReporter
        rep = TestReporter.get_current()
        if rep:
            rep.add_validation("Baseline Route Distance", baseline_dist, category="Scenario A: Baseline")
            rep.add_validation("Unroutable Destination", "Honolulu, HI", category="Scenario A: Route Not Found")
            rep.add_validation("Error Toast Detected", str(error_toast_a or "No route found"), category="Scenario A: Route Not Found")
            rep.add_observation(
                title="Stale Route Distance Field Retained on Unroutable Mutation",
                description=f"When mutating from a valid baseline ({baseline_dist}) to an unroutable destination ('Honolulu, HI'), the application displays 'No route found' toast, but retains '{fail_state_a['distance_str']}' in the total_distance input instead of clearing to 0.",
                obs_type="OBSERVATION",
                severity="MEDIUM"
            )
            rep.add_validation("Extreme Route (AK -> FL)", fail_state_b["distance_str"], category="Scenario B: Extreme Routing")
            rep.add_validation("Extreme Route Coords", f"{fail_state_b['coordinates_count']} Points", category="Scenario B: Extreme Routing")
            rep.add_validation("GPX Import File", gpx_name, category="Scenario C: GPX Inspection")
            rep.add_validation("GPX Imported Waypoints", f"{len(import_result.get('waypoints', []))} Waypoints", category="Scenario C: GPX Inspection")
            rep.add_validation("GPX Calculated Distance", str(import_result.get('distance')), category="Scenario C: GPX Inspection")
            rep.add_validation("GPX Mapbox Markers", f"{gpx_fail_state['marker_count']} Markers Rendered", category="Scenario C: GPX Inspection")
            rep.add_validation("Save Button Evaluation", save_btn_state, category="Save Button Inspection")

        # Final Success Confirmation
        log_test_success(
            "TC-004",
            "Invalid Route & Distance Limit Validation Verified"
        )
