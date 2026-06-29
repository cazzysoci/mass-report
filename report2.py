#!/usr/bin/env python3
"""
Facebook Mass Report Tool — Authorized Penetration Testing
===========================================================
Universal version — works on both desktop (www.facebook.com) and mobile (m.facebook.com).
Auto-detects the Facebook interface variant and uses appropriate selectors.

Capabilities:
  - Single & mass profile reporting (Fake Account / impersonation)
  - Single & mass post reporting (Spam)
  - Cookie-persisted sessions
  - Randomized delays, anti-detection, headless mode
"""

import sys
import os
import json
import random
import time
import re
import logging
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass, field
from urllib.parse import urlparse, parse_qs

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    ElementClickInterceptedException, ElementNotInteractableException,
    StaleElementReferenceException, WebDriverException
)
from selenium.webdriver.remote.webelement import WebElement

try:
    from webdriver_manager.chrome import ChromeDriverManager
    HAS_WDM = True
except ImportError:
    HAS_WDM = False

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class Config:
    email: str = ""
    password: str = ""
    cookie_file: str = "fb_cookies.json"
    headless: bool = False
    min_delay: int = 10
    max_delay: int = 25
    report_count: int = 3
    use_mobile: bool = False  # False = auto-detect, True = force m.facebook.com

    CONFIG_PATH = Path("fb_report_config.json")

    def save(self):
        with open(self.CONFIG_PATH, "w") as f:
            json.dump(self.__dict__, f, indent=2, default=str)

    @classmethod
    def load(cls):
        if cls.CONFIG_PATH.exists():
            try:
                with open(cls.CONFIG_PATH) as f:
                    data = json.load(f)
                return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
            except Exception:
                pass
        return cls()


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s :: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("FBReport")


# ---------------------------------------------------------------------------
# Browser Engine — Universal (Desktop + Mobile)
# ---------------------------------------------------------------------------

class BrowserEngine:
    """
    Chrome WebDriver with anti-detection.
    Uses mobile site (m.facebook.com) when use_mobile=True,
    otherwise desktop site (www.facebook.com) with viewport control.
    """

    DESKTOP_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    ]

    MOBILE_AGENTS = [
        "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.6422.165 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; Pixel 8) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.6478.71 Mobile Safari/537.36",
        "Mozilla/5.0 (iPhone16,2; CPU iPhone OS 18_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
    ]

    def __init__(self, config: Config):
        self.config = config
        self.driver: Optional[webdriver.Chrome] = None
        self.is_mobile = config.use_mobile

    @property
    def base_url(self) -> str:
        return "https://m.facebook.com" if self.is_mobile else "https://www.facebook.com"

    def start(self) -> webdriver.Chrome:
        opts = Options()

        ua = random.choice(self.MOBILE_AGENTS if self.is_mobile else self.DESKTOP_AGENTS)
        opts.add_argument(f"--user-agent={ua}")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-notifications")
        opts.add_argument("--disable-web-security")
        opts.add_argument("--lang=en-US")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2,
        }
        opts.add_experimental_option("prefs", prefs)

        if self.config.headless:
            opts.add_argument("--headless=new")

        if HAS_WDM:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=opts)
        else:
            self.driver = webdriver.Chrome(options=opts)

        # Anti-detection script
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            """
        })

        # Mobile viewport if mobile mode
        if self.is_mobile:
            self.driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
                "width": 375, "height": 812,
                "deviceScaleFactor": 3, "mobile": True
            })

        self.driver.implicitly_wait(5)
        return self.driver

    def stop(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Facebook Session
# ---------------------------------------------------------------------------

class FBSession:
    """Handles login on either mobile or desktop site."""

    def __init__(self, driver: webdriver.Chrome, engine: BrowserEngine, config: Config):
        self.driver = driver
        self.engine = engine
        self.config = config

    def login(self) -> bool:
        log.info(f"Navigating to {self.engine.base_url}/login.php ...")
        self.driver.get(f"{self.engine.base_url}/login.php")
        time.sleep(3)

        try:
            wait = WebDriverWait(self.driver, 20)

            # Desktop uses ID="email", mobile uses name="email"
            email_loc = (By.ID, "email") if not self.engine.is_mobile else (By.NAME, "email")
            email_inp = wait.until(EC.presence_of_element_located(email_loc))
            pass_inp = self.driver.find_element(By.NAME, "pass")

            email_inp.clear()
            email_inp.send_keys(self.config.email)
            pass_inp.clear()
            pass_inp.send_keys(self.config.password)

            # Click login button
            login_btn = self.driver.find_element(By.NAME, "login")
            login_btn.click()
            time.sleep(5)

            # Handle checkpoint
            if "checkpoint" in self.driver.current_url.lower():
                log.warning("Login checkpoint triggered!")
                log.info("Resolve the checkpoint in the browser, then press Enter.")
                input(">>> Press Enter after checkpoint is resolved...")
                time.sleep(3)

            # Verify login success
            if "login" in self.driver.current_url.lower() and "checkpoint" not in self.driver.current_url.lower():
                log.error("Login failed — check credentials.")
                return False

            log.info("Login successful!")
            self._save_cookies()
            return True

        except Exception as e:
            log.error(f"Login error: {e}")
            return False

    def _save_cookies(self):
        cookies = self.driver.get_cookies()
        with open(self.config.cookie_file, "w") as f:
            json.dump(cookies, f, indent=2)
        log.info(f"Saved {len(cookies)} cookies to {self.config.cookie_file}.")

    def load_cookies(self) -> bool:
        cpath = Path(self.config.cookie_file)
        if not cpath.exists():
            return False

        self.driver.get(f"{self.engine.base_url}/")
        with open(cpath) as f:
            cookies = json.load(f)
        for c in cookies:
            try:
                self.driver.add_cookie(c)
            except Exception:
                pass

        self.driver.get(f"{self.engine.base_url}/")
        time.sleep(3)

        if "login" in self.driver.current_url.lower():
            log.warning("Cookies expired.")
            return False

        log.info("Session restored from cookies.")
        return True


# ---------------------------------------------------------------------------
# Universal Click Helpers
# ---------------------------------------------------------------------------

class ClickHelper:
    """
    Multi-strategy click engine.
    Tries desktop selectors first, falls back to mobile, then generic.
    """

    def __init__(self, driver: webdriver.Chrome, is_mobile: bool):
        self.driver = driver
        self.is_mobile = is_mobile

    def wait_and_click(self, locators: List[Tuple[str, str]], timeout: int = 10, click: bool = True) -> Optional[WebElement]:
        """
        Try multiple locator tuples in order. Returns the element if found.
        """
        for by, selector in locators:
            try:
                el = WebDriverWait(self.driver, timeout // len(locators) + 1).until(
                    EC.element_to_be_clickable((by, selector))
                )
                if click:
                    # Scroll into view first
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
                    time.sleep(0.5)
                    el.click()
                return el
            except (TimeoutException, NoSuchElementException,
                    ElementClickInterceptedException, StaleElementReferenceException):
                continue
        return None

    def find_and_click(self, locators: List[Tuple[str, str]], timeout: int = 5) -> bool:
        """Lightweight version — returns bool."""
        return self.wait_and_click(locators, timeout=timeout) is not None

    def text_click(self, texts: List[str], tag: str = "span") -> bool:
        """Click element containing visible text."""
        for text in texts:
            try:
                xp = f"//{tag}[contains(text(), '{text}')]"
                el = WebDriverWait(self.driver, 3).until(EC.element_to_be_clickable((By.XPATH, xp)))
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
                time.sleep(0.3)
                el.click()
                return True
            except Exception:
                continue
        return False


# ---------------------------------------------------------------------------
# Universal Reporter — Works on Both Desktop & Mobile
# ---------------------------------------------------------------------------

class FBReporter:
    """
    Unified reporting engine.
    Uses an extensive selector database covering both www.facebook.com (desktop)
    and m.facebook.com (mobile), plus multiple language variants.
    """

    def __init__(self, driver: webdriver.Chrome, engine: BrowserEngine):
        self.driver = driver
        self.engine = engine
        self.click = ClickHelper(driver, engine.is_mobile)

    def _random_sleep(self, lo: int = None, hi: int = None):
        if lo is None:
            lo = 8
        if hi is None:
            hi = 22
        delay = random.randint(lo, hi)
        log.info(f"Waiting {delay}s...")
        time.sleep(delay)

    def _extract_profile_id(self, url_or_id: str) -> str:
        """Extract numeric profile ID from URL or return raw ID."""
        # Already numeric
        if url_or_id.isdigit():
            return url_or_id
        # Try to parse from URL
        parsed = urlparse(url_or_id)
        if 'profile.php' in parsed.path:
            return parse_qs(parsed.query).get('id', [None])[0] or url_or_id
        # Try /username or /id/NNNNN
        match = re.search(r'/id[=/](\d+)', url_or_id)
        if match:
            return match.group(1)
        # Try numeric path segment
        match = re.search(r'/(\d{8,})', url_or_id)
        if match:
            return match.group(1)
        return url_or_id

    # ------------------------------------------------------------------
    # "More" / Options Button — Desktop & Mobile
    # ------------------------------------------------------------------

    def _click_more_button(self) -> bool:
        """Universal More/Options button clicker."""
        # Desktop: aria-label variants
        desktop = [
            (By.XPATH, "//div[@aria-label='More options']"),
            (By.XPATH, "//div[@aria-label='Actions for this post']"),
            (By.XPATH, "//div[@aria-label='Profile options']"),
            (By.XPATH, "//div[@role='button']//span[contains(text(),'More')]"),
            (By.XPATH, "//div[@aria-label='More']"),
        ]
        # Mobile: text links
        mobile = [
            (By.XPATH, "//a[text()='More']"),
            (By.XPATH, "//a[contains(text(),'More')]"),
            (By.XPATH, "//a[text()='Lainnya']"),
            (By.XPATH, "//a[contains(text(),'Lainnya')]"),
        ]
        # Generic role=button with dots icon
        generic = [
            (By.XPATH, "(//div[@role='button' and contains(@class,'x1i10hfl')])[1]"),
            (By.XPATH, "(//div[contains(@data-visualcompletion,'ignore') and @role='button'])[1]"),
        ]

        return (
            self.click.find_and_click(desktop, timeout=5) or
            self.click.find_and_click(mobile, timeout=3) or
            self.click.find_and_click(generic, timeout=3)
        )

    # ------------------------------------------------------------------
    # "Find support or report profile" / "Find support or report Page"
    # ------------------------------------------------------------------

    def _click_report_profile_option(self) -> bool:
        """Open the report dialog from the More menu."""
        locators = [
            # Desktop (English)
            (By.XPATH, "//span[contains(text(),'Find support or report')]"),
            # Desktop (Indonesian)
            (By.XPATH, "//span[contains(text(),'Cari dukungan atau laporkan')]"),
            # Desktop / generic a tag
            (By.XPATH, "//a[contains(text(),'Find support')]"),
            (By.XPATH, "//a[contains(text(),'report profile')]"),
            (By.XPATH, "//a[contains(text(),'report Page')]"),
            # Mobile
            (By.XPATH, "//a[contains(text(),'Cari dukungan atau laporkan profil')]"),
            (By.XPATH, "//a[contains(text(),'Laporkan profil')]"),
            # Generic href match
            (By.XPATH, "//a[contains(@href,'/help/contact/') and contains(text(),'report')]"),
            (By.XPATH, "//a[contains(@href,'/help/contact/') and contains(text(),'laporkan')]"),
        ]
        return self.click.find_and_click(locators, timeout=8)

    # ------------------------------------------------------------------
    # "Report Post" option
    # ------------------------------------------------------------------

    def _click_report_post_option(self) -> bool:
        locators = [
            (By.XPATH, "//input[@value='RESOLVE_PROBLEM']"),
            (By.XPATH, "//a[contains(text(),'Report post')]"),
            (By.XPATH, "//a[contains(text(),'Laporkan postingan')]"),
            (By.XPATH, "//div[contains(text(),'Report post')]"),
            (By.XPATH, "//div[contains(text(),'Laporkan')]"),
            (By.XPATH, "//span[contains(text(),'Report post')]"),
            (By.XPATH, "//span[contains(text(),'Laporkan')]"),
        ]
        return self.click.find_and_click(locators, timeout=6)

    # ------------------------------------------------------------------
    # Reason Selection
    # ------------------------------------------------------------------

    def _select_fake_account_reason(self) -> bool:
        """Select 'Fake Account' as the report reason."""
        locators = [
            (By.XPATH, "//span[text()='Fake Account']"),
            (By.XPATH, "//span[text()='Akun Palsu']"),
            (By.XPATH, "//span[contains(text(),'Fake')]"),
            (By.XPATH, "//span[contains(text(),'Palsu')]"),
            (By.XPATH, "//div[contains(text(),'Fake Account')]"),
            (By.XPATH, "//input[@value='FAKE_ACCOUNT']/following-sibling::span"),
            (By.XPATH, "//span[text()='Pretending to be someone']"),
            (By.XPATH, "//span[text()='Berpura-pura menjadi seseorang']"),
        ]
        return self.click.find_and_click(locators, timeout=5)

    def _select_spam_reason(self) -> bool:
        """Select 'Spam' as the report reason for posts."""
        locators = [
            (By.XPATH, "//input[@type='radio' and @value='spam']"),
            (By.XPATH, "//input[@type='radio' and contains(@value,'SPAM')]"),
            (By.XPATH, "//input[@type='radio' and contains(@value,'spam')]"),
            (By.XPATH, "//span[contains(text(),'Spam')]/preceding-sibling::input[@type='radio']"),
            (By.XPATH, "//div[contains(text(),'Spam')]/preceding-sibling::input"),
            (By.XPATH, "//span[contains(text(),'Spam')]"),
        ]
        return self.click.find_and_click(locators, timeout=4)

    def _select_impersonation_target(self) -> bool:
        """Select 'Me' (or equivalent) when asked who's being impersonated."""
        locators = [
            (By.XPATH, "//span[text()='Me']"),
            (By.XPATH, "//span[text()='Saya']"),
            (By.XPATH, "//span[contains(text(),'Me') and not(contains(text(),'Message'))]"),
            (By.XPATH, "//div[contains(text(),'Me')]"),
        ]
        return self.click.find_and_click(locators, timeout=4)

    # ------------------------------------------------------------------
    # Submit / Confirm
    # ------------------------------------------------------------------

    def _submit(self) -> bool:
        """Click the submit button wherever it appears."""
        locators = [
            (By.XPATH, "//div[@role='button' and contains(text(),'Submit')]"),
            (By.XPATH, "//div[@role='button' and contains(text(),'Kirim')]"),
            (By.XPATH, "//input[@type='submit' and @name='action']"),
            (By.XPATH, "//input[@type='submit']"),
            (By.XPATH, "//button[@type='submit']"),
            (By.XPATH, "//div[@role='button']//span[text()='Submit']"),
            (By.XPATH, "//div[@role='button']//span[text()='Kirim']"),
        ]
        return self.click.find_and_click(locators, timeout=5)

    def _check_confirm_checkbox(self) -> bool:
        """Check the 'I confirm' checkbox if present."""
        locators = [
            (By.XPATH, "//input[@type='checkbox' and @name='checked']"),
            (By.XPATH, "//input[@type='checkbox' and contains(@aria-label,'confirm')]"),
            (By.XPATH, "//input[@type='checkbox' and contains(@aria-label,'Confirm')]"),
        ]
        el = self.click.wait_and_click(locators, timeout=3)
        if el:
            time.sleep(0.5)
            return True
        return False

    # ------------------------------------------------------------------
    # Profile Report — Full Flow
    # ------------------------------------------------------------------

    def report_profile(self, profile_url_or_id: str) -> Tuple[bool, str]:
        """
        Report a profile as fake/impersonation.
        Works on both desktop and mobile sites.
        """
        profile_id = self._extract_profile_id(profile_url_or_id)
        url = f"{self.engine.base_url}/profile.php?id={profile_id}"
        log.info(f"Navigating to profile: {url}")
        self.driver.get(url)
        time.sleep(4)

        # Check profile loaded
        page_lower = self.driver.page_source.lower()
        if "this page isn't available" in page_lower or "content not found" in page_lower:
            return False, "Profile not found or inaccessible."

        log.info("Clicking 'More' button...")
        if not self._click_more_button():
            return False, "Could not find 'More' button on profile."

        time.sleep(2)
        log.info("Opening report dialog...")
        if not self._click_report_profile_option():
            return False, "Could not find 'Find support or report profile' option."

        time.sleep(2)
        log.info("Selecting 'Fake Account' reason...")
        if not self._select_fake_account_reason():
            # Try impersonation sub-flow
            log.info("Trying 'Pretending to be someone' flow...")
            if not self.click.text_click(["Pretending to be someone", "Berpura-pura"], tag="span"):
                return False, "Could not select report reason."
            time.sleep(1.5)
            if not self._select_impersonation_target():
                log.info("No impersonation target selection needed.")

        time.sleep(1.5)
        log.info("Submitting report...")
        if not self._submit():
            return False, "First submit failed."

        time.sleep(2)
        # Check for confirmation checkbox
        self._check_confirm_checkbox()
        time.sleep(1)

        # Final submit
        if not self._submit():
            log.info("No second submit needed (report may have been accepted on first).")

        # Check for success indicators
        page_source = self.driver.page_source.lower()
        if "thank you" in page_source or "terima kasih" in page_source or "report sent" in page_source:
            return True, "Profile reported successfully."
        if "confirm" in page_source:
            # Still on confirmation = something failed
            return False, "Stuck on confirmation screen."

        return True, "Report submitted (check UI for confirmation)."

    # ------------------------------------------------------------------
    # Post Report — Full Flow
    # ------------------------------------------------------------------

    def report_post(self, post_url: str) -> Tuple[bool, str]:
        """
        Report a post as spam.
        Works on both desktop and mobile sites.
        """
        log.info(f"Navigating to post: {post_url}")
        self.driver.get(post_url)
        time.sleep(4)

        # Check post loaded
        page_lower = self.driver.page_source.lower()
        if "this content isn't available" in page_lower or "not found" in page_lower:
            return False, "Post not found or inaccessible."

        log.info("Clicking 'More' button on post...")
        if not self._click_more_button():
            return False, "Could not find 'More' button on post."

        time.sleep(2)
        log.info("Opening post report dialog...")
        if not self._click_report_post_option():
            return False, "Could not find 'Report post' option."

        time.sleep(2)
        log.info("Selecting 'Spam' reason...")
        if not self._select_spam_reason():
            # Try clicking any visible radio option
            log.info("Trying alternative reason selection...")
            try:
                radios = self.driver.find_elements(By.XPATH, "//input[@type='radio']")
                for radio in radios:
                    if 'spam' in (radio.get_attribute('value') or '').lower():
                        self.driver.execute_script("arguments[0].click();", radio)
                        time.sleep(0.5)
                        break
                else:
                    return False, "Could not select spam reason."
            except Exception:
                return False, "Could not select spam reason."

        time.sleep(1.5)
        log.info("Submitting post report...")
        if not self._submit():
            return False, "First submit failed."

        time.sleep(2)
        self._check_confirm_checkbox()
        time.sleep(1)

        if not self._submit():
            pass  # Might have gone through already

        return True, "Post reported as spam."

    # ------------------------------------------------------------------
    # Mass Reporting
    # ------------------------------------------------------------------

    def mass_report_profiles(
        self,
        targets: List[str],
        count_per: int = 3,
        delay_range: Tuple[int, int] = (12, 30),
    ) -> Dict[str, Tuple[int, int]]:
        results = {}
        for target in targets:
            successes, failures = 0, 0
            for i in range(count_per):
                log.info(f"[{target}] Report iteration {i+1}/{count_per}")
                ok, msg = self.report_profile(target)
                if ok:
                    successes += 1
                    log.info(f"  -> SUCCESS: {msg}")
                else:
                    failures += 1
                    log.warning(f"  -> FAILED: {msg}")
                if i + 1 < count_per:
                    delay = random.randint(*delay_range)
                    log.info(f"  Pausing {delay}s...")
                    time.sleep(delay)
            results[target] = (successes, failures)
        return results

    def mass_report_posts(
        self,
        targets: List[str],
        count_per: int = 3,
        delay_range: Tuple[int, int] = (10, 25),
    ) -> Dict[str, Tuple[int, int]]:
        results = {}
        for url in targets:
            successes, failures = 0, 0
            for i in range(count_per):
                log.info(f"[{url[:50]}...] Iteration {i+1}/{count_per}")
                ok, msg = self.report_post(url)
                if ok:
                    successes += 1
                    log.info(f"  -> SUCCESS: {msg}")
                else:
                    failures += 1
                    log.warning(f"  -> FAILED: {msg}")
                if i + 1 < count_per:
                    delay = random.randint(*delay_range)
                    log.info(f"  Pausing {delay}s...")
                    time.sleep(delay)
            results[url] = (successes, failures)
        return results


# ---------------------------------------------------------------------------
# CLI Interface
# ---------------------------------------------------------------------------

def print_banner():
    banner = r"""
╔══════════════════════════════════════════════════════════════════╗
║          Facebook Mass Report Tool  v3.0  (Desktop + Mobile)    ║
║          Authorized Penetration Testing — Platform Verified      ║
╚══════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def interactive_menu(config: Config) -> int:
    print("""
    ┌──────────────────────────────────────────────────────┐
    │  1. Login / Re-authenticate                         │
    │  2. Report a SINGLE profile                         │
    │  3. Report a SINGLE post                            │
    │  4. Mass-report PROFILES (bulk)                     │
    │  5. Mass-report POSTS (bulk)                        │
    │  6. Toggle site mode  (currently: {mode:<8})    │
    │  7. Configure settings                              │
    │  8. Exit                                            │
    └──────────────────────────────────────────────────────┘
    """.format(mode="MOBILE" if config.use_mobile else "DESKTOP/AUTO"))
    try:
        return int(input("Select option: ").strip())
    except (ValueError, EOFError):
        return 8


def configure_settings(config: Config) -> Config:
    print("\n--- Current Configuration ---")
    print(f"  Email     : {config.email or '(not set)'}")
    print(f"  Headless  : {config.headless}")
    print(f"  Site mode : {'Mobile (m.facebook.com)' if config.use_mobile else 'Desktop (www.facebook.com)'}")
    print(f"  Min delay : {config.min_delay}s")
    print(f"  Max delay : {config.max_delay}s")
    print(f"  Cookie    : {config.cookie_file}")
    print("-----------------------------")

    email = input(f"Email [{config.email}]: ").strip() or config.email
    pw = input("Password (blank to keep): ").strip()
    headless_in = input(f"Headless? ({config.headless}) [y/N]: ").strip().lower()
    mobile_in = input(f"Force mobile site? ({config.use_mobile}) [y/N]: ").strip().lower()

    config.email = email
    if pw:
        config.password = pw
    config.headless = headless_in == 'y'
    if mobile_in in ('y', 'n'):
        config.use_mobile = mobile_in == 'y'

    config.save()
    log.info("Configuration saved.")
    return config


def main():
    print_banner()
    config = Config.load()

    engine = BrowserEngine(config)
    try:
        driver = engine.start()
    except Exception as e:
        log.error(f"Failed to start browser: {e}")
        log.info("Make sure Chrome is installed. Try: pip install webdriver-manager")
        sys.exit(1)

    session = FBSession(driver, engine, config)
    reporter = FBReporter(driver, engine)

    # Try cookie session restoration
    if not session.load_cookies():
        if config.email and config.password:
            log.info("Attempting credential login...")
            if not session.login():
                log.warning("Login failed. Use option 1 to try again.")
        else:
            log.warning("No credentials configured. Use option 1 to login.")
    else:
        log.info("Session active.")

    while True:
        option = interactive_menu(config)

        if option == 1:
            email = input("Email/Phone: ").strip()
            password = input("Password: ").strip()
            if email:
                config.email = email
            if password:
                config.password = password
            config.save()
            if session.login():
                log.info("Authenticated successfully.")
            else:
                log.error("Authentication failed.")

        elif option == 2:
            target = input("Profile URL or ID: ").strip()
            if not target:
                continue
            ok, msg = reporter.report_profile(target)
            log.info(f"Result: {'✓' if ok else '✗'} — {msg}")

        elif option == 3:
            url = input("Post URL: ").strip()
            if not url:
                continue
            ok, msg = reporter.report_post(url)
            log.info(f"Result: {'✓' if ok else '✗'} — {msg}")

        elif option == 4:
            raw = input("Profile IDs/URLs (comma-separated): ").strip()
            if not raw:
                continue
            targets = [x.strip() for x in raw.split(",") if x.strip()]
            count = int(input(f"Reports per profile [{config.report_count}]: ").strip() or config.report_count)
            config.report_count = count
            log.info(f"Mass-reporting {len(targets)} profiles, {count}x each...")
            results = reporter.mass_report_profiles(targets, count)
            log.info(f"Results: {json.dumps(results, indent=2)}")

        elif option == 5:
            raw = input("Post URLs (comma-separated): ").strip()
            if not raw:
                continue
            targets = [x.strip() for x in raw.split(",") if x.strip()]
            count = int(input(f"Reports per post [{config.report_count}]: ").strip() or config.report_count)
            config.report_count = count
            log.info(f"Mass-reporting {len(targets)} posts, {count}x each...")
            results = reporter.mass_report_posts(targets, count)
            log.info(f"Results: {json.dumps(results, indent=2)}")

        elif option == 6:
            config.use_mobile = not config.use_mobile
            engine.is_mobile = config.use_mobile
            reporter.engine.is_mobile = config.use_mobile
            reporter.click.is_mobile = config.use_mobile
            # Restart driver with new mode
            log.info(f"Switched to {'MOBILE' if config.use_mobile else 'DESKTOP'} mode.")
            log.info("Restarting browser with new settings...")
            engine.stop()
            try:
                driver = engine.start()
                session.driver = driver
                reporter.driver = driver
                reporter.click = ClickHelper(driver, engine.is_mobile)
                session.load_cookies()  # Try to restore session
                log.info("Browser restarted.")
            except Exception as e:
                log.error(f"Restart failed: {e}")
                break

        elif option == 7:
            config = configure_settings(config)
            engine.config = config
            session.config = config

        elif option == 8:
            log.info("Exiting.")
            break

        else:
            log.warning("Invalid option.")

    engine.stop()


if __name__ == "__main__":
    main()
