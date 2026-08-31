# RoadTripTribes Selenium + Pytest Test Automation Framework

A production-grade, enterprise-ready end-to-end automation testing suite built with **Selenium WebDriver (Python)** and **Pytest** for the [RoadTripTribes](https://staging.roadtriptribes.com) web application.

---

## 📋 Table of Contents

- [Overview & Architecture](#-overview--architecture)
- [Automated Test Suite (TC-001 to TC-007)](#-automated-test-suite-tc-001-to-tc-007)
- [Framework Capabilities & Highlights](#-framework-capabilities--highlights)
- [Prerequisites](#-prerequisites)
- [Fresh Machine Setup & Quickstart](#-fresh-machine-setup--quickstart)
- [Environment Configuration](#-environment-configuration)
- [Running Test Cases](#-running-test-cases)
- [Automated Test Reporting System](#-automated-test-reporting-system)
- [Project Directory Structure](#-project-directory-structure)

---

## 🔭 Overview & Architecture

This framework follows the **Page Object Model (POM)** design pattern, ensuring clean separation between page interaction logic, test assertions, and configuration.

```
                  ┌─────────────────────────────────────┐
                  │          Pytest Test Runner         │
                  └──────────────────┬──────────────────┘
                                     │
           ┌─────────────────────────┼─────────────────────────┐
           ▼                         ▼                         ▼
┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
│  Test Cases (tests) │   │ Page Objects(pages) │   │ Utilities (utils)   │
│  - TC-001 to TC-007 │   │ - BasePage          │   │ - Config            │
│  - Parameterized    │   │ - LoginPage         │   │ - Custom Logger     │
│  - Strict Assertions│   │ - PlannerPage       │   │ - GeoHelpers (CDP)  │
└─────────────────────┘   └─────────────────────┘   │ - GPXParser         │
                                                    │ - MapHelpers        │
                                                    │ - TestReporter      │
                                                    └─────────────────────┘
```

---

## 🧪 Automated Test Suite (TC-001 to TC-007)

| Test ID | Test Scenario | Description & Coverage | Markers |
| :--- | :--- | :--- | :--- |
| **TC-001** | **Multi-Waypoint Roadtrip Creation & Swapping** | Validates sequential 5-waypoint creation (SF -> Sacramento -> Tahoe -> Reno -> LA), 4 distinct drag-and-drop waypoint reordering swaps, real-time route distance/duration recalculations, save operation, and exact reopened persistence from *My Roadtrips*. | `tc001`, `planner`, `regression` |
| **TC-002** | **GPX Import Multi-Waypoint Roadtrip** | Validates GPX file upload parsing, automated extraction of start, end, and intermediate coordinates, reverse-geocoding into human-readable locations, route recalculation, waypoint reordering, save operation, and persistence. | `tc002`, `gpx`, `planner`, `regression` |
| **TC-003** | **Multi-Roadtrip Editing & State Isolation** | Opens and edits an existing saved Roadtrip, verifies save persistence, switches to a second distinct Roadtrip to ensure 100% state isolation (zero DOM/memory cross-trip leakage), edits the second Roadtrip, and returns to the first Roadtrip to confirm exact state restoration. | `tc003`, `editing`, `planner`, `regression` |
| **TC-004** | **Invalid Route & Distance Limit Validation** | Validates Planner error handling across impossible overland routes (e.g. Hawaii to SF "Route Not Found"), maximum distance threshold limits (>3500 km), GPX route geometry validation, and prevention of stale route calculations. | `tc004`, `invalid_routes`, `planner`, `regression` |
| **TC-005** | **Roadtrip Lifecycle, Persistence & State Regression** | Multi-phase lifecycle validation: initial 3-waypoint baseline creation -> save -> navigation away to My Roadtrips -> reopen & verify Checkpoint 1 persistence -> append 4th waypoint -> recalculate route -> save/update -> navigation away -> reopen & verify Checkpoint 2 persistence. | `tc005`, `lifecycle`, `planner`, `regression` |
| **TC-006** | **Waypoint Deletion, Route Restructuring & Recovery** | Robust deletion testing: removes middle waypoint (Lake Tahoe), end waypoint (Sacramento), recovers route with new waypoint (Yosemite), reorders sequence, saves initial version, reopens (Checkpoint 1), deletes Reno, saves updated version, and verifies Checkpoint 2 persistence with zero state leakage. | `tc006`, `deletion`, `planner`, `regression` |
| **TC-007** | **Stops, Route Editing & Map Waypoint Placement** | Validates toggling waypoints between *Stop* (`is-active`) and *Passthrough*, editing Route Name & Description, directly clicking the Mapbox WebGL canvas to place coordinates via reverse-geocoding, dragging map pin markers (`div.marker-dot`), route recalculations, and backend persistence. | `tc007`, `stops`, `route_editing`, `map`, `regression` |

---

## ⚡ Framework Capabilities & Highlights

- **CDP Geolocation Emulation**: Uses Chrome DevTools Protocol (`Emulation.setGeolocationOverride`) to ensure deterministic location resolution independent of local IP/machine.
- **Dynamic Element Synchronization**: Custom explicit wait abstractions handle React hydration, CSS transitions, Mapbox tile rendering, and asynchronous route recalculations without arbitrary sleeps.
- **Mapbox WebGL Canvas & DOM Marker Dragging**: Native and synthetic event dispatching for Mapbox canvas coordinate insertion and marker pin dragging (`mousedown` -> `mousemove` -> `mouseup`).
- **Zero Test Data Destruction**: All test runs preserve created Roadtrips on staging for auditability and manual inspection.
- **Automated Individual Reporting**: After **every** test execution, the framework automatically generates a standalone executive HTML report and structured JSON summary with timing, phase breakdowns, verified business metrics, and failure screenshots.

---

## 💻 Prerequisites

- **Python**: Version `3.10` or higher (`3.12` recommended)
- **Browser**: Google Chrome (or Edge / Firefox)
- **Git**: Installed and configured on your machine

---

## 🚀 Fresh Machine Setup & Quickstart

Follow these steps to get up and running on a new computer:

### 1. Clone the Repository
```bash
git clone https://github.com/PranavThakur07/Selenium-RTT.git
cd Selenium-RTT
```

### 2. Create and Activate Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 🔐 Environment Configuration

Create a `.env` file in the root directory by copying `.env.example`:

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**Linux / macOS:**
```bash
cp .env.example .env
```

Edit `.env` with your test credentials:
```ini
BASE_URL=https://staging.roadtriptribes.com
LOGIN_URL=https://staging.roadtriptribes.com/login

RTT_TEST_EMAIL=your_email@example.com
RTT_TEST_PASSWORD=your_password_here

RTT_GEO_LATITUDE=28.6139
RTT_GEO_LONGITUDE=77.2090
RTT_GEO_ACCURACY=10

BROWSER=chrome
HEADLESS=false
IMPLICIT_TIMEOUT=10
EXPLICIT_TIMEOUT=20
```

> **Note**: You can also set these environment variables directly in your terminal session if you prefer not to create a `.env` file.

---

## 🏃 Running Test Cases

### Option A: Set Environment Variables & Run (PowerShell)
```powershell
# Set credentials in current PowerShell session
$env:RTT_TEST_EMAIL="pranav.designoweb@gmail.com"
$env:RTT_TEST_PASSWORD="your_password_here"
$env:RTT_GEO_LATITUDE="28.6139"
$env:RTT_GEO_LONGITUDE="77.2090"
$env:RTT_GEO_ACCURACY="10"

# Run individual test cases
python -m pytest tests/test_roadtrip_creation.py -v -s         # TC-001
python -m pytest tests/test_gpx_import.py -v -s               # TC-002
python -m pytest tests/test_roadtrip_editing.py -v -s          # TC-003
python -m pytest tests/test_invalid_route_handling.py -v -s   # TC-004
python -m pytest tests/test_roadtrip_lifecycle.py -v -s        # TC-005
python -m pytest tests/test_waypoint_deletion.py -v -s         # TC-006
python -m pytest tests/test_stops_route_editing_map.py -v -s   # TC-007

# Run the complete regression suite
python -m pytest tests/ -v -s
```

### Option B: Run Using Pytest Markers
```powershell
# Run smoke tests
python -m pytest -m smoke -v -s

# Run specific test case marker
python -m pytest -m tc007 -v -s
python -m pytest -m gpx -v -s
python -m pytest -m deletion -v -s

# Run in headless mode
python -m pytest tests/test_roadtrip_creation.py --headless=true -v -s
```

---

## 📊 Automated Test Reporting System

After each test execution, reports are automatically generated inside `reports/test_reports/`:

```
reports/
├── screenshots/                     # Automatic screenshots captured on test failure
│   └── test_<name>_<timestamp>.png
└── test_reports/
    ├── TC-001/
    │   ├── TC-001_YYYY-MM-DD_HHMMSS.html   # Standalone Executive HTML Report
    │   └── TC-001_YYYY-MM-DD_HHMMSS.json   # Machine-readable JSON Summary
    ├── TC-002/
    ├── TC-003/
    ├── TC-004/
    ├── TC-005/
    ├── TC-006/
    └── TC-007/
```

### Executive HTML Report Features:
- **Executive Summary Card**: Test status badge, overall duration, execution environment, and tested application.
- **Objective Overview**: Clear description of what business capability was validated.
- **Step-by-Step Execution Log**: Detailed action and status for every phase.
- **Key Validations Table**: Categorized business assertions (e.g. Distance calculations, Waypoint sequences, Mapbox rendering).
- **Diagnostics & Observations**: Non-fatal application observations and warnings.
- **Failure Details**: Embedded screenshot and traceback if an error occurs.

---

## 📁 Project Directory Structure

```
selenium-RTT/
├── .env.example                     # Environment variables configuration template
├── .gitignore                       # Git ignore rules (excludes secrets, venv, reports, cache)
├── conftest.py                      # Global Pytest fixtures, browser lifecycle, hooks, and report integration
├── pytest.ini                       # Pytest configuration, options, and test markers
├── README.md                        # Framework setup, usage, and architectural documentation
├── requirements.txt                 # Python package dependencies
│
├── GPX files/                       # Sample GPX test files for import validation
│   ├── 2022-6-22_Wo_Dag_1_Corsica__Bastia_-_Galeria.gpx
│   ├── 2022-6-25_Za__Dag_4_Corsica__Bastia_naar_Boot.gpx
│   ├── 2027 Dag 1.gpx
│   ├── Cheddar -_ Tetbury (78.6km).gpx
│   ├── Route2.gpx
│   └── mapstogpx20230130_143449.gpx
│
├── pages/                           # Page Object Model classes
│   ├── __init__.py
│   ├── base_page.py                 # Core wrapper for WebDriver operations, explicit waits, and CDP actions
│   ├── login_page.py                # Login modal interactions, credentials input, and submit flows
│   └── planner_page.py              # Roadtrip Planner interactions (waypoints, stops, map clicks, drag, save, reopen)
│
├── reports/                         # Test output directory (git-tracked directory structure)
│   ├── screenshots/                 # Captured failure screenshots
│   └── test_reports/                # Automated HTML/JSON reports organized by TC ID
│
├── tests/                           # End-to-end automation test cases
│   ├── __init__.py
│   ├── test_roadtrip_creation.py    # TC-001: 5-waypoint creation & 4 swap reordering
│   ├── test_gpx_import.py           # TC-002: GPX import & waypoint extraction
│   ├── test_roadtrip_editing.py     # TC-003: Multi-trip editing & state isolation
│   ├── test_invalid_route_handling.py # TC-004: Invalid routes & distance limit validation
│   ├── test_roadtrip_lifecycle.py   # TC-005: Complete lifecycle & multi-checkpoint persistence
│   ├── test_waypoint_deletion.py    # TC-006: Waypoint deletion, restructuring & recovery
│   └── test_stops_route_editing_map.py # TC-007: Stops toggle, route details, map placement & dragging
│
└── utils/                           # Shared framework utilities
    ├── __init__.py
    ├── config.py                    # Environment variable loader and settings validator
    ├── geo_helpers.py               # CDP geolocation override helper for Chrome/Edge
    ├── gpx_parser.py                # XML GPX parser for route point extraction
    ├── logger.py                    # Formatted colored console logger with file output
    ├── map_helpers.py               # Mapbox diagnostic and DOM inspection utilities
    └── reporter.py                  # Automated executive HTML and JSON report generator
```
