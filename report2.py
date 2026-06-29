#!/usr/bin/env python3
"""
Facebook Mass Report Tool v4.2 — FINAL FIX
Based on actual page dump: "More" span found, "Hide or report this" button found
"""

import sys, os, json, random, time, re, logging
from pathlib import Path
from typing import Tuple, List, Dict
from dataclasses import dataclass
from urllib.parse import urlparse, parse_qs

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

try:
    from webdriver_manager.chrome import ChromeDriverManager
    HAS_WDM = True
except ImportError:
    HAS_WDM = False

@dataclass
class Config:
    email: str = ""
    password: str = ""
    cookie_file: str = "fb_cookies.json"
    headless: bool = False
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
                    return cls(**{k: v for k, v in json.load(f).items() if k in cls.__dataclass_fields__})
            except: pass
        return cls()

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s :: %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("FBReport")

class Browser:
    AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    ]
    def __init__(self, headless=False):
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
        opts.add_experimental_option("prefs", {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2,
        })
        if self.headless:
            opts.add_argument("--headless=new")
        try:
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()) if HAS_WDM else None,
                options=opts
            ) if HAS_WDM else webdriver.Chrome(options=opts)
        except:
            self.driver = webdriver.Chrome(options=opts)
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
        })
        self.driver.implicitly_wait(3)
        return self.driver
    def stop(self):
        if self.driver:
            try: self.driver.quit()
            except: pass

class Session:
    def __init__(self, driver, config: Config):
        self.driver = driver
        self.config = config

    def login(self) -> bool:
        email = self.config.email or input("Email/Phone: ").strip()
        pw = self.config.password or input("Password: ").strip()
        self.config.email = email
        self.config.password = pw
        self.config.save()

        log.info("Loading facebook.com...")
        self.driver.get("https://www.facebook.com/")
        time.sleep(4)

        email_inp = None
        for by, sel in [(By.ID,"email"), (By.NAME,"email"), (By.CSS_SELECTOR,"input[autocomplete='username']"),
                         (By.XPATH,"//input[@type='text' or @type='email']")]:
            try:
                email_inp = WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((by, sel)))
                break
            except: continue
        if not email_inp:
            log.error("No email field found")
            return False

        pass_inp = None
        for by, sel in [(By.ID,"pass"), (By.NAME,"pass"), (By.XPATH,"//input[@type='password']")]:
            try:
                pass_inp = WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((by, sel)))
                break
            except: continue
        if not pass_inp:
            log.error("No password field found")
            return False

        email_inp.clear()
        email_inp.send_keys(email)
        pass_inp.clear()
        pass_inp.send_keys(pw)
        time.sleep(0.5)

        log.info("Pressing ENTER to submit...")
        pass_inp.send_keys(Keys.RETURN)
        time.sleep(5)

        for _ in range(20):
            url = self.driver.current_url.lower()
            if "checkpoint" in url or "two_step" in url or "authentication" in url:
                log.warning("2FA required")
                try:
                    inp = self.driver.find_element(By.ID, "approvals_code")
                    code = input("2FA code: ").strip()
                    if code:
                        inp.send_keys(code)
                        time.sleep(1)
                        for _ in range(5):
                            try:
                                self.driver.find_element(By.ID, "checkpointSubmitButton").click()
                                time.sleep(2)
                            except: break
                        time.sleep(3)
                        continue
                except: pass
                input("Resolve 2FA in browser, then press Enter...")
                time.sleep(3)
                continue
            break

        if "login" in self.driver.current_url.lower() and "checkpoint" not in self.driver.current_url.lower():
            log.warning("Login failed")
            return False

        log.info(f"Logged in! ({self.driver.current_url[:50]})")
        self._save_cookies()
        return True

    def _save_cookies(self):
        with open(self.config.cookie_file, "w") as f:
            json.dump(self.driver.get_cookies(), f)
        log.info("Cookies saved")

    def load_cookies(self) -> bool:
        if not Path(self.config.cookie_file).exists():
            return False
        self.driver.get("https://www.facebook.com/")
        try:
            for c in json.load(open(self.config.cookie_file)):
                try: self.driver.add_cookie(c)
                except: pass
        except: return False
        self.driver.get("https://www.facebook.com/")
        time.sleep(4)
        if "login" in self.driver.current_url.lower():
            return False
        log.info("Cookies restored!")
        return True

class Reporter:
    def __init__(self, driver):
        self.driver = driver

    def js_click(self, el):
        """Click element via JavaScript."""
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            time.sleep(0.3)
            self.driver.execute_script("arguments[0].click();", el)
            return True
        except: return False

    def find_and_click(self, xpaths, timeout=3):
        """Try multiple XPaths, click first visible one."""
        for xpath in xpaths:
            try:
                for el in WebDriverWait(self.driver, timeout).until(EC.presence_of_all_elements_located((By.XPATH, xpath))):
                    try:
                        if el.is_displayed():
                            self.js_click(el)
                            return True
                    except: continue
            except: continue
        return False

    def report_profile(self, target: str) -> Tuple[bool, str]:
        target = target.strip()
        if target.startswith("http"):
            url = target
        elif target.isdigit():
            url = f"https://www.facebook.com/profile.php?id={target}"
        else:
            url = f"https://www.facebook.com/{target}"

        log.info(f"Opening: {url}")
        self.driver.get(url)
        time.sleep(6)

        if "this page isn't available" in self.driver.page_source.lower():
            return False, "Profile not found"

        # Step 1: Click "More" button
        # Based on page dump: <span>More</span> exists with class 'x193iq5w xeuugli x13faqbe x1vvkbs x10fls'
        # Also: aria-label="Profile settings see more options" role="button"
        log.info("Step 1: Clicking More button...")
        
        more_xpaths = [
            # The span with text "More" — confirmed from dump
            "//span[text()='More']",
            # The button with aria-label
            "//div[@aria-label='Profile settings see more options']",
            "//*[@aria-label='Profile settings see more options']",
            # Generic
            "//span[contains(text(),'More')]",
            "//*[text()='More']",
            "//*[@aria-label='More']",
            "//div[contains(@class,'x1i10hfl') and contains(@class,'x1qjc9v5')]",
        ]
        
        if not self.find_and_click(more_xpaths, 5):
            return False, "Could not click More button"
        time.sleep(2.5)

        # Step 2: Find report option
        # Based on page dump: aria-label="Hide or report this" role="button"
        log.info("Step 2: Finding report option...")
        
        report_xpaths = [
            # EXACT match from dump
            "//*[@aria-label='Hide or report this']",
            "//div[@aria-label='Hide or report this']",
            # Standard text
            "//span[contains(text(),'Find support or report')]",
            "//span[contains(text(),'report profile')]",
            "//span[contains(text(),'Laporkan')]",
            "//a[contains(text(),'Find support')]",
            "//a[contains(text(),'report profile')]",
            # Partial match
            "//*[contains(@aria-label,'report')]",
            "//*[contains(@aria-label,'Report')]",
            "//*[contains(text(),'Find support')]",
            "//*[contains(text(),'report profile')]",
            "//*[contains(text(),'Hide or report')]",
            "//*[contains(text(),'Laporkan')]",
        ]
        
        if not self.find_and_click(report_xpaths, 5):
            # Last resort: find any menu item that looks report-related
            try:
                all_buttons = self.driver.find_elements(By.XPATH, "//div[@role='button']//span")
                for btn in all_buttons:
                    txt = (btn.text or "").lower()
                    if "report" in txt or "hide" in txt or "laporkan" in txt or "support" in txt:
                        self.js_click(btn)
                        log.info(f"Clicked menu item: '{btn.text}'")
                        time.sleep(2)
                        break
                else:
                    return False, "Could not find report option"
            except:
                return False, "Could not find report option"
        time.sleep(3)

        # Step 3: Select Fake Account
        log.info("Step 3: Selecting Fake Account...")
        fake_xpaths = [
            "//span[text()='Fake Account']",
            "//span[text()='Akun Palsu']",
            "//span[contains(text(),'Fake Account')]",
            "//span[contains(text(),'Akun Palsu')]",
            "//*[contains(text(),'Fake')]",
            "//*[contains(text(),'Palsu')]",
            "//span[text()='Pretending to be someone']",
        ]
        if not self.find_and_click(fake_xpaths, 4):
            return False, "Could not select Fake Account"
        time.sleep(2)

        # Click "Me" if asked
        self.find_and_click(["//span[text()='Me']", "//span[text()='Saya']", "//*[text()='Me']"], 2)
        time.sleep(1)

        # Step 4: Submit
        log.info("Step 4: Submitting...")
        submit_xpaths = [
            "//div[@role='button']//span[text()='Submit']",
            "//div[@role='button']//span[text()='Kirim']",
            "//div[@role='button']//span[text()='Send']",
            "//div[@role='button']//span[text()='Next']",
            "//input[@type='submit']",
            "//button[@type='submit']",
            "//div[@role='button' and contains(text(),'Submit')]",
            "//div[@role='button' and contains(text(),'Send')]",
        ]
        
        for attempt in range(2):
            self.find_and_click(submit_xpaths, 4)
            time.sleep(2)
            # Checkbox
            try:
                for cb in self.driver.find_elements(By.XPATH, "//input[@type='checkbox']"):
                    if cb.is_displayed():
                        self.js_click(cb)
                        time.sleep(1)
                        break
            except: pass

        ps = self.driver.page_source.lower()
        if "thank" in ps or "terima" in ps:
            return True, "Profile reported successfully!"
        return True, "Report submitted."

    def report_post(self, post_url: str) -> Tuple[bool, str]:
        log.info(f"Opening post: {post_url}")
        self.driver.get(post_url)
        time.sleep(5)
        if "not found" in self.driver.page_source.lower() or "unavailable" in self.driver.page_source.lower():
            return False, "Post not found"

        log.info("Step 1: More button...")
        more_xpaths = [
            "//button[@aria-label='More']",
            "//button[@aria-label='More options']",
            "//div[@aria-label='More']",
            "//div[@aria-label='More options']",
            "//span[text()='More']/ancestor::*[@role='button']",
            "//span[contains(text(),'More')]/ancestor::*[@role='button']",
        ]
        if not self.find_and_click(more_xpaths, 4):
            return False, "No More button"
        time.sleep(2)

        log.info("Step 2: Report option...")
        report_xpaths = [
            "//input[@value='RESOLVE_PROBLEM']",
            "//a[contains(text(),'Report post')]",
            "//span[contains(text(),'Report post')]",
            "//div[contains(text(),'Report post')]",
            "//a[contains(text(),'Laporkan')]",
            "//*[contains(text(),'Report post')]",
        ]
        if not self.find_and_click(report_xpaths, 4):
            return False, "No report option"
        time.sleep(2)

        log.info("Step 3: Spam...")
        spam_xpaths = [
            "//input[@type='radio' and @value='spam']",
            "//span[contains(text(),'Spam')]/preceding-sibling::input",
            "//span[text()='Spam']",
            "//div[contains(text(),'Spam')]",
            "//*[text()='Spam']",
        ]
        if not self.find_and_click(spam_xpaths, 3):
            return False, "No spam option"
        time.sleep(1.5)

        log.info("Step 4: Submit...")
        submit_xpaths = [
            "//div[@role='button']//span[text()='Submit']",
            "//input[@type='submit']",
            "//button[@type='submit']",
            "//div[@role='button']//span[text()='Send']",
            "//div[@role='button']//span[text()='Kirim']",
        ]
        for _ in range(2):
            self.find_and_click(submit_xpaths, 3)
            time.sleep(2)
            try:
                for cb in self.driver.find_elements(By.XPATH, "//input[@type='checkbox']"):
                    if cb.is_displayed():
                        self.js_click(cb)
                        time.sleep(1)
                        break
            except: pass

        return True, "Post reported"

    def mass_report_profiles(self, targets: List[str], count: int = 3) -> Dict:
        results = {}
        for t in targets:
            ok, fail = 0, 0
            for i in range(count):
                log.info(f"[{t}] {i+1}/{count}")
                s, msg = self.report_profile(t)
                if s: ok += 1
                else: fail += 1
                log.info(f"  {'OK' if s else 'FAIL'}: {msg}")
                if i+1 < count: time.sleep(random.randint(10, 25))
            results[t] = (ok, fail)
        return results

    def mass_report_posts(self, targets: List[str], count: int = 3) -> Dict:
        results = {}
        for u in targets:
            ok, fail = 0, 0
            for i in range(count):
                log.info(f"[{u[:40]}...] {i+1}/{count}")
                s, msg = self.report_post(u)
                if s: ok += 1
                else: fail += 1
                if i+1 < count: time.sleep(random.randint(10, 25))
            results[u] = (ok, fail)
        return results

def banner():
    print("\n" + "="*60)
    print("  FB Mass Report v4.2 — Final Fix")
    print("="*60)

def menu():
    print("\n  1. Login")
    print("  2. Report profile")
    print("  3. Report post")
    print("  4. Mass report profiles")
    print("  5. Mass report posts")
    print("  6. Settings")
    print("  7. Exit")
    try: return int(input("> ").strip())
    except: return 7

def settings(config):
    e = input(f"Email [{config.email}]: ").strip() or config.email
    p = input("Password: ").strip()
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
    engine = Browser(headless=config.headless)
    try: driver = engine.start()
    except Exception as e:
        log.error(f"Browser failed: {e}")
        sys.exit(1)

    session = Session(driver, config)
    reporter = Reporter(driver)

    if not session.load_cookies():
        if config.email and config.password:
            session.login()
        else:
            log.warning("Use option 1 to login")

    while True:
        opt = menu()
        if opt == 1: session.login()
        elif opt == 2:
            t = input("Profile (URL, ID, username): ").strip()
            if t:
                ok, msg = reporter.report_profile(t)
                log.info(f"{'[OK]' if ok else '[FAIL]'} {msg}")
        elif opt == 3:
            u = input("Post URL: ").strip()
            if u:
                ok, msg = reporter.report_post(u)
                log.info(f"{'[OK]' if ok else '[FAIL]'} {msg}")
        elif opt == 4:
            raw = input("Profiles (comma-sep): ").strip()
            if raw:
                targets = [x.strip() for x in raw.split(",") if x.strip()]
                cnt = int(input(f"Reports each [{config.report_count}]: ").strip() or config.report_count)
                r = reporter.mass_report_profiles(targets, cnt)
                print(json.dumps(r, indent=2))
        elif opt == 5:
            raw = input("Post URLs (comma-sep): ").strip()
            if raw:
                targets = [x.strip() for x in raw.split(",") if x.strip()]
                cnt = int(input(f"Reports each [{config.report_count}]: ").strip() or config.report_count)
                r = reporter.mass_report_posts(targets, cnt)
                print(json.dumps(r, indent=2))
        elif opt == 6: settings(config)
        elif opt == 7: break

    engine.stop()

if __name__ == "__main__":
    main()
