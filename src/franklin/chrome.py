import shutil
import os
import platform
import time

def is_chrome_installed():
    system = platform.system()

    # Try known executable names and paths
    candidates = {
        "Windows": [
            "chrome.exe",
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        ],
        "Darwin": [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        ],
        "Linux": [
            "google-chrome",
            "google-chrome-stable",
            "chromium-browser",
            "chromium",
        ]
    }

    for path in candidates.get(system, []):
        if shutil.which(path) or os.path.exists(path):
            return True

    return False


from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchWindowException
from selenium.webdriver.chrome.options import Options


def wait_for_chrome(token_url: str) -> None:
    options = Options()
    options.add_argument("--disable-infobars")  # suppresses the "Chrome is being controlled..." message
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # Set up the WebDriver with the correct version of ChromeDriver
    driver = webdriver.Chrome(
        service=ChromeService(
            ChromeDriverManager().install()
            ),
            options=options
        )
    # Open the Jupyter Notebook in the Chrome controlled by Selenium
    driver.get(token_url)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """
    })
    shutdown = False
    try:
        # Wait until the Jupyter main page loads
        WebDriverWait(driver, 60).until(
            # EC.presence_of_element_located((By.CLASS_NAME, "jp-Notebook"))
            lambda d: shutdown or d.current_url and "lab/tree" in d.current_url       
            )
        # Polling loop to detect when the tab is closed
        while True:
            if len(driver.window_handles) == 0:
                break
            time.sleep(1)

    except NoSuchWindowException as e:
        pass
    finally:
        # Close the browser if it's still open
        try:
            driver.quit()
        except NoSuchWindowException:
            pass
