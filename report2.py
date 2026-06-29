#!/usr/bin/env python3
"""
Facebook Mass Report Tool v4.0 — BULLETPROOF
=============================================
- Fast login (paste credentials at once, not char-by-char)
- 2FA auto-detection + prompt
- mbasic.facebook.com for reliable profile reporting
- JS click() to bypass overlays
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

# --- Config ---
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

# --- Browser ---
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

# --- Session ---
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

        # Find email
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

        # Fill fields FAST (not char by char)
        email_inp.clear()
        email_inp.send_keys(email)
        pass_inp.clear()
        pass_inp.send_keys(pw)
        time.sleep(0.5)

        # Press ENTER
        log.info("Pressing ENTER to submit...")
        pass_inp.send_keys(Keys.RETURN)
        time.sleep(5)

        # Handle 2FA
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
                except:
                    pass
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

# --- Reporter ---
class Reporter:
    def __init__(self, driver):
        self.driver = driver

    def js_click(self, by, sel, timeout=5):
        """Find element and click via JavaScript (bypasses overlays)."""
        try:
            el = WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((by, sel)))
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            time.sleep(0.3)
            self.driver.execute_script("arguments[0].click();", el)
            return True
        except: return False

    def click_text(self, text, tag="*", timeout=3):
        """Click element containing text."""
        return self.js_click(By.XPATH, f"//{tag}[contains(text(),'{text}')]", timeout)

    def click_value(self, value, timeout=3):
        """Click input with matching value attribute."""
        return self.js_click(By.XPATH, f"//input[@type='submit' and contains(@value,'{value}')]", timeout)

    # --- Profile Report via mbasic ---
    def report_profile(self, target: str) -> Tuple[bool, str]:
        """Report profile using mbasic.facebook.com."""
        # Normalize target to mbasic URL
        target = target.strip()
        if target.startswith("http"):
            parsed = urlparse(target)
            path = parsed.path.strip("/")
            if "profile.php" in path:
                uid = parse_qs(parsed.query).get("id", [None])[0]
                if uid:
                    url = f"https://mbasic.facebook.com/profile.php?id={uid}"
                else:
                    url = target.replace("www.", "mbasic.")
            else:
                username = path.split("/")[0] if path else ""
                url = f"https://mbasic.facebook.com/{username}" if username else target
        elif target.isdigit():
            url = f"https://mbasic.facebook.com/profile.php?id={target}"
        else:
            url = f"https://mbasic.facebook.com/{target}"

        log.info(f"Opening: {url}")
        self.driver.get(url)
        time.sleep(4)

        # Check if loaded
        if "this page isn't available" in self.driver.page_source.lower():
            return False, "Profile not found"

        # Step 1: Click "More" link (mbasic uses simple <a> tags)
        log.info("Step 1: Clicking 'More'...")
        if not self.click_text("More", "a") and not self.click_text("Lainnya", "a"):
            # Try partial_match
            try:
                els = self.driver.find_elements(By.XPATH, "//a[contains(text(),'More') or contains(text(),'Lainnya')]")
                if els:
                    self.driver.execute_script("arguments[0].click();", els[0])
                else:
                    return False, "No 'More' link found"
            except:
                return False, "No 'More' link found"
        time.sleep(3)

        # Step 2: Find "Find support or report profile" link
        log.info("Step 2: Finding report link...")
        found_report = False
        for txt in ["Find support or report", "Report", "Laporkan profil", "Cari dukungan", "report"]:
            try:
                els = self.driver.find_elements(By.PARTIAL_LINK_TEXT, txt)
                if els:
                    self.driver.execute_script("arguments[0].click();", els[0])
                    found_report = True
                    log.info(f"Clicked report via: '{txt}'")
                    break
            except: continue
        if not found_report:
            return False, "No report link found"
        time.sleep(3)

        # Step 3: Select "Fake Account"
        log.info("Step 3: Selecting 'Fake Account'...")
        clicked = False
        for val in ["Fake Account", "Akun Palsu", "Fake", "Pretending"]:
            if self.click_value(val):
                clicked = True
                break
        if not clicked:
            # Try any submit button
            try:
                btns = self.driver.find_elements(By.XPATH, "//input[@type='submit']")
                if btns:
                    self.driver.execute_script("arguments[0].click();", btns[0])
                    clicked = True
            except: pass
        if not clicked:
            return False, "Could not select Fake Account"
        time.sleep(2)

        # Step 4: "Me" if present
        self.click_value("Me")
        self.click_value("Saya")
        time.sleep(1)

        # Step 5: Submit everything
        log.info("Step 4: Submitting...")
        for _ in range(3):
            try:
                btns = self.driver.find_elements(By.XPATH, "//input[@type='submit']")
                if not btns:
                    break
                self.driver.execute_script("arguments[0].click();", btns[0])
                time.sleep(2)
            except: break

        if "thank" in self.driver.page_source.lower() or "terima" in self.driver.page_source.lower():
            return True, "Profile reported successfully!"
        return True, "Report submitted."

    # --- Post Report via www (posts don't work well on mbasic) ---
    def report_post(self, post_url: str) -> Tuple[bool, str]:
        log.info(f"Opening post: {post_url}")
        self.driver.get(post_url)
        time.sleep(5)

        if "not found" in self.driver.page_source.lower() or "unavailable" in self.driver.page_source.lower():
            return False, "Post not found"

        # Click More via JS
        log.info("Step 1: Clicking 'More'...")
        more_found = False
        for sel in [
            "//button[@aria-label='More']",
            "//button[@aria-label='More options']",
            "//div[@aria-label='More']",
            "//div[@aria-label='More options']",
            "//span[text()='More']/ancestor::div[@role='button']",
            "//span[contains(text(),'More')]/ancestor::*[@role='button']",
            "//a[text()='More']",
        ]:
            if self.js_click(By.XPATH, sel, 3):
                more_found = True
                break
        if not more_found:
            return False, "Could not click More on post"
        time.sleep(2)

        # Report post
        log.info("Step 2: Report post option...")
        report_found = False
        for sel in [
            "//input[@value='RESOLVE_PROBLEM']",
            "//a[contains(text(),'Report post')]",
            "//span[contains(text(),'Report post')]",
            "//div[contains(text(),'Report post')]",
            "//a[contains(text(),'Laporkan')]",
        ]:
            if self.js_click(By.XPATH, sel, 3):
                report_found = True
                break
        if not report_found:
            return False, "Could not find Report post option"
        time.sleep(2)

        # Spam
        log.info("Step 3: Selecting Spam...")
        if not self.js_click(By.XPATH, "//input[@type='radio' and @value='spam']", 3):
            if not self.click_text("Spam"):
                return False, "Could not select Spam"
        time.sleep(1.5)

        # Submit
        log.info("Step 4: Submitting...")
        for sel in [
            "//div[@role='button']//span[text()='Submit']",
            "//div[@role='button']//span[text()='Kirim']",
            "//input[@type='submit']",
            "//button[@type='submit']",
            "//div[@role='button']//span[text()='Send']",
        ]:
            if self.js_click(By.XPATH, sel, 2):
                break
        time.sleep(2)

        # Checkbox
        self.js_click(By.XPATH, "//input[@type='checkbox' and @name='checked']", 2)
        time.sleep(1)

        # Final submit
        for sel in [
            "//div[@role='button']//span[text()='Submit']",
            "//div[@role='button']//span[text()='Kirim']",
            "//input[@type='submit']",
            "//button[@type='submit']",
        ]:
            if self.js_click(By.XPATH, sel, 2):
                break

        return True, "Post reported as spam"

    # Mass
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
                if i+1 < count:
                    time.sleep(random.randint(10, 25))
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
                if i+1 < count:
                    time.sleep(random.randint(10, 25))
            results[u] = (ok, fail)
        return results

# --- CLI ---
def banner():
    print("\n" + "="*60)
    print("  FB Mass Report v4.0 — mbasic approach + JS clicks")
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
            t = input("Profile (URL, ID, or username): ").strip()
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
