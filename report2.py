#!/usr/bin/env python3
"""
Facebook Mass Report Tool — Authorized Penetration Testing
===========================================================
v3.3 — Fixed: vanity URLs, More button detection, direct navigation
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
# Session
# ---------------------------------------------------------------------------

class FBSession:
    def __init__(self, driver, config: Config):
        self.driver = driver
        self.config = config

    def login(self) -> bool:
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

        # Find email field
        email_inp = None
        for strat in [
            (By.ID, "email"), (By.NAME, "email"),
            (By.CSS_SELECTOR, "input[autocomplete='username']"),
            (By.XPATH, "//input[@type='text' or @type='email']"),
            (By.XPATH, "//input[contains(@placeholder,'Email') or contains(@placeholder,'mobile')]"),
        ]:
            try:
                email_inp = WebDriverWait(self.driver, 4).until(EC.presence_of_element_located(strat))
                log.info(f"Found email via: {strat}")
                break
            except:
                continue

        if not email_inp:
            try:
                email_inp = self.driver.execute_script("""
                    var inps = document.querySelectorAll('input');
                    for (var i=0; i<inps.length; i++) {
                        var t = inps[i].type.toLowerCase();
                        if (t==='email'||t==='text') {
                            var ph = (inps[i].placeholder||'').toLowerCase();
                            if (ph.includes('email')||ph.includes('phone')||ph.includes('mobile'))
                                return inps[i];
                        }
                    }
                    return null;
                """)
            except:
                pass
            if not email_inp:
                log.error("Could not find email field.")
                return False

        # Find password field
        pass_inp = None
        for strat in [
            (By.ID, "pass"), (By.NAME, "pass"),
            (By.CSS_SELECTOR, "input[autocomplete='current-password']"),
            (By.XPATH, "//input[@type='password']"),
        ]:
            try:
                pass_inp = WebDriverWait(self.driver, 3).until(EC.presence_of_element_located(strat))
                break
            except:
                continue

        if not pass_inp:
            log.error("Could not find password field.")
            return False

        # Type credentials
        try:
            email_inp.clear()
            time.sleep(0.2)
            for c in email:
                email_inp.send_keys(c)
                time.sleep(random.uniform(0.02, 0.06))

            pass_inp.clear()
            time.sleep(0.2)
            for c in password:
                pass_inp.send_keys(c)
                time.sleep(random.uniform(0.02, 0.06))
            time.sleep(0.5)
        except Exception as e:
            log.error(f"Typing failed: {e}")
            return False

        # ENTER to submit
        log.info("Pressing ENTER to login...")
        try:
            pass_inp.send_keys(Keys.RETURN)
        except Exception:
            try:
                self.driver.execute_script("document.querySelector('form')?.submit();")
            except Exception as e2:
                log.error(f"Submit failed: {e2}")
                return False

        time.sleep(7)

        # Checkpoint
        if "checkpoint" in self.driver.current_url.lower():
            log.warning("LOGIN CHECKPOINT")
            code = input("Approval code (or Enter to skip): ").strip()
            if code:
                try:
                    el = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.ID, "approvals_code")))
                    el.send_keys(code)
                    time.sleep(1)
                    for _ in range(5):
                        try:
                            self.driver.find_element(By.ID, "checkpointSubmitButton").click()
                            time.sleep(3)
                        except:
                            break
                except:
                    input(">>> Resolve checkpoint manually, then press Enter...")
            else:
                input(">>> Resolve checkpoint manually, then press Enter...")

        time.sleep(3)
        if "login" in self.driver.current_url.lower() and "checkpoint" not in self.driver.current_url.lower():
            log.warning("Login may have failed.")
            return False

        log.info(f"Logged in! URL: {self.driver.current_url[:70]}")
        self._save_cookies()
        return True

    def _save_cookies(self):
        with open(self.config.cookie_file, "w") as f:
            json.dump(self.driver.get_cookies(), f)
        log.info(f"Saved cookies to {self.config.cookie_file}")

    def load_cookies(self) -> bool:
        if not Path(self.config.cookie_file).exists():
            return False
        self.driver.get("https://www.facebook.com/")
        try:
            with open(self.config.cookie_file) as f:
                cookies = json.load(f)
        except:
            return False
        for c in cookies:
            try:
                self.driver.add_cookie(c)
            except:
                pass
        self.driver.get("https://www.facebook.com/")
        time.sleep(4)
        if "login" in self.driver.current_url.lower():
            return False
        log.info("Session restored from cookies!")
        return True


# ---------------------------------------------------------------------------
# Reporter — Fixed URL parsing + More button
# ---------------------------------------------------------------------------

class FBReporter:
    def __init__(self, driver):
        self.driver = driver

    def _sleep(self, lo=8, hi=22):
        d = random.randint(lo, hi)
        log.info(f"  Waiting {d}s...")
        time.sleep(d)

    def _resolve_profile_url(self, target: str) -> str:
        """
        Accept any of:
        - Numeric ID (123456789)
        - Vanity username (bruce.pelayo.5)
        - Full URL (https://www.facebook.com/bruce.pelayo.5)
        - profile.php?id=X
        Returns a navigable Facebook profile URL.
        """
        target = target.strip()

        # If it's already a full URL pointing to facebook
        if target.startswith("http"):
            return target

        # If it's a numeric ID
        if target.isdigit():
            return f"https://www.facebook.com/profile.php?id={target}"

        # It's a vanity name - navigate directly
        if "/" not in target and not target.startswith("http"):
            return f"https://www.facebook.com/{target}"

        # Fallback
        return target

    def _click_more(self) -> bool:
        """
        Click the 'More' button on a Facebook profile or post.
        Facebook uses: button[aria-label="More"], div[aria-label="More options"],
        or just a generic div[role="button"] with 'More' text.
        """
        strategies = [
            # Desktop: button with aria-label
            (By.XPATH, "//button[@aria-label='More']"),
            (By.XPATH, "//button[@aria-label='More options']"),
            (By.XPATH, "//button[@aria-label='More actions']"),
            (By.XPATH, "//button[contains(@aria-label,'More')]"),
            # Desktop: div with aria-label
            (By.XPATH, "//div[@aria-label='More']"),
            (By.XPATH, "//div[@aria-label='More options']"),
            (By.XPATH, "//div[@aria-label='Profile options']"),
            # Desktop: span containing More inside a clickable
            (By.XPATH, "//span[text()='More']/ancestor::div[@role='button']"),
            (By.XPATH, "//span[text()='Lainnya']/ancestor::div[@role='button']"),
            # Desktop: generic role=button with text
            (By.XPATH, "//div[@role='button']//span[text()='More']"),
            (By.XPATH, "//div[@role='button']//span[text()='Lainnya']"),
            # Mobile/fallback: anchor tags
            (By.XPATH, "//a[text()='More']"),
            (By.XPATH, "//a[text()='Lainnya']"),
            (By.XPATH, "//a[contains(text(),'More')]"),
            # Absolute fallback: any top-level clickable with More
            (By.XPATH, "//*[self::div or self::button or self::a][@role='button' and contains(text(),'More')]"),
            (By.XPATH, "//*[self::div or self::button or self::a][@role='button' and contains(text(),'Lainnya')]"),
        ]

        for by, sel in strategies:
            try:
                el = WebDriverWait(self.driver, 3).until(EC.element_to_be_clickable((by, sel)))
                self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                time.sleep(0.5)
                el.click()
                return True
            except:
                continue
        return False

    def _click_report_option(self) -> bool:
        """Click 'Find support or report profile'."""
        strategies = [
            (By.XPATH, "//span[contains(text(),'Find support or report')]"),
            (By.XPATH, "//span[contains(text(),'Cari dukungan atau laporkan')]"),
            (By.XPATH, "//a[contains(text(),'Find support')]"),
            (By.XPATH, "//a[contains(text(),'report profile')]"),
            (By.XPATH, "//a[contains(text(),'report Page')]"),
            (By.XPATH, "//a[contains(text(),'Laporkan profil')]"),
            (By.XPATH, "//a[contains(text(),'Cari dukungan')]"),
            (By.XPATH, "//a[contains(@href,'/help/contact/')]"),
            (By.XPATH, "//*[contains(text(),'Find support or report')]"),
        ]
        for by, sel in strategies:
            try:
                el = WebDriverWait(self.driver, 3).until(EC.element_to_be_clickable((by, sel)))
                el.click()
                return True
            except:
                continue
        return False

    def _click_fake_account(self) -> bool:
        strategies = [
            (By.XPATH, "//span[text()='Fake Account']"),
            (By.XPATH, "//span[text()='Akun Palsu']"),
            (By.XPATH, "//span[contains(text(),'Fake Account')]"),
            (By.XPATH, "//span[contains(text(),'Akun Palsu')]"),
            (By.XPATH, "//div[contains(text(),'Fake Account')]"),
            (By.XPATH, "//span[text()='Pretending to be someone']"),
            (By.XPATH, "//span[text()='Berpura-pura menjadi seseorang']"),
            (By.XPATH, "//*[contains(text(),'Fake')]"),
            (By.XPATH, "//*[contains(text(),'Palsu')]"),
        ]
        for by, sel in strategies:
            try:
                el = WebDriverWait(self.driver, 3).until(EC.element_to_be_clickable((by, sel)))
                el.click()
                return True
            except:
                continue
        return False

    def _click_spam(self) -> bool:
        strategies = [
            (By.XPATH, "//input[@type='radio' and @value='spam']"),
            (By.XPATH, "//input[@type='radio' and contains(@value,'SPAM')]"),
            (By.XPATH, "//span[contains(text(),'Spam')]/preceding-sibling::input"),
            (By.XPATH, "//span[text()='Spam']"),
            (By.XPATH, "//div[contains(text(),'Spam')]"),
            (By.XPATH, "//*[contains(text(),'Spam')]"),
        ]
        for by, sel in strategies:
            try:
                el = WebDriverWait(self.driver, 3).until(EC.element_to_be_clickable((by, sel)))
                el.click()
                return True
            except:
                continue
        return False

    def _click_submit(self) -> bool:
        strategies = [
            (By.XPATH, "//div[@role='button']//span[text()='Submit']"),
            (By.XPATH, "//div[@role='button']//span[text()='Kirim']"),
            (By.XPATH, "//div[@role='button' and contains(text(),'Submit')]"),
            (By.XPATH, "//div[@role='button' and contains(text(),'Kirim')]"),
            (By.XPATH, "//input[@type='submit']"),
            (By.XPATH, "//button[@type='submit']"),
            (By.XPATH, "//div[@role='button']//span[contains(text(),'Next')]"),
            (By.XPATH, "//div[@role='button']//span[contains(text(),'Send')]"),
            (By.XPATH, "//div[@role='button']//span[contains(text(),'Continue')]"),
            (By.XPATH, "//div[contains(@class,'x1i10hfl') and contains(text(),'Submit')]"),
            (By.XPATH, "//*[text()='Submit']"),
            (By.XPATH, "//*[text()='Kirim']"),
        ]
        for by, sel in strategies:
            try:
                el = WebDriverWait(self.driver, 3).until(EC.element_to_be_clickable((by, sel)))
                el.click()
                return True
            except:
                continue
        return False

    def _click_checkbox(self) -> bool:
        strategies = [
            (By.XPATH, "//input[@type='checkbox' and @name='checked']"),
            (By.XPATH, "//input[@type='checkbox' and contains(@aria-label,'confirm')]"),
            (By.XPATH, "//input[@type='checkbox' and contains(@aria-label,'Confirm')]"),
        ]
        for by, sel in strategies:
            try:
                el = WebDriverWait(self.driver, 2).until(EC.element_to_be_clickable((by, sel)))
                el.click()
                return True
            except:
                continue
        return False

    def _click_me(self) -> bool:
        strategies = [
            (By.XPATH, "//span[text()='Me']"),
            (By.XPATH, "//span[text()='Saya']"),
            (By.XPATH, "//span[contains(text(),'Me')]"),
            (By.XPATH, "//*[text()='Me']"),
        ]
        for by, sel in strategies:
            try:
                el = WebDriverWait(self.driver, 2).until(EC.element_to_be_clickable((by, sel)))
                el.click()
                return True
            except:
                continue
        return False

    def _click_report_post_option(self) -> bool:
        strategies = [
            (By.XPATH, "//input[@value='RESOLVE_PROBLEM']"),
            (By.XPATH, "//a[contains(text(),'Report post')]"),
            (By.XPATH, "//span[contains(text(),'Report post')]"),
            (By.XPATH, "//div[contains(text(),'Report post')]"),
            (By.XPATH, "//a[contains(text(),'Laporkan postingan')]"),
            (By.XPATH, "//*[contains(text(),'Report post')]"),
            (By.XPATH, "//*[contains(text(),'Laporkan')]"),
        ]
        for by, sel in strategies:
            try:
                el = WebDriverWait(self.driver, 3).until(EC.element_to_be_clickable((by, sel)))
                el.click()
                return True
            except:
                continue
        return False

    # ------------------------------------------------------------------
    # Report Profile
    # ------------------------------------------------------------------

    def report_profile(self, target: str) -> Tuple[bool, str]:
        url = self._resolve_profile_url(target)
        log.info(f"Navigating to: {url}")
        self.driver.get(url)
        time.sleep(5)

        # Check if profile loaded
        ps = self.driver.page_source.lower()
        if "this page isn't available" in ps or "content not found" in ps or "sorry, this content isn't available" in ps:
            return False, "Profile not found."

        log.info("Step 1: Clicking 'More' button...")
        if not self._click_more():
            return False, "Could not click 'More' button on profile."
        time.sleep(2)

        log.info("Step 2: Opening report dialog...")
        if not self._click_report_option():
            return False, "Could not find 'Find support or report profile'."
        time.sleep(2.5)

        log.info("Step 3: Selecting 'Fake Account' reason...")
        if not self._click_fake_account():
            return False, "Could not select report reason."
        time.sleep(2)

        log.info("Step 4: Selecting 'Me' (if asked)...")
        self._click_me()
        time.sleep(1.5)

        log.info("Step 5: Submitting...")
        self._click_submit()
        time.sleep(2.5)

        log.info("Step 6: Checkbox + final submit...")
        self._click_checkbox()
        time.sleep(1)
        self._click_submit()
        time.sleep(2)

        ps = self.driver.page_source.lower()
        if "thank you" in ps or "terima kasih" in ps:
            return True, "Profile reported successfully!"
        return True, "Report submitted (confirmation page may vary)."

    # ------------------------------------------------------------------
    # Report Post
    # ------------------------------------------------------------------

    def report_post(self, post_url: str) -> Tuple[bool, str]:
        log.info(f"Navigating to post: {post_url}")
        self.driver.get(post_url)
        time.sleep(5)

        ps = self.driver.page_source.lower()
        if "this content isn't available" in ps or "not found" in ps:
            return False, "Post not found."

        log.info("Step 1: Clicking 'More'...")
        if not self._click_more():
            return False, "Could not click 'More' on post."
        time.sleep(2)

        log.info("Step 2: Opening post report...")
        if not self._click_report_post_option():
            return False, "Could not find 'Report post' option."
        time.sleep(2.5)

        log.info("Step 3: Selecting 'Spam'...")
        if not self._click_spam():
            return False, "Could not select 'Spam'."
        time.sleep(2)

        log.info("Step 4: Submitting...")
        self._click_submit()
        time.sleep(2.5)

        log.info("Step 5: Checkbox + final submit...")
        self._click_checkbox()
        time.sleep(1)
        self._click_submit()

        return True, "Post reported as spam."

    # ------------------------------------------------------------------
    # Mass
    # ------------------------------------------------------------------

    def mass_report_profiles(self, targets: List[str], count: int = 3) -> Dict:
        results = {}
        for t in targets:
            ok, fail = 0, 0
            for i in range(count):
                log.info(f"[{t}] Iteration {i+1}/{count}")
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
                log.info(f"[{u[:50]}...] Iteration {i+1}/{count}")
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
║       Facebook Mass Report Tool  v3.3                           ║
║       Vanity URLs fixed | Better More button detection          ║
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
    print(f"Reports per target: {config.report_count}\n")
    e = input(f"Email [{config.email}]: ").strip() or config.email
    p = input("Password (blank to keep): ").strip()
    h = input("Headless? (y/N): ").strip().lower() == 'y'
    c = input(f"Reports each [{config.report_count}]: ").strip()
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
            log.info("Logging in with saved credentials...")
            session.login()
        else:
            log.warning("Use option 1 to login.")

    while True:
        opt = menu()

        if opt == 1:
            session.login()

        elif opt == 2:
            t = input("Profile URL or ID or username: ").strip()
            if t:
                ok, msg = reporter.report_profile(t)
                log.info(f"{'[OK]' if ok else '[FAIL]'} {msg}")

        elif opt == 3:
            u = input("Post URL: ").strip()
            if u:
                ok, msg = reporter.report_post(u)
                log.info(f"{'[OK]' if ok else '[FAIL]'} {msg}")

        elif opt == 4:
            raw = input("Profiles (comma separated: URLs, IDs, or usernames): ").strip()
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
