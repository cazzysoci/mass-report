#!/usr/bin/env python3
"""
Facebook Mass Report Tool v5.0 — Stealth Edition
Features:
  - undetected_chromedriver or selenium-stealth integration
  - Rotating User-Agents via fake_useragent
  - Human-like mouse movements via HumanCursor/ActionChains
  - Request header interception via CDP
  - Realistic typing and click patterns
"""

import sys, os, json, random, time, re, logging
from pathlib import Path
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs

# ── Stealth imports ──────────────────────────────────────────────
try:
    import undetected_chromedriver as uc
    HAS_UC = True
except ImportError:
    HAS_UC = False

try:
    from selenium_stealth import stealth
    HAS_STEALTH = True
except ImportError:
    HAS_STEALTH = False

try:
    from fake_useragent import UserAgent as FakeUA
    HAS_FAKE_UA = True
except ImportError:
    HAS_FAKE_UA = False

try:
    from humancursor import WebCursor
    HAS_HUMAN_CURSOR = True
except ImportError:
    HAS_HUMAN_CURSOR = False

# ── Standard Selenium ────────────────────────────────────────────
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException,
    ElementClickInterceptedException, StaleElementReferenceException
)

try:
    from webdriver_manager.chrome import ChromeDriverManager
    HAS_WDM = True
except ImportError:
    HAS_WDM = False


# ═══════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ═══════════════════════════════════════════════════════════════════

@dataclass
class Config:
    email: str = ""
    password: str = ""
    cookie_file: str = "fb_cookies.json"
    headless: bool = False
    report_count: int = 3
    use_undetected: bool = True
    rotate_ua: bool = True
    human_mouse: bool = True
    min_delay: float = 1.5
    max_delay: float = 4.0
    CONFIG_PATH = Path("fb_report_config.json")

    def save(self):
        with open(self.CONFIG_PATH, "w") as f:
            json.dump(self.__dict__, f, indent=2, default=str)

    @classmethod
    def load(cls):
        if cls.CONFIG_PATH.exists():
            try:
                with open(cls.CONFIG_PATH) as f:
                    return cls(**{k: v for k, v in json.load(f).items()
                                  if k in cls.__dataclass_fields__})
            except:
                pass
        return cls()


logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s :: %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("FBReport")


# ═══════════════════════════════════════════════════════════════════
#  STEALTH HELPERS
# ═══════════════════════════════════════════════════════════════════

class StealthManager:
    """Manages rotating user agents, CDP header overrides, and stealth patches."""

    DEFAULT_UA_LIST = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    ]

    def __init__(self, rotate_ua: bool = True):
        self.rotate_ua = rotate_ua
        self._current_ua = None
        self._fake_ua = None

        if HAS_FAKE_UA and rotate_ua:
            try:
                self._fake_ua = FakeUA(
                    browsers=['chrome'],
                    os=['Windows', 'Mac OS X'],
                    platforms=['pc']
                )
                log.info("fake_useragent initialized for UA rotation")
            except Exception as e:
                log.warning(f"fake_useragent init failed: {e}")
                self._fake_ua = None

    def get_random_ua(self) -> str:
        """Return a random modern Chrome UA string."""
        if self._fake_ua:
            try:
                ua = self._fake_ua.random
                if 'chrome' in ua.lower():
                    self._current_ua = ua
                    return ua
            except:
                pass
        self._current_ua = random.choice(self.DEFAULT_UA_LIST)
        return self._current_ua

    @property
    def current_ua(self) -> str:
        return self._current_ua or self.get_random_ua()

    def get_accept_language(self) -> str:
        """Return a randomized Accept-Language header."""
        langs = [
            "en-US,en;q=0.9",
            "en-US,en;q=0.9,es;q=0.8",
            "en-GB,en;q=0.9,en-US;q=0.8",
            "en-US,en;q=0.9,fr;q=0.8",
            "en-US,en;q=0.9,de;q=0.8",
        ]
        return random.choice(langs)

    def apply_stealth(self, driver):
        """Apply selenium-stealth patches if available."""
        if HAS_STEALTH:
            try:
                stealth(
                    driver,
                    languages=[self.get_accept_language().split(",")[0]],
                    vendor="Google Inc.",
                    platform="Win32",
                    webgl_vendor="Intel Inc.",
                    renderer="Intel Iris OpenGL Engine",
                    fix_hairline=True,
                    run_on_insecure_origins=True,
                )
                log.info("selenium-stealth patches applied")
            except Exception as e:
                log.warning(f"selenium-stealth apply failed: {e}")

    def override_headers(self, driver):
        """Use CDP to override UA and other headers for all requests."""
        ua = self.current_ua
        lang = self.get_accept_language()
        try:
            driver.execute_cdp_cmd("Network.setUserAgentOverride", {
                "userAgent": ua,
                "acceptLanguage": lang,
                "platform": "Win32",
            })
            log.info(f"CDP headers overridden: UA={ua[:50]}..., Lang={lang}")
        except Exception as e:
            log.warning(f"CDP header override failed: {e}")

    def rotate_headers(self, driver):
        """Call this before each navigation to rotate headers."""
        if self.rotate_ua:
            self.override_headers(driver)


# ═══════════════════════════════════════════════════════════════════
#  HUMAN-LIKE INTERACTION HELPERS
# ═══════════════════════════════════════════════════════════════════

class HumanActions:
    """Human-like mouse movements, typing, and scrolling."""

    def __init__(self, driver):
        self.driver = driver
        self.actions = ActionChains(driver)
        if HAS_HUMAN_CURSOR:
            try:
                self.hcursor = WebCursor(driver)
                log.info("HumanCursor initialized")
            except:
                self.hcursor = None
        else:
            self.hcursor = None

    def random_delay(self, min_s: float = 0.8, max_s: float = 2.5):
        """Sleep a random amount mimicking human hesitation."""
        time.sleep(random.uniform(min_s, max_s))

    def move_to_element_human(self, element) -> bool:
        """
        Move cursor to element with human-like trajectory.
        Uses HumanCursor if available, otherwise ActionChains with jitter.
        """
        try:
            if self.hcursor:
                self.hcursor.move_to(element)
                self.random_delay(0.1, 0.3)
                return True
            else:
                # Fallback: ActionChains with slight jitter
                self.actions = ActionChains(self.driver)
                self.actions.move_to_element(element)
                self.actions.perform()
                # Small jitter to look natural
                for _ in range(random.randint(1, 3)):
                    ox = random.randint(-3, 3)
                    oy = random.randint(-3, 3)
                    self.actions = ActionChains(self.driver)
                    self.actions.move_by_offset(ox, oy)
                    self.actions.perform()
                    time.sleep(random.uniform(0.05, 0.15))
                return True
        except Exception as e:
            log.warning(f"Human move failed: {e}")
            return False

    def click_human(self, element) -> bool:
        """Click an element with human-like hover + pause + click."""
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});",
                element
            )
            time.sleep(random.uniform(0.3, 0.8))
            self.move_to_element_human(element)
            self.random_delay(0.15, 0.5)
            self.actions = ActionChains(self.driver)
            self.actions.click(element)
            self.actions.perform()
            return True
        except Exception as e:
            log.warning(f"Human click failed: {e}")
            return False

    def type_human(self, element, text: str):
        """Type text character by character with variable delays."""
        element.click()
        element.clear()
        time.sleep(random.uniform(0.2, 0.5))
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(0.02, 0.15))
            # Occasionally pause longer (mimics thinking)
            if random.random() < 0.05:
                time.sleep(random.uniform(0.3, 0.8))

    def scroll_random(self):
        """Perform a small random scroll to mimic human browsing."""
        try:
            scroll_by = random.randint(-300, 300)
            self.driver.execute_script(f"window.scrollBy(0, {scroll_by});")
            self.random_delay(0.3, 0.8)
        except:
            pass

    def random_page_interaction(self):
        """Random mouse movement + scroll to look human before actions."""
        try:
            self.scroll_random()
            # Move to a random position on the page
            body = self.driver.find_element(By.TAG_NAME, "body")
            size = body.size
            if self.hcursor:
                target_x = random.randint(50, size.get('width', 1200) - 50)
                target_y = random.randint(50, size.get('height', 800) - 50)
                self.hcursor.move_to_coordinates((target_x, target_y))
            self.random_delay(0.2, 0.6)
        except:
            pass


# ═══════════════════════════════════════════════════════════════════
#  BROWSER (now with stealth)
# ═══════════════════════════════════════════════════════════════════

class Browser:
    def __init__(self, headless=False, use_undetected=True, stealth_mgr: StealthManager = None):
        self.headless = headless
        self.use_undetected = use_undetected and HAS_UC
        self.stealth_mgr = stealth_mgr or StealthManager()
        self.driver = None

    def start(self):
        ua = self.stealth_mgr.get_random_ua()

        if self.use_undetected:
            log.info("Using undetected_chromedriver...")
            opts = uc.ChromeOptions()
            opts.add_argument(f"--user-agent={ua}")
            opts.add_argument("--disable-blink-features=AutomationControlled")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--disable-notifications")
            opts.add_argument("--window-size=1280,720")
            opts.add_argument("--lang=en-US")
            opts.add_argument("--mute-audio")
            opts.add_argument("--disable-background-timer-throttling")
            opts.add_argument("--disable-renderer-backgrounding")

            prefs = {
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
                "profile.default_content_setting_values.notifications": 2,
                "profile.default_content_setting_values.images": 1,
            }
            opts.add_experimental_option("prefs", prefs)

            if self.headless:
                opts.add_argument("--headless=new")

            try:
                self.driver = uc.Chrome(options=opts, version_main=None,
                                        use_subprocess=False)
            except Exception as e:
                log.warning(f"undetected_chromedriver failed: {e}, falling back to standard")
                self.driver = self._start_standard(ua)

        else:
            self.driver = self._start_standard(ua)

        # Apply stealth patches
        if not self.use_undetected:
            self.stealth_mgr.apply_stealth(self.driver)

        # Override headers via CDP
        self.stealth_mgr.override_headers(self.driver)

        # Override navigator.webdriver
        try:
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                window.chrome = {runtime: {}};
                """
            })
        except:
            pass

        self.driver.implicitly_wait(3)
        log.info(f"Browser started | UA: {ua[:60]}...")
        return self.driver

    def _start_standard(self, ua: str):
        """Fallback standard Chrome with evasion flags."""
        opts = Options()
        opts.add_argument(f"--user-agent={ua}")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-notifications")
        opts.add_argument("--window-size=1280,720")
        opts.add_argument("--lang=en-US")
        opts.add_argument("--mute-audio")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        opts.add_experimental_option("prefs", {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2,
        })
        if self.headless:
            opts.add_argument("--headless=new")

        try:
            return webdriver.Chrome(
                service=Service(ChromeDriverManager().install()) if HAS_WDM else None,
                options=opts
            ) if HAS_WDM else webdriver.Chrome(options=opts)
        except:
            return webdriver.Chrome(options=opts)

    def stop(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass


# ═══════════════════════════════════════════════════════════════════
#  SESSION
# ═══════════════════════════════════════════════════════════════════

class Session:
    def __init__(self, driver, config: Config, human: HumanActions):
        self.driver = driver
        self.config = config
        self.human = human

    def login(self) -> bool:
        email = self.config.email or input("Email/Phone: ").strip()
        pw = self.config.password or input("Password: ").strip()
        self.config.email = email
        self.config.password = pw
        self.config.save()

        log.info("Loading facebook.com...")
        self.driver.get("https://www.facebook.com/")
        self.human.random_delay(3, 5)

        email_inp = None
        for by, sel in [
            (By.ID, "email"),
            (By.NAME, "email"),
            (By.CSS_SELECTOR, "input[autocomplete='username']"),
            (By.XPATH, "//input[@type='text' or @type='email']"),
        ]:
            try:
                email_inp = WebDriverWait(self.driver, 4).until(
                    EC.presence_of_element_located((by, sel))
                )
                break
            except:
                continue
        if not email_inp:
            return False

        pass_inp = None
        for by, sel in [
            (By.ID, "pass"),
            (By.NAME, "pass"),
            (By.XPATH, "//input[@type='password']"),
        ]:
            try:
                pass_inp = WebDriverWait(self.driver, 4).until(
                    EC.presence_of_element_located((by, sel))
                )
                break
            except:
                continue
        if not pass_inp:
            return False

        self.human.type_human(email_inp, email)
        self.human.random_delay(0.3, 0.8)
        self.human.type_human(pass_inp, pw)
        self.human.random_delay(0.5, 1.0)

        log.info("Clicking login...")
        try:
            login_btn = self.driver.find_element(By.XPATH,
                "//button[@type='submit' and contains(@name, 'login')] | "
                "//button[@type='submit']//ancestor::div[@data-testid]//button | "
                "//button[@name='login']"
            )
            self.human.click_human(login_btn)
        except:
            pass_inp.send_keys(Keys.RETURN)

        self.human.random_delay(4, 7)

        # Handle 2FA
        for _ in range(20):
            url = self.driver.current_url.lower()
            if "checkpoint" in url or "two_step" in url or "authentication" in url:
                log.warning("2FA required")
                try:
                    inp = self.driver.find_element(By.ID, "approvals_code")
                    code = input("2FA code: ").strip()
                    if code:
                        self.human.type_human(inp, code)
                        self.human.random_delay(0.5, 1)
                        for _ in range(5):
                            try:
                                btn = self.driver.find_element(By.ID, "checkpointSubmitButton")
                                self.human.click_human(btn)
                                self.human.random_delay(2, 3)
                            except:
                                break
                        self.human.random_delay(2, 4)
                        continue
                except:
                    pass
                input("Resolve 2FA in browser, then press Enter...")
                self.human.random_delay(3, 5)
                continue
            break

        if "login" in self.driver.current_url.lower() and "checkpoint" not in self.driver.current_url.lower():
            return False

        log.info(f"Logged in! ({self.driver.current_url[:50]})")
        self._save_cookies()
        return True

    def _save_cookies(self):
        with open(self.config.cookie_file, "w") as f:
            json.dump(self.driver.get_cookies(), f)

    def load_cookies(self) -> bool:
        if not Path(self.config.cookie_file).exists():
            return False
        self.driver.get("https://www.facebook.com/")
        try:
            for c in json.load(open(self.config.cookie_file)):
                try:
                    self.driver.add_cookie(c)
                except:
                    pass
        except:
            return False
        self.driver.get("https://www.facebook.com/")
        self.human.random_delay(3, 5)
        if "login" in self.driver.current_url.lower():
            return False
        log.info("Cookies restored!")
        return True


# ═══════════════════════════════════════════════════════════════════
#  REPORTER (with stealth)
# ═══════════════════════════════════════════════════════════════════

class Reporter:
    def __init__(self, driver, human: HumanActions, stealth_mgr: StealthManager = None):
        self.driver = driver
        self.human = human
        self.stealth_mgr = stealth_mgr or StealthManager()
        # ── NEW: store the resolved profile URL after navigation ──
        self._resolved_profile_url = None

    # ── NEW: shared URL resolver ──
    def _resolve_profile_url(self, target: str) -> str:
        """Normalize any input type (URL, numeric ID, username) into a proper FB profile URL."""
        target = target.strip()
        if target.startswith("http"):
            return target
        elif target.isdigit():
            return f"https://www.facebook.com/profile.php?id={target}"
        else:
            # Remove any leading @ or /
            clean = target.lstrip("@/")
            return f"https://www.facebook.com/{clean}"

    def js_click(self, el):
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center', behavior:'smooth'});", el
            )
            self.human.random_delay(0.3, 0.7)
            # Try human click first, fallback to JS
            if self.human.click_human(el):
                return True
            self.driver.execute_script("arguments[0].click();", el)
            return True
        except:
            return False

    def find_and_click(self, xpaths, timeout=4):
        for xpath in xpaths:
            try:
                elements = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_all_elements_located((By.XPATH, xpath))
                )
                for el in elements:
                    try:
                        if el.is_displayed():
                            self.human.random_page_interaction()
                            if self.js_click(el):
                                return True
                    except:
                        continue
            except:
                continue
        return False

    def click_three_dots(self):
        """
        Click the three-dots SVG menu on a Facebook profile.
        Uses multiple strategies with stealth.
        """
        # Strategy 1: SVG circle detection (precise)
        try:
            svgs = self.driver.find_elements(By.XPATH, "//*[name()='svg']")
            for svg in svgs:
                try:
                    circles = svg.find_elements(By.XPATH, ".//*[name()='circle']")
                    if len(circles) >= 3:
                        radii = [c.get_attribute("r") for c in circles[:3]]
                        if radii == ["2.5", "2.5", "2.5"]:
                            for attr in ['role="button"',
                                         "contains(@class,'x1i10hfl')",
                                         "contains(@class,'x1q0g3np')",
                                         "contains(@class,'x1ypdohk')"]:
                                try:
                                    parent = svg.find_element(
                                        By.XPATH, f"./ancestor::*[{attr}]"
                                    )
                                    if parent:
                                        self.js_click(parent)
                                        log.info("Clicked three-dots via SVG circle detection")
                                        return True
                                except:
                                    continue
                except:
                    continue
        except Exception as e:
            log.warning(f"SVG detection failed: {e}")

        # Strategy 2: viewBox + width match
        try:
            svgs = self.driver.find_elements(
                By.XPATH,
                "//*[name()='svg' and @viewBox='0 0 24 24' and @width='16']"
            )
            for svg in svgs:
                try:
                    parent = svg.find_element(
                        By.XPATH, "./ancestor::*[@role='button']"
                    )
                    if parent:
                        self.js_click(parent)
                        log.info("Clicked three-dots via viewBox detection")
                        return True
                except:
                    continue
        except:
            pass

        # Strategy 3: aria-labels
        for label in [
            "Profile settings see more options",
            "More",
            "More options",
            "Account",
            "Account settings",
        ]:
            try:
                el = self.driver.find_element(By.XPATH, f"//*[@aria-label='{label}']")
                if el.is_displayed():
                    self.js_click(el)
                    log.info(f"Clicked via aria-label '{label}'")
                    return True
            except:
                continue

        # Strategy 4: text "More"
        if self.find_and_click([
            "//span[text()='More']",
            "//span[contains(text(),'More')]",
            "//div[contains(text(),'More')]",
            "//*[contains(text(),'More') and @role='button']",
        ]):
            return True

        return False

    def check_if_banned(self, target: str) -> bool:
        try:
            page_source = self.driver.page_source.lower()
            if "this account has been disabled" in page_source \
               or "account disabled" in page_source \
               or "account has been banned" in page_source \
               or "this page isn't available" in page_source:
                log.info("Account has been banned!")
                return True
        except:
            pass
        return False

    def _navigate_to_profile(self, target: str) -> Tuple[bool, str]:
        """Navigate to a profile URL with header rotation."""
        url = self._resolve_profile_url(target)

        # Rotate headers before navigation
        if self.stealth_mgr:
            self.stealth_mgr.rotate_headers(self.driver)

        log.info(f"Opening: {url}")
        self.driver.get(url)
        self.human.random_delay(5, 8)

        page_lower = self.driver.page_source.lower()
        if "this page isn't available" in page_lower:
            return False, "Profile not found"

        # ── NEW: store the actual resolved URL from the address bar ──
        self._resolved_profile_url = self.driver.current_url

        self.human.random_page_interaction()
        return True, url

    def _submit_report(self) -> bool:
        """Submit, handle checkboxes, proceed through Next/Done."""
        submit_xpaths = [
            "//div[@role='button']//span[text()='Submit']",
            "//div[@role='button']//span[text()='Kirim']",
            "//div[@role='button']//span[contains(text(),'Submit')]",
            "//div[@role='button']//span[contains(text(),'Kirim')]",
            "//input[@type='submit']",
            "//button[@type='submit']",
            "//div[@role='button' and contains(text(),'Submit')]",
            "//div[@role='button']//span[text()='Send']",
        ]

        submitted = False
        for attempt in range(3):
            if self.find_and_click(submit_xpaths, 4):
                submitted = True
                self.human.random_delay(3, 5)
                break
            self.human.random_delay(1, 2)

        # Handle checkboxes that may appear
        try:
            checkboxes = self.driver.find_elements(By.XPATH, "//input[@type='checkbox']")
            for cb in checkboxes:
                if cb.is_displayed():
                    self.js_click(cb)
                    self.human.random_delay(1, 2)
                    self.find_and_click(submit_xpaths, 3)
                    break
        except:
            pass

        # Next button
        self.human.random_delay(1, 2)
        self.find_and_click([
            "//div[@role='button']//span[text()='Next']",
            "//span[text()='Next']",
            "//span[contains(text(),'Next')]",
            "//button[contains(text(),'Next')]",
            "//div[@role='button' and contains(text(),'Next')]",
            "//div[@role='button']//span[text()='Lanjut']",
            "//span[text()='Lanjut']",
        ], 3)
        self.human.random_delay(2, 3)

        # Done button
        self.find_and_click([
            "//div[@role='button']//span[text()='Done']",
            "//span[text()='Done']",
            "//span[contains(text(),'Done')]",
            "//button[contains(text(),'Done')]",
            "//div[@role='button' and contains(text(),'Done')]",
            "//div[@role='button']//span[text()='Selesai']",
            "//span[text()='Selesai']",
        ], 3)
        self.human.random_delay(2, 3)

        return submitted

    def report_profile_adult(self, target: str) -> Tuple[bool, str]:
        """Report profile for Adult content -> Nudity or sexual activity."""
        ok, msg = self._navigate_to_profile(target)
        if not ok:
            return False, msg

        log.info("Step 1: Three-dots menu...")
        if not self.click_three_dots():
            return False, "Could not click three-dots"
        self.human.random_delay(2, 4)

        log.info("Step 2: Report profile...")
        if not self.find_and_click([
            "//span[text()='Report profile']",
            "//span[contains(text(),'Report profile')]",
            "//span[text()='Laporkan profil']",
            "//span[contains(text(),'Laporkan profil')]",
            "//*[contains(text(),'Report profile')]",
        ], 5):
            return False, "Could not find Report profile button"
        self.human.random_delay(2, 4)

        log.info("Step 3: Something about this profile...")
        if not self.find_and_click([
            "//span[text()='Something about this profile']",
            "//span[contains(text(),'Something about this profile')]",
            "//span[text()='Sesuatu tentang profil ini']",
            "//span[contains(text(),'Sesuatu tentang profil ini')]",
            "//*[contains(text(),'Something about this profile')]",
        ], 5):
            return False, "Could not find 'Something about this profile'"
        self.human.random_delay(2, 4)

        log.info("Step 4: Adult content...")
        if not self.find_and_click([
            "//span[text()='Adult content']",
            "//span[contains(text(),'Adult content')]",
            "//span[text()='Konten dewasa']",
            "//span[contains(text(),'Konten dewasa')]",
            "//*[contains(text(),'Adult content')]",
        ], 5):
            return False, "Could not find 'Adult content'"
        self.human.random_delay(2, 3)

        log.info("Step 5: Nudity or sexual activity...")
        if not self.find_and_click([
            "//span[text()='Nudity or sexual activity']",
            "//span[contains(text(),'Nudity or sexual activity')]",
            "//span[text()='Ketelanjangan atau aktivitas seksual']",
            "//span[contains(text(),'Ketelanjangan atau aktivitas seksual')]",
            "//*[contains(text(),'Nudity or sexual activity')]",
        ], 5):
            return False, "Could not find 'Nudity or sexual activity'"
        self.human.random_delay(2, 3)

        log.info("Step 6+7+8: Submit -> Next -> Done...")
        submitted = self._submit_report()

        if self.check_if_banned(target):
            return True, "ACCOUNT BANNED! Report successful!"

        page_text = self.driver.page_source.lower()
        if "thank" in page_text or "terima" in page_text:
            return True, "Profile reported for Adult content successfully!"
        if submitted:
            return True, "Adult content report submitted!"
        return False, "Could not submit adult content report"

    def report_profile_bullying_harassment(self, target: str) -> Tuple[bool, str]:
        """Report profile for Bullying, harassment -> sexual exploitation."""
        ok, msg = self._navigate_to_profile(target)
        if not ok:
            return False, msg

        log.info("Step 1: Three-dots...")
        if not self.click_three_dots():
            return False, "Could not click three-dots"
        self.human.random_delay(2, 4)

        log.info("Step 2: Report profile...")
        if not self.find_and_click([
            "//span[text()='Report profile']",
            "//span[contains(text(),'Report profile')]",
            "//span[text()='Laporkan profil']",
            "//span[contains(text(),'Laporkan profil')]",
            "//*[contains(text(),'Report profile')]",
        ], 5):
            return False, "Could not find Report profile button"
        self.human.random_delay(2, 4)

        log.info("Step 3: Something about this profile...")
        if not self.find_and_click([
            "//span[text()='Something about this profile']",
            "//span[contains(text(),'Something about this profile')]",
            "//span[text()='Sesuatu tentang profil ini']",
            "//span[contains(text(),'Sesuatu tentang profil ini')]",
            "//*[contains(text(),'Something about this profile')]",
        ], 5):
            return False, "Could not find 'Something about this profile'"
        self.human.random_delay(2, 4)

        log.info("Step 4: Bullying, harassment or abuse...")
        if not self.find_and_click([
            "//span[text()='Bullying, harassment or abuse']",
            "//span[contains(text(),'Bullying, harassment or abuse')]",
            "//span[text()='Penindasan, pelecehan, atau penyalahgunaan']",
            "//span[contains(text(),'Penindasan')]",
            "//span[contains(text(),'pelecehan')]",
            "//*[contains(text(),'Bullying')]",
            "//*[contains(text(),'Penindasan')]",
        ], 5):
            return False, "Could not find 'Bullying, harassment or abuse'"
        self.human.random_delay(2, 4)

        log.info("Step 5: Seems like sexual exploitation...")
        if not self.find_and_click([
            "//span[text()='Seems like sexual exploitation']",
            "//span[contains(text(),'Seems like sexual exploitation')]",
            "//span[text()='Terlihat seperti eksploitasi seksual']",
            "//span[contains(text(),'eksploitasi seksual')]",
            "//*[contains(text(),'sexual exploitation')]",
        ], 5):
            return False, "Could not find 'Seems like sexual exploitation'"
        self.human.random_delay(2, 3)

        log.info("Step 6+7+8: Submit -> Next -> Done...")
        submitted = self._submit_report()

        if "thank" in self.driver.page_source.lower() or "terima" in self.driver.page_source.lower():
            return True, "Profile reported for bullying/harassment successfully!"
        if submitted:
            return True, "Report submitted for bullying/harassment."
        return False, "Could not submit report"

    def report_post(self, post_url: str) -> Tuple[bool, str]:
        if self.stealth_mgr:
            self.stealth_mgr.rotate_headers(self.driver)

        log.info(f"Opening post: {post_url}")
        self.driver.get(post_url)
        self.human.random_delay(4, 7)

        if "not found" in self.driver.page_source.lower() or "unavailable" in self.driver.page_source.lower():
            return False, "Post not found"

        log.info("Step 1: More button...")
        if not self.click_three_dots():
            return False, "No More button"
        self.human.random_delay(2, 3)

        log.info("Step 2: Report option...")
        if not self.find_and_click([
            "//input[@value='RESOLVE_PROBLEM']",
            "//a[contains(text(),'Report post')]",
            "//span[contains(text(),'Report post')]",
            "//div[contains(text(),'Report post')]",
        ], 4):
            return False, "No report option"
        self.human.random_delay(2, 3)

        log.info("Step 3: Spam...")
        if not self.find_and_click([
            "//input[@type='radio' and @value='spam']",
            "//span[contains(text(),'Spam')]/preceding-sibling::input",
            "//span[text()='Spam']",
            "//div[contains(text(),'Spam')]",
        ], 3):
            return False, "No spam option"
        self.human.random_delay(1, 2)

        log.info("Step 4: Submit...")
        submit_xpaths = [
            "//div[@role='button']//span[text()='Submit']",
            "//input[@type='submit']",
            "//button[@type='submit']",
        ]
        for _ in range(2):
            self.find_and_click(submit_xpaths, 3)
            self.human.random_delay(2, 3)
            try:
                for cb in self.driver.find_elements(By.XPATH, "//input[@type='checkbox']"):
                    if cb.is_displayed():
                        self.js_click(cb)
                        self.human.random_delay(1, 2)
                        break
            except:
                pass

        return True, "Post reported"

    def auto_report_until_banned(self, target: str, delay_between: int = 30) -> Tuple[bool, str]:
        """Automatically report cycling both methods until banned."""
        target = target.strip()
        # ── FIX: resolve the profile URL ONCE at the start ──
        resolved_url = self._resolve_profile_url(target)

        report_types = ['adult', 'bullying']
        report_count = 0
        success_count = 0

        log.info(f"Starting auto-reporting for {resolved_url} until banned...")
        log.info("Cycling between Adult content and Bullying/Harassment")

        while True:
            for report_type in report_types:
                report_count += 1
                log.info(f"\n{'='*60}")
                log.info(f"Report #{report_count} - Type: {report_type.upper()}")
                log.info(f"{'='*60}")

                if report_type == 'adult':
                    success, msg = self.report_profile_adult(resolved_url)
                else:
                    success, msg = self.report_profile_bullying_harassment(resolved_url)

                if success:
                    success_count += 1
                    log.info(f"[SUCCESS] {msg}")
                else:
                    log.warning(f"[FAILED] {msg}")

                # ── FIX: check banned status AFTER the report ──
                if self.check_if_banned(resolved_url):
                    log.info(f"\n{'='*60}")
                    log.info(f"🎯 ACCOUNT BANNED! Reports sent: {report_count}")
                    log.info(f"Successful: {success_count}")
                    log.info(f"{'='*60}")
                    return True, f"Account banned after {report_count} reports!"

                wait = delay_between + random.randint(0, 15)
                log.info(f"Waiting {wait}s before next report...")
                time.sleep(wait)

                # ── FIX: navigate home, then back to profile using the STORED resolved URL ──
                try:
                    # Navigate to Facebook home first to clear any checkpoint/error state
                    if self.stealth_mgr:
                        self.stealth_mgr.rotate_headers(self.driver)
                    self.driver.get("https://www.facebook.com/")
                    self.human.random_delay(3, 5)

                    # Use the stored resolved URL from _navigate_to_profile, or fallback
                    nav_url = self._resolved_profile_url or resolved_url

                    if self.stealth_mgr:
                        self.stealth_mgr.rotate_headers(self.driver)
                    self.driver.get(nav_url)
                    self.human.random_delay(4, 7)

                    page_lower = self.driver.page_source.lower()
                    if "this page isn't available" in page_lower:
                        log.info(f"\n{'='*60}")
                        log.info(f"🎯 PROFILE DELETED/BANNED! Reports: {report_count}")
                        log.info(f"Successful: {success_count}")
                        log.info(f"{'='*60}")
                        return True, f"Profile deleted after {report_count} reports!"

                    # Update stored resolved URL (in case FB redirects)
                    self._resolved_profile_url = self.driver.current_url

                except Exception as e:
                    log.warning(f"Navigation back to profile failed: {e}")
                    # Try one more time with the raw resolved URL
                    try:
                        self.driver.get(resolved_url)
                        self.human.random_delay(4, 7)
                    except:
                        log.error("Critical navigation failure, aborting.")
                        return False, f"Navigation failed after {report_count} reports"

    def mass_report_profiles_adult(self, targets: List[str], count: int = 3) -> Dict:
        results = {}
        for t in targets:
            ok, fail = 0, 0
            for i in range(count):
                log.info(f"[{t}] {i+1}/{count}")
                s, msg = self.report_profile_adult(t)
                if s:
                    ok += 1
                else:
                    fail += 1
                log.info(f"  {'OK' if s else 'FAIL'}: {msg}")
                if i + 1 < count:
                    time.sleep(random.randint(15, 30))
            results[t] = (ok, fail)
        return results

    def mass_report_profiles_bullying_harassment(self, targets: List[str], count: int = 3) -> Dict:
        results = {}
        for t in targets:
            ok, fail = 0, 0
            for i in range(count):
                log.info(f"[{t}] {i+1}/{count}")
                s, msg = self.report_profile_bullying_harassment(t)
                if s:
                    ok += 1
                else:
                    fail += 1
                log.info(f"  {'OK' if s else 'FAIL'}: {msg}")
                if i + 1 < count:
                    time.sleep(random.randint(15, 30))
            results[t] = (ok, fail)
        return results

    def mass_report_posts(self, targets: List[str], count: int = 3) -> Dict:
        results = {}
        for u in targets:
            ok, fail = 0, 0
            for i in range(count):
                log.info(f"[{u[:40]}...] {i+1}/{count}")
                s, msg = self.report_post(u)
                if s:
                    ok += 1
                else:
                    fail += 1
                if i + 1 < count:
                    time.sleep(random.randint(15, 30))
            results[u] = (ok, fail)
        return results


# ═══════════════════════════════════════════════════════════════════
#  MENU / CLI
# ═══════════════════════════════════════════════════════════════════

def banner():
    print("\n" + "=" * 60)
    print("  FB Mass Report v5.0 — STEALTH EDITION")
    print("  ● undetected_chromedriver  ● Rotating UAs")
    print("  ● Human-like movements     ● Header spoofing")
    print("=" * 60)


def menu():
    print("\n  1. Login")
    print("  2. Report profile (Nudity/Sexual Activity)")
    print("  3. Mass report profiles (Nudity/Sexual Activity)")
    print("  4. Report profile (Bullying/Harassment)")
    print("  5. Mass report profiles (Bullying/Harassment)")
    print("  6. Report post")
    print("  7. Mass report posts")
    print("  8. 🔥 AUTO-REPORT UNTIL BANNED")
    print("  9. Settings")
    print("  10. Exit")
    try:
        return int(input("> ").strip())
    except:
        return 10


def settings(config):
    e = input(f"Email [{config.email}]: ").strip() or config.email
    p = input("Password: ").strip()
    h = input("Headless? (y/N): ").strip().lower() == 'y'
    c = input(f"Reports per target [{config.report_count}]: ").strip()

    print("\n--- Stealth Settings ---")
    ua_opt = input("Rotate User-Agent headers? (Y/n): ").strip().lower()
    ua_on = ua_opt != 'n'
    hm_opt = input("Human-like mouse movements? (Y/n): ").strip().lower()
    hm_on = hm_opt != 'n'

    config.email = e
    if p:
        config.password = p
    config.headless = h
    if c:
        config.report_count = int(c)
    config.rotate_ua = ua_on
    config.human_mouse = hm_on
    config.save()


def main():
    banner()
    config = Config.load()

    # Print installation tips
    missing = []
    if not HAS_UC:
        missing.append("undetected-chromedriver")
    if not HAS_STEALTH:
        missing.append("selenium-stealth")
    if not HAS_FAKE_UA:
        missing.append("fake-useragent")
    if not HAS_HUMAN_CURSOR:
        missing.append("humancursor")
    if missing:
        print(f"\n[INFO] Install optional packages: pip install {' '.join(missing)}")

    stealth_mgr = StealthManager(rotate_ua=config.rotate_ua)
    engine = Browser(
        headless=config.headless,
        use_undetected=config.use_undetected,
        stealth_mgr=stealth_mgr,
    )

    try:
        driver = engine.start()
    except Exception as e:
        log.error(f"Browser failed: {e}")
        sys.exit(1)

    human = HumanActions(driver)
    session = Session(driver, config, human)
    reporter = Reporter(driver, human, stealth_mgr)

    if not session.load_cookies():
        if config.email and config.password:
            session.login()
        else:
            log.warning("Use option 1 to login")

    while True:
        opt = menu()
        if opt == 1:
            session.login()
        elif opt == 2:
            t = input("Profile (URL, ID, username): ").strip()
            if t:
                ok, msg = reporter.report_profile_adult(t)
                log.info(f"{'[OK]' if ok else '[FAIL]'} {msg}")
        elif opt == 3:
            raw = input("Profiles (comma-sep): ").strip()
            if raw:
                targets = [x.strip() for x in raw.split(",") if x.strip()]
                cnt = int(input(f"Reports each [{config.report_count}]: ").strip() or config.report_count)
                r = reporter.mass_report_profiles_adult(targets, cnt)
                print(json.dumps(r, indent=2))
        elif opt == 4:
            t = input("Profile (URL, ID, username): ").strip()
            if t:
                ok, msg = reporter.report_profile_bullying_harassment(t)
                log.info(f"{'[OK]' if ok else '[FAIL]'} {msg}")
        elif opt == 5:
            raw = input("Profiles (comma-sep): ").strip()
            if raw:
                targets = [x.strip() for x in raw.split(",") if x.strip()]
                cnt = int(input(f"Reports each [{config.report_count}]: ").strip() or config.report_count)
                r = reporter.mass_report_profiles_bullying_harassment(targets, cnt)
                print(json.dumps(r, indent=2))
        elif opt == 6:
            u = input("Post URL: ").strip()
            if u:
                ok, msg = reporter.report_post(u)
                log.info(f"{'[OK]' if ok else '[FAIL]'} {msg}")
        elif opt == 7:
            raw = input("Post URLs (comma-sep): ").strip()
            if raw:
                targets = [x.strip() for x in raw.split(",") if x.strip()]
                cnt = int(input(f"Reports each [{config.report_count}]: ").strip() or config.report_count)
                r = reporter.mass_report_posts(targets, cnt)
                print(json.dumps(r, indent=2))
        elif opt == 8:
            t = input("Profile (URL, ID, username): ").strip()
            if t:
                delay = input("Delay between reports in seconds [30]: ").strip()
                delay = int(delay) if delay else 30
                ok, msg = reporter.auto_report_until_banned(t, delay)
                log.info(f"{'[OK]' if ok else '[FAIL]'} {msg}")
        elif opt == 9:
            settings(config)
        elif opt == 10:
            break

    engine.stop()


if __name__ == "__main__":
    main()
