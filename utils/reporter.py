"""
RoadTripTribes Automated Test Report System

Generates professional, executive-friendly, layman-understandable HTML and JSON
test reports automatically after every test case execution for both PASS and FAIL states.
"""

import os
import sys
import json
import html
import platform
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple
import pytest
from utils.config import Config
from utils.logger import get_logger

logger = get_logger("TestReporter")


@dataclass
class StepRecord:
    step_number: int
    action: str
    result: str = "PASS"  # PASS, FAIL, WARN, INFO
    details: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))


@dataclass
class ValidationRecord:
    category: str
    name: str
    value: str
    status: str = "VERIFIED"  # VERIFIED, MATCHED, PASS, FAIL
    details: str = ""


@dataclass
class ObservationRecord:
    type: str  # OBSERVATION, WARNING, DIAGNOSTIC
    title: str
    description: str
    severity: str = "INFO"  # LOW, MEDIUM, HIGH, INFO


@dataclass
class FailureRecord:
    summary: str
    failed_step: Optional[int] = None
    exception_type: str = ""
    exception_message: str = ""
    current_url: str = ""
    screenshot_path: str = ""
    traceback_text: str = ""


@dataclass
class AttachmentRecord:
    name: str
    path: str
    type: str = "screenshot"


class TestReport:
    """Encapsulates all execution data and metadata for a single test case run."""
    __test__ = False

    def __init__(
        self,
        test_id: str = "TC-UNKNOWN",
        test_name: str = "Automated Test Case",
        objective: str = "Validate application functionality and data integrity.",
        test_file: str = ""
    ):
        self.test_id = test_id
        self.test_name = test_name
        self.objective = objective
        self.test_file = test_file
        self.environment = "Staging"
        self.application = "RoadTripTribes"
        self.browser = "Chrome"
        self.execution_mode = "Visible / Headed"
        self.python_version = platform.python_version()
        self.pytest_version = pytest.__version__
        self.os_info = f"{platform.system()} {platform.release()}"
        
        self.status = "PENDING"  # PASSED, FAILED, ERROR, SKIPPED
        self.start_time: datetime = datetime.now()
        self.end_time: Optional[datetime] = None
        self.duration_seconds: float = 0.0

        self.steps: List[StepRecord] = []
        self.validations: List[ValidationRecord] = []
        self.observations: List[ObservationRecord] = []
        self.failure: Optional[FailureRecord] = None
        self.attachments: List[AttachmentRecord] = []
        self.raw_logs: List[str] = []

    def format_duration(self) -> str:
        """Formats duration into human-readable minutes and seconds."""
        secs = int(self.duration_seconds)
        mins = secs // 60
        rem_secs = secs % 60
        if mins > 0:
            return f"{mins} min{'s' if mins != 1 else ''} {rem_secs} sec{'s' if rem_secs != 1 else ''}"
        return f"{self.duration_seconds:.2f} seconds"

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the test report to a clean dictionary."""
        return {
            "test_execution_summary": {
                "test_case_id": self.test_id,
                "test_case_name": self.test_name,
                "status": self.status,
                "execution_date": self.start_time.strftime("%d %B %Y"),
                "start_time": self.start_time.strftime("%I:%M:%S %p"),
                "end_time": self.end_time.strftime("%I:%M:%S %p") if self.end_time else "",
                "total_duration": self.format_duration(),
                "duration_seconds": round(self.duration_seconds, 2),
                "environment": self.environment,
                "application": self.application,
                "browser": self.browser,
                "execution_mode": self.execution_mode,
                "python_version": self.python_version,
                "pytest_version": self.pytest_version,
                "operating_system": self.os_info,
                "test_file": self.test_file
            },
            "test_objective": self.objective,
            "step_by_step_execution": [asdict(s) for s in self.steps],
            "key_validations": [asdict(v) for v in self.validations],
            "warnings_and_observations": [asdict(o) for o in self.observations],
            "failure_details": asdict(self.failure) if self.failure else None,
            "attachments": [asdict(a) for a in self.attachments],
            "technical_details": {
                "raw_logs_count": len(self.raw_logs),
                "system_info": f"Python {self.python_version} | Pytest {self.pytest_version} | {self.os_info}"
            }
        }


class TestReporter:
    """
    Manager class responsible for recording execution events and generating
    structured HTML and JSON reports after test execution.
    """
    __test__ = False

    # Global active reporter instance for current test thread
    _current_reporter: Optional["TestReporter"] = None

    def __init__(self, test_id: str = "TC-UNKNOWN", test_name: str = "Automated Test Case"):
        self.report = TestReport(test_id=test_id, test_name=test_name)
        self._is_finalized = False
        TestReporter._current_reporter = self

    @classmethod
    def get_current(cls) -> Optional["TestReporter"]:
        """Returns the currently active TestReporter instance."""
        return cls._current_reporter

    def set_metadata(
        self,
        test_id: str,
        test_name: str,
        objective: str,
        test_file: str = "",
        browser: str = "Chrome",
        execution_mode: str = "Visible / Headed",
        environment: str = "Staging"
    ) -> None:
        """Sets or updates high-level test metadata."""
        self.report.test_id = test_id
        self.report.test_name = test_name
        self.report.objective = objective
        if test_file:
            self.report.test_file = test_file
        self.report.browser = browser
        self.report.execution_mode = execution_mode
        self.report.environment = environment

    def log_step(
        self,
        step_number: int,
        action: str,
        result: str = "PASS",
        details: str = ""
    ) -> None:
        """Records a structured human-readable step execution event."""
        # Avoid duplicate step logging if called multiple times for same step number
        for s in self.report.steps:
            if s.step_number == step_number:
                s.action = action
                s.result = result
                if details:
                    s.details = details
                return

        self.report.steps.append(
            StepRecord(
                step_number=step_number,
                action=action,
                result=result,
                details=details
            )
        )

    def add_validation(
        self,
        name: str,
        value: Any,
        category: str = "General Validations",
        status: str = "VERIFIED",
        details: str = ""
    ) -> None:
        """Records a verified business metric or data integrity assertion."""
        val_str = str(value) if not isinstance(value, str) else value
        self.report.validations.append(
            ValidationRecord(
                category=category,
                name=name,
                value=val_str,
                status=status,
                details=details
            )
        )

    def add_observation(
        self,
        title: str,
        description: str,
        obs_type: str = "OBSERVATION",
        severity: str = "INFO"
    ) -> None:
        """Records a product behavior observation or diagnostic notice without failing the test."""
        self.report.observations.append(
            ObservationRecord(
                type=obs_type,
                title=title,
                description=description,
                severity=severity
            )
        )

    def add_warning(self, title: str, description: str) -> None:
        """Shortcut to record a product warning."""
        self.add_observation(title, description, obs_type="WARNING", severity="MEDIUM")

    def add_attachment(self, name: str, path: str, att_type: str = "screenshot") -> None:
        """Records an attachment or screenshot file path."""
        self.report.attachments.append(
            AttachmentRecord(name=name, path=path, type=att_type)
        )

    def set_failure(
        self,
        summary: str,
        failed_step: Optional[int] = None,
        exception_type: str = "",
        exception_message: str = "",
        current_url: str = "",
        screenshot_path: str = "",
        traceback_text: str = ""
    ) -> None:
        """Records failure details when a test encounters an error or assertion failure."""
        self.report.status = "FAILED"
        self.report.failure = FailureRecord(
            summary=summary,
            failed_step=failed_step,
            exception_type=exception_type,
            exception_message=exception_message,
            current_url=current_url,
            screenshot_path=screenshot_path,
            traceback_text=traceback_text
        )

    def finalize(self, status: Optional[str] = None) -> Tuple[Path, Path]:
        """
        Finalizes the test report calculations and generates both HTML and JSON files.
        Returns (html_report_path, json_report_path).
        """
        if self._is_finalized:
            return self._get_target_paths()

        self.report.end_time = datetime.now()
        self.report.duration_seconds = max(0.0, (self.report.end_time - self.report.start_time).total_seconds())

        if status:
            self.report.status = status
        elif self.report.status == "PENDING":
            self.report.status = "PASSED"

        # Generate target directories
        test_dir = Config.REPORTS_DIR / "test_reports" / self.report.test_id
        test_dir.mkdir(parents=True, exist_ok=True)

        timestamp_str = self.report.start_time.strftime("%Y-%m-%d_%H%M%S")
        html_file = test_dir / f"{self.report.test_id}_{timestamp_str}.html"
        json_file = test_dir / f"{self.report.test_id}_{timestamp_str}.json"

        # Generate JSON Report
        try:
            with open(json_file, "w", encoding="utf-8") as jf:
                json.dump(self.report.to_dict(), jf, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to generate JSON report: {e}")

        # Generate HTML Report
        try:
            html_content = self._render_html_report()
            with open(html_file, "w", encoding="utf-8") as hf:
                hf.write(html_content)
        except Exception as e:
            logger.error(f"Failed to generate HTML report: {e}")

        self._is_finalized = True
        return html_file, json_file

    def _get_target_paths(self) -> Tuple[Path, Path]:
        test_dir = Config.REPORTS_DIR / "test_reports" / self.report.test_id
        timestamp_str = self.report.start_time.strftime("%Y-%m-%d_%H%M%S")
        return (
            test_dir / f"{self.report.test_id}_{timestamp_str}.html",
            test_dir / f"{self.report.test_id}_{timestamp_str}.json"
        )

    def _render_html_report(self) -> str:
        """Renders a self-contained, professional, modern executive HTML report."""
        rep = self.report

        # Status Badge Colors
        status_color = "#10B981" if rep.status == "PASSED" else ("#EF4444" if rep.status == "FAILED" else "#F59E0B")
        status_bg = "#ECFDF5" if rep.status == "PASSED" else ("#FEF2F2" if rep.status == "FAILED" else "#FFFBEB")
        status_border = "#A7F3D0" if rep.status == "PASSED" else ("#FECACA" if rep.status == "FAILED" else "#FDE68A")
        status_icon = "&#10004;" if rep.status == "PASSED" else ("&#10008;" if rep.status == "FAILED" else "&#9888;")

        # Steps HTML Table Rows
        steps_rows = []
        for s in rep.steps:
            res_class = "badge-pass" if s.result == "PASS" else ("badge-fail" if s.result == "FAIL" else "badge-warn")
            step_details_html = f"<div class='step-details'>{html.escape(s.details)}</div>" if s.details else ""
            steps_rows.append(f"""
                <tr>
                    <td class="step-num"><span class="step-circle">{s.step_number:02d}</span></td>
                    <td class="step-action">
                        <strong>{html.escape(s.action)}</strong>
                        {step_details_html}
                    </td>
                    <td class="step-res"><span class="badge {res_class}">{s.result}</span></td>
                    <td class="step-time">{s.timestamp}</td>
                </tr>
            """)
        steps_table_html = "".join(steps_rows) if steps_rows else "<tr><td colspan='4' class='no-data'>No steps recorded.</td></tr>"

        # Key Validations Grid
        val_cards = []
        for v in rep.validations:
            status_badge_class = "badge-pass" if v.status in ("VERIFIED", "MATCHED", "PASS") else "badge-warn"
            val_cards.append(f"""
                <div class="val-card">
                    <div class="val-category">{html.escape(v.category)}</div>
                    <div class="val-name">{html.escape(v.name)}</div>
                    <div class="val-value">{html.escape(v.value)}</div>
                    <div class="val-footer">
                        <span class="badge {status_badge_class}">{v.status}</span>
                        {f"<span class='val-details'>{html.escape(v.details)}</span>" if v.details else ""}
                    </div>
                </div>
            """)
        validations_grid_html = "".join(val_cards) if val_cards else "<p class='empty-state'>All business assertions verified successfully through execution flow.</p>"

        # Warnings & Observations Cards
        obs_cards = []
        for o in rep.observations:
            obs_type_class = "obs-warning" if o.type == "WARNING" else "obs-observation"
            badge_class = "badge-warn" if o.type == "WARNING" else "badge-info"
            icon = "&#9888;" if o.type == "WARNING" else "&#8505;"
            obs_cards.append(f"""
                <div class="obs-card {obs_type_class}">
                    <div class="obs-header">
                        <span class="obs-icon">{icon}</span>
                        <span class="obs-title">{html.escape(o.title)}</span>
                        <span class="badge {badge_class}">{o.type}</span>
                    </div>
                    <div class="obs-desc">{html.escape(o.description)}</div>
                </div>
            """)
        observations_html = "".join(obs_cards)

        # Failure Details Card
        failure_html = ""
        if rep.failure:
            f = rep.failure
            screenshot_elem = ""
            if f.screenshot_path:
                rel_path = html.escape(f.screenshot_path)
                screenshot_elem = f"""
                <div class="failure-screenshot">
                    <strong>Failure Screenshot:</strong>
                    <div class="screenshot-preview">
                        <a href="{rel_path}" target="_blank">
                            <img src="{rel_path}" alt="Failure Screenshot" class="thumb-img" onerror="this.style.display='none'; this.nextElementSibling.style.display='block';" />
                            <span class="screenshot-fallback" style="display:none;">View Screenshot File: {rel_path}</span>
                        </a>
                    </div>
                    <div class="screenshot-path"><code>{rel_path}</code></div>
                </div>
                """

            failure_html = f"""
            <section class="card failure-card">
                <div class="card-header failure-header">
                    <span class="header-icon">&#10008;</span>
                    <h2>Failure Summary & Diagnostics</h2>
                </div>
                <div class="card-body">
                    <div class="failure-summary-box">
                        <strong>Reason for Failure:</strong>
                        <p>{html.escape(f.summary)}</p>
                    </div>
                    <div class="meta-grid">
                        <div class="meta-item"><span class="meta-label">Failed Step:</span> <span class="meta-val">{f'Step {f.failed_step:02d}' if f.failed_step else 'Setup / Execution'}</span></div>
                        <div class="meta-item"><span class="meta-label">Exception:</span> <span class="meta-val"><code>{html.escape(f.exception_type or 'Assertion / Runtime Error')}</code></span></div>
                        <div class="meta-item"><span class="meta-label">Current URL:</span> <span class="meta-val"><a href="{html.escape(f.current_url)}" target="_blank">{html.escape(f.current_url or 'N/A')}</a></span></div>
                    </div>
                    {screenshot_elem}
                </div>
            </section>
            """

        # Technical Details / Traceback
        tech_traceback_html = ""
        if rep.failure and rep.failure.traceback_text:
            tech_traceback_html = f"""
            <div class="tech-section">
                <h4>Exception Traceback (Technical):</h4>
                <pre class="code-block"><code>{html.escape(rep.failure.traceback_text)}</code></pre>
            </div>
            """

        raw_logs_html = ""
        if rep.raw_logs:
            raw_logs_html = f"""
            <div class="tech-section">
                <h4>Execution Trace Logs:</h4>
                <pre class="code-block"><code>{html.escape('\n'.join(rep.raw_logs))}</code></pre>
            </div>
            """

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{rep.test_id} - Test Execution Report | RoadTripTribes</title>
    <style>
        :root {{
            --primary: #2563EB;
            --primary-dark: #1D4ED8;
            --success: #10B981;
            --success-bg: #ECFDF5;
            --danger: #EF4444;
            --danger-bg: #FEF2F2;
            --warning: #F59E0B;
            --warning-bg: #FFFBEB;
            --info: #3B82F6;
            --info-bg: #EFF6FF;
            --bg: #F8FAFC;
            --surface: #FFFFFF;
            --border: #E2E8F0;
            --text-main: #0F172A;
            --text-muted: #64748B;
            --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: var(--font);
            background-color: var(--bg);
            color: var(--text-main);
            line-height: 1.5;
            padding: 2rem 1rem;
        }}
        .container {{
            max-width: 1040px;
            margin: 0 auto;
        }}
        /* Header Banner */
        .header-banner {{
            background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
            color: #FFFFFF;
            border-radius: 16px;
            padding: 2rem 2.5rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1.5rem;
        }}
        .header-title-group h1 {{
            font-size: 1.75rem;
            font-weight: 700;
            letter-spacing: -0.025em;
            margin-bottom: 0.25rem;
        }}
        .header-subtitle {{
            color: #94A3B8;
            font-size: 0.95rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .status-badge-lg {{
            background-color: {status_bg};
            color: {status_color};
            border: 2px solid {status_border};
            padding: 0.6rem 1.4rem;
            border-radius: 9999px;
            font-size: 1.15rem;
            font-weight: 700;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        }}
        /* Summary Metrics Grid */
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin-bottom: 1.5rem;
        }}
        .metric-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.25rem 1rem;
            text-align: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .metric-label {{
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            margin-bottom: 0.25rem;
        }}
        .metric-value {{
            font-size: 1.25rem;
            font-weight: 700;
            color: var(--text-main);
        }}
        /* Card Structure */
        .card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 14px;
            margin-bottom: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            overflow: hidden;
        }}
        .card-header {{
            padding: 1.25rem 1.5rem;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 0.75rem;
            background-color: #FAFAFA;
        }}
        .card-header h2 {{
            font-size: 1.15rem;
            font-weight: 600;
            color: var(--text-main);
        }}
        .card-header .header-icon {{
            font-size: 1.2rem;
        }}
        .card-body {{
            padding: 1.5rem;
        }}
        /* Objective Box */
        .objective-text {{
            font-size: 1.05rem;
            color: #334155;
            line-height: 1.6;
        }}
        /* Meta Grid */
        .meta-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 0.75rem 1.5rem;
            margin-top: 0.5rem;
        }}
        .meta-item {{
            font-size: 0.9rem;
            color: var(--text-muted);
        }}
        .meta-label {{
            font-weight: 600;
            color: #475569;
        }}
        .meta-val {{
            color: var(--text-main);
            font-weight: 500;
        }}
        /* Steps Table */
        .table-responsive {{
            overflow-x: auto;
        }}
        table.steps-table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }}
        table.steps-table th {{
            background-color: #F8FAFC;
            color: var(--text-muted);
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            padding: 0.85rem 1rem;
            border-bottom: 1px solid var(--border);
        }}
        table.steps-table td {{
            padding: 1rem;
            border-bottom: 1px solid #F1F5F9;
            vertical-align: top;
            font-size: 0.92rem;
        }}
        table.steps-table tr:last-child td {{
            border-bottom: none;
        }}
        .step-num {{
            width: 50px;
        }}
        .step-circle {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 28px;
            height: 28px;
            background-color: #F1F5F9;
            color: #475569;
            font-weight: 700;
            font-size: 0.8rem;
            border-radius: 50%;
        }}
        .step-action {{
            color: #1E293B;
        }}
        .step-details {{
            margin-top: 0.35rem;
            font-size: 0.85rem;
            color: #64748B;
        }}
        .step-time {{
            color: #94A3B8;
            font-size: 0.8rem;
            width: 90px;
        }}
        .step-res {{
            width: 80px;
        }}
        /* Badges */
        .badge {{
            display: inline-block;
            padding: 0.25rem 0.6rem;
            font-size: 0.75rem;
            font-weight: 700;
            border-radius: 6px;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }}
        .badge-pass {{ background-color: var(--success-bg); color: var(--success); border: 1px solid #A7F3D0; }}
        .badge-fail {{ background-color: var(--danger-bg); color: var(--danger); border: 1px solid #FECACA; }}
        .badge-warn {{ background-color: var(--warning-bg); color: var(--warning); border: 1px solid #FDE68A; }}
        .badge-info {{ background-color: var(--info-bg); color: var(--info); border: 1px solid #BFDBFE; }}
        /* Key Validations Grid */
        .val-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 1rem;
        }}
        .val-card {{
            background: #F8FAFC;
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 1rem 1.25rem;
        }}
        .val-category {{
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--primary);
            margin-bottom: 0.25rem;
        }}
        .val-name {{
            font-size: 0.85rem;
            font-weight: 600;
            color: #334155;
            margin-bottom: 0.25rem;
        }}
        .val-value {{
            font-size: 1.15rem;
            font-weight: 700;
            color: var(--text-main);
            margin-bottom: 0.5rem;
        }}
        .val-footer {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .val-details {{
            font-size: 0.8rem;
            color: var(--text-muted);
        }}
        /* Observations & Warnings */
        .obs-card {{
            border-radius: 10px;
            padding: 1rem 1.25rem;
            margin-bottom: 1rem;
        }}
        .obs-card:last-child {{ margin-bottom: 0; }}
        .obs-warning {{
            background-color: var(--warning-bg);
            border: 1px solid #FDE68A;
        }}
        .obs-observation {{
            background-color: var(--info-bg);
            border: 1px solid #BFDBFE;
        }}
        .obs-header {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 0.35rem;
        }}
        .obs-icon {{
            font-size: 1.1rem;
        }}
        .obs-title {{
            font-weight: 700;
            font-size: 0.95rem;
            color: #1E293B;
            flex-grow: 1;
        }}
        .obs-desc {{
            font-size: 0.9rem;
            color: #334155;
            line-height: 1.5;
        }}
        /* Failure Section */
        .failure-card {{
            border-left: 5px solid var(--danger);
        }}
        .failure-header {{
            background-color: #FEF2F2;
            color: var(--danger);
        }}
        .failure-summary-box {{
            background-color: #FEF2F2;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
            color: #991B1B;
        }}
        .failure-summary-box p {{
            margin-top: 0.25rem;
            font-size: 0.95rem;
            color: #7F1D1D;
        }}
        .failure-screenshot {{
            margin-top: 1.25rem;
            padding-top: 1rem;
            border-top: 1px solid #F1F5F9;
        }}
        .thumb-img {{
            max-width: 100%;
            max-height: 380px;
            border-radius: 8px;
            border: 1px solid var(--border);
            margin-top: 0.5rem;
            display: block;
        }}
        .screenshot-path {{
            margin-top: 0.5rem;
            font-size: 0.8rem;
            color: var(--text-muted);
        }}
        /* Technical Details Collapsible */
        details.tech-details {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            margin-bottom: 1.5rem;
            overflow: hidden;
        }}
        details.tech-details summary {{
            padding: 1rem 1.25rem;
            cursor: pointer;
            font-weight: 600;
            color: var(--text-muted);
            background-color: #F8FAFC;
            user-select: none;
        }}
        details.tech-details summary:hover {{
            background-color: #F1F5F9;
            color: var(--text-main);
        }}
        .tech-content {{
            padding: 1.25rem;
            border-top: 1px solid var(--border);
        }}
        .tech-section {{
            margin-bottom: 1rem;
        }}
        .tech-section h4 {{
            font-size: 0.85rem;
            text-transform: uppercase;
            color: var(--text-muted);
            margin-bottom: 0.35rem;
        }}
        .code-block {{
            background-color: #0F172A;
            color: #E2E8F0;
            padding: 1rem;
            border-radius: 8px;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            font-size: 0.82rem;
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-all;
            max-height: 350px;
        }}
        /* Footer */
        footer {{
            text-align: center;
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-top: 2rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header Banner -->
        <header class="header-banner">
            <div class="header-title-group">
                <h1>{html.escape(rep.test_name)}</h1>
                <div class="header-subtitle">
                    <span>RoadTripTribes Automated Execution Report</span>
                    <span>&bull;</span>
                    <strong>{html.escape(rep.test_id)}</strong>
                </div>
            </div>
            <div>
                <span class="status-badge-lg">{status_icon} {rep.status}</span>
            </div>
        </header>

        <!-- Summary Metrics -->
        <section class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Execution Status</div>
                <div class="metric-value" style="color:{status_color}">{rep.status}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total Duration</div>
                <div class="metric-value">{rep.format_duration()}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Environment</div>
                <div class="metric-value">{html.escape(rep.environment)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Browser</div>
                <div class="metric-value">{html.escape(rep.browser)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Execution Steps</div>
                <div class="metric-value">{len(rep.steps)}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Validations</div>
                <div class="metric-value">{len(rep.validations)}</div>
            </div>
        </section>

        <!-- Failure Details (If Failed) -->
        {failure_html}

        <!-- Test Objective -->
        <section class="card">
            <div class="card-header">
                <span class="header-icon">&#127919;</span>
                <h2>Test Objective</h2>
            </div>
            <div class="card-body">
                <p class="objective-text">{html.escape(rep.objective)}</p>
                <div class="meta-grid">
                    <div class="meta-item"><span class="meta-label">Execution Date:</span> <span class="meta-val">{rep.start_time.strftime('%d %B %Y')}</span></div>
                    <div class="meta-item"><span class="meta-label">Time Window:</span> <span class="meta-val">{rep.start_time.strftime('%I:%M:%S %p')} - {rep.end_time.strftime('%I:%M:%S %p') if rep.end_time else 'In Progress'}</span></div>
                    <div class="meta-item"><span class="meta-label">Test File:</span> <span class="meta-val"><code>{html.escape(rep.test_file or 'N/A')}</code></span></div>
                </div>
            </div>
        </section>

        <!-- Warnings and Observations (If Any) -->
        {f'''
        <section class="card">
            <div class="card-header">
                <span class="header-icon">&#9888;</span>
                <h2>Product Observations & Diagnostic Warnings</h2>
            </div>
            <div class="card-body">
                {observations_html}
            </div>
        </section>
        ''' if obs_cards else ''}

        <!-- Step-by-Step Execution -->
        <section class="card">
            <div class="card-header">
                <span class="header-icon">&#128221;</span>
                <h2>Step-by-Step Execution Timeline</h2>
            </div>
            <div class="card-body" style="padding: 0;">
                <div class="table-responsive">
                    <table class="steps-table">
                        <thead>
                            <tr>
                                <th>Step</th>
                                <th>Action Performed & Description</th>
                                <th>Result</th>
                                <th>Time</th>
                            </tr>
                        </thead>
                        <tbody>
                            {steps_table_html}
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- Key Validations -->
        <section class="card">
            <div class="card-header">
                <span class="header-icon">&#9989;</span>
                <h2>Key Business Validations & Data Persistence</h2>
            </div>
            <div class="card-body">
                <div class="val-grid">
                    {validations_grid_html}
                </div>
            </div>
        </section>

        <!-- Collapsible Technical Details -->
        <details class="tech-details">
            <summary>&#128295; Technical Execution Details & Diagnostics (Expand for Engineers)</summary>
            <div class="tech-content">
                <div class="tech-section">
                    <h4>Environment Details:</h4>
                    <p style="font-size:0.88rem; color:#475569;">
                        <strong>Python:</strong> {html.escape(rep.python_version)} | 
                        <strong>Pytest:</strong> {html.escape(rep.pytest_version)} | 
                        <strong>OS:</strong> {html.escape(rep.os_info)} | 
                        <strong>Mode:</strong> {html.escape(rep.execution_mode)}
                    </p>
                </div>
                {tech_traceback_html}
                {raw_logs_html}
            </div>
        </details>

        <!-- Footer -->
        <footer>
            Generated automatically by <strong>RoadTripTribes Automation Framework</strong> &bull; {datetime.now().strftime('%d %b %Y, %I:%M:%S %p')}
        </footer>
    </div>
</body>
</html>
"""
