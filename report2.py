#!/usr/bin/env python3
"""
Facebook Mass Report Tool — Authorized Penetration Testing
===========================================================
v3.2 — Fixed login: ENTER key instead of button detection.
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
from dataclasses import dataclass
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
    ElementClickInterceptedException, StaleElementReferenceException,
    WebDriverException
)

try:
    from webdriver_manager.chrome import ChromeDriverManager
    HAS_WDM = True
except ImportError:
    HAS_WDM = False

# ---------------------------------------------------------------------------
# Config
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


logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s :: %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("FBReport")


# ---------------------------------------------------------------------------
# Browser Engine
# ---------------------------------------------------------------------------

class BrowserEngine:
    AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.165 Mobile Safari/537.36",
        "Mozilla/5.0 (iPhone16,2; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
    ]

    def __init__(self, headless: bool = False):
        self.headless = headless
        self.driver = None

    def start(self):
        opts = Options()
        opts.add_argument(f"--user-agent={random.choice(self.AGENTS)}")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-notifications")
        opts.add_argument("--window-size=1280,720")
        opts.add_argument("--lang=en-US")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        prefs = {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2,
        }
        opts.add_experimental_option("prefs", prefs)
        if self.headless:
            opts.add_argument("--headless=new")

        try:
            if HAS_WDM:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=opts)
            else:
                self.driver = webdriver.Chrome(options=opts)
        except Exception as e:
            log.error(f"ChromeDriver init failed: {e}")
            log.info("Install it: pip install webdriver-manager, or put chromedriver in PATH")
            raise

        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US','en'] });
            """
        })

        self.driver.implicitly_wait(3)
        return self.driver

    def stop(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Session — FIXED LOGIN: ENTER key instead of button
# ---------------------------------------------------------------------------

class FBSession:
    def __init__(self, driver, config: Config):
        self.driver = driver
        self.config = config

    def login(self) -> bool:
        """Login using credentials. Presses ENTER on password field instead of finding login button."""
        email = self.config.email
        password = self.config.password

        if not email or not password:
            email = input("Email/Phone: ").strip()
            password = input("Password: ").strip()
            self.config.email = email
            self.config.password = password
            self.config.save()

        log.info("Opening facebook.com...")
        self.driver.get("https://www.facebook.com/")
        time.sleep(4)

        # ========== FIND EMAIL FIELD ==========
        email_inp = None
        email_strategies = [
            (By.ID, "email"),
            (By.NAME, "email"),
            (By.CSS_SELECTOR, "input[autocomplete='username']"),
            (By.XPATH, "//input[@type='text' or @type='email']"),
            (By.XPATH, "//input[contains(@placeholder,'Email') or contains(@placeholder,'mobile')]"),
        ]

        for strat in email_strategies:
            try:
                email_inp = WebDriverWait(self.driver, 4).until(
                    EC.presence_of_element_located(strat)
                )
                log.info(f"Found email field via: {strat}")
                break
            except (TimeoutException, NoSuchElementException):
                continue

        if not email_inp:
            log.warning("Trying JS-based field detection...")
            try:
                email_inp = self.driver.execute_script("""
                    var inputs = document.querySelectorAll('input');
                    for (var i = 0; i < inputs.length; i++) {
                        var type = inputs[i].type.toLowerCase();
                        if (type === 'email' || type === 'text') {
                            var ph = (inputs[i].placeholder || '').toLowerCase();
                            if (ph.includes('email') || ph.includes('phone') || ph.includes('mobile')) {
                                return inputs[i];
                            }
                        }
                    }
                    return null;
                """)
                if not email_inp:
                    log.error("Could not find email input field.")
                    return False
            except Exception:
                log.error("Could not find email input field.")
                return False

        # ========== FIND PASSWORD FIELD ==========
        pass_strategies = [
            (By.ID, "pass"),
            (By.NAME, "pass"),
            (By.CSS_SELECTOR, "input[autocomplete='current-password']"),
            (By.XPATH, "//input[@type='password']"),
        ]
        pass_inp = None
        for strat in pass_strategies:
            try:
                pass_inp = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located(strat)
                )
                break
            except (TimeoutException, NoSuchElementException):
                continue

        if not pass_inp:
            log.error("Could not find password field.")
            return False

        # ========== TYPE CREDENTIALS ==========
        try:
            email_inp.clear()
            time.sleep(0.3)
            for char in email:
                email_inp.send_keys(char)
                time.sleep(random.uniform(0.02, 0.06))

            pass_inp.clear()
            time.sleep(0.3)
            for char in password:
                pass_inp.send_keys(char)
                time.sleep(random.uniform(0.02, 0.06))

            time.sleep(0.5)
        except Exception as e:
            log.error(f"Failed to type credentials: {e}")
            return False

        # ========== PRESS ENTER ON PASSWORD FIELD ==========
        # This is the key fix — ENTER submits the form without needing to find the button
        log.info("Pressing ENTER to submit login form...")
        try:
            pass_inp.send_keys(Keys.RETURN)
        except Exception:
            # Fallback: try submit via JS
            log.warning("ENTER failed, trying JS form submit...")
            try:
                self.driver.execute_script("""
                    var form = document.querySelector('form');
                    if (form) form.submit();
                """)
            except Exception as e2:
                log.error(f"All submit methods failed: {e2}")
                return False

        # ========== WAIT FOR POST-LOGIN ==========
        log.info("Waiting for login to complete...")
        time.sleep(7)

        # Handle checkpoint
        if "checkpoint" in self.driver.current_url.lower():
            log.warning("LOGIN CHECKPOINT DETECTED.")
            log.info("Enter the approval code sent to your email/phone.")
            code = input("Approval code (or press Enter to resolve manually): ").strip()
            if code:
                try:
                    code_inp = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.ID, "approvals_code"))
                    )
                    code_inp.send_keys(code)
                    time.sleep(1)
                    for _ in range(5):
                        try:
                            btn = self.driver.find_element(By.ID, "checkpointSubmitButton")
                            btn.click()
                            time.sleep(3)
                        except:
                            break
                    log.info("Checkpoint resolved.")
                except Exception as ce:
                    log.error(f"Checkpoint auto-resolve failed: {ce}")
                    input(">>> Press Enter after manually resolving checkpoint in browser...")
            else:
                input(">>> Press Enter after manually resolving checkpoint in browser...")

        # ========== VERIFY LOGIN ==========
        time.sleep(3)
        current = self.driver.current_url.lower()
        if "login" in current and "checkpoint" not in current:
            log.warning("Still on login page. Login may have failed.")
            return False

        log.info(f"Logged in! Current URL: {current[:80]}")
        self._save_cookies()
        return True

    def _save_cookies(self):
        cookies = self.driver.get_cookies()
        with open(self.config.cookie_file, "w") as f:
            json.dump(cookies, f)
        log.info(f"Saved {len(cookies)} cookies to {self.config.cookie_file}")

    def load_cookies(self) -> bool:
        cpath = Path(self.config.cookie_file)
        if not cpath.exists():
            return False

        self.driver.get("https://www.facebook.com/")
        try:
            with open(cpath) as f:
                cookies = json.load(f)
        except Exception:
            return False

        for c in cookies:
            try:
                self.driver.add_cookie(c)
            except Exception:
                pass

        self.driver.get("https://www.facebook.com/")
        time.sleep(4)

        if "login" in self.driver.current_url.lower():
            log.warning("Cookies expired.")
            return False

        log.info("Session restored from cookies!")
        return True


# ---------------------------------------------------------------------------
# Universal Reporter
# ---------------------------------------------------------------------------

class FBReporter:
    def __init__(self, driver):
        self.driver = driver

    def _sleep(self, lo=8, hi=22):
        d = random.randint(lo, hi)
        log.info(f"  Waiting {d}s...")
        time.sleep(d)

    def _click_first(self, strategies, timeout=5, scroll=True):
        for by, sel in strategies:
            try:
                el = WebDriverWait(self.driver, max(2, timeout // len(strategies))).until(
                    EC.element_to_be_clickable((by, sel))
                )
                if scroll:
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                    time.sleep(0.3)
                el.click()
                return True
            except Exception:
                continue
        return False

    def _submit_btn(self):
        return self._click_first([
            (By.XPATH, "//div[@role='button']//span[text()='Submit']"),
            (By.XPATH, "//div[@role='button']//span[text()='Kirim']"),
            (By.XPATH, "//input[@type='submit']"),
            (By.XPATH, "//button[@type='submit']"),
            (By.XPATH, "//div[@role='button' and contains(text(),'Submit')]"),
            (By.XPATH, "//div[@role='button' and contains(text(),'Kirim')]"),
            (By.XPATH, "//div[@role='button']//span[contains(text(),'Next')]"),
            (By.XPATH, "//div[@role='button']//span[contains(text(),'Continue')]"),
        ], timeout=6)

    # ------------------------------------------------------------------
    # Report Profile
    # ------------------------------------------------------------------

    def report_profile(self, target: str) -> Tuple[bool, str]:
        if target.isdigit():
            profile_id = target
        else:
            parsed = urlparse(target)
            q = parse_qs(parsed.query)
            profile_id = q.get('id', [None])[0]
            if not profile_id:
                m = re.search(r'/id[/=]?(\d+)', target)
                profile_id = m.group(1) if m else target

        url = f"https://www.facebook.com/profile.php?id={profile_id}"
        log.info(f"Opening profile: {url}")
        self.driver.get(url)
        time.sleep(5)

        if "not found" in self.driver.page_source.lower() or "this page isn't available" in self.driver.page_source.lower():
            return False, "Profile not found."

        log.info("Step 1: Clicking 'More' button...")
        more_clicked = self._click_first([
            (By.XPATH, "//div[@aria-label='More options']"),
            (By.XPATH, "//div[@aria-label='More']"),
            (By.XPATH, "//div[@aria-label='Profile options']"),
            (By.XPATH, "//div[@role='button']//span[contains(text(),'More')]"),
            (By.XPATH, "//div[@role='button']//span[text()='Lainnya']"),
            (By.XPATH, "//a[contains(text(),'More')]"),
            (By.XPATH, "//a[text()='Lainnya']"),
            (By.XPATH, "(//div[@role='button'])[1]"),
        ], timeout=6)
        if not more_clicked:
            return False, "Could not click 'More' button."
        time.sleep(2)

        log.info("Step 2: Opening report dialog...")
        report_clicked = self._click_first([
            (By.XPATH, "//span[contains(text(),'Find support or report')]"),
            (By.XPATH, "//span[contains(text(),'Cari dukungan atau laporkan')]"),
            (By.XPATH, "//a[contains(text(),'Find support')]"),
            (By.XPATH, "//a[contains(text(),'report profile')]"),
            (By.XPATH, "//a[contains(text(),'report Page')]"),
            (By.XPATH, "//a[contains(text(),'Laporkan profil')]"),
            (By.XPATH, "//a[contains(text(),'Cari dukungan')]"),
            (By.XPATH, "//a[contains(@href,'/help/contact/')]"),
        ], timeout=7)
        if not report_clicked:
            return False, "Could not find report option."
        time.sleep(2)

        log.info("Step 3: Selecting report reason...")
        reason_clicked = self._click_first([
            (By.XPATH, "//span[text()='Fake Account']"),
            (By.XPATH, "//span[text()='Akun Palsu']"),
            (By.XPATH, "//span[contains(text(),'Fake Account')]"),
            (By.XPATH, "//span[contains(text(),'Akun Palsu')]"),
            (By.XPATH, "//div[contains(text(),'Fake Account')]"),
            (By.XPATH, "//input[@value='FAKE_ACCOUNT']/following-sibling::span"),
            (By.XPATH, "//span[text()='Pretending to be someone']"),
            (By.XPATH, "//span[text()='Berpura-pura menjadi seseorang']"),
        ], timeout=5)
        if not reason_clicked:
            return False, "Could not select reason."
        time.sleep(1.5)

        self._click_first([
            (By.XPATH, "//span[text()='Me']"),
            (By.XPATH, "//span[text()='Saya']"),
            (By.XPATH, "//span[contains(text(),'Me')]"),
        ], timeout=2)
        time.sleep(1)

        log.info("Step 4: Submitting...")
        self._submit_btn()
        time.sleep(2)

        self._click_first([
            (By.XPATH, "//input[@type='checkbox' and @name='checked']"),
            (By.XPATH, "//input[@type='checkbox' and contains(@aria-label,'confirm')]"),
        ], timeout=2)
        time.sleep(1)

        self._submit_btn()
        time.sleep(2)

        ps = self.driver.page_source.lower()
        if "thank you" in ps or "terima kasih" in ps or "report sent" in ps:
            return True, "Profile reported successfully."
        return True, "Report submitted."

    # ------------------------------------------------------------------
    # Report Post
    # ------------------------------------------------------------------

    def report_post(self, post_url: str) -> Tuple[bool, str]:
        log.info(f"Opening post: {post_url}")
        self.driver.get(post_url)
        time.sleep(5)

        if "not found" in self.driver.page_source.lower():
            return False, "Post not found."

        log.info("Step 1: Clicking 'More'...")
        if not self._click_first([
            (By.XPATH, "//div[@aria-label='More options']"),
            (By.XPATH, "//div[@aria-label='More']"),
            (By.XPATH, "//div[@role='button']//span[contains(text(),'More')]"),
            (By.XPATH, "//a[contains(text(),'More')]"),
            (By.XPATH, "//a[text()='Lainnya']"),
        ], timeout=6):
            return False, "Could not click 'More' on post."
        time.sleep(2)

        log.info("Step 2: Opening post report...")
        if not self._click_first([
            (By.XPATH, "//input[@value='RESOLVE_PROBLEM']"),
            (By.XPATH, "//a[contains(text(),'Report post')]"),
            (By.XPATH, "//span[contains(text(),'Report post')]"),
            (By.XPATH, "//div[contains(text(),'Report post')]"),
            (By.XPATH, "//a[contains(text(),'Laporkan postingan')]"),
        ], timeout=6):
            return False, "Could not find 'Report post' option."
        time.sleep(2)

        log.info("Step 3: Selecting 'Spam'...")
        if not self._click_first([
            (By.XPATH, "//input[@type='radio' and @value='spam']"),
            (By.XPATH, "//input[@type='radio' and contains(@value,'SPAM')]"),
            (By.XPATH, "//span[contains(text(),'Spam')]/preceding-sibling::input"),
            (By.XPATH, "//span[contains(text(),'Spam')]"),
            (By.XPATH, "//div[contains(text(),'Spam')]"),
        ], timeout=4):
            return False, "Could not select 'Spam' reason."
        time.sleep(1.5)

        log.info("Step 4: Submitting...")
        self._submit_btn()
        time.sleep(2)

        self._click_first([
            (By.XPATH, "//input[@type='checkbox' and @name='checked']"),
        ], timeout=2)
        time.sleep(1)

        self._submit_btn()
        return True, "Post reported as spam."

    # ------------------------------------------------------------------
    # Mass
    # ------------------------------------------------------------------

    def mass_report_profiles(self, targets: List[str], count: int = 3) -> Dict:
        results = {}
        for t in targets:
            ok, fail = 0, 0
            for i in range(count):
                log.info(f"[{t}] Report {i+1}/{count}")
                s, msg = self.report_profile(t)
                if s:
                    ok += 1
                    log.info(f"  OK: {msg}")
                else:
                    fail += 1
                    log.warning(f"  FAIL: {msg}")
                if i + 1 < count:
                    self._sleep()
            results[t] = (ok, fail)
        return results

    def mass_report_posts(self, targets: List[str], count: int = 3) -> Dict:
        results = {}
        for u in targets:
            ok, fail = 0, 0
            for i in range(count):
                log.info(f"[{u[:50]}...] Report {i+1}/{count}")
                s, msg = self.report_post(u)
                if s:
                    ok += 1
                else:
                    fail += 1
                if i + 1 < count:
                    self._sleep(10, 25)
            results[u] = (ok, fail)
        return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def banner():
    print(r"""
╔══════════════════════════════════════════════════════════════════╗
║          Facebook Mass Report Tool  v3.2                        ║
║          Login via ENTER key — no button detection needed       ║
╚══════════════════════════════════════════════════════════════════╝
    """)

def menu():
    print("""
  1. Login / Re-authenticate
  2. Report a SINGLE profile
  3. Report a SINGLE post
  4. Mass-report PROFILES
  5. Mass-report POSTS
  6. Configure settings
  7. Exit
    """)
    try:
        return int(input("Option: ").strip())
    except:
        return 7

def configure(config: Config):
    print(f"\nEmail: {config.email or '(not set)'}")
    print(f"Headless: {config.headless}")
    print(f"Delays: {config.min_delay}-{config.max_delay}s")
    print(f"Reports per target: {config.report_count}\n")
    e = input(f"Email [{config.email}]: ").strip() or config.email
    p = input("Password (blank to keep): ").strip()
    h = input("Headless? (y/N): ").strip().lower() == 'y'
    c = input(f"Reports per target [{config.report_count}]: ").strip()
    config.email = e
    if p: config.password = p
    config.headless = h
    if c: config.report_count = int(c)
    config.save()


def main():
    banner()
    config = Config.load()

    engine = BrowserEngine(headless=config.headless)
    try:
        driver = engine.start()
    except Exception as e:
        log.error(f"Browser start failed: {e}")
        sys.exit(1)

    session = FBSession(driver, config)
    reporter = FBReporter(driver)

    if not session.load_cookies():
        if config.email and config.password:
            log.info("Cookies expired. Logging in with saved credentials...")
            session.login()
        else:
            log.warning("No saved credentials. Use option 1 to login.")

    while True:
        opt = menu()

        if opt == 1:
            session.login()

        elif opt == 2:
            t = input("Profile URL or ID: ").strip()
            if t:
                ok, msg = reporter.report_profile(t)
                log.info(f"{'[OK]' if ok else '[FAIL]'} {msg}")

        elif opt == 3:
            u = input("Post URL: ").strip()
            if u:
                ok, msg = reporter.report_post(u)
                log.info(f"{'[OK]' if ok else '[FAIL]'} {msg}")

        elif opt == 4:
            raw = input("Profile IDs/URLs (comma separated): ").strip()
            if raw:
                targets = [x.strip() for x in raw.split(",") if x.strip()]
                cnt = int(input(f"Reports each [{config.report_count}]: ").strip() or config.report_count)
                r = reporter.mass_report_profiles(targets, cnt)
                print(json.dumps(r, indent=2))

        elif opt == 5:
            raw = input("Post URLs (comma separated): ").strip()
            if raw:
                targets = [x.strip() for x in raw.split(",") if x.strip()]
                cnt = int(input(f"Reports each [{config.report_count}]: ").strip() or config.report_count)
                r = reporter.mass_report_posts(targets, cnt)
                print(json.dumps(r, indent=2))

        elif opt == 6:
            configure(config)

        elif opt == 7:
            log.info("Exiting.")
            break

    engine.stop()


if __name__ == "__main__":
    main()
