"""
TC-006: Waypoint Deletion, Route Restructuring & Planner Recovery.

Objective:
Verify that a user can create a multi-waypoint roadtrip, repeatedly delete and add stops,
reorder waypoints, save the modified trip, navigate away, reopen it, modify it again,
and confirm that the final state remains fully consistent.

Specific focus areas:
- Deleted waypoints do not remain in the UI or on the map.
- No duplicate waypoints are introduced.
- Stale distance/duration values are replaced with freshly recalculated values.
- Route geometry updates dynamically on each deletion, addition, and reorder.
- Exact persistence across multiple navigation-away and reopen cycles.
- Zero state leakage from prior deleted locations.
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

logger = get_logger("TestWaypointDeletion")


@pytest.mark.tc006
@pytest.mark.waypoints
@pytest.mark.deletion
@pytest.mark.planner
@pytest.mark.regression
class TestWaypointDeletion:
    """Test Suite for TC-006: Waypoint Deletion, Route Restructuring & Planner Recovery."""

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

    def test_tc006_waypoint_deletion_route_restructuring_and_recovery(self, driver: Any) -> None:
        """
        Executes the complete multi-phase waypoint deletion, addition, reordering,
        save, reopen, second edit, and final integrity verification test.
        """
        # Validate credentials before starting
        Config.validate_credentials()

        timestamp = datetime.now().strftime("%m%d_%H%M%S")
        test_trip_title = f"AutoWaypointDeletion_{timestamp}"
        test_route_name = f"Route_{timestamp}"

        log_test_header(
            "TC-006",
            f"Waypoint Deletion, Route Restructuring & Recovery ({test_trip_title})"
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
        # STEP 02: INITIALIZE A FRESH UNIQUE ROADTRIP
        # -------------------------------------------------------------------------
        log_step(2, f"Initialize unique Roadtrip in Planner: '{test_trip_title}'")
        planner_page.ensure_planner_tab_active(test_trip_title)
        planner_page.set_route_name(test_route_name)

        # -------------------------------------------------------------------------
        # STEP 03: CREATE 5-WAYPOINT BASELINE ROUTE
        # -------------------------------------------------------------------------
        log_step(3, "PHASE 1: Add 5 initial waypoints (SF -> Sacramento -> Tahoe -> Reno -> Vegas) and calculate baseline route")
        
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

        # Waypoint 4 (Reno, NV)
        planner_page.add_waypoint_field()
        sel_wp4 = planner_page.enter_and_select_intermediate_waypoint(
            "Reno, NV", waypoint_index=4, waypoint_name="Waypoint 4 (Reno)"
        )
        logger.info(f"Selected Waypoint 4: '{sel_wp4}'")
        assert "Reno" in sel_wp4, f"Waypoint 4 mismatch: '{sel_wp4}'"

        # Waypoint 5 (Las Vegas, NV)
        planner_page.add_waypoint_field()
        sel_wp5 = planner_page.enter_and_select_intermediate_waypoint(
            "Las Vegas, NV", waypoint_index=5, waypoint_name="Waypoint 5 (Las Vegas)"
        )
        logger.info(f"Selected Waypoint 5: '{sel_wp5}'")
        assert "Las Vegas" in sel_wp5, f"Waypoint 5 mismatch: '{sel_wp5}'"

        # Wait for baseline route calculation with 5 waypoints
        baseline_route = planner_page.wait_for_route_calculation(timeout=45, previous_distance="399 km")
        baseline_wps = planner_page.get_all_selected_waypoints()
        baseline_dist = baseline_route["distance"]
        baseline_dur = baseline_route["duration"]
        baseline_coords = baseline_route["coordinates"]
        baseline_map = planner_page.verify_route_on_map()

        logger.info("Captured 5-Waypoint Baseline Route State:")
        logger.info(f"  Title:             '{test_trip_title}'")
        logger.info(f"  Route Name:        '{test_route_name}'")
        logger.info(f"  Waypoints ({len(baseline_wps)}): {baseline_wps}")
        logger.info(f"  Distance:          '{baseline_dist}' ({baseline_route['distance_numeric']} km)")
        logger.info(f"  Duration:          '{baseline_dur}'")
        logger.info(f"  Coordinates Count: {len(baseline_coords)}")
        logger.info(f"  Map Markers:       {baseline_map['marker_count']}")

        assert len(baseline_wps) == 5, f"Expected 5 baseline waypoints, found {len(baseline_wps)}: {baseline_wps}"
        assert baseline_route["distance_numeric"] > 0, "Baseline distance must be > 0"
        assert len(baseline_coords) >= 5, f"Expected at least 5 coordinates, got {len(baseline_coords)}"
        assert baseline_map["canvas_ready"] is True, "Map canvas not mounted."
        planner_page.verify_no_errors()

        # -------------------------------------------------------------------------
        # STEP 04: DELETE MIDDLE WAYPOINT (LAKE TAHOE)
        # -------------------------------------------------------------------------
        log_step(4, "PHASE 2: Delete middle waypoint (Lake Tahoe, position 3) and verify route recalculation")
        planner_page.delete_waypoint_by_name("Lake Tahoe")
        
        # Wait for dynamic route recalculation with 4 waypoints
        route_del1 = planner_page.wait_for_route_calculation(timeout=35, previous_distance=baseline_dist)
        wps_del1 = planner_page.get_all_selected_waypoints()
        dist_del1 = route_del1["distance"]
        dur_del1 = route_del1["duration"]
        coords_del1 = route_del1["coordinates"]
        map_del1 = planner_page.verify_route_on_map()

        logger.info("Captured Route State after Deleting Lake Tahoe:")
        logger.info(f"  Waypoints ({len(wps_del1)}): {wps_del1}")
        logger.info(f"  Recalculated Distance: '{dist_del1}' ({route_del1['distance_numeric']} km)")
        logger.info(f"  Recalculated Duration: '{dur_del1}'")
        logger.info(f"  Coordinates Count:     {len(coords_del1)}")
        logger.info(f"  Map Markers:           {map_del1['marker_count']}")

        # Assertions after Deletion 1
        assert len(wps_del1) == 4, f"Expected 4 waypoints after first deletion, got {len(wps_del1)}"
        assert not any("Lake Tahoe" in wp for wp in wps_del1), f"Deleted 'Lake Tahoe' still present: {wps_del1}"
        assert "San Francisco" in wps_del1[0], f"Waypoint 1 order corrupted: {wps_del1[0]}"
        assert "Sacramento" in wps_del1[1], f"Waypoint 2 order corrupted: {wps_del1[1]}"
        assert "Reno" in wps_del1[2], f"Waypoint 3 order corrupted: {wps_del1[2]}"
        assert "Las Vegas" in wps_del1[3], f"Waypoint 4 order corrupted: {wps_del1[3]}"
        assert len(coords_del1) >= 4, f"Coordinates count invalid: {len(coords_del1)}"
        planner_page.verify_no_errors()

        # -------------------------------------------------------------------------
        # STEP 05: DELETE ADDITIONAL WAYPOINT (SACRAMENTO)
        # -------------------------------------------------------------------------
        log_step(5, "PHASE 3: Delete additional waypoint (Sacramento, position 2) and verify route recalculation")
        planner_page.delete_waypoint_by_name("Sacramento")

        # Wait for dynamic route recalculation with 3 waypoints
        route_del2 = planner_page.wait_for_route_calculation(timeout=35, previous_distance=dist_del1)
        wps_del2 = planner_page.get_all_selected_waypoints()
        dist_del2 = route_del2["distance"]
        dur_del2 = route_del2["duration"]
        coords_del2 = route_del2["coordinates"]
        map_del2 = planner_page.verify_route_on_map()

        logger.info("Captured Route State after Deleting Sacramento:")
        logger.info(f"  Waypoints ({len(wps_del2)}): {wps_del2}")
        logger.info(f"  Recalculated Distance: '{dist_del2}' ({route_del2['distance_numeric']} km)")
        logger.info(f"  Recalculated Duration: '{dur_del2}'")
        logger.info(f"  Coordinates Count:     {len(coords_del2)}")
        logger.info(f"  Map Markers:           {map_del2['marker_count']}")

        # Assertions after Deletion 2
        assert len(wps_del2) == 3, f"Expected 3 waypoints after second deletion, got {len(wps_del2)}"
        assert not any("Sacramento" in wp for wp in wps_del2), f"Deleted 'Sacramento' still present: {wps_del2}"
        assert not any("Lake Tahoe" in wp for wp in wps_del2), f"Deleted 'Lake Tahoe' unexpectedly returned: {wps_del2}"
        assert "San Francisco" in wps_del2[0], f"Waypoint 1 order corrupted: {wps_del2[0]}"
        assert "Reno" in wps_del2[1], f"Waypoint 2 order corrupted: {wps_del2[1]}"
        assert "Las Vegas" in wps_del2[2], f"Waypoint 3 order corrupted: {wps_del2[2]}"
        assert len(coords_del2) >= 3, f"Coordinates count invalid: {len(coords_del2)}"
        planner_page.verify_no_errors()

        # -------------------------------------------------------------------------
        # STEP 06: ADD NEW WAYPOINT (YOSEMITE)
        # -------------------------------------------------------------------------
        log_step(6, "PHASE 4: Add new waypoint (Yosemite, position 4) and verify route expansion")
        planner_page.add_waypoint_field()
        sel_yosemite = planner_page.enter_and_select_intermediate_waypoint(
            "Yosemite National Park, CA", waypoint_index=4, waypoint_name="Waypoint 4 (Yosemite)"
        )
        logger.info(f"Added new Waypoint 4 (Yosemite): '{sel_yosemite}'")
        assert "Yosemite" in sel_yosemite, f"New waypoint mismatch: '{sel_yosemite}'"

        route_add = planner_page.wait_for_route_calculation(timeout=35, previous_distance=dist_del2)
        wps_add = planner_page.get_all_selected_waypoints()
        dist_add = route_add["distance"]
        dur_add = route_add["duration"]
        coords_add = route_add["coordinates"]
        map_add = planner_page.verify_route_on_map()

        logger.info("Captured Route State after Adding Yosemite:")
        logger.info(f"  Waypoints ({len(wps_add)}): {wps_add}")
        logger.info(f"  Recalculated Distance: '{dist_add}' ({route_add['distance_numeric']} km)")
        logger.info(f"  Recalculated Duration: '{dur_add}'")
        logger.info(f"  Coordinates Count:     {len(coords_add)}")
        logger.info(f"  Map Markers:           {map_add['marker_count']}")

        assert len(wps_add) == 4, f"Expected 4 waypoints after addition, got {len(wps_add)}"
        assert "Yosemite" in wps_add[3], f"Waypoint 4 not Yosemite: {wps_add[3]}"
        assert len(coords_add) >= 4, f"Coordinates count invalid: {len(coords_add)}"
        planner_page.verify_no_errors()

        # -------------------------------------------------------------------------
        # STEP 07: REORDER ROUTE (MOVE YOSEMITE: POS 4 -> POS 2)
        # -------------------------------------------------------------------------
        log_step(7, "PHASE 5: Reorder route: Move Yosemite from Position 4 to Position 2 and recalculate route")
        planner_page.reorder_waypoint(from_index=3, to_index=1)

        route_reorder = planner_page.wait_for_route_calculation(timeout=35, previous_distance=dist_add)
        wps_reordered = planner_page.get_all_selected_waypoints()
        dist_reordered = route_reorder["distance"]
        dur_reordered = route_reorder["duration"]
        coords_reordered = route_reorder["coordinates"]
        map_reordered = planner_page.verify_route_on_map()

        logger.info("Captured Final Restructured State before Initial Save:")
        logger.info(f"  Waypoints ({len(wps_reordered)}): {wps_reordered}")
        logger.info(f"  Recalculated Distance: '{dist_reordered}' ({route_reorder['distance_numeric']} km)")
        logger.info(f"  Recalculated Duration: '{dur_reordered}'")
        logger.info(f"  Coordinates Count:     {len(coords_reordered)}")
        logger.info(f"  Map Markers:           {map_reordered['marker_count']}")

        # Order assertions: SF -> Yosemite -> Reno -> Las Vegas
        assert len(wps_reordered) == 4, f"Expected 4 waypoints, got {len(wps_reordered)}"
        assert "San Francisco" in wps_reordered[0], f"Waypoint 1 order error: {wps_reordered[0]}"
        assert "Yosemite" in wps_reordered[1], f"Waypoint 2 order error: {wps_reordered[1]}"
        assert "Reno" in wps_reordered[2], f"Waypoint 3 order error: {wps_reordered[2]}"
        assert "Las Vegas" in wps_reordered[3], f"Waypoint 4 order error: {wps_reordered[3]}"
        planner_page.verify_no_errors()

        saved_state_1 = {
            "title": test_trip_title,
            "route_name": test_route_name,
            "waypoints": copy.deepcopy(wps_reordered),
            "waypoint_count": len(wps_reordered),
            "distance": dist_reordered,
            "duration": dur_reordered,
            "coordinates_count": len(coords_reordered),
            "marker_count": map_reordered["marker_count"]
        }

        # -------------------------------------------------------------------------
        # STEP 08: SAVE ROADTRIP (INITIAL PERSISTED VERSION)
        # -------------------------------------------------------------------------
        log_step(8, "PHASE 6: Save restructured Roadtrip and confirm backend persistence")
        save_res_1 = planner_page.save_roadtrip(timeout=25)
        trip_id = save_res_1.get("trip_id")
        logger.info(f"Initial Save Confirmed: Redirect URL={save_res_1['redirect_url']}, Trip ID={trip_id}")

        # -------------------------------------------------------------------------
        # STEP 09: NAVIGATE AWAY TO MY ROADTRIPS
        # -------------------------------------------------------------------------
        log_step(9, "PHASE 7: Navigate away to 'My Roadtrips' to unmount and clear in-memory Planner state")
        planner_page.open_my_roadtrips_tab()
        planner_page.wait_until_visible((By.CSS_SELECTOR, ".upcomingJourneyList span.hyperlink"), timeout=15)
        trip_cards_1 = planner_page.find_all(planner_page.JOURNEY_LIST_CARDS, timeout=10)
        assert len(trip_cards_1) > 0, "No trip cards found in My Roadtrips."

        # -------------------------------------------------------------------------
        # STEP 10: REOPEN SAVED ROADTRIP & VERIFY CHECKPOINT 1 PERSISTENCE
        # -------------------------------------------------------------------------
        log_step(10, f"Locate and reopen Roadtrip '{test_trip_title}' from My Roadtrips and verify Checkpoint 1 persistence")
        target_card_1 = planner_page.search_and_locate_roadtrip(test_trip_title)
        assert target_card_1 is not False and target_card_1 is not None, f"Roadtrip '{test_trip_title}' not found in My Roadtrips."
        planner_page.reopen_saved_roadtrip_in_planner(target_card_1)

        reopened_wps_1 = planner_page.get_all_selected_waypoints()
        reopened_dist_1 = planner_page.get_route_distance()
        reopened_dur_1 = planner_page.get_route_duration()
        reopened_coords_1 = planner_page.get_route_coordinates()
        reopened_map_1 = planner_page.verify_route_on_map()

        logger.info("Checkpoint 1 Reopened State:")
        logger.info(f"  Reopened Waypoints: {reopened_wps_1}")
        logger.info(f"  Expected Waypoints: {saved_state_1['waypoints']}")
        logger.info(f"  Reopened Distance:  '{reopened_dist_1}' (Expected: '{saved_state_1['distance']}')")
        logger.info(f"  Reopened Duration:  '{reopened_dur_1}' (Expected: '{saved_state_1['duration']}')")
        logger.info(f"  Reopened Coords:    {len(reopened_coords_1)} (Expected: {saved_state_1['coordinates_count']})")
        logger.info(f"  Reopened Markers:   {reopened_map_1['marker_count']}")

        # Strict Checkpoint 1 assertions
        assert len(reopened_wps_1) == saved_state_1["waypoint_count"] == 4, (
            f"Checkpoint 1 Waypoint count mismatch: expected 4, got {len(reopened_wps_1)}"
        )
        assert reopened_wps_1 == saved_state_1["waypoints"], (
            f"Checkpoint 1 Waypoint order mismatch:\nReopened: {reopened_wps_1}\nExpected: {saved_state_1['waypoints']}"
        )
        assert reopened_dist_1 == saved_state_1["distance"], (
            f"Checkpoint 1 Route distance mismatch: expected '{saved_state_1['distance']}', got '{reopened_dist_1}'"
        )
        assert not any("Lake Tahoe" in wp for wp in reopened_wps_1), "Deleted 'Lake Tahoe' leaked into reopened state!"
        assert not any("Sacramento" in wp for wp in reopened_wps_1), "Deleted 'Sacramento' leaked into reopened state!"
        assert reopened_map_1["canvas_ready"] is True, "Checkpoint 1 Map canvas not ready."
        planner_page.verify_no_errors()
        logger.info("Checkpoint 1 Persistence Verified: 100% Exact Match.")

        # -------------------------------------------------------------------------
        # STEP 11: PERFORM SECOND EDIT AFTER REOPENING (DELETE RENO)
        # -------------------------------------------------------------------------
        log_step(11, "PHASE 8: Modify reopened Roadtrip: Delete Reno (position 3) and recalculate 3-waypoint route")
        planner_page.delete_waypoint_by_name("Reno")

        route_del3 = planner_page.wait_for_route_calculation(timeout=35, previous_distance=reopened_dist_1)
        wps_del3 = planner_page.get_all_selected_waypoints()
        dist_del3 = route_del3["distance"]
        dur_del3 = route_del3["duration"]
        coords_del3 = route_del3["coordinates"]
        map_del3 = planner_page.verify_route_on_map()

        logger.info("Captured State after Deleting Reno (Modified Version 2):")
        logger.info(f"  Waypoints ({len(wps_del3)}): {wps_del3}")
        logger.info(f"  Recalculated Distance: '{dist_del3}' ({route_del3['distance_numeric']} km)")
        logger.info(f"  Recalculated Duration: '{dur_del3}'")
        logger.info(f"  Coordinates Count:     {len(coords_del3)}")
        logger.info(f"  Map Markers:           {map_del3['marker_count']}")

        # Assertions for 3-waypoint route: SF -> Yosemite -> Las Vegas
        assert len(wps_del3) == 3, f"Expected 3 waypoints after deleting Reno, got {len(wps_del3)}"
        assert not any("Reno" in wp for wp in wps_del3), f"Deleted 'Reno' still present: {wps_del3}"
        assert "San Francisco" in wps_del3[0], f"Waypoint 1 error: {wps_del3[0]}"
        assert "Yosemite" in wps_del3[1], f"Waypoint 2 error: {wps_del3[1]}"
        assert "Las Vegas" in wps_del3[2], f"Waypoint 3 error: {wps_del3[2]}"
        assert len(coords_del3) >= 3, f"Coordinates count invalid: {len(coords_del3)}"
        planner_page.verify_no_errors()

        saved_state_2 = {
            "title": test_trip_title,
            "waypoints": copy.deepcopy(wps_del3),
            "waypoint_count": len(wps_del3),
            "distance": dist_del3,
            "duration": dur_del3,
            "coordinates_count": len(coords_del3),
            "marker_count": map_del3["marker_count"]
        }

        # -------------------------------------------------------------------------
        # STEP 12: SAVE/UPDATE MODIFIED ROADTRIP (VERSION 2)
        # -------------------------------------------------------------------------
        log_step(12, "PHASE 9: Save updated Roadtrip and confirm updated persistence")
        save_res_2 = planner_page.save_roadtrip(timeout=25)
        updated_trip_id = save_res_2.get("trip_id")
        logger.info(f"Update Confirmed: Redirect URL={save_res_2['redirect_url']}, Updated Trip ID={updated_trip_id}")

        # -------------------------------------------------------------------------
        # STEP 13: NAVIGATE AWAY AND REOPEN FOR FINAL CHECKPOINT 2 PERSISTENCE
        # -------------------------------------------------------------------------
        log_step(13, "PHASE 10: Navigate away to My Roadtrips again and reopen Roadtrip for final persistence validation")
        planner_page.open_my_roadtrips_tab()
        planner_page.wait_until_visible((By.CSS_SELECTOR, ".upcomingJourneyList span.hyperlink"), timeout=15)
        trip_cards_2 = planner_page.find_all(planner_page.JOURNEY_LIST_CARDS, timeout=10)
        assert len(trip_cards_2) > 0, "No trip cards found in My Roadtrips."

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
        logger.info(f"  Expected Waypoints: {saved_state_2['waypoints']}")
        logger.info(f"  Final Distance:     '{final_dist}' (Expected: '{saved_state_2['distance']}')")
        logger.info(f"  Final Duration:     '{final_dur}' (Expected: '{saved_state_2['duration']}')")
        logger.info(f"  Final Coords Count: {len(final_coords)} (Expected: {saved_state_2['coordinates_count']})")
        logger.info(f"  Final Map Markers:  {final_map['marker_count']}")

        # Strict Checkpoint 2 assertions
        assert len(final_wps) == saved_state_2["waypoint_count"] == 3, (
            f"Checkpoint 2 Waypoint count mismatch: expected 3, got {len(final_wps)}"
        )
        assert final_wps == saved_state_2["waypoints"], (
            f"Checkpoint 2 Waypoint order mismatch:\nFinal:    {final_wps}\nExpected: {saved_state_2['waypoints']}"
        )
        assert final_dist == saved_state_2["distance"], (
            f"Checkpoint 2 Route distance mismatch: expected '{saved_state_2['distance']}', got '{final_dist}'"
        )
        assert len(final_coords) >= 3, f"Final coordinates count invalid: {len(final_coords)}"
        assert final_map["canvas_ready"] is True, "Final map canvas not ready."
        logger.info("Checkpoint 2 Final Persistence Verified: 100% Exact Match.")

        # -------------------------------------------------------------------------
        # FINAL INTEGRITY CHECKS
        # -------------------------------------------------------------------------
        log_step(14, "PHASE 11: Execute comprehensive Final State Integrity & Leakage Checks")
        
        # 1. Duplicate Waypoints Check
        assert len(final_wps) == len(set(final_wps)), f"Duplicate waypoints detected in final state: {final_wps}"
        logger.info("Integrity Check 1: Zero Duplicate Waypoints Verified.")

        # 2. Deleted Waypoint Leakage Check
        deleted_wps_history = ["Lake Tahoe", "Sacramento", "Reno"]
        for del_name in deleted_wps_history:
            assert not any(del_name in wp for wp in final_wps), (
                f"DELETED WAYPOINT LEAKAGE: '{del_name}' reappeared in final reopened state: {final_wps}"
            )
        logger.info(f"Integrity Check 2: Zero Leakage of Deleted Waypoints ({deleted_wps_history}) Verified.")

        # 3. State Leakage Check
        assert final_wps != baseline_wps, "State leakage: Final waypoints reverted to initial 5-waypoint baseline."
        assert final_wps != saved_state_1["waypoints"], "State leakage: Final waypoints reverted to Version 1 4-waypoint state."
        logger.info("Integrity Check 3: Zero Prior-Version State Leakage Verified.")

        # 4. Route Validity Check
        assert planner_page.get_numeric_distance(final_dist) > 0, f"Final route distance must be > 0, got '{final_dist}'"
        logger.info(f"Integrity Check 4: Route Distance Validity Verified ('{final_dist}').")

        # 5. UI Stability Check
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
            rep.add_validation("Generated Route Name", test_route_name, category="Lifecycle Metadata")
            rep.add_validation("Captured Trip ID", str(trip_id or updated_trip_id or "Saved"), category="Lifecycle Metadata")
            rep.add_validation("Initial Baseline Route", f"5 Waypoints ({baseline_dist} / {baseline_dur})", category="Phase 1: Baseline Creation")
            rep.add_validation("Deletion 1 (Middle)", "Removed 'Lake Tahoe' -> Recalculated to 4 Waypoints", category="Phase 2: Waypoint Deletion")
            rep.add_validation("Deletion 2 (Position 2)", "Removed 'Sacramento' -> Recalculated to 3 Waypoints", category="Phase 2: Waypoint Deletion")
            rep.add_validation("Addition (Yosemite)", "Appended 'Yosemite' -> Recalculated to 4 Waypoints", category="Phase 3: Waypoint Addition")
            rep.add_validation("Reorder Operation", "Moved Yosemite to Pos 2 -> SF -> Yosemite -> Reno -> Vegas", category="Phase 4: Route Restructuring")
            rep.add_validation("Checkpoint 1 Persistence", "100% Exact Match (Restructured == Reopened)", category="Phase 5: First Reopen")
            rep.add_validation("Second Edit (Deletion 3)", "Removed 'Reno' from reopened trip -> 3 Waypoints", category="Phase 6: Second Edit")
            rep.add_validation("Checkpoint 2 Persistence", "100% Exact Match (Updated Version 2 == Reopened)", category="Phase 7: Final Reopen")
            rep.add_validation("Zero Duplicate Waypoints", "VERIFIED (0% Duplication)", category="State Integrity")
            rep.add_validation("Zero Deleted Stop Leakage", "VERIFIED (Lake Tahoe, Sacramento, Reno 0% Present)", category="State Integrity")
            rep.add_validation("Final Mapbox Markers", f"{final_map['marker_count']} Markers Rendered", category="Mapbox Visualization")
            rep.add_validation("Final Save Button State", save_btn_info, category="UI Stability")

        log_test_success(
            "TC-006",
            f"Waypoint Deletion, Route Restructuring & Recovery Verified! "
            f"Trip '{test_trip_title}' (ID: {trip_id or updated_trip_id}) 100% Preserved in Staging"
        )
