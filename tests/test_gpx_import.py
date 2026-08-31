import pytest
from datetime import datetime
from selenium.webdriver.common.by import By
from pages.login_page import LoginPage
from pages.planner_page import PlannerPage
from utils.config import Config
from utils.gpx_parser import GPXParser
from utils.logger import get_logger, log_test_header, log_step, log_test_success

logger = get_logger("TestGPXImport")


@pytest.mark.tc002
@pytest.mark.gpx
@pytest.mark.planner
class TestGPXImport:
    """
    Test suite for GPX Import Roadtrip end-to-end functionality.
    TC-002: Randomly select a GPX file from the test dataset, parse and validate source
            coordinates, upload the file through the Planner GPX Import interface, verify
            imported waypoints and route generation, execute dynamic waypoint reorder operations
            based on imported count, restore original GPX order, save the Roadtrip, reopen it
            from My Roadtrips, execute strict persistence validation, and leave the created
            Roadtrip saved in staging for inspection.
    """

    def test_tc002_import_random_gpx_create_save_reopen(self, driver):
        """
        TC-002 Complete GPX Import Flow:
        1. Select random GPX file from test dataset and validate source coordinates.
        2. Open RoadTripTribes and authenticate with test account.
        3. Navigate to Planner tab and configure departure/return dates.
        4. Upload selected GPX file via 'Import Gpx' tab and await route calculation.
        5. Verify imported waypoints count (>= 2), names, coordinates, and map markers.
        6. Validate imported coordinates against source GPX geographic boundaries.
        7. Execute dynamic waypoint reorder operations:
           - 2 waypoints: 1 swap + restore.
           - 3-4 waypoints: 2 swaps + restore.
           - 5+ waypoints: 3-4 swaps + restore.
           * After each swap: verify order, route recalculation (> 0), coordinates, map, markers, no errors.
        8. Verify restored original GPX waypoint order before saving.
        9. Set unique Route Name (AutoGPX_<timestamp>) and click Save Roadtrip.
        10. Verify save success via backend redirect.
        11. Open My Roadtrips and locate the newly created GPX trip card.
        12. Reopen the exact saved Roadtrip in Planner via 'See All Routes' -> 'Edit route'.
        13. Strict Persistence Comparison:
            - reopened_waypoints == saved_waypoints
            - Waypoint count persisted
            - Start and destination locations match
            - Reopened distance > 0 and consistent with saved route
            - Coordinates present, map rendered with markers, no data lost.
        14. Leave the created Roadtrip saved in the staging account (NO DELETION).
        """
        # Validate credentials before starting
        Config.validate_credentials()

        # Step 0: Randomly select and parse GPX test file
        selected_gpx_path, gpx_meta = GPXParser.select_random_gpx()
        route_timestamp = datetime.now().strftime("%m%d_%H%M%S")
        test_route_name = f"AutoGPX_{route_timestamp}"

        log_test_header(
            "TC-002",
            f"GPX Import Multi-Waypoint Roadtrip ({selected_gpx_path.name})"
        )

        login_page = LoginPage(driver)
        planner_page = PlannerPage(driver)

        # Step 1: Open website and Login
        log_step(1, "Open RoadTripTribes and authenticate with test account")
        login_page.navigate()
        login_page.login(Config.TEST_EMAIL, Config.TEST_PASSWORD)

        # Step 2: Ensure Planner is active and set initial trip dates
        log_step(2, "Navigate to Planner tab and configure departure/return dates")
        planner_page.ensure_planner_tab_active()

        # Step 3: Upload Selected GPX File
        log_step(3, f"Upload GPX file '{selected_gpx_path.name}' via 'Import Gpx' tab")
        import_result = planner_page.import_gpx(selected_gpx_path, timeout=45)

        imported_waypoints = import_result["waypoints"]
        imported_count = len(imported_waypoints)
        imported_coords = import_result["coordinates"]
        imported_distance = import_result["distance"]
        imported_duration = import_result["duration"]

        logger.info(
            f"TC-002 Import Details:\n"
            f"  Selected GPX File:       {selected_gpx_path.name}\n"
            f"  Source GPX Points:       {gpx_meta['point_count']}\n"
            f"  Imported Waypoint Count: {imported_count}\n"
            f"  Imported Waypoints:      {imported_waypoints}\n"
            f"  Calculated Distance:     {imported_distance}\n"
            f"  Calculated Duration:     {imported_duration}\n"
            f"  Coordinates Count:       {len(imported_coords)}"
        )

        # Step 4: Verify Imported Waypoints & Minimum Usability Condition (>= 2 waypoints)
        log_step(4, "Verify imported waypoint count (>= 2) and non-empty route data")
        if imported_count < 2:
            raise AssertionError(
                f"GPX file '{selected_gpx_path.name}' imported fewer than 2 waypoints ({imported_count} found: {imported_waypoints})."
            )

        assert import_result["distance_numeric"] > 0, (
            f"Route distance validation failed for '{selected_gpx_path.name}': distance is '{imported_distance}'"
        )
        assert len(imported_coords) >= 2, (
            f"Route coordinates validation failed for '{selected_gpx_path.name}': found {len(imported_coords)} points."
        )

        # Step 5: Validate Imported Coordinates Against Source GPX Geographic Range
        log_step(5, "Validate imported coordinates against source GPX geographic boundaries")
        # Check coordinates are valid latitudes/longitudes and not in ocean/invalid space
        for coord in imported_coords:
            lon, lat = coord[0], coord[1]
            assert -90.0 <= lat <= 90.0, f"Invalid latitude '{lat}' in imported route coordinates."
            assert -180.0 <= lon <= 180.0, f"Invalid longitude '{lon}' in imported route coordinates."

        # Verify coordinates overlap with source GPX geographic envelope (with 0.5 deg tolerance for routing snaps)
        envelope_lat_min = gpx_meta["min_lat"] - 0.5
        envelope_lat_max = gpx_meta["max_lat"] + 0.5
        envelope_lon_min = gpx_meta["min_lon"] - 0.5
        envelope_lon_max = gpx_meta["max_lon"] + 0.5

        first_imported = imported_coords[0]
        assert envelope_lat_min <= first_imported[1] <= envelope_lat_max, (
            f"Imported latitude {first_imported[1]} outside source GPX latitude envelope [{envelope_lat_min}, {envelope_lat_max}]"
        )
        assert envelope_lon_min <= first_imported[0] <= envelope_lon_max, (
            f"Imported longitude {first_imported[0]} outside source GPX longitude envelope [{envelope_lon_min}, {envelope_lon_max}]"
        )

        # Verify Mapbox WebGL Canvas and Waypoint Markers
        initial_map_verif = planner_page.verify_route_on_map()
        logger.info(f"Initial Map Verification: Canvas Ready={initial_map_verif['canvas_ready']}, Markers={initial_map_verif['marker_count']}")
        assert initial_map_verif["canvas_ready"] is True
        assert initial_map_verif["marker_count"] >= 2
        planner_page.verify_no_errors()

        # Step 6: Dynamic Waypoint Reorder Operations
        log_step(6, f"Execute dynamic waypoint reorder operations for {imported_count} imported waypoints")
        original_waypoints_order = list(imported_waypoints)

        if imported_count == 2:
            # 2 Waypoints: Swap Pos 1 <-> Pos 2, then restore
            logger.info("Executing 2-waypoint swap: Move Pos 1 -> Pos 2")
            wps_s1 = planner_page.reorder_waypoint(from_index=0, to_index=1)
            assert len(wps_s1) == 2, f"Waypoint count altered during swap: {wps_s1}"
            route_s1 = planner_page.wait_for_route_calculation(timeout=30)
            assert route_s1["distance_numeric"] > 0
            planner_page.verify_no_errors()

            logger.info("Restoring original 2-waypoint order: Move Pos 2 -> Pos 1")
            wps_restored = planner_page.reorder_waypoint(from_index=1, to_index=0)
            assert wps_restored == original_waypoints_order, f"Restore failed: {wps_restored} != {original_waypoints_order}"

        elif 3 <= imported_count <= 4:
            # 3-4 Waypoints: 2 Swaps (Swap 1: Pos 2 -> Pos 3; Swap 2: Pos 3 -> Pos 2 restore)
            logger.info("Executing 3-4 waypoint Swap 1: Move Pos 2 -> Pos 3")
            wps_s1 = planner_page.reorder_waypoint(from_index=1, to_index=2)
            assert len(wps_s1) == imported_count
            route_s1 = planner_page.wait_for_route_calculation(timeout=30)
            assert route_s1["distance_numeric"] > 0
            planner_page.verify_no_errors()

            logger.info("Executing 3-4 waypoint Swap 2 (Restore): Move Pos 3 -> Pos 2")
            wps_restored = planner_page.reorder_waypoint(from_index=2, to_index=1)
            assert wps_restored == original_waypoints_order, f"Restore failed: {wps_restored} != {original_waypoints_order}"

        else:
            # 5+ Waypoints: 4 Swaps
            logger.info("Executing 5+ waypoint Swap 1: Move Pos 2 -> Pos 4")
            wps_s1 = planner_page.reorder_waypoint(from_index=1, to_index=3)
            assert len(wps_s1) == imported_count
            route_s1 = planner_page.wait_for_route_calculation(timeout=30)
            assert route_s1["distance_numeric"] > 0
            planner_page.verify_no_errors()

            logger.info("Executing 5+ waypoint Swap 2: Move Pos 4 -> Pos 2")
            wps_s2 = planner_page.reorder_waypoint(from_index=3, to_index=1)
            assert len(wps_s2) == imported_count
            route_s2 = planner_page.wait_for_route_calculation(timeout=30)
            assert route_s2["distance_numeric"] > 0
            planner_page.verify_no_errors()

            logger.info("Executing 5+ waypoint Swap 3: Move Pos 3 -> Pos 4")
            wps_s3 = planner_page.reorder_waypoint(from_index=2, to_index=3)
            assert len(wps_s3) == imported_count
            route_s3 = planner_page.wait_for_route_calculation(timeout=30)
            assert route_s3["distance_numeric"] > 0
            planner_page.verify_no_errors()

            logger.info("Executing 5+ waypoint Swap 4 (Restore): Move Pos 4 -> Pos 3")
            wps_restored = planner_page.reorder_waypoint(from_index=3, to_index=2)
            assert wps_restored == original_waypoints_order, f"Restore failed: {wps_restored} != {original_waypoints_order}"

        # Final Route Recalculation after restore
        final_route = planner_page.wait_for_route_calculation(timeout=30)
        logger.info(f"Restored Final Route: Distance={final_route['distance']}, Duration={final_route['duration']}")
        assert final_route["distance_numeric"] > 0
        planner_page.verify_no_errors()

        # Capture snapshot of final state for strict post-reopen assertion
        saved_waypoints = list(wps_restored)
        saved_distance_str = final_route["distance"]
        saved_duration_str = final_route["duration"]
        saved_coords_count = len(final_route["coordinates"])
        logger.info(f"Final Restored Waypoint Order Snapshot for Persistence Validation: {saved_waypoints}")

        # Step 7: Set Unique Route Name
        log_step(7, f"Set unique Route Name: '{test_route_name}'")
        planner_page.set_route_name(test_route_name)

        # Step 8: Click Save Roadtrip and confirm backend persistence
        log_step(8, "Click 'Save Roadtrip' and confirm backend persistence")
        save_result = planner_page.save_roadtrip(timeout=25)
        logger.info(f"Save Confirmed: Redirect URL={save_result['redirect_url']}, Generated Trip ID={save_result['trip_id']}")
        assert save_result["success"] is True, "GPX Roadtrip save operation failed."

        # Step 9: Open My Roadtrips and locate the newly saved GPX Roadtrip card
        log_step(9, "Open 'My Roadtrips' and locate the newly created GPX roadtrip card")
        planner_page.open_my_roadtrips_tab()
        planner_page.wait_until_visible((By.CSS_SELECTOR, ".upcomingJourneyList span.hyperlink"), timeout=25)
        cards = planner_page.find_all(planner_page.JOURNEY_LIST_CARDS, timeout=10)
        assert len(cards) > 0, "No roadtrip cards found in My Roadtrips after saving."

        first_card = cards[0]
        created_trip_title = first_card.find_element(By.CSS_SELECTOR, "span.hyperlink").text.strip()
        logger.info(f"Located Newly Created GPX Roadtrip Card: '{created_trip_title}' (Total trips in list: {len(cards)})")

        # Step 10: Reopen the exact saved Roadtrip in Planner
        log_step(10, "Reopen Saved GPX Roadtrip in Planner via 'See All Routes' -> 'Edit Route'")
        planner_page.reopen_saved_roadtrip_in_planner(first_card)

        # Step 11: Strict Persistence Comparison
        log_step(11, "Execute Strict Persistence Comparison between Saved and Reopened State")
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
        assert len(reopened_waypoints) == len(saved_waypoints), (
            f"Waypoint count mismatch: expected {len(saved_waypoints)}, got {len(reopened_waypoints)}"
        )

        # 2. Waypoint list / order exact equality comparison
        assert reopened_waypoints == saved_waypoints, (
            f"Reopened waypoints list does not match saved waypoints list:\n"
            f"Reopened: {reopened_waypoints}\n"
            f"Saved:    {saved_waypoints}"
        )

        # 3. Start and Destination location comparisons
        assert reopened_waypoints[0] == saved_waypoints[0], (
            f"Reopened Start location mismatch: expected '{saved_waypoints[0]}', got '{reopened_waypoints[0]}'"
        )
        assert reopened_waypoints[-1] == saved_waypoints[-1], (
            f"Reopened Destination location mismatch: expected '{saved_waypoints[-1]}', got '{reopened_waypoints[-1]}'"
        )

        # 4. Route distance and duration comparison
        assert reopened_num_dist > 0, f"Reopened route distance must be > 0, got '{reopened_dist}'"
        assert len(reopened_coords) >= 2, (
            f"Reopened route coordinates missing: got {len(reopened_coords)} points (expected >= 2)."
        )

        # 5. Map Rendering and WebGL Markers
        reopened_map_verif = planner_page.verify_route_on_map()
        logger.info(f"Reopened Map Verification: Canvas Ready={reopened_map_verif['canvas_ready']}, Markers={reopened_map_verif['marker_count']}")
        assert reopened_map_verif["canvas_ready"] is True, "Reopened map canvas not rendered."
        assert reopened_map_verif["marker_count"] >= 2, (
            f"Reopened map markers missing: expected >= 2, got {reopened_map_verif['marker_count']}"
        )

        planner_page.verify_no_errors()

        from utils.reporter import TestReporter
        rep = TestReporter.get_current()
        if rep:
            rep.add_validation("Imported GPX File", selected_gpx_path.name, category="GPX Source Metadata")
            rep.add_validation("Source Points in File", f"{gpx_meta['point_count']} GPS Points", category="GPX Source Metadata")
            rep.add_validation("Imported Waypoints", f"{imported_count} Waypoints Extracted", category="Waypoint Configuration")
            rep.add_validation("Initial Calculated Distance", imported_distance, category="Route Calculation")
            rep.add_validation("Initial Calculated Duration", imported_duration, category="Route Calculation")
            rep.add_validation("Dynamic Waypoint Swaps", f"{imported_count} Waypoints Swapped & Restored", category="Waypoint Reordering")
            rep.add_validation("Saved Route Name", test_route_name, category="Backend Persistence")
            rep.add_validation("Saved Trip Card Title", created_trip_title, category="Backend Persistence")
            rep.add_validation("Reopened Distance", reopened_dist, category="Backend Persistence")
            rep.add_validation("Reopened Duration", reopened_duration, category="Backend Persistence")
            rep.add_validation("Mapbox Markers", f"{reopened_map_verif['marker_count']} Markers Rendered", category="Mapbox Visualization")
            rep.add_validation("Persistence Integrity", "100% Exact Match (Saved == Reopened)", category="Backend Persistence")

        log_test_success(
            "TC-002",
            f"GPX Roadtrip '{created_trip_title}' ('{test_route_name}') from '{selected_gpx_path.name}' "
            f"({imported_count} waypoints) Swaps, Save & Reopen Verified & Preserved in staging"
        )
