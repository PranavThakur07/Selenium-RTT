import logging
import sys
import colorama
from colorama import Fore, Back, Style

# Ensure stdout and stderr use UTF-8 and auto-reset colors on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

colorama.init(autoreset=True)


class ColoredFormatter(logging.Formatter):
    """
    Custom logging formatter producing high-contrast, structured,
    and aesthetic console output across all terminal environments.
    """

    LEVEL_BADGES = {
        logging.DEBUG: f"{Fore.LIGHTBLACK_EX}[DEBUG]{Style.RESET_ALL}",
        logging.INFO: f"{Fore.CYAN}[INFO ]{Style.RESET_ALL}",
        logging.WARNING: f"{Fore.YELLOW}{Style.BRIGHT}[WARN ]{Style.RESET_ALL}",
        logging.ERROR: f"{Fore.RED}{Style.BRIGHT}[ERROR]{Style.RESET_ALL}",
        logging.CRITICAL: f"{Fore.WHITE}{Back.RED}{Style.BRIGHT}[CRIT ]{Style.RESET_ALL}",
    }

    def format(self, record: logging.LogRecord) -> str:
        badge = self.LEVEL_BADGES.get(record.levelno, f"[{record.levelname}]")
        timestamp = f"{Fore.LIGHTBLACK_EX}{self.formatTime(record, '%H:%M:%S')}{Style.RESET_ALL}"
        module_name = f"{Fore.MAGENTA}{Style.BRIGHT}{record.name:<18}{Style.RESET_ALL}"

        raw_msg = record.getMessage()

        # Format message styling contextually
        if raw_msg.startswith("===") or raw_msg.startswith("---"):
            msg = f"{Fore.YELLOW}{Style.BRIGHT}{raw_msg}{Style.RESET_ALL}"
        elif "PASSED" in raw_msg or "successfully" in raw_msg.lower():
            msg = f"{Fore.GREEN}{Style.BRIGHT}{raw_msg}{Style.RESET_ALL}"
        elif "failed" in raw_msg.lower() or "mismatch" in raw_msg.lower() or "exception" in raw_msg.lower():
            msg = f"{Fore.RED}{Style.BRIGHT}{raw_msg}{Style.RESET_ALL}"
        elif raw_msg.startswith("[STEP") or "STEP " in raw_msg:
            msg = f"{Fore.CYAN}{Style.BRIGHT}{raw_msg}{Style.RESET_ALL}"
        elif "selected" in raw_msg.lower() or "setting" in raw_msg.lower() or "clicking" in raw_msg.lower():
            msg = f"{Fore.WHITE}{raw_msg}{Style.RESET_ALL}"
        else:
            msg = f"{Fore.LIGHTWHITE_EX}{raw_msg}{Style.RESET_ALL}"

        return f"{timestamp} | {badge} | {module_name} | {msg}"


def get_logger(name: str = "RTT_Framework") -> logging.Logger:
    """Returns a standardized logger instance with colorized stream output."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        handler.setFormatter(ColoredFormatter(datefmt="%H:%M:%S"))
        logger.addHandler(handler)
        logger.propagate = False
    return logger


def log_test_header(test_id: str, title: str) -> None:
    """Prints a styled test case start banner and syncs with TestReporter if active."""
    bar = "=" * 76
    print(f"\n{Fore.CYAN}{Style.BRIGHT}+{bar}+")
    print(f"|  [*] TEST CASE: {test_id:<10} | {title:<48} |")
    print(f"+{bar}+{Style.RESET_ALL}\n")
    try:
        from utils.reporter import TestReporter
        current_rep = TestReporter.get_current()
        if current_rep:
            current_rep.report.test_id = test_id
            current_rep.report.test_name = title
    except Exception:
        pass


def log_step(step_number: int, step_desc: str) -> None:
    """Prints a styled step divider and records step into TestReporter."""
    step_str = f"STEP {step_number:02d}"
    divider = "-" * max(2, 56 - len(step_desc))
    print(f"\n{Fore.BLUE}{Style.BRIGHT}[>>] {Fore.YELLOW}{step_str}{Fore.BLUE} : {Fore.WHITE}{step_desc} {Fore.BLUE}{divider}{Style.RESET_ALL}")
    try:
        from utils.reporter import TestReporter
        current_rep = TestReporter.get_current()
        if current_rep:
            current_rep.log_step(step_number=step_number, action=step_desc, result="PASS")
    except Exception:
        pass


def log_test_success(test_id: str, message: str) -> None:
    """Prints a styled test case success summary badge."""
    bar = "=" * 76
    print(f"\n{Fore.GREEN}{Style.BRIGHT}+{bar}+")
    print(f"|  [OK] SUCCESS [{test_id}]: {message:<52} |")
    print(f"+{bar}+{Style.RESET_ALL}\n")
    try:
        from utils.reporter import TestReporter
        current_rep = TestReporter.get_current()
        if current_rep:
            current_rep.add_validation(
                category="Final Execution State",
                name="Test Case Result",
                value="PASSED",
                status="VERIFIED",
                details=message
            )
    except Exception:
        pass
