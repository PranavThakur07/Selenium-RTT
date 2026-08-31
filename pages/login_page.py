from typing import Tuple, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from pages.base_page import BasePage
from utils.config import Config
from utils.logger import get_logger

logger = get_logger("LoginPage")


class LoginPage(BasePage):
    """Page Object for RoadTripTribes Login Modal / Page."""

    # Locators (Verified from staging DOM)
    EMAIL_INPUT: Tuple[str, str] = (By.ID, "email")
    PASSWORD_INPUT: Tuple[str, str] = (By.ID, "password")
    SUBMIT_BUTTON: Tuple[str, str] = (By.CSS_SELECTOR, "button.loginModalSubmitBtn, button[type='submit']")
    LOGIN_MODAL: Tuple[str, str] = (By.CSS_SELECTOR, ".login-modal-root.show")
    LOGIN_MODAL_BACKDROP: Tuple[str, str] = (By.CSS_SELECTOR, ".login-modal-backdrop")
    FORM_ERROR: Tuple[str, str] = (By.CSS_SELECTOR, ".loginModalErrorSlot--form")
    FIELD_ERRORS: Tuple[str, str] = (By.CSS_SELECTOR, ".loginModalErrorSlot")
    TOAST_ERROR: Tuple[str, str] = (By.CSS_SELECTOR, ".Toastify__toast--error")
    SWAL_ERROR: Tuple[str, str] = (By.CSS_SELECTOR, ".swal2-error, .swal2-popup")

    def navigate(self) -> "LoginPage":
        """Navigates to the login page with retry."""
        logger.info(f"Opening Login page: {Config.LOGIN_URL}")
        for attempt in range(2):
            try:
                self.open(Config.LOGIN_URL)
                self.wait_until_visible(self.EMAIL_INPUT, timeout=Config.EXPLICIT_TIMEOUT)
                return self
            except Exception as e:
                if attempt == 1:
                    raise
                logger.warning(f"Initial login page navigation attempt failed ({e}), refreshing...")
                time.sleep(2)
        return self

    def enter_email(self, email: str) -> "LoginPage":
        """Enters the user email."""
        logger.info(f"Entering email: {email}")
        self.type_text(self.EMAIL_INPUT, email)
        return self

    def enter_password(self, password: str) -> "LoginPage":
        """Enters the user password."""
        logger.info("Entering password (masked)")
        self.type_text(self.PASSWORD_INPUT, password)
        return self

    def click_sign_in(self) -> None:
        """Clicks the Sign In submit button."""
        logger.info("Clicking 'Sign In' button")
        self.click(self.SUBMIT_BUTTON)

    def login(self, email: Optional[str] = None, password: Optional[str] = None) -> None:
        """
        Executes full login sequence using provided credentials or Config defaults.
        """
        user_email = email or Config.TEST_EMAIL
        user_password = password or Config.TEST_PASSWORD

        if not user_email or not user_password:
            Config.validate_credentials()

        self.enter_email(user_email)
        self.enter_password(user_password)
        self.click_sign_in()
        self.wait_for_login_completion()

    def wait_for_login_completion(self, timeout: Optional[int] = None) -> None:
        """
        Explicitly waits until the login modal closes and user is redirected / authenticated.
        """
        timeout = timeout or Config.EXPLICIT_TIMEOUT
        logger.info("Waiting for login to complete and modal to close...")

        # 1. Check if an error appears immediately
        if self.is_element_visible(self.FORM_ERROR, timeout=1):
            err_msg = self.get_text(self.FORM_ERROR)
            if err_msg:
                raise AssertionError(f"Login failed with form error: '{err_msg}'")

        # 2. Wait for modal to become invisible or URL to change
        self.wait_until_invisible(self.LOGIN_MODAL, timeout=timeout)
        logger.info("Login modal closed successfully.")

    def get_visible_error(self) -> Optional[str]:
        """Returns any visible error message on the login form or toast."""
        for locator in [self.FORM_ERROR, self.TOAST_ERROR, self.SWAL_ERROR]:
            if self.is_element_visible(locator, timeout=1):
                txt = self.get_text(locator)
                if txt:
                    return txt
        return None
