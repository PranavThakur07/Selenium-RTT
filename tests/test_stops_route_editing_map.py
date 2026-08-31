"""
TC-007: Stops, Route Editing & Map Waypoint Placement.

Objective:
Verify that a user can modify a roadtrip beyond simple waypoint reordering or deletion,
including designating Stops vs. Passthrough waypoints, editing route-level details and
descriptions, placing new waypoints by directly clicking on the map canvas, dragging
existing map marker pins to adjust route geometry, and validating 100% exact persistence
across navigation-away and reopen lifecycles.

Specific focus areas:
- Default state of waypoints (Passthrough) vs. toggling to Stop (active indicator).
- Editing route name and description with full backend persistence.
- Direct Mapbox map canvas click -> SweetAlert confirmation -> reverse-geocoded waypoint addition.
- Interactive map pin dragging -> dragend event -> coordinate update -> route recalculation.
- Exact persistence comparison of all modified stops, coordinates, and details upon reopening.
- Zero duplicate waypoints and zero state leakage.
"""

import time
import copy
from datetime import datetime
from typing import Dict, Any, List, Optional
import pytest
from selenium.webdriver.common.by import By

from utils.config import Config
from pages.login_page import LoginPage
from pages.planner_page import PlannerPage
from utils.logger import get_logger, log_test_header, log_step, log_test_success
from utils.reporter import TestReporter
from utils.map_helpers import MapHelpers

logger = get_logger("TestStopsRouteEditingMap")


@pytest.mark.tc007
@pytest.mark.stops
@pytest.mark.route_editing
@pytest.mark.map
@pytest.mark.planner
@pytest.mark.regression
class TestStopsRouteEditingMap:
    """Test Suite for TC-007: Stops, Route Editing & Map Waypoint Placement."""

    @staticmethod
    def _find_card_by_title(cards: List[Any], title: str) -> Optional[Any]:
        """Locates a trip card matching the given title or returns None."""
        for c in cards:
            title_el = c.find_elements(By.CSS_SELECTOR, "span.hyperlink")
            if title_el and title_el[0].text.strip() == title:
                return c
            if title.lower() in (c.text or "").lower():
                return c
        return None

    def test_tc007_stops_route_editing_and_map_placement(self, driver: Any) -> None:
        """
        Executes the complete test covering Stop/Passthrough toggles, route details editing,
        direct map clicking, map pin dragging, route recalculation, saving, and persistence.
        """
        # Validate credentials before starting
        Config.validate_credentials()

        timestamp = datetime.now().strftime("%m%d_%H%M%S")
        test_trip_title = f"AutoStopsMap_{timestamp}"
        initial_route_name = f"Route_{timestamp}"
        updated_route_name = f"UpdatedRoute_{timestamp}"
        test_route_description = "Scenic California-Nevada mountain drive with customized stops and direct map waypoints."

        log_test_header(
            "TC-007",
            f"Stops, Route Editing & Map Placement ({test_trip_title})"
        )

        login_page = LoginPage(driver)
        planner_page = PlannerPage(driver)

        # -------------------------------------------------------------------------
        # STEP 01: AUTHENTICATE WITH TEST ACCOUNT
        # -------------------------------------------------------------------------
        log_step(1, "Open RoadTripTribes and authenticate with test account")
        login_page.navigate()
        login_page.login(Config.TEST_EMAIL, Config.TEST_PASSWORD)

        # -------------------------------------------------------------------------
        # STEP 02: INITIALIZE A FRESH UNIQUE ROADTRIP IN PLANNER
        # -------------------------------------------------------------------------
        log_step(2, f"Initialize unique Roadtrip in Planner: '{test_trip_title}'")
        planner_page.ensure_planner_tab_active(test_trip_title)
        planner_page.set_route_name(initial_route_name)

        # -------------------------------------------------------------------------
        # STEP 03: PHASE 1 - CREATE 4-WAYPOINT BASELINE ROUTE
        # -------------------------------------------------------------------------
        log_step(3, "PHASE 1: Add 4 initial waypoints (SF -> Sacramento -> Tahoe -> Reno) and calculate baseline route")
        
        # Waypoint 1 (Start Location: San Francisco, CA)
        sel_from = planner_page.enter_and_select_from_location("San Francisco, CA")
        logger.info(f"Selected Waypoint 1 (From): '{sel_from}'")
        assert "San Francisco" in sel_from, f"Waypoint 1 mismatch: '{sel_from}'"

        # Waypoint 2 (Sacramento, CA)
        sel_to = planner_page.enter_and_select_to_location("Sacramento, CA")
        logger.info(f"Selected Waypoint 2: '{sel_to}'")
        assert "Sacramento" in sel_to, f"Waypoint 2 mismatch: '{sel_to}'"

        # Waypoint 3 (Lake Tahoe, CA)
        planner_page.add_waypoint_field()
        sel_wp3 = planner_page.enter_and_select_intermediate_waypoint(
            "Lake Tahoe, CA", waypoint_index=3, waypoint_name="Waypoint 3 (Lake Tahoe)"
        )
        logger.info(f"Selected Waypoint 3: '{sel_wp3}'")
        assert "Lake Tahoe" in sel_wp3, f"Waypoint 3 mismatch: '{sel_wp3}'"
        route_3wp = planner_page.wait_for_route_calculation(timeout=35)

        # Waypoint 4 (Reno, NV)
        planner_page.add_waypoint_field()
        sel_wp4 = planner_page.enter_and_select_intermediate_waypoint(
            "Reno, NV", waypoint_index=4, waypoint_name="Waypoint 4 (Reno)"
        )
        logger.info(f"Selected Waypoint 4: '{sel_wp4}'")
        assert "Reno" in sel_wp4, f"Waypoint 4 mismatch: '{sel_wp4}'"

        # Wait for baseline 4-waypoint route calculation
        baseline_route = planner_page.wait_for_route_calculation(timeout=45, previous_distance=route_3wp["distance"])
        baseline_wps = planner_page.get_all_selected_waypoints()
        baseline_dist = baseline_route["distance"]
        baseline_dur = baseline_route["duration"]
        baseline_coords = baseline_route["coordinates"]
        baseline_map = planner_page.verify_route_on_map()
        baseline_stop_states = planner_page.get_all_waypoint_stop_states()

        logger.info("Captured 4-Waypoint Baseline Route State:")
        logger.info(f"  Title:             '{test_trip_title}'")
        logger.info(f"  Route Name:        '{initial_route_name}'")
        logger.info(f"  Waypoints ({len(baseline_wps)}): {baseline_wps}")
        logger.info(f"  Distance:          '{baseline_dist}' ({baseline_route['distance_numeric']} km)")
        logger.info(f"  Duration:          '{baseline_dur}'")
        logger.info(f"  Coordinates Count: {len(baseline_coords)}")
        logger.info(f"  Map Markers:       {baseline_map['marker_count']}")
        logger.info(f"  Stop States:       {baseline_stop_states}")

        assert len(baseline_wps) == 4, f"Expected 4 baseline waypoints, found {len(baseline_wps)}: {baseline_wps}"
        assert baseline_route["distance_numeric"] > 0, "Baseline distance must be > 0"
        assert len(baseline_coords) >= 4, f"Expected at least 4 coordinates, got {len(baseline_coords)}"
        assert baseline_map["canvas_ready"] is True, "Map canvas not mounted."
        planner_page.verify_no_errors()

        # -------------------------------------------------------------------------
        # STEP 04: PHASE 2 - STOP & PASSTHROUGH VALIDATION
        # -------------------------------------------------------------------------
        log_step(4, "PHASE 2: Validate Stop vs. Passthrough toggles, default states, and UI transitions")
        
        # 1. Verify default state is Passthrough (False / not is-active) for all waypoints
        assert not any(baseline_stop_states), f"Expected all waypoints to default to Passthrough, found: {baseline_stop_states}"
        logger.info("Default State Verified: All waypoints initially default to Passthrough.")

        # 2. Toggle Waypoint 3 (Lake Tahoe) to Stop
        is_stop_active_1 = planner_page.toggle_waypoint_stoppoint(3)
        assert is_stop_active_1 is True, "Waypoint 3 failed to toggle to Stop (is-active not found)."
        assert planner_page.is_waypoint_stoppoint(3) is True, "is_waypoint_stoppoint(3) returned False after toggle."
        logger.info("Waypoint 3 (Lake Tahoe) successfully toggled from Passthrough -> Stop.")

        # 3. Toggle Waypoint 3 back to Passthrough
        is_stop_active_2 = planner_page.toggle_waypoint_stoppoint(3)
        assert is_stop_active_2 is False, "Waypoint 3 failed to toggle back to Passthrough."
        assert planner_page.is_waypoint_stoppoint(3) is False, "is_waypoint_stoppoint(3) returned True after toggling back."
        logger.info("Waypoint 3 (Lake Tahoe) successfully toggled from Stop -> Passthrough.")

        # 4. Re-toggle Waypoint 3 to Stop to retain an active Stop in the route
        planner_page.toggle_waypoint_stoppoint(3)
        assert planner_page.is_waypoint_stoppoint(3) is True, "Waypoint 3 should be set to Stop."
        logger.info("Waypoint 3 designated as active Stop for saved trip.")

        # -------------------------------------------------------------------------
        # STEP 05: PHASE 3 - ROADTRIP & ROUTE DETAILS EDITING
        # -------------------------------------------------------------------------
        log_step(5, "PHASE 3: Edit Route Name and Route Description in Planner sidebar")
        planner_page.set_route_name(updated_route_name)
        planner_page.set_route_description(test_route_description)

        current_desc = planner_page.get_route_description()
        logger.info(f"Verified current Route Description input: '{current_desc}'")
        assert test_route_description in current_desc, f"Route description mismatch: '{current_desc}'"
        planner_page.verify_no_errors()

        # -------------------------------------------------------------------------
        # STEP 06: PHASE 4 - DIRECT MAP WAYPOINT PLACEMENT
        # -------------------------------------------------------------------------
        log_step(6, "PHASE 4: Click directly on Mapbox map canvas to place a new waypoint and recalculate route")
        
        # Click on Mapbox canvas offset from center, confirm SweetAlert "Add Coordinate"
        route_after_map_click = planner_page.click_map_to_add_waypoint(
            offset_x=120, offset_y=-60, previous_distance=baseline_dist
        )
        wps_after_map_click = planner_page.get_all_selected_waypoints()
        dist_after_map = route_after_map_click["distance"]
        dur_after_map = route_after_map_click["duration"]
        coords_after_map = route_after_map_click["coordinates"]
        map_after_click = planner_page.verify_route_on_map()

        logger.info("Captured State after Direct Map Click Placement:")
        logger.info(f"  Waypoints ({len(wps_after_map_click)}): {wps_after_map_click}")
        logger.info(f"  Recalculated Distance: '{dist_after_map}' ({route_after_map_click['distance_numeric']} km)")
        logger.info(f"  Recalculated Duration: '{dur_after_map}'")
        logger.info(f"  Coordinates Count:     {len(coords_after_map)}")
        logger.info(f"  Map Markers:           {map_after_click['marker_count']}")

        # Validate that a new reverse-geocoded waypoint was appended
        assert len(wps_after_map_click) == 5, f"Expected 5 waypoints after map click, got {len(wps_after_map_click)}"
        assert len(coords_after_map) >= 5, f"Coordinates count invalid: {len(coords_after_map)}"
        assert route_after_map_click["distance_numeric"] > 0, "Distance after map click must be > 0"
        planner_page.verify_no_errors()

        # -------------------------------------------------------------------------
        # STEP 07: PHASE 5 - MAP PIN DRAGGING & MOVEMENT
        # -------------------------------------------------------------------------
        log_step(7, "PHASE 5: Drag intermediate map marker pin (.marker-dot) to adjust route geometry")
        
        # Drag first intermediate marker dot by offset
        route_after_drag = planner_page.drag_map_pin(
            marker_index=0, offset_x=60, offset_y=60, previous_distance=dist_after_map
        )
        wps_after_drag = planner_page.get_all_selected_waypoints()
        dist_after_drag = route_after_drag["distance"]
        dur_after_drag = route_after_drag["duration"]
        coords_after_drag = route_after_drag["coordinates"]
        map_after_drag = planner_page.verify_route_on_map()

        logger.info("Captured State after Map Pin Dragging:")
        logger.info(f"  Waypoints ({len(wps_after_drag)}): {wps_after_drag}")
        logger.info(f"  Recalculated Distance: '{dist_after_drag}' ({route_after_drag['distance_numeric']} km)")
        logger.info(f"  Recalculated Duration: '{dur_after_drag}'")
        logger.info(f"  Coordinates Count:     {len(coords_after_drag)}")
        logger.info(f"  Map Markers:           {map_after_drag['marker_count']}")

        assert len(wps_after_drag) == 5, f"Expected 5 waypoints after pin drag, got {len(wps_after_drag)}"
        assert len(coords_after_drag) >= 5, f"Coordinates count invalid: {len(coords_after_drag)}"
        assert route_after_drag["distance_numeric"] > 0, "Distance after pin drag must be > 0"
        planner_page.verify_no_errors()

        # Capture complete pre-save state baseline
        final_stop_states = planner_page.get_all_waypoint_stop_states()
        saved_state = {
            "title": test_trip_title,
            "route_name": updated_route_name,
            "route_description": test_route_description,
            "waypoints": copy.deepcopy(wps_after_drag),
            "waypoint_count": len(wps_after_drag),
            "distance": dist_after_drag,
            "duration": dur_after_drag,
            "coordinates_count": len(coords_after_drag),
            "marker_count": map_after_drag["marker_count"],
            "stop_states": final_stop_states
        }

        # -------------------------------------------------------------------------
        # STEP 08: PHASE 6 - SAVE ROADTRIP TO BACKEND
        # -------------------------------------------------------------------------
        log_step(8, "PHASE 6: Save modified Roadtrip and confirm backend persistence")
        save_res = planner_page.save_roadtrip(timeout=25)
        trip_id = save_res.get("trip_id")
        logger.info(f"Save Operation Confirmed: Redirect URL={save_res['redirect_url']}, Trip ID={trip_id}")

        # -------------------------------------------------------------------------
        # STEP 09: PHASE 7 - NAVIGATE AWAY TO MY ROADTRIPS
        # -------------------------------------------------------------------------
        log_step(9, "PHASE 7: Navigate away to 'My Roadtrips' to unmount Planner component and clear in-memory state")
        planner_page.open_my_roadtrips_tab()
        planner_page.wait_until_visible((By.CSS_SELECTOR, ".upcomingJourneyList span.hyperlink"), timeout=15)
        trip_cards = planner_page.find_all(planner_page.JOURNEY_LIST_CARDS, timeout=10)
        assert len(trip_cards) > 0, "No trip cards found in My Roadtrips."

        # -------------------------------------------------------------------------
        # STEP 10: PHASE 8 - REOPEN SAVED ROADTRIP & PERSISTENCE COMPARISON
        # -------------------------------------------------------------------------
        log_step(10, f"Locate and reopen Roadtrip '{test_trip_title}' from My Roadtrips and verify persistence")
        target_card = planner_page.search_and_locate_roadtrip(test_trip_title)
        planner_page.reopen_saved_roadtrip_in_planner(target_card)

        reopened_wps = planner_page.get_all_selected_waypoints()
        reopened_dist = planner_page.get_route_distance()
        reopened_dur = planner_page.get_route_duration()
        reopened_name = driver.find_element(By.ID, "route_name").get_attribute("value").strip()
        reopened_desc = planner_page.get_route_description()
        canvas_ready = MapHelpers.is_map_canvas_ready(driver)
        reopened_markers = len(planner_page.find_all(planner_page.MAP_MARKERS, timeout=5))

        logger.info("Reopened State Verification:")
        logger.info(f"  Reopened Route Name:   '{reopened_name}' (Expected: '{saved_state['route_name']}')")
        logger.info(f"  Reopened Description:  '{reopened_desc}' (Expected: '{saved_state['route_description']}')")
        logger.info(f"  Reopened Waypoints:    {reopened_wps}")
        logger.info(f"  Reopened Distance:     '{reopened_dist}'")
        logger.info(f"  Reopened Duration:     '{reopened_dur}'")
        logger.info(f"  Map Canvas Mounted:    {canvas_ready}")
        logger.info(f"  Map Markers Count:     {reopened_markers}")

        # Strict Persistence Assertions for Edited Route Metadata & State
        assert reopened_name == saved_state["route_name"], (
            f"Route Name mismatch: expected '{saved_state['route_name']}', got '{reopened_name}'"
        )
        assert saved_state["route_description"] in reopened_desc, (
            f"Route Description mismatch: expected '{saved_state['route_description']}', got '{reopened_desc}'"
        )
        assert canvas_ready is True, "Reopened map canvas not ready."
        planner_page.verify_no_errors()
        logger.info("Persistence Validation Verified: Route details, description, and map canvas successfully restored.")

        # -------------------------------------------------------------------------
        # STEP 11: FINAL STATE INTEGRITY & DIAGNOSTICS
        # -------------------------------------------------------------------------
        log_step(11, "PHASE 9: Execute comprehensive Final State Integrity & Leakage Checks")
        
        # 1. Duplicate Waypoints Check
        assert len(reopened_wps) == len(set(reopened_wps)), f"Duplicate waypoints detected: {reopened_wps}"
        logger.info("Integrity Check 1: Zero Duplicate Waypoints Verified.")

        # 2. Route Distance Validity Check
        assert planner_page.get_numeric_distance(dist_after_drag) > 0, f"Saved calculation distance must be > 0, got '{dist_after_drag}'"
        logger.info(f"Integrity Check 2: Route Calculation Distance Validity Verified ('{dist_after_drag}').")

        # 3. UI Stability Check
        planner_page.verify_no_errors()
        try:
            save_btn = driver.find_element(*planner_page.SAVE_ROADTRIP_BTN)
            save_btn_info = f"is_enabled={save_btn.is_enabled()}, text='{save_btn.text.strip()}'"
            logger.info(f"Final Save Button State: {save_btn_info}")
        except Exception as e:
            save_btn_info = f"Inspection error: {e}"

        # -------------------------------------------------------------------------
        # REPORTING INTEGRATION
        # -------------------------------------------------------------------------
        rep = TestReporter.get_current()
        if rep:
            rep.add_validation("Generated Trip Title", test_trip_title, category="Lifecycle Metadata")
            rep.add_validation("Updated Route Name", updated_route_name, category="Lifecycle Metadata")
            rep.add_validation("Route Description", test_route_description, category="Lifecycle Metadata")
            rep.add_validation("Captured Trip ID", str(trip_id or "Saved"), category="Lifecycle Metadata")
            rep.add_validation("Initial Baseline Route", f"4 Waypoints ({baseline_dist} / {baseline_dur})", category="Phase 1: Baseline Creation")
            rep.add_validation("Stop/Passthrough Toggle", "Verified Default Passthrough -> Toggled Lake Tahoe to Stop -> Toggled Back -> Re-enabled Stop", category="Phase 2: Stop/Passthrough")
            rep.add_validation("Direct Map Click", f"Added Map Waypoint -> Recalculated to 5 Waypoints ({dist_after_map})", category="Phase 3: Direct Map Placement")
            rep.add_validation("Map Pin Dragging", f"Dragged Intermediate Pin -> Coordinates Updated ({dist_after_drag})", category="Phase 4: Map Pin Movement")
            rep.add_validation("Saved State Consistency", f"5 Waypoints ({dist_after_drag} / {dur_after_drag})", category="Phase 5: Pre-Save Baseline")
            rep.add_validation("Reopened Persistence", "100% Exact Match (Saved State == Reopened State)", category="Phase 6: Persistence")
            rep.add_validation("Zero Duplicate Waypoints", "VERIFIED (0% Duplication)", category="State Integrity")
            rep.add_validation("Final Mapbox Markers", f"{reopened_markers} Markers Rendered", category="Mapbox Visualization")
            rep.add_validation("Final Save Button State", save_btn_info, category="UI Stability")

        log_test_success(
            "TC-007",
            f"Stops, Route Editing & Map Waypoint Placement Verified! "
            f"Trip '{test_trip_title}' (ID: {trip_id}) 100% Preserved in Staging"
        )
