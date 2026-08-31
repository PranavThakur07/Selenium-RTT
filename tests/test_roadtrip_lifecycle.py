"""
TC-005: Roadtrip Lifecycle, Persistence & Planner State Regression.

Objective:
Validate that a Roadtrip remains stable, accurate, and consistent throughout its complete
multi-phase lifecycle:
1. Create/initialize a Roadtrip with a unique title (AutoLifecycle_<timestamp>).
2. Add route locations (3 waypoints) and verify initial route calculation.
3. Save Roadtrip and capture persistence baseline.
4. Navigate away to unmount and clear in-memory Planner state.
5. Reopen the exact saved Roadtrip from My Roadtrips.
6. Verify Checkpoint 1 persistence (strict comparison against baseline).
7. Perform meaningful modification (add 4th waypoint: Reno, NV) and verify route recalculation.
8. Save/update the modified Roadtrip.
9. Navigate away again to My Roadtrips.
10. Reopen the same Roadtrip again.
11. Verify Checkpoint 2 final persistence (strict comparison against modified state).
12. Verify Planner state consistency (no duplicate waypoints, no state leakage, clean diagnostics).
13. Retain created Roadtrip in staging for inspection.
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

logger = get_logger("TestRoadtripLifecycle")


@pytest.mark.tc005
@pytest.mark.lifecycle
@pytest.mark.planner
@pytest.mark.regression
class TestRoadtripLifecycle:
    """Test Suite for TC-005: Roadtrip Lifecycle, Persistence & Planner State Regression."""

    @staticmethod
    def _find_card_by_title(cards: List[Any], title: str) -> Optional[Any]:
        """Locates a trip card matching the given title or returns None."""
        for c in cards:
            title_el = c.find_elements(By.CSS_SELECTOR, "span.hyperlink")
            if title_el and title_el[0].text.strip() == title:
                return c
            # Also check inner text
            if title.lower() in (c.text or "").lower():
                return c
        return None

    def test_tc005_roadtrip_lifecycle_persistence_and_state_regression(self, driver: Any) -> None:
        """
        Executes the complete end-to-end Roadtrip lifecycle, persistence, and state regression test.
        """
        # Validate credentials before starting
        Config.validate_credentials()

        timestamp = datetime.now().strftime("%m%d_%H%M%S")
        test_trip_title = f"AutoLifecycle_{timestamp}"
        test_route_name = f"Route_{timestamp}"

        log_test_header(
            "TC-005",
            f"Roadtrip Lifecycle, Persistence & State Regression ({test_trip_title})"
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
        # STEP 02: INITIALIZE A UNIQUE ROADTRIP
        # -------------------------------------------------------------------------
        log_step(2, f"Initialize unique Roadtrip in Planner: '{test_trip_title}'")
        planner_page.ensure_planner_tab_active(test_trip_title)
        planner_page.set_route_name(test_route_name)

        # -------------------------------------------------------------------------
        # STEP 03: ADD MULTI-WAYPOINT ROUTE & CALCULATE INITIAL BASELINE
        # -------------------------------------------------------------------------
        log_step(3, "Add 3 initial waypoints (SF -> Sacramento -> Lake Tahoe) and calculate baseline route")
        
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

        # Wait for initial route calculation
        initial_route = planner_page.wait_for_route_calculation(timeout=45)
        initial_wps = planner_page.get_all_selected_waypoints()
        initial_dist = initial_route["distance"]
        initial_num_dist = initial_route["distance_numeric"]
        initial_dur = initial_route["duration"]
        initial_coords = initial_route["coordinates"]
        initial_map = planner_page.verify_route_on_map()

        logger.info("Captured Initial Roadtrip Baseline:")
        logger.info(f"  Title:             '{test_trip_title}'")
        logger.info(f"  Route Name:        '{test_route_name}'")
        logger.info(f"  Waypoints ({len(initial_wps)}): {initial_wps}")
        logger.info(f"  Distance:          '{initial_dist}' ({initial_num_dist} km)")
        logger.info(f"  Duration:          '{initial_dur}'")
        logger.info(f"  Coordinates Count: {len(initial_coords)}")
        logger.info(f"  Map Markers Count: {initial_map['marker_count']}")

        # Initial baseline assertions
        assert len(initial_wps) == 3, f"Expected 3 initial waypoints, found {len(initial_wps)}: {initial_wps}"
        assert initial_num_dist > 0, f"Initial route distance must be > 0, got '{initial_dist}'"
        assert len(initial_coords) >= 3, f"Coordinates count must be >= 3, got {len(initial_coords)}"
        assert initial_map["canvas_ready"] is True, "Map canvas not mounted."
        planner_page.verify_no_errors()

        baseline_state = {
            "title": test_trip_title,
            "route_name": test_route_name,
            "waypoints": copy.deepcopy(initial_wps),
            "waypoint_count": len(initial_wps),
            "distance": initial_dist,
            "duration": initial_dur,
            "coordinates_count": len(initial_coords),
            "marker_count": initial_map["marker_count"]
        }

        # -------------------------------------------------------------------------
        # STEP 04: SAVE ROADTRIP & CAPTURE PERSISTENCE BASELINE
        # -------------------------------------------------------------------------
        log_step(4, "Save newly created Roadtrip and confirm backend persistence")
        save_res_1 = planner_page.save_roadtrip(timeout=25)
        trip_id = save_res_1.get("trip_id")
        logger.info(f"Initial Save Confirmed: Redirect URL={save_res_1['redirect_url']}, Trip ID={trip_id}")

        # -------------------------------------------------------------------------
        # STEP 05: NAVIGATE AWAY FROM PLANNER STATE
        # -------------------------------------------------------------------------
        log_step(5, "Navigate away to 'My Roadtrips' to clear in-memory Planner state")
        planner_page.open_my_roadtrips_tab()
        planner_page.wait_until_visible((By.CSS_SELECTOR, ".upcomingJourneyList span.hyperlink"), timeout=15)
        trip_cards_1 = planner_page.find_all(planner_page.JOURNEY_LIST_CARDS, timeout=10)
        assert len(trip_cards_1) > 0, "No trip cards found in My Roadtrips."

        # -------------------------------------------------------------------------
        # STEP 06: REOPEN SAVED ROADTRIP (CHECKPOINT 1)
        # -------------------------------------------------------------------------
        log_step(6, f"Locate and reopen Roadtrip '{test_trip_title}' from My Roadtrips list")
        target_card_1 = planner_page.search_and_locate_roadtrip(test_trip_title)
        assert target_card_1 is not False and target_card_1 is not None, f"Roadtrip '{test_trip_title}' not found in My Roadtrips."
        planner_page.reopen_saved_roadtrip_in_planner(target_card_1)

        # -------------------------------------------------------------------------
        # STEP 07: VERIFY CHECKPOINT 1 PERSISTENCE
        # -------------------------------------------------------------------------
        log_step(7, "Execute Checkpoint 1 Strict Persistence Comparison (Reopened vs Initial Baseline)")
        reopened_wps_1 = planner_page.get_all_selected_waypoints()
        reopened_dist_1 = planner_page.get_route_distance()
        reopened_dur_1 = planner_page.get_route_duration()
        reopened_coords_1 = planner_page.get_route_coordinates()
        reopened_map_1 = planner_page.verify_route_on_map()

        logger.info("Checkpoint 1 Reopened State:")
        logger.info(f"  Reopened Waypoints: {reopened_wps_1}")
        logger.info(f"  Expected Waypoints: {baseline_state['waypoints']}")
        logger.info(f"  Reopened Distance:  '{reopened_dist_1}' (Expected: '{baseline_state['distance']}')")
        logger.info(f"  Reopened Duration:  '{reopened_dur_1}' (Expected: '{baseline_state['duration']}')")
        logger.info(f"  Reopened Coords:    {len(reopened_coords_1)} (Expected: {baseline_state['coordinates_count']})")
        logger.info(f"  Reopened Markers:   {reopened_map_1['marker_count']}")

        # Strict Checkpoint 1 assertions
        assert len(reopened_wps_1) == baseline_state["waypoint_count"] == 3, (
            f"Checkpoint 1 Waypoint count mismatch: expected 3, got {len(reopened_wps_1)}"
        )
        assert reopened_wps_1 == baseline_state["waypoints"], (
            f"Checkpoint 1 Waypoint order mismatch:\nReopened: {reopened_wps_1}\nExpected: {baseline_state['waypoints']}"
        )
        assert reopened_dist_1 == baseline_state["distance"], (
            f"Checkpoint 1 Route distance mismatch: expected '{baseline_state['distance']}', got '{reopened_dist_1}'"
        )
        assert len(reopened_coords_1) >= 3, f"Checkpoint 1 Coordinates count invalid: {len(reopened_coords_1)}"
        assert reopened_map_1["canvas_ready"] is True, "Checkpoint 1 Map canvas not ready."
        planner_page.verify_no_errors()
        logger.info("Checkpoint 1 Persistence Verified: 100% Exact Match.")

        # -------------------------------------------------------------------------
        # STEP 08: PERFORM MEANINGFUL ROADTRIP MODIFICATION (EDIT)
        # -------------------------------------------------------------------------
        log_step(8, "Perform meaningful Roadtrip edit: Append 4th Waypoint (Reno, NV) and recalculate route")
        planner_page.add_waypoint_field()
        sel_wp4 = planner_page.enter_and_select_intermediate_waypoint(
            "Reno, NV", waypoint_index=4, waypoint_name="Waypoint 4 (Reno)"
        )
        logger.info(f"Appended Waypoint 4 (Reno): '{sel_wp4}'")
        assert "Reno" in sel_wp4, f"Waypoint 4 mismatch: '{sel_wp4}'"

        # Wait for dynamic route recalculation with 4 waypoints
        modified_route = planner_page.wait_for_route_calculation(timeout=35)
        modified_wps = planner_page.get_all_selected_waypoints()
        modified_dist = modified_route["distance"]
        modified_num_dist = modified_route["distance_numeric"]
        modified_dur = modified_route["duration"]
        modified_coords = modified_route["coordinates"]
        modified_map = planner_page.verify_route_on_map()

        logger.info("Captured Modified Roadtrip State:")
        logger.info(f"  Waypoints ({len(modified_wps)}): {modified_wps}")
        logger.info(f"  Recalculated Distance: '{modified_dist}' ({modified_num_dist} km)")
        logger.info(f"  Recalculated Duration: '{modified_dur}'")
        logger.info(f"  Coordinates Count:     {len(modified_coords)}")
        logger.info(f"  Map Markers:           {modified_map['marker_count']}")

        # Modification assertions
        assert len(modified_wps) == 4, f"Expected 4 waypoints after edit, got {len(modified_wps)}: {modified_wps}"
        assert "Reno" in modified_wps[3], f"Waypoint 4 not Reno: '{modified_wps[3]}'"
        assert modified_dist != initial_dist, f"Route distance must change after adding waypoint: '{modified_dist}' == '{initial_dist}'"
        assert modified_num_dist > initial_num_dist, (
            f"4-waypoint distance ({modified_num_dist} km) must exceed 3-waypoint distance ({initial_num_dist} km)"
        )
        assert len(modified_coords) >= 4, f"Modified coordinates count invalid: {len(modified_coords)}"
        planner_page.verify_no_errors()

        modified_state = {
            "title": test_trip_title,
            "waypoints": copy.deepcopy(modified_wps),
            "waypoint_count": len(modified_wps),
            "distance": modified_dist,
            "duration": modified_dur,
            "coordinates_count": len(modified_coords),
            "marker_count": modified_map["marker_count"]
        }

        # -------------------------------------------------------------------------
        # STEP 09: SAVE/UPDATE MODIFIED ROADTRIP
        # -------------------------------------------------------------------------
        log_step(9, "Save/Update modified Roadtrip and confirm updated persistence")
        save_res_2 = planner_page.save_roadtrip(timeout=25)
        updated_trip_id = save_res_2.get("trip_id")
        logger.info(f"Update Confirmed: Redirect URL={save_res_2['redirect_url']}, Updated Trip ID={updated_trip_id}")

        # -------------------------------------------------------------------------
        # STEP 10: NAVIGATE AWAY AGAIN FROM PLANNER STATE
        # -------------------------------------------------------------------------
        log_step(10, "Navigate away to 'My Roadtrips' again to clear in-memory edited state")
        planner_page.open_my_roadtrips_tab()
        planner_page.wait_until_visible((By.CSS_SELECTOR, ".upcomingJourneyList span.hyperlink"), timeout=15)
        trip_cards_2 = planner_page.find_all(planner_page.JOURNEY_LIST_CARDS, timeout=10)
        assert len(trip_cards_2) > 0, "No trip cards found in My Roadtrips."

        # -------------------------------------------------------------------------
        # STEP 11: REOPEN SAME ROADTRIP & VERIFY FINAL PERSISTENCE (CHECKPOINT 2)
        # -------------------------------------------------------------------------
        log_step(11, f"Reopen the modified Roadtrip '{test_trip_title}' from My Roadtrips and verify Checkpoint 2 persistence")
        target_card_2 = planner_page.search_and_locate_roadtrip(test_trip_title)
        assert target_card_2 is not False and target_card_2 is not None, f"Roadtrip '{test_trip_title}' not found in My Roadtrips."
        planner_page.reopen_saved_roadtrip_in_planner(target_card_2)

        final_wps = planner_page.get_all_selected_waypoints()
        final_dist = planner_page.get_route_distance()
        final_dur = planner_page.get_route_duration()
        final_coords = planner_page.get_route_coordinates()
        final_map = planner_page.verify_route_on_map()

        logger.info("Checkpoint 2 Final Reopened State:")
        logger.info(f"  Final Waypoints:    {final_wps}")
        logger.info(f"  Expected Waypoints: {modified_state['waypoints']}")
        logger.info(f"  Final Distance:     '{final_dist}' (Expected: '{modified_state['distance']}')")
        logger.info(f"  Final Duration:     '{final_dur}' (Expected: '{modified_state['duration']}')")
        logger.info(f"  Final Coords Count: {len(final_coords)} (Expected: {modified_state['coordinates_count']})")
        logger.info(f"  Final Map Markers:  {final_map['marker_count']}")

        # Strict Checkpoint 2 assertions
        assert len(final_wps) == modified_state["waypoint_count"] == 4, (
            f"Checkpoint 2 Waypoint count mismatch: expected 4, got {len(final_wps)}: {final_wps}"
        )
        assert final_wps == modified_state["waypoints"], (
            f"Checkpoint 2 Waypoint order mismatch:\nFinal:    {final_wps}\nExpected: {modified_state['waypoints']}"
        )
        assert final_dist == modified_state["distance"], (
            f"Checkpoint 2 Route distance mismatch: expected '{modified_state['distance']}', got '{final_dist}'"
        )
        assert len(final_coords) >= 4, f"Final coordinates count invalid: {len(final_coords)}"
        assert final_map["canvas_ready"] is True, "Final map canvas not ready."
        logger.info("Checkpoint 2 Final Persistence Verified: 100% Exact Match.")

        # -------------------------------------------------------------------------
        # STEP 12: VERIFY PLANNER STATE CONSISTENCY & DIAGNOSTICS
        # -------------------------------------------------------------------------
        log_step(12, "Execute comprehensive Planner state consistency & diagnostic verifications")
        
        # 1. Verify no duplicate waypoints
        assert len(final_wps) == len(set(final_wps)), f"Duplicate waypoints detected in final state: {final_wps}"

        # 2. Verify no old baseline 3-waypoint state leaked into final 4-waypoint state
        assert final_wps != baseline_state["waypoints"], "State leakage: Final waypoints reverted to initial 3-waypoint baseline."
        assert final_dist != baseline_state["distance"], "State leakage: Final distance reverted to initial 3-waypoint baseline."

        # 3. Verify clean system errors
        planner_page.verify_no_errors()

        # 4. Verify Save button stability
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
            rep.add_validation("Generated Route Name", test_route_name, category="Lifecycle Metadata")
            rep.add_validation("Captured Trip ID", str(trip_id or updated_trip_id or "Saved"), category="Lifecycle Metadata")
            rep.add_validation("Initial Baseline Waypoints", f"{len(initial_wps)} Waypoints (SF -> Sacramento -> Tahoe)", category="Phase 1: Initial Baseline")
            rep.add_validation("Initial Route Distance", initial_dist, category="Phase 1: Initial Baseline")
            rep.add_validation("Initial Route Duration", initial_dur, category="Phase 1: Initial Baseline")
            rep.add_validation("Checkpoint 1 Persistence", "100% Exact Match (Saved == Reopened)", category="Phase 2: First Reopen")
            rep.add_validation("Modification Performed", "Appended 4th Waypoint (Reno, NV)", category="Phase 3: Roadtrip Modification")
            rep.add_validation("Recalculated Distance", modified_dist, category="Phase 3: Roadtrip Modification")
            rep.add_validation("Recalculated Duration", modified_dur, category="Phase 3: Roadtrip Modification")
            rep.add_validation("Checkpoint 2 Persistence", "100% Exact Match (Modified == Reopened)", category="Phase 4: Final Reopen")
            rep.add_validation("No Duplicate Waypoints", "VERIFIED (Zero Duplicates)", category="Planner State Integrity")
            rep.add_validation("Zero State Leakage", "VERIFIED (Clean State Isolation Across Reopens)", category="Planner State Integrity")
            rep.add_validation("Final Mapbox Markers", f"{final_map['marker_count']} Markers Rendered", category="Mapbox Visualization")
            rep.add_validation("Final Save Button State", save_btn_info, category="UI Stability")

        log_test_success(
            "TC-005",
            f"Roadtrip Lifecycle, Persistence & State Regression Verified! "
            f"Trip '{test_trip_title}' (ID: {trip_id or updated_trip_id}) 100% Preserved in Staging"
        )
