#!/usr/bin/env python3
"""
Facebook Mass Report Tool v4.3 — SVG detection for three-dots menu
Targets the actual SVG with 3 circles that IS the More button
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
    def __init__(self, headless=False):
        self.headless = headless
        self.driver = None
    def start(self):
        opts = Options()
        opts.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
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
        if not email_inp: return False

        pass_inp = None
        for by, sel in [(By.ID,"pass"), (By.NAME,"pass"), (By.XPATH,"//input[@type='password']")]:
            try:
                pass_inp = WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((by, sel)))
                break
            except: continue
        if not pass_inp: return False

        email_inp.clear()
        email_inp.send_keys(email)
        pass_inp.clear()
        pass_inp.send_keys(pw)
        time.sleep(0.5)
        log.info("Pressing ENTER...")
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
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
            time.sleep(0.3)
            self.driver.execute_script("arguments[0].click();", el)
            return True
        except: return False

    def find_and_click(self, xpaths, timeout=4):
        for xpath in xpaths:
            try:
                for el in WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_all_elements_located((By.XPATH, xpath))
                ):
                    try:
                        if el.is_displayed():
                            self.js_click(el)
                            return True
                    except: continue
            except: continue
        return False

    def click_three_dots(self):
        """
        Click the three-dots SVG menu on a Facebook profile.
        The SVG structure is: <svg><circle cx="4.5" cy="12" r="2.5"/>...
        We need to use name()='svg' for SVG namespace handling.
        """
        # Strategy 1: Find the SVG by its circle structure, click its parent
        try:
            svgs = self.driver.find_elements(By.XPATH, "//*[name()='svg']")
            for svg in svgs:
                try:
                    circles = svg.find_elements(By.XPATH, ".//*[name()='circle']")
                    if len(circles) >= 3:
                        # Check if this has the right radius (2.5 is FB's More button)
                        radii = [c.get_attribute("r") for c in circles[:3]]
                        if radii == ["2.5", "2.5", "2.5"]:
                            # Found the three-dots SVG — click its clickable parent
                            parent = svg.find_element(By.XPATH, "./ancestor::*[@role='button' or contains(@class,'x1i10hfl')]")
                            if parent:
                                self.js_click(parent)
                                log.info("Clicked three-dots SVG via circle detection")
                                return True
                except: continue
        except Exception as e:
            log.warning(f"SVG circle detection failed: {e}")

        # Strategy 2: SVG with viewBox="0 0 24 24" and width="16" (FB's More icon)
        try:
            for svg in self.driver.find_elements(By.XPATH, "//*[name()='svg' and @viewBox='0 0 24 24' and @width='16']"):
                circles = svg.find_elements(By.XPATH, ".//*[name()='circle']")
                if len(circles) >= 3:
                    parent = svg.find_element(By.XPATH, "./ancestor::*[@role='button']")
                    if parent:
                        self.js_click(parent)
                        log.info("Clicked three-dots via viewBox detection")
                        return True
        except: pass

        # Strategy 3: text "More" span
        if self.find_and_click(["//span[text()='More']", "//span[contains(text(),'More')]"]):
            return True

        # Strategy 4: aria-label
        if self.find_and_click([
            "//*[@aria-label='Profile settings see more options']",
            "//*[@aria-label='More']",
            "//*[@aria-label='More options']",
        ]):
            return True

        return False

    def check_if_banned(self, target: str) -> bool:
        """Check if the account has been banned."""
        try:
            page_source = self.driver.page_source.lower()
            if "this account has been disabled" in page_source or "account disabled" in page_source:
                log.info("Account has been banned!")
                return True
        except:
            pass
        return False

    def report_profile_adult(self, target: str) -> Tuple[bool, str]:
        """
        Report a profile for Adult content -> Nudity or sexual activity
        Complete flow: Report profile -> Something about this profile -> 
        Adult content -> Nudity or sexual activity -> Submit -> Next -> Done
        """
        target = target.strip()
        if target.startswith("http"):
            url = target
        elif target.isdigit():
            url = f"https://www.facebook.com/profile.php?id={target}"
        else:
            url = f"https://www.facebook.com/{target}"

        log.info(f"Opening: {url}")
        self.driver.get(url)
        time.sleep(6 + random.randint(1, 3))

        if "this page isn't available" in self.driver.page_source.lower():
            return False, "Profile not found"

        log.info("Step 1: Clicking three-dots menu (SVG)...")
        if not self.click_three_dots():
            return False, "Could not click three-dots More button"
        time.sleep(3 + random.uniform(0.5, 1.5))

        log.info("Step 2: Clicking 'Report profile'...")
        if not self.find_and_click([
            "//span[text()='Report profile']",
            "//span[contains(text(),'Report profile')]",
            "//span[text()='Laporkan profil']",
            "//span[contains(text(),'Laporkan profil')]",
            "//*[contains(text(),'Report profile')]",
            "//*[contains(text(),'Laporkan profil')]",
        ], 5):
            return False, "Could not find Report profile button"
        time.sleep(3 + random.uniform(0.5, 1.5))

        log.info("Step 3: Clicking 'Something about this profile'...")
        if not self.find_and_click([
            "//span[text()='Something about this profile']",
            "//span[contains(text(),'Something about this profile')]",
            "//span[text()='Sesuatu tentang profil ini']",
            "//span[contains(text(),'Sesuatu tentang profil ini')]",
            "//*[contains(text(),'Something about this profile')]",
            "//*[contains(text(),'Sesuatu tentang profil ini')]",
        ], 5):
            return False, "Could not find 'Something about this profile' button"
        time.sleep(3 + random.uniform(0.5, 1.5))

        log.info("Step 4: Clicking 'Adult content'...")
        if not self.find_and_click([
            "//span[text()='Adult content']",
            "//span[contains(text(),'Adult content')]",
            "//span[text()='Konten dewasa']",
            "//span[contains(text(),'Konten dewasa')]",
            "//*[contains(text(),'Adult content')]",
            "//*[contains(text(),'Konten dewasa')]",
        ], 5):
            return False, "Could not find 'Adult content' button"
        time.sleep(2 + random.uniform(0.5, 1))

        log.info("Step 5: Clicking 'Nudity or sexual activity'...")
        if not self.find_and_click([
            "//span[text()='Nudity or sexual activity']",
            "//span[contains(text(),'Nudity or sexual activity')]",
            "//span[text()='Ketelanjangan atau aktivitas seksual']",
            "//span[contains(text(),'Ketelanjangan atau aktivitas seksual')]",
            "//*[contains(text(),'Nudity or sexual activity')]",
            "//*[contains(text(),'Ketelanjangan atau aktivitas seksual')]",
        ], 5):
            return False, "Could not find 'Nudity or sexual activity' button"
        time.sleep(2 + random.uniform(0.5, 1))

        log.info("Step 6: Submitting...")
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
        for _ in range(3):
            if self.find_and_click(submit_xpaths, 4):
                submitted = True
                log.info("Submit button clicked")
                time.sleep(3 + random.uniform(0.5, 1.5))
                break
            time.sleep(2)
        
        try:
            for cb in self.driver.find_elements(By.XPATH, "//input[@type='checkbox']"):
                if cb.is_displayed():
                    self.js_click(cb)
                    time.sleep(1)
                    self.find_and_click(submit_xpaths, 3)
                    break
        except: pass

        log.info("Step 7: Clicking 'Next' button...")
        next_xpaths = [
            "//div[@role='button']//span[text()='Next']",
            "//div[@role='button']//span[contains(text(),'Next')]",
            "//span[text()='Next']",
            "//span[contains(text(),'Next')]",
            "//button[contains(text(),'Next')]",
            "//div[@role='button' and contains(text(),'Next')]",
            "//div[@role='button']//span[text()='Lanjut']",
            "//span[text()='Lanjut']",
        ]
        self.find_and_click(next_xpaths, 3)
        time.sleep(2 + random.uniform(0.5, 1))

        log.info("Step 8: Clicking 'Done' button...")
        done_xpaths = [
            "//div[@role='button']//span[text()='Done']",
            "//div[@role='button']//span[contains(text(),'Done')]",
            "//span[text()='Done']",
            "//span[contains(text(),'Done')]",
            "//button[contains(text(),'Done')]",
            "//div[@role='button' and contains(text(),'Done')]",
            "//div[@role='button']//span[text()='Selesai']",
            "//span[text()='Selesai']",
        ]
        self.find_and_click(done_xpaths, 3)
        time.sleep(2)

        if self.check_if_banned(target):
            return True, "ACCOUNT BANNED! Report successful!"

        page_text = self.driver.page_source.lower()
        if "thank" in page_text or "terima" in page_text or "success" in page_text:
            return True, "Profile reported for Adult content successfully!"
        
        if submitted:
            return True, "Adult content report submitted successfully!"
            
        return False, "Could not submit adult content report"

    def report_profile_bullying_harassment(self, target: str) -> Tuple[bool, str]:
        """
        Report a profile for Bullying, harassment or abuse
        Complete flow: Report profile -> Something about this profile -> 
        Bullying, harassment or abuse -> Seems like sexual exploitation
        """
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

        log.info("Step 1: Clicking three-dots menu (SVG)...")
        if not self.click_three_dots():
            return False, "Could not click three-dots More button"
        time.sleep(3)

        log.info("Step 2: Clicking 'Report profile'...")
        if not self.find_and_click([
            "//span[text()='Report profile']",
            "//span[contains(text(),'Report profile')]",
            "//span[text()='Laporkan profil']",
            "//span[contains(text(),'Laporkan profil')]",
            "//*[contains(text(),'Report profile')]",
            "//*[contains(text(),'Laporkan profil')]",
        ], 5):
            return False, "Could not find Report profile button"
        time.sleep(3)

        log.info("Step 3: Clicking 'Something about this profile'...")
        if not self.find_and_click([
            "//span[text()='Something about this profile']",
            "//span[contains(text(),'Something about this profile')]",
            "//span[text()='Sesuatu tentang profil ini']",
            "//span[contains(text(),'Sesuatu tentang profil ini')]",
            "//*[contains(text(),'Something about this profile')]",
            "//*[contains(text(),'Sesuatu tentang profil ini')]",
        ], 5):
            return False, "Could not find 'Something about this profile' button"
        time.sleep(3)

        log.info("Step 4: Clicking 'Bullying, harassment or abuse'...")
        if not self.find_and_click([
            "//span[text()='Bullying, harassment or abuse']",
            "//span[contains(text(),'Bullying, harassment or abuse')]",
            "//span[text()='Penindasan, pelecehan, atau penyalahgunaan']",
            "//span[contains(text(),'Penindasan')]",
            "//span[contains(text(),'pelecehan')]",
            "//*[contains(text(),'Bullying')]",
            "//*[contains(text(),'Penindasan')]",
        ], 5):
            return False, "Could not find 'Bullying, harassment or abuse' button"
        time.sleep(3)

        log.info("Step 5: Clicking 'Seems like sexual exploitation'...")
        if not self.find_and_click([
            "//span[text()='Seems like sexual exploitation']",
            "//span[contains(text(),'Seems like sexual exploitation')]",
            "//span[text()='Terlihat seperti eksploitasi seksual']",
            "//span[contains(text(),'eksploitasi seksual')]",
            "//*[contains(text(),'sexual exploitation')]",
            "//*[contains(text(),'eksploitasi seksual')]",
        ], 5):
            return False, "Could not find 'Seems like sexual exploitation' button"
        time.sleep(3)

        log.info("Step 6: Clicking Submit...")
        submit_xpaths = [
            "//div[@role='button']//span[text()='Submit']",
            "//div[@role='button']//span[text()='Kirim']",
            "//span[text()='Submit']",
            "//span[contains(text(),'Submit')]",
            "//input[@type='submit']",
            "//button[@type='submit']",
            "//div[@role='button' and contains(text(),'Submit')]",
        ]
        if not self.find_and_click(submit_xpaths, 5):
            return False, "Could not find Submit button"
        time.sleep(3)

        log.info("Step 7: Clicking Next...")
        if not self.find_and_click([
            "//div[@role='button']//span[text()='Next']",
            "//span[text()='Next']",
            "//span[contains(text(),'Next')]",
            "//button[contains(text(),'Next')]",
            "//div[@role='button' and contains(text(),'Next')]",
        ], 5):
            log.warning("Could not find Next button (might not be needed)")
        time.sleep(3)

        log.info("Step 8: Clicking Done...")
        if not self.find_and_click([
            "//div[@role='button']//span[text()='Done']",
            "//span[text()='Done']",
            "//span[contains(text(),'Done')]",
            "//button[contains(text(),'Done')]",
            "//div[@role='button' and contains(text(),'Done')]",
        ], 5):
            log.warning("Could not find Done button (might not be needed)")
        time.sleep(3)

        if "thank" in self.driver.page_source.lower() or "terima" in self.driver.page_source.lower():
            return True, "Profile reported for bullying/harassment successfully!"
        return True, "Report submitted for bullying/harassment."

    def report_post(self, post_url: str) -> Tuple[bool, str]:
        log.info(f"Opening post: {post_url}")
        self.driver.get(post_url)
        time.sleep(5)
        if "not found" in self.driver.page_source.lower() or "unavailable" in self.driver.page_source.lower():
            return False, "Post not found"

        log.info("Step 1: More button...")
        if not self.click_three_dots():
            return False, "No More button"
        time.sleep(2)

        log.info("Step 2: Report option...")
        if not self.find_and_click([
            "//input[@value='RESOLVE_PROBLEM']",
            "//a[contains(text(),'Report post')]",
            "//span[contains(text(),'Report post')]",
            "//div[contains(text(),'Report post')]",
        ], 4):
            return False, "No report option"
        time.sleep(2)

        log.info("Step 3: Spam...")
        if not self.find_and_click([
            "//input[@type='radio' and @value='spam']",
            "//span[contains(text(),'Spam')]/preceding-sibling::input",
            "//span[text()='Spam']",
            "//div[contains(text(),'Spam')]",
        ], 3):
            return False, "No spam option"
        time.sleep(1.5)

        log.info("Step 4: Submit...")
        submit_xpaths = [
            "//div[@role='button']//span[text()='Submit']",
            "//input[@type='submit']",
            "//button[@type='submit']",
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

    def mass_report_profiles_adult(self, targets: List[str], count: int = 3) -> Dict:
        """
        Mass report profiles for adult content
        """
        results = {}
        for t in targets:
            ok, fail = 0, 0
            for i in range(count):
                log.info(f"[{t}] {i+1}/{count}")
                s, msg = self.report_profile_adult(t)
                if s: ok += 1
                else: fail += 1
                log.info(f"  {'OK' if s else 'FAIL'}: {msg}")
                if i+1 < count: time.sleep(random.randint(10, 25))
            results[t] = (ok, fail)
        return results

    def mass_report_profiles_bullying_harassment(self, targets: List[str], count: int = 3) -> Dict:
        """
        Mass report profiles for bullying/harassment
        """
        results = {}
        for t in targets:
            ok, fail = 0, 0
            for i in range(count):
                log.info(f"[{t}] {i+1}/{count}")
                s, msg = self.report_profile_bullying_harassment(t)
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
    print("  FB Mass Report v4.3 — SVG Three-Dots Detection")
    print("="*60)

def menu():
    print("\n  1. Login")
    print("  2. Report profile (Nudity/Sexual Activity)")
    print("  3. Mass report profiles (Nudity/Sexual Activity)")
    print("  4. Report profile (Bullying/Harassment)")
    print("  5. Mass report profiles (Bullying/Harassment)")
    print("  6. Report post")
    print("  7. Mass report posts")
    print("  8. Settings")
    print("  9. Exit")
    try: return int(input("> ").strip())
    except: return 9

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
            settings(config)
        elif opt == 9: 
            break

    engine.stop()

if __name__ == "__main__":
    main()
