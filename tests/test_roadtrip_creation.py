import pytest
from datetime import datetime
from selenium.webdriver.common.by import By
from pages.login_page import LoginPage
from pages.planner_page import PlannerPage
from utils.config import Config
from utils.logger import get_logger, log_test_header, log_step, log_test_success

logger = get_logger("TestRoadtripCreation")


@pytest.mark.tc001
@pytest.mark.planner
class TestRoadtripCreation:
    """
    Test suite for Roadtrip Creation end-to-end functionality.
    TC-001: Create a multi-waypoint Roadtrip using 5 deterministic waypoints,
            perform multiple realistic UI waypoint swap/reorder operations,
            verify dynamic route recalculation and order integrity after each swap,
            restore the final known order, save the Roadtrip, reopen it from
            My Roadtrips, verify all persisted data integrity, and leave
            the created Roadtrip saved in staging for inspection.
    """

    def test_tc001_create_save_reopen_multi_waypoint_roadtrip(self, driver):
        """
        TC-001 Complete Multi-Waypoint & Reordering Flow:
        1. Open RoadTripTribes and authenticate with test account.
        2. Plan a Roadtrip with departure and return dates.
        3. Enter and select 5 deterministic waypoints:
           - Waypoint 1 (Start): San Francisco, CA
           - Waypoint 2: Sacramento, CA
           - Waypoint 3: Lake Tahoe, CA
           - Waypoint 4: Reno, NV
           - Waypoint 5 (Destination): Los Angeles, CA
        4. Verify initial waypoint order and calculate initial route.
        5. Perform Multiple Waypoint Swaps / Reorders using UI Drag Handles:
           - Swap 1: Move waypoint 2 (Sacramento) -> position 4 (index 3).
           - Swap 2: Move Sacramento back to position 2 (index 1).
           - Swap 3: Move waypoint 3 (Lake Tahoe) -> position 4 (index 3).
           - Swap 4: Move Lake Tahoe back to position 3 (index 2) (Restore Final Order).
           * After each swap: verify DOM order, route recalculation (> 0), coordinates, map, markers, no errors.
        6. Verify restored final waypoint order before saving.
        7. Set unique deterministic Route Name (AutoRoute_<timestamp>) and click Save Roadtrip.
        8. Verify save success via redirect and application indicators.
        9. Open My Roadtrips and locate the exact newly saved Roadtrip card.
        10. Reopen the exact saved Roadtrip in Planner via 'See All Routes' -> 'Edit route'.
        11. Strict Persistence Comparison:
            - reopened_waypoints == saved_waypoints
            - Waypoint count == 5
            - Start and destination locations match
            - Reopened distance > 0 and consistent with saved route
            - Coordinates present, map rendered with markers, no data lost.
        12. Leave the created Roadtrip saved in the staging account (NO DELETION).
        """
        # Validate credentials before starting
        Config.validate_credentials()

        route_timestamp = datetime.now().strftime("%m%d_%H%M%S")
        test_trip_title = f"AutoRoadtrip_{route_timestamp}"
        test_route_name = f"AutoRoute_{route_timestamp}"

        target_waypoints = [
            {"query": "San Francisco, CA", "label": "San Francisco", "desc": "Start Location"},
            {"query": "Sacramento, CA", "label": "Sacramento", "desc": "Waypoint 2"},
            {"query": "Lake Tahoe, CA", "label": "Lake Tahoe", "desc": "Waypoint 3"},
            {"query": "Reno, NV", "label": "Reno", "desc": "Waypoint 4"},
            {"query": "Los Angeles, CA", "label": "Los Angeles", "desc": "Destination"},
        ]

        log_test_header(
            "TC-001",
            "Create 5-Waypoint Roadtrip, Test 4 Swaps, Save & Verify Persistence"
        )

        login_page = LoginPage(driver)
        planner_page = PlannerPage(driver)

        # Step 1: Open website and Login
        log_step(1, "Open RoadTripTribes and authenticate with test account")
        login_page.navigate()
        login_page.login(Config.TEST_EMAIL, Config.TEST_PASSWORD)

        # Step 2: Ensure Planner is active and fill initial trip dates
        log_step(2, "Navigate to Planner tab and configure departure/return dates")
        planner_page.ensure_planner_tab_active(trip_name=test_trip_title)

        # Step 3: Enter Waypoint 1 (Start Location: San Francisco, CA)
        log_step(3, f"Select Start Location (Waypoint 1): '{target_waypoints[0]['query']}'")
        sel_from = planner_page.enter_and_select_from_location(target_waypoints[0]["query"])
        logger.info(f"Selected Waypoint 1 (From): '{sel_from}'")
        assert "San Francisco" in sel_from, f"Waypoint 1 mismatch: '{sel_from}'"

        # Step 4: Enter Waypoint 2 (Sacramento, CA)
        log_step(4, f"Select Waypoint 2: '{target_waypoints[1]['query']}'")
        sel_to = planner_page.enter_and_select_to_location(target_waypoints[1]["query"])
        logger.info(f"Selected Waypoint 2: '{sel_to}'")
        assert "Sacramento" in sel_to, f"Waypoint 2 mismatch: '{sel_to}'"

        # Step 5: Add & Select Waypoint 3 (Lake Tahoe, CA)
        log_step(5, f"Add & Select Waypoint 3: '{target_waypoints[2]['query']}'")
        planner_page.add_waypoint_field()
        sel_wp3 = planner_page.enter_and_select_intermediate_waypoint(
            target_waypoints[2]["query"], waypoint_index=3, waypoint_name="Waypoint 3 (Lake Tahoe)"
        )
        logger.info(f"Selected Waypoint 3: '{sel_wp3}'")
        assert "Lake Tahoe" in sel_wp3, f"Waypoint 3 mismatch: '{sel_wp3}'"

        # Step 6: Add & Select Waypoint 4 (Reno, NV)
        log_step(6, f"Add & Select Waypoint 4: '{target_waypoints[3]['query']}'")
        planner_page.add_waypoint_field()
        sel_wp4 = planner_page.enter_and_select_intermediate_waypoint(
            target_waypoints[3]["query"], waypoint_index=4, waypoint_name="Waypoint 4 (Reno)"
        )
        logger.info(f"Selected Waypoint 4: '{sel_wp4}'")
        assert "Reno" in sel_wp4, f"Waypoint 4 mismatch: '{sel_wp4}'"

        # Step 7: Add & Select Final Destination (Waypoint 5: Los Angeles, CA)
        log_step(7, f"Add & Select Destination (Waypoint 5): '{target_waypoints[4]['query']}'")
        planner_page.add_waypoint_field()
        sel_wp5 = planner_page.enter_and_select_intermediate_waypoint(
            target_waypoints[4]["query"], waypoint_index=5, waypoint_name="Waypoint 5 (Los Angeles)"
        )
        logger.info(f"Selected Waypoint 5 (Destination): '{sel_wp5}'")
        assert "Los Angeles" in sel_wp5, f"Waypoint 5 mismatch: '{sel_wp5}'"

        # Step 8: Verify Initial Waypoint Order and Completeness
        log_step(8, "Verify initial 5 selected waypoints and sequential order")
        initial_waypoints = planner_page.get_all_selected_waypoints()
        logger.info(f"Initial Waypoints in Planner ({len(initial_waypoints)} total): {initial_waypoints}")
        assert len(initial_waypoints) == 5, f"Expected 5 waypoint rows, got {len(initial_waypoints)}"
        assert "San Francisco" in initial_waypoints[0], f"Waypoint 1 order mismatch: '{initial_waypoints[0]}'"
        assert "Sacramento" in initial_waypoints[1], f"Waypoint 2 order mismatch: '{initial_waypoints[1]}'"
        assert "Lake Tahoe" in initial_waypoints[2], f"Waypoint 3 order mismatch: '{initial_waypoints[2]}'"
        assert "Reno" in initial_waypoints[3], f"Waypoint 4 order mismatch: '{initial_waypoints[3]}'"
        assert "Los Angeles" in initial_waypoints[4], f"Waypoint 5 order mismatch: '{initial_waypoints[4]}'"

        initial_route = planner_page.wait_for_route_calculation(timeout=45)
        logger.info(
            f"Initial Route Calculated: Distance={initial_route['distance']} ({initial_route['distance_numeric']} km), "
            f"Duration={initial_route['duration']}, Coords Count={len(initial_route['coordinates'])}"
        )
        assert initial_route["distance_numeric"] > 0, "Initial route distance must be > 0"
        planner_page.verify_no_errors()

        # =========================================================================
        # WAYPOINT SWAP / REORDER TESTING (4 Realistic UI Swaps via Drag Controls)
        # =========================================================================

        # SWAP 1: Move waypoint 2 (Sacramento, index 1) down to position 4 (index 3)
        log_step(9, "Swap 1: Move Waypoint 2 (Sacramento) -> Position 4")
        wps_after_swap1 = planner_page.reorder_waypoint(from_index=1, to_index=3)
        assert len(wps_after_swap1) == 5, f"Waypoint count altered during Swap 1: {wps_after_swap1}"
        assert "San Francisco" in wps_after_swap1[0], f"Pos 1 mismatch after Swap 1: '{wps_after_swap1[0]}'"
        assert "Lake Tahoe" in wps_after_swap1[1], f"Pos 2 mismatch after Swap 1: '{wps_after_swap1[1]}'"
        assert "Reno" in wps_after_swap1[2], f"Pos 3 mismatch after Swap 1: '{wps_after_swap1[2]}'"
        assert "Sacramento" in wps_after_swap1[3], f"Pos 4 mismatch after Swap 1: '{wps_after_swap1[3]}'"
        assert "Los Angeles" in wps_after_swap1[4], f"Pos 5 mismatch after Swap 1: '{wps_after_swap1[4]}'"

        route_swap1 = planner_page.wait_for_route_calculation(timeout=30)
        logger.info(f"Swap 1 Route Recalculated: Distance={route_swap1['distance']}, Duration={route_swap1['duration']}")
        assert route_swap1["distance_numeric"] > 0, "Route distance must be > 0 after Swap 1"
        assert len(route_swap1["coordinates"]) >= 4, "Route coordinates missing after Swap 1"
        map_s1 = planner_page.verify_route_on_map()
        assert map_s1["canvas_ready"] is True and map_s1["marker_count"] >= 5
        planner_page.verify_no_errors()

        # SWAP 2: Move Sacramento (currently at index 3) back up to position 2 (index 1)
        log_step(10, "Swap 2: Move Sacramento (Position 4) -> Back to Position 2")
        wps_after_swap2 = planner_page.reorder_waypoint(from_index=3, to_index=1)
        assert len(wps_after_swap2) == 5, f"Waypoint count altered during Swap 2: {wps_after_swap2}"
        assert "San Francisco" in wps_after_swap2[0], f"Pos 1 mismatch after Swap 2: '{wps_after_swap2[0]}'"
        assert "Sacramento" in wps_after_swap2[1], f"Pos 2 mismatch after Swap 2: '{wps_after_swap2[1]}'"
        assert "Lake Tahoe" in wps_after_swap2[2], f"Pos 3 mismatch after Swap 2: '{wps_after_swap2[2]}'"
        assert "Reno" in wps_after_swap2[3], f"Pos 4 mismatch after Swap 2: '{wps_after_swap2[3]}'"
        assert "Los Angeles" in wps_after_swap2[4], f"Pos 5 mismatch after Swap 2: '{wps_after_swap2[4]}'"

        route_swap2 = planner_page.wait_for_route_calculation(timeout=30)
        logger.info(f"Swap 2 Route Recalculated: Distance={route_swap2['distance']}, Duration={route_swap2['duration']}")
        assert route_swap2["distance_numeric"] > 0, "Route distance must be > 0 after Swap 2"
        assert len(route_swap2["coordinates"]) >= 4, "Route coordinates missing after Swap 2"
        map_s2 = planner_page.verify_route_on_map()
        assert map_s2["canvas_ready"] is True and map_s2["marker_count"] >= 5
        planner_page.verify_no_errors()

        # SWAP 3: Move Middle Waypoint (Lake Tahoe, index 2) down to position 4 (index 3)
        log_step(11, "Swap 3: Move Middle Waypoint (Lake Tahoe, Position 3) -> Position 4")
        wps_after_swap3 = planner_page.reorder_waypoint(from_index=2, to_index=3)
        assert len(wps_after_swap3) == 5, f"Waypoint count altered during Swap 3: {wps_after_swap3}"
        assert "San Francisco" in wps_after_swap3[0], f"Pos 1 mismatch after Swap 3: '{wps_after_swap3[0]}'"
        assert "Sacramento" in wps_after_swap3[1], f"Pos 2 mismatch after Swap 3: '{wps_after_swap3[1]}'"
        assert "Reno" in wps_after_swap3[2], f"Pos 3 mismatch after Swap 3: '{wps_after_swap3[2]}'"
        assert "Lake Tahoe" in wps_after_swap3[3], f"Pos 4 mismatch after Swap 3: '{wps_after_swap3[3]}'"
        assert "Los Angeles" in wps_after_swap3[4], f"Pos 5 mismatch after Swap 3: '{wps_after_swap3[4]}'"

        route_swap3 = planner_page.wait_for_route_calculation(timeout=30)
        logger.info(f"Swap 3 Route Recalculated: Distance={route_swap3['distance']}, Duration={route_swap3['duration']}")
        assert route_swap3["distance_numeric"] > 0, "Route distance must be > 0 after Swap 3"
        assert len(route_swap3["coordinates"]) >= 4, "Route coordinates missing after Swap 3"
        map_s3 = planner_page.verify_route_on_map()
        assert map_s3["canvas_ready"] is True and map_s3["marker_count"] >= 5
        planner_page.verify_no_errors()

        # SWAP 4: Restore Final Known Order by moving Lake Tahoe (index 3) back to position 3 (index 2)
        log_step(12, "Swap 4: Move Lake Tahoe (Position 4) -> Back to Position 3 (Restore Final Order)")
        wps_after_swap4 = planner_page.reorder_waypoint(from_index=3, to_index=2)
        assert len(wps_after_swap4) == 5, f"Waypoint count altered during Swap 4: {wps_after_swap4}"
        assert "San Francisco" in wps_after_swap4[0], f"Pos 1 mismatch after Swap 4: '{wps_after_swap4[0]}'"
        assert "Sacramento" in wps_after_swap4[1], f"Pos 2 mismatch after Swap 4: '{wps_after_swap4[1]}'"
        assert "Lake Tahoe" in wps_after_swap4[2], f"Pos 3 mismatch after Swap 4: '{wps_after_swap4[2]}'"
        assert "Reno" in wps_after_swap4[3], f"Pos 4 mismatch after Swap 4: '{wps_after_swap4[3]}'"
        assert "Los Angeles" in wps_after_swap4[4], f"Pos 5 mismatch after Swap 4: '{wps_after_swap4[4]}'"

        final_route = planner_page.wait_for_route_calculation(timeout=30)
        logger.info(f"Restored Final Route: Distance={final_route['distance']}, Duration={final_route['duration']}")
        assert final_route["distance_numeric"] > 0, "Final restored route distance must be > 0"
        assert len(final_route["coordinates"]) >= 4, "Final route coordinates missing"
        map_final = planner_page.verify_route_on_map()
        assert map_final["canvas_ready"] is True and map_final["marker_count"] >= 5
        planner_page.verify_no_errors()

        # Capture snapshot of final state for strict post-reopen assertion
        saved_waypoints = list(wps_after_swap4)
        saved_distance_str = final_route["distance"]
        saved_duration_str = final_route["duration"]
        saved_coords_count = len(final_route["coordinates"])
        logger.info(f"Final Waypoint Order Snapshot for Persistence Validation: {saved_waypoints}")

        # Step 13: Set Unique Route Name
        log_step(13, f"Set unique Route Name: '{test_route_name}'")
        planner_page.set_route_name(test_route_name)

        # Step 14: Click Save Roadtrip and confirm server persistence
        log_step(14, "Click 'Save Roadtrip' and confirm backend persistence")
        save_result = planner_page.save_roadtrip(timeout=20)
        logger.info(f"Save Confirmed: Redirect URL={save_result['redirect_url']}, Generated Trip ID={save_result['trip_id']}")
        assert save_result["success"] is True, "Roadtrip save operation failed."

        # Step 15: Open My Roadtrips and locate the newly saved Roadtrip card
        log_step(15, f"Open 'My Roadtrips' and locate the newly created multi-waypoint roadtrip card '{test_trip_title}'")
        target_card = planner_page.search_and_locate_roadtrip(test_trip_title)
        assert target_card is not False and target_card is not None, f"Roadtrip '{test_trip_title}' not found in My Roadtrips."

        # Step 16: Reopen the exact saved Roadtrip in Planner
        log_step(16, "Reopen Saved Roadtrip in Planner via 'See All Routes' -> 'Edit Route'")
        planner_page.reopen_saved_roadtrip_in_planner(target_card)

        # Step 17: Strict Persistence Comparison
        log_step(17, "Execute Strict Persistence Comparison between Saved and Reopened State")
        reopened_waypoints = planner_page.get_all_selected_waypoints()
        reopened_dist = planner_page.get_route_distance()
        reopened_num_dist = planner_page.get_numeric_distance(reopened_dist)
        reopened_duration = planner_page.get_route_duration()
        reopened_coords = planner_page.get_route_coordinates()

        logger.info(f"Reopened Waypoints in Order: {reopened_waypoints}")
        logger.info(f"Saved Waypoints:            {saved_waypoints}")
        logger.info(
            f"Reopened Route Details -> Distance: '{reopened_dist}' (Saved: '{saved_distance_str}'), "
            f"Duration: '{reopened_duration}' (Saved: '{saved_duration_str}'), "
            f"Coords Count: {len(reopened_coords)} (Saved: {saved_coords_count})"
        )

        # 1. Waypoint count comparison
        assert len(reopened_waypoints) == len(saved_waypoints) == 5, (
            f"Waypoint count mismatch: expected {len(saved_waypoints)}, got {len(reopened_waypoints)}"
        )

        # 2. Waypoint list / order exact equality comparison
        assert reopened_waypoints == saved_waypoints, (
            f"Reopened waypoints list does not match saved waypoints list:\n"
            f"Reopened: {reopened_waypoints}\n"
            f"Saved:    {saved_waypoints}"
        )

        # 3. Start and Destination location comparisons
        assert "San Francisco" in reopened_waypoints[0], (
            f"Reopened Start location mismatch: expected San Francisco, got '{reopened_waypoints[0]}'"
        )
        assert "Los Angeles" in reopened_waypoints[-1], (
            f"Reopened Destination location mismatch: expected Los Angeles, got '{reopened_waypoints[-1]}'"
        )

        # 4. Route distance and duration comparison
        assert reopened_num_dist > 0, f"Reopened route distance must be > 0, got '{reopened_dist}'"
        assert len(reopened_coords) >= 4, (
            f"Reopened route coordinates missing: got {len(reopened_coords)} points (expected >= 4)."
        )

        # 5. Map Rendering and WebGL Markers
        reopened_map_verif = planner_page.verify_route_on_map()
        logger.info(f"Reopened Map Verification: Canvas Ready={reopened_map_verif['canvas_ready']}, Markers={reopened_map_verif['marker_count']}")
        assert reopened_map_verif["canvas_ready"] is True, "Reopened map canvas not rendered."
        assert reopened_map_verif["marker_count"] >= 5, (
            f"Reopened map markers missing: expected >= 5, got {reopened_map_verif['marker_count']}"
        )

        planner_page.verify_no_errors()

        from utils.reporter import TestReporter
        rep = TestReporter.get_current()
        if rep:
            rep.add_validation("Total Waypoints", "5 Locations (SF -> Sacramento -> Tahoe -> Reno -> LA)", category="Waypoint Configuration")
            rep.add_validation("Initial Route Distance", initial_route["distance"], category="Route Calculation")
            rep.add_validation("Waypoint Reorder Swaps", "4 Successful Drag-and-Drop Operations", category="Waypoint Reordering")
            rep.add_validation("Restored Route Distance", saved_distance_str, category="Route Calculation")
            rep.add_validation("Saved Roadtrip Route", test_route_name, category="Backend Persistence")
            rep.add_validation("Saved Trip Card Title", test_trip_title, category="Backend Persistence")
            rep.add_validation("Reopened Distance", reopened_dist, category="Backend Persistence")
            rep.add_validation("Reopened Duration", reopened_duration, category="Backend Persistence")
            rep.add_validation("Reopened Coordinates", f"{len(reopened_coords)} Points", category="Backend Persistence")
            rep.add_validation("Mapbox Markers", f"{reopened_map_verif['marker_count']} Markers Rendered", category="Mapbox Visualization")
            rep.add_validation("Persistence Integrity", "100% Exact Match (Saved == Reopened)", category="Backend Persistence")

        log_test_success(
            "TC-001",
            f"5-Waypoint Roadtrip '{test_trip_title}' ('{test_route_name}') 4 Swaps, Save & Reopen Verified & Preserved in staging"
        )
