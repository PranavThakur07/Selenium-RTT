import os
import time
from datetime import datetime
from pathlib import Path
import pytest
from colorama import Fore, Style
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from utils.config import Config
from utils.logger import get_logger
from utils.geo_helpers import GeoHelpers

logger = get_logger("Conftest")


def pytest_addoption(parser):
    """Add command line options to pytest."""
    parser.addoption(
        "--headless",
        action="store",
        default=None,
        help="Run browser in headless mode: true or false"
    )
    parser.addoption(
        "--browser",
        action="store",
        default=Config.BROWSER,
        help="Browser to run tests on (chrome, firefox, edge)"
    )


@pytest.fixture(scope="session", autouse=True)
def setup_directories():
    """Ensures reports and screenshots directories exist."""
    Config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    Config.SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


import re
from utils.reporter import TestReporter

DEFAULT_TEST_METADATA = {
    "TC-001": {
        "name": "Multi-Waypoint Roadtrip Creation & Swapping",
        "objective": "This test verifies that a user can create a roadtrip with multiple waypoints, change the order of locations, confirm that the route updates correctly, save the roadtrip, and verify that all information remains correct when the trip is opened again."
    },
    "TC-002": {
        "name": "GPX Import Multi-Waypoint Roadtrip",
        "objective": "This test verifies that a user can import a GPX file into the Planner, automatically extract waypoints and generate a drivable route, dynamically reorder waypoints, save the roadtrip, and reopen it with strict persistence validation."
    },
    "TC-003": {
        "name": "Multi-Roadtrip Editing, State Isolation & Cross-Trip Persistence",
        "objective": "This test verifies that an existing Roadtrip can be opened, edited, and saved, that switching to a second distinct Roadtrip operates with complete state isolation (zero cross-trip data leakage), and that returning to the first Roadtrip accurately restores its exact previously saved state."
    },
    "TC-004": {
        "name": "Invalid Route Handling & Route Calculation Validation",
        "objective": "This test validates that the Planner correctly handles scenarios where a route cannot be generated (Route Not Found), routes exceeding maximum distance, GPX route consistency, and that invalid or stale route lines and data are not treated as valid calculations."
    },
    "TC-005": {
        "name": "Roadtrip Lifecycle, Persistence & Planner State Regression",
        "objective": "This test validates that a Roadtrip remains stable, accurate, and consistent throughout its complete multi-phase lifecycle (creation -> save -> navigate away -> reopen & verify persistence -> edit & recalculate -> save/update -> navigate away -> reopen & verify final persistence)."
    },
    "TC-006": {
        "name": "Waypoint Deletion, Route Restructuring & Planner Recovery",
        "objective": "This test checks whether a roadtrip can safely be changed multiple times. It creates a route with several stops, removes stops from different positions, adds a new stop, changes the order of the route, saves it, leaves the page, and repeatedly opens it again. The goal is to make sure deleted stops do not return, route data does not become duplicated or stale, and the final saved version of the roadtrip remains exactly as the user last configured it."
    },
    "TC-007": {
        "name": "Stops, Route Editing & Map Waypoint Placement",
        "objective": "This test validates how a user can modify a roadtrip beyond simple waypoint reordering or deletion, including designating stops vs. passthroughs, modifying route details and descriptions, directly clicking the map to place new waypoints, dragging map pins to adjust routes, dynamic route recalculation, and verifying exact multi-phase persistence."
    },
    "TC-008": {
        "name": "Roadtrip Details, Date/Time Changes & Persistence",
        "objective": "This test verifies that a user can create a baseline roadtrip, edit roadtrip-level details (trip name, description, start date/time, return date), validate date change behavior and route integrity, save the roadtrip, clear the Planner in-memory state, and reopen the saved roadtrip with strict persistence validation."
    }
}


@pytest.fixture(scope="function", autouse=True)
def test_reporter(request):
    """
    Initializes a TestReporter instance for every test case and automatically
    finalizes HTML and JSON reports upon completion.
    """
    # Detect Test ID from markers or test name
    test_id = "TC-UNKNOWN"
    for mark in ("tc001", "tc002", "tc003", "tc004", "tc005", "tc006", "tc007", "tc008"):
        if request.node.get_closest_marker(mark):
            # Format as TC-001, TC-002, etc.
            raw_id = mark.upper()
            if not "-" in raw_id and len(raw_id) >= 5:
                test_id = f"{raw_id[:2]}-{raw_id[2:]}"
            else:
                test_id = raw_id
            break

    if test_id == "TC-UNKNOWN":
        match = re.search(r"tc[-_]?(\d+)", request.node.name, re.IGNORECASE)
        if match:
            test_id = f"TC-{int(match.group(1)):03d}"

    default_meta = DEFAULT_TEST_METADATA.get(test_id, {
        "name": request.node.name.replace("_", " ").title(),
        "objective": (request.node.function.__doc__ or "Validate application functionality and data integrity.").strip()
    })

    test_file_rel = ""
    try:
        test_file_rel = str(Path(request.node.fspath).relative_to(Config.PROJECT_ROOT))
    except Exception:
        test_file_rel = str(request.node.fspath)

    browser_name = request.config.getoption("--browser") or Config.BROWSER
    headless_opt = request.config.getoption("--headless")
    is_headless = (headless_opt.lower() in ("true", "1", "yes")) if headless_opt is not None else Config.HEADLESS
    mode_label = "Headless" if is_headless else "Visible / Headed"

    rep = TestReporter(test_id=test_id, test_name=default_meta["name"])
    rep.set_metadata(
        test_id=test_id,
        test_name=default_meta["name"],
        objective=default_meta["objective"],
        test_file=test_file_rel,
        browser=browser_name.upper(),
        execution_mode=mode_label,
        environment="Staging"
    )

    request.node.reporter = rep

    yield rep

    # Finalize and generate reports
    try:
        html_p, json_p = rep.finalize()
        print(f"\n{Fore.CYAN}{Style.BRIGHT}[REPORT GENERATED]{Style.RESET_ALL}")
        print(f"{Fore.GREEN}HTML Report:{Style.RESET_ALL} {html_p}")
        print(f"{Fore.BLUE}JSON Report:{Style.RESET_ALL} {json_p}\n")
    except Exception as e:
        logger.error(f"Error during automatic report generation: {e}")


@pytest.fixture(scope="function")
def driver(request):
    """
    Initializes and manages the WebDriver instance for tests.
    Supports Chrome, Firefox, Edge with configurable headless mode
    and optional controlled CDP geolocation override.
    """
    browser_name = request.config.getoption("--browser") or Config.BROWSER
    headless_opt = request.config.getoption("--headless")

    if headless_opt is not None:
        is_headless = headless_opt.lower() in ("true", "1", "yes")
    else:
        is_headless = Config.HEADLESS

    mode_label = "Headless" if is_headless else "Visible / Headed"
    logger.info(f"Launching {Fore.CYAN}{browser_name.upper()}{Style.RESET_ALL} in {Fore.YELLOW}{mode_label}{Style.RESET_ALL} mode")

    if browser_name.lower() == "firefox":
        options = FirefoxOptions()
        if is_headless:
            options.add_argument("-headless")
        driver_instance = webdriver.Firefox(options=options)
    elif browser_name.lower() == "edge":
        options = EdgeOptions()
        if is_headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        prefs = {"profile.default_content_setting_values.geolocation": 1}
        options.add_experimental_option("prefs", prefs)
        driver_instance = webdriver.Edge(options=options)
    else:  # Default to Chrome
        options = ChromeOptions()
        if is_headless:
            options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-search-engine-choice-screen")
        prefs = {"profile.default_content_setting_values.geolocation": 1}
        options.add_experimental_option("prefs", prefs)
        driver_instance = webdriver.Chrome(options=options)

    # Configure controlled CDP Geolocation if enabled
    if Config.is_geolocation_configured():
        GeoHelpers.configure_browser_geolocation(
            driver_instance,
            latitude=Config.GEO_LATITUDE,
            longitude=Config.GEO_LONGITUDE,
            accuracy=Config.GEO_ACCURACY,
            origin=Config.BASE_URL
        )

    driver_instance.maximize_window()
    driver_instance.implicitly_wait(Config.IMPLICIT_TIMEOUT)

    # Attach driver to test node for hook access
    request.node.driver = driver_instance

    yield driver_instance

    logger.info("Closing browser session and freeing resources...")
    try:
        driver_instance.quit()
    except Exception as e:
        logger.warning(f"Error during driver quit: {e}")


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Captures screenshot and logs diagnostics automatically on test failure,
    updating the active TestReporter instance with full failure details.
    """
    outcome = yield
    report = outcome.get_result()

    reporter_instance = getattr(item, "reporter", None) or TestReporter.get_current()

    if report.when == "call":
        if report.passed and reporter_instance:
            reporter_instance.report.status = "PASSED"
        elif report.failed:
            driver_instance = getattr(item, "driver", None)
            screenshot_path_str = ""
            current_url = ""

            if driver_instance:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                test_name = item.name.replace("/", "_").replace("::", "_")
                screenshot_path = Config.SCREENSHOTS_DIR / f"{test_name}_{timestamp}.png"

                try:
                    driver_instance.save_screenshot(str(screenshot_path))
                    screenshot_path_str = str(screenshot_path)
                    current_url = getattr(driver_instance, "current_url", "")
                    logger.error(f"FAILURE SCREENSHOT SAVED: {screenshot_path}")
                    logger.error(f"URL AT FAILURE: {current_url}")
                except Exception as e:
                    logger.error(f"Failed to capture failure screenshot: {e}")

            if reporter_instance:
                exc_info = call.excinfo
                exc_type = exc_info.typename if exc_info else "AssertionError"
                exc_msg = str(exc_info.value) if exc_info else "Test execution encountered an error."
                tb_text = str(report.longrepr) if report.longrepr else ""

                # Extract last executed step number if available
                last_step = None
                if reporter_instance.report.steps:
                    last_step = reporter_instance.report.steps[-1].step_number
                    reporter_instance.report.steps[-1].result = "FAIL"

                clean_summary = f"Execution failed at Step {last_step or 'Execution'}: {exc_msg}"

                reporter_instance.set_failure(
                    summary=clean_summary,
                    failed_step=last_step,
                    exception_type=exc_type,
                    exception_message=exc_msg,
                    current_url=current_url,
                    screenshot_path=screenshot_path_str,
                    traceback_text=tb_text
                )
