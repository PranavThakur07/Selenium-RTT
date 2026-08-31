from typing import List, Tuple, Optional, Callable, Any
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
    ElementClickInterceptedException
)
from utils.config import Config
from utils.logger import get_logger

logger = get_logger("BasePage")


class BasePage:
    """Base class for all Page Objects providing explicit wait abstractions and interactions."""

    def __init__(self, driver: WebDriver, timeout: int = Config.EXPLICIT_TIMEOUT) -> None:
        self.driver = driver
        self.timeout = timeout
        self.wait = WebDriverWait(
            self.driver,
            self.timeout,
            poll_frequency=0.5,
            ignored_exceptions=[NoSuchElementException, StaleElementReferenceException]
        )

    def open(self, url: str) -> None:
        """Navigates to the specified URL."""
        logger.info(f"Navigating to URL: {url}")
        self.driver.get(url)

    def find(self, locator: Tuple[str, str], timeout: Optional[int] = None) -> WebElement:
        """Waits for an element to be present in the DOM and returns it."""
        wait = self._get_wait(timeout)
        try:
            return wait.until(EC.presence_of_element_located(locator))
        except TimeoutException:
            logger.error(f"Element not present within {timeout or self.timeout}s: {locator}")
            raise

    def wait_until_present(self, locator: Tuple[str, str], timeout: Optional[int] = None) -> WebElement:
        """Waits until the element is present in the DOM and returns it."""
        return self.find(locator, timeout=timeout)

    def find_all(self, locator: Tuple[str, str], timeout: Optional[int] = None) -> List[WebElement]:
        """Waits for at least one element to be present and returns all matching elements."""
        wait = self._get_wait(timeout)
        try:
            return wait.until(EC.presence_of_all_elements_located(locator))
        except TimeoutException:
            return []

    def wait_until_visible(self, locator: Tuple[str, str], timeout: Optional[int] = None) -> WebElement:
        """Waits until the element is visible on the page."""
        wait = self._get_wait(timeout)
        try:
            return wait.until(EC.visibility_of_element_located(locator))
        except TimeoutException:
            logger.error(f"Element not visible within {timeout or self.timeout}s: {locator}")
            raise

    def wait_until_invisible(self, locator: Tuple[str, str], timeout: Optional[int] = None) -> bool:
        """Waits until the element is not visible or removed from DOM."""
        wait = self._get_wait(timeout)
        try:
            return wait.until(EC.invisibility_of_element_located(locator))
        except TimeoutException:
            logger.error(f"Element did not disappear within {timeout or self.timeout}s: {locator}")
            return False

    def wait_until_clickable(self, locator: Tuple[str, str], timeout: Optional[int] = None) -> WebElement:
        """Waits until the element is clickable."""
        wait = self._get_wait(timeout)
        try:
            return wait.until(EC.element_to_be_clickable(locator))
        except TimeoutException:
            logger.error(f"Element not clickable within {timeout or self.timeout}s: {locator}")
            raise

    def click(self, locator: Tuple[str, str], timeout: Optional[int] = None) -> None:
        """Clicks an element with retry on click interception."""
        element = self.wait_until_clickable(locator, timeout)
        try:
            element.click()
        except ElementClickInterceptedException:
            logger.warning(f"Click intercepted on {locator}, retrying with JavaScript click.")
            self.execute_script("arguments[0].click();", element)

    def type_text(self, locator: Tuple[str, str], text: str, timeout: Optional[int] = None, clear: bool = True) -> None:
        """Enters text into an input field with optional clearing."""
        element = self.wait_until_visible(locator, timeout)
        if clear:
            element.clear()
        element.send_keys(text)

    def get_text(self, locator: Tuple[str, str], timeout: Optional[int] = None) -> str:
        """Returns the inner text of an element."""
        element = self.wait_until_visible(locator, timeout)
        return element.text.strip()

    def get_attribute(self, locator: Tuple[str, str], attribute: str, timeout: Optional[int] = None) -> Optional[str]:
        """Returns the specified attribute value of an element."""
        element = self.find(locator, timeout)
        return element.get_attribute(attribute)

    def is_element_present(self, locator: Tuple[str, str], timeout: int = 2) -> bool:
        """Checks if an element exists within a short timeout."""
        try:
            self._get_wait(timeout).until(EC.presence_of_element_located(locator))
            return True
        except TimeoutException:
            return False

    def is_element_visible(self, locator: Tuple[str, str], timeout: int = 2) -> bool:
        """Checks if an element is visible within a short timeout."""
        try:
            self._get_wait(timeout).until(EC.visibility_of_element_located(locator))
            return True
        except TimeoutException:
            return False

    def wait_for_condition(self, condition_func: Callable[[WebDriver], Any], timeout: Optional[int] = None, message: str = "") -> Any:
        """Waits for a custom callable condition returning truthy value."""
        wait = self._get_wait(timeout)
        return wait.until(condition_func, message=message)

    def execute_script(self, script: str, *args) -> Any:
        """Executes JavaScript in the browser context."""
        return self.driver.execute_script(script, *args)

    def scroll_into_view(self, locator: Tuple[str, str]) -> None:
        """Scrolls the element into view."""
        element = self.find(locator)
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)

    def _get_wait(self, timeout: Optional[int]) -> WebDriverWait:
        """Helper to create a WebDriverWait if a custom timeout is passed."""
        if timeout is None or timeout == self.timeout:
            return self.wait
        return WebDriverWait(
            self.driver,
            timeout,
            poll_frequency=0.5,
            ignored_exceptions=[NoSuchElementException, StaleElementReferenceException]
        )
