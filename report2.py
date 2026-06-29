#!/usr/bin/env python3
"""
Facebook Mass Report Tool v5.0 — Auto-Report Until Banned with Rotating User Agents
"""

import sys, os, json, random, time, re, logging
from pathlib import Path
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass, field
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

try:
    from webdriver_manager.chrome import ChromeDriverManager
    HAS_WDM = True
except ImportError:
    HAS_WDM = False

# Rotating User Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]

# Additional headers
EXTRA_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}

@dataclass
class Config:
    email: str = ""
    password: str = ""
    cookie_file: str = "fb_cookies.json"
    headless: bool = False
    report_count: int = 3
    max_reports: int = 100
    report_delay_min: int = 30
    report_delay_max: int = 90
    auto_continue: bool = True
    report_type: str = "adult"  # "adult" or "bullying"
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
        self.current_ua_index = 0
        
    def get_random_user_agent(self) -> str:
        """Get a random user agent from the list"""
        return random.choice(USER_AGENTS)
    
    def start(self):
        opts = Options()
        
        # Random user agent
        user_agent = self.get_random_user_agent()
        opts.add_argument(f"--user-agent={user_agent}")
        log.info(f"Using User-Agent: {user_agent[:50]}...")
        
        # Anti-detection arguments
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-notifications")
        opts.add_argument("--window-size=1280,720")
        opts.add_argument("--lang=en-US")
        opts.add_argument("--disable-web-security")
        opts.add_argument("--disable-features=IsolateOrigins,site-per-process")
        opts.add_argument("--disable-site-isolation-trials")
        opts.add_argument("--disable-features=BlockInsecurePrivateNetworkRequests")
        opts.add_argument("--disable-features=OutOfBlinkCors")
        
        # Additional anti-fingerprinting
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        opts.add_experimental_option("prefs", {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_setting_values.popups": 2,
            "profile.default_content_setting_values.images": 1,
            "profile.default_content_setting_values.stylesheets": 1,
            "profile.default_content_setting_values.scripts": 1,
            "profile.default_content_setting_values.cookies": 1,
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
            
        # Execute CDP commands to hide automation
        self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
                window.chrome = {runtime: {}};
            """
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
        time.sleep(4 + random.randint(1, 3))

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

        # Human-like typing
        for char in email:
            email_inp.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))
        
        for char in pw:
            pass_inp.send_keys(char)
            time.sleep(random.uniform(0.05, 0.15))
            
        time.sleep(random.uniform(0.5, 1.5))
        log.info("Pressing ENTER...")
        pass_inp.send_keys(Keys.RETURN)
        time.sleep(5 + random.randint(1, 3))

        for _ in range(20):
            url = self.driver.current_url.lower()
            if "checkpoint" in url or "two_step" in url or "authentication" in url:
                log.warning("2FA required")
                try:
                    inp = self.driver.find_element(By.ID, "approvals_code")
                    code = input("2FA code: ").strip()
                    if code:
                        for char in code:
                            inp.send_keys(char)
                            time.sleep(random.uniform(0.05, 0.1))
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
        self.report_count = 0
        self.failed_count = 0
        self.last_report_time = None
        
    def random_delay(self, min_sec: int = 30, max_sec: int = 90):
        """Random delay between reports to avoid detection"""
        delay = random.randint(min_sec, max_sec)
        log.info(f"Waiting {delay} seconds before next report...")
        time.sleep(delay)

    def js_click(self, el):
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center', behavior:'smooth'});", el)
            time.sleep(random.uniform(0.3, 0.7))
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
        """Click the three-dots SVG menu on a Facebook profile."""
        try:
            svgs = self.driver.find_elements(By.XPATH, "//*[name()='svg']")
            for svg in svgs:
                try:
                    circles = svg.find_elements(By.XPATH, ".//*[name()='circle']")
                    if len(circles) >= 3:
                        radii = [c.get_attribute("r") for c in circles[:3]]
                        if radii == ["2.5", "2.5", "2.5"]:
                            parent = svg.find_element(By.XPATH, "./ancestor::*[@role='button' or contains(@class,'x1i10hfl')]")
                            if parent:
                                self.js_click(parent)
                                log.info("Clicked three-dots SVG via circle detection")
                                return True
                except: continue
        except Exception as e:
            log.warning(f"SVG circle detection failed: {e}")

        if self.find_and_click(["//span[text()='More']", "//span[contains(text(),'More')]"]):
            return True

        if self.find_and_click([
            "//*[@aria-label='Profile settings see more options']",
            "//*[@aria-label='More']",
            "//*[@aria-label='More options']",
        ]):
            return True

        return False

    def check_if_banned(self, target: str) -> bool:
        """Check if the account has been banned"""
        try:
            # Check for account disabled message
            page_source = self.driver.page_source.lower()
            banned_indicators = [
                "account disabled",
                "account suspended",
                "your account has been disabled",
                "this account has been disabled",
                "account not available",
                "this page isn't available",
                "content not available",
                "sorry, this page isn't available",
                "the page you requested cannot be displayed",
            ]
            
            for indicator in banned_indicators:
                if indicator in page_source:
                    return True
                    
            # Check for specific URLs indicating ban
            current_url = self.driver.current_url.lower()
            if "disabled" in current_url or "suspended" in current_url:
                return True
                
            return False
        except:
            return False

    def report_profile_adult(self, target: str) -> Tuple[bool, str]:
        """Report profile for Adult content -> Nudity or sexual activity"""
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

        # Step 1: Click three-dots SVG menu
        log.info("Step 1: Clicking three-dots menu (SVG)...")
        if not self.click_three_dots():
            return False, "Could not click three-dots More button"
        time.sleep(3 + random.uniform(0.5, 1.5))

        # Step 2: Click "Report profile"
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

        # Step 3: Click "Something about this profile"
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

        # Step 4: Click "Adult content"
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

        # Step 5: Click "Nudity or sexual activity"
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

        # Step 6: Submit
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
        
        # Handle any checkboxes that might appear
        try:
            for cb in self.driver.find_elements(By.XPATH, "//input[@type='checkbox']"):
                if cb.is_displayed():
                    self.js_click(cb)
                    time.sleep(1)
                    self.find_and_click(submit_xpaths, 3)
                    break
        except: pass

        # Step 7: Click "Next" button if present
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

        # Step 8: Click "Done" button if present
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

        # Check if account got banned
        if self.check_if_banned(target):
            return True, "ACCOUNT BANNED! Report successful!"

        # Check for success
        page_text = self.driver.page_source.lower()
        if "thank" in page_text or "terima" in page_text or "success" in page_text:
            return True, "Profile reported for Adult content successfully!"
        
        if submitted:
            return True, "Adult content report submitted successfully!"
            
        return False, "Could not submit adult content report"

    def report_profile_bullying(self, target: str) -> Tuple[bool, str]:
        """Report profile for Bullying, harassment or abuse -> Seems like sexual exploitation"""
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

        # Step 1: Click three-dots SVG menu
        log.info("Step 1: Clicking three-dots menu (SVG)...")
        if not self.click_three_dots():
            return False, "Could not click three-dots More button"
        time.sleep(3 + random.uniform(0.5, 1.5))

        # Step 2: Click "Report profile"
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

        # Step 3: Click "Something about this profile"
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

        # Step 4: Click "Bullying, harassment or abuse"
        log.info("Step 4: Clicking 'Bullying, harassment or abuse'...")
        if not self.find_and_click([
            "//span[text()='Bullying, harassment or abuse']",
            "//span[contains(text(),'Bullying, harassment or abuse')]",
            "//span[text()='Penindasan, pelecehan atau penyalahgunaan']",
            "//span[contains(text(),'Penindasan, pelecehan atau penyalahgunaan')]",
            "//*[contains(text(),'Bullying, harassment or abuse')]",
            "//*[contains(text(),'Penindasan, pelecehan atau penyalahgunaan')]",
        ], 5):
            return False, "Could not find 'Bullying, harassment or abuse' button"
        time.sleep(2 + random.uniform(0.5, 1))

        # Step 5: Click "Seems like sexual exploitation"
        log.info("Step 5: Clicking 'Seems like sexual exploitation'...")
        if not self.find_and_click([
            "//span[text()='Seems like sexual exploitation']",
            "//span[contains(text(),'Seems like sexual exploitation')]",
            "//span[text()='Sepertinya eksploitasi seksual']",
            "//span[contains(text(),'Sepertinya eksploitasi seksual')]",
            "//*[contains(text(),'Seems like sexual exploitation')]",
            "//*[contains(text(),'Sepertinya eksploitasi seksual')]",
        ], 5):
            return False, "Could not find 'Seems like sexual exploitation' button"
        time.sleep(2 + random.uniform(0.5, 1))

        # Step 6: Submit
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
        
        # Handle any checkboxes that might appear
        try:
            for cb in self.driver.find_elements(By.XPATH, "//input[@type='checkbox']"):
                if cb.is_displayed():
                    self.js_click(cb)
                    time.sleep(1)
                    self.find_and_click(submit_xpaths, 3)
                    break
        except: pass

        # Step 7: Click "Next" button if present
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

        # Step 8: Click "Done" button if present
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

        # Check if account got banned
        if self.check_if_banned(target):
            return True, "ACCOUNT BANNED! Report successful!"

        # Check for success
        page_text = self.driver.page_source.lower()
        if "thank" in page_text or "terima" in page_text or "success" in page_text:
            return True, "Profile reported for Bullying/Harassment successfully!"
        
        if submitted:
            return True, "Bullying/Harassment report submitted successfully!"
            
        return False, "Could not submit bullying/harassment report"

    def report_profile(self, target: str, report_type: str = "adult") -> Tuple[bool, str]:
        """Report profile with specified type: 'adult' or 'bullying'"""
        if report_type == "bullying":
            return self.report_profile_bullying(target)
        else:
            return self.report_profile_adult(target)

    def auto_report_until_banned(self, target: str, report_type: str = "adult", 
                                  max_reports: int = 100, 
                                  delay_min: int = 30, 
                                  delay_max: int = 90) -> Dict:
        """Automatically report a profile until it gets banned"""
        results = {
            "target": target,
            "report_type": report_type,
            "total_reports": 0,
            "successful_reports": 0,
            "failed_reports": 0,
            "banned": False,
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "reports": []
        }
        
        log.info(f"=== AUTO-REPORT STARTED ===")
        log.info(f"Target: {target}")
        log.info(f"Report Type: {report_type}")
        log.info(f"Max Reports: {max_reports}")
        log.info(f"Delay Range: {delay_min}-{delay_max} seconds")
        log.info("=" * 60)
        
        for i in range(1, max_reports + 1):
            log.info(f"\n--- Report #{i} ---")
            
            # Check if account is already banned before reporting
            self.driver.get(f"https://www.facebook.com/{target}")
            time.sleep(3)
            if self.check_if_banned(target):
                log.info("✅ ACCOUNT IS BANNED! Stopping...")
                results["banned"] = True
                results["end_time"] = datetime.now().isoformat()
                break
            
            # Perform the report
            success, message = self.report_profile(target, report_type)
            
            report_entry = {
                "report_number": i,
                "timestamp": datetime.now().isoformat(),
                "success": success,
                "message": message
            }
            results["reports"].append(report_entry)
            
            if success:
                results["successful_reports"] += 1
                log.info(f"✅ Report #{i} SUCCESS: {message}")
                
                # Check if account is now banned after the report
                time.sleep(2)
                if self.check_if_banned(target):
                    log.info("🎯 ACCOUNT BANNED! Target eliminated!")
                    results["banned"] = True
                    results["end_time"] = datetime.now().isoformat()
                    break
            else:
                results["failed_reports"] += 1
                log.warning(f"❌ Report #{i} FAILED: {message}")
            
            results["total_reports"] = i
            
            # Random delay between reports (except after last report)
            if i < max_reports and not results["banned"]:
                self.random_delay(delay_min, delay_max)
        
        if not results["banned"]:
            results["end_time"] = datetime.now().isoformat()
            log.info(f"\n⚠️ Reached max reports ({max_reports}) without ban.")
        
        log.info("\n" + "=" * 60)
        log.info("=== AUTO-REPORT SUMMARY ===")
        log.info(f"Total Reports: {results['total_reports']}")
        log.info(f"Successful: {results['successful_reports']}")
        log.info(f"Failed: {results['failed_reports']}")
        log.info(f"Account Banned: {results['banned']}")
        log.info("=" * 60)
        
        return results

    def report_post(self, post_url: str) -> Tuple[bool, str]:
        log.info(f"Opening post: {post_url}")
        self.driver.get(post_url)
        time.sleep(5 + random.randint(1, 2))
        if "not found" in self.driver.page_source.lower() or "unavailable" in self.driver.page_source.lower():
            return False, "Post not found"

        log.info("Step 1: More button...")
        if not self.click_three_dots():
            return False, "No More button"
        time.sleep(2 + random.uniform(0.5, 1))

        log.info("Step 2: Report option...")
        if not self.find_and_click([
            "//input[@value='RESOLVE_PROBLEM']",
            "//a[contains(text(),'Report post')]",
            "//span[contains(text(),'Report post')]",
            "//div[contains(text(),'Report post')]",
        ], 4):
            return False, "No report option"
        time.sleep(2 + random.uniform(0.5, 1))

        log.info("Step 3: Spam...")
        if not self.find_and_click([
            "//input[@type='radio' and @value='spam']",
            "//span[contains(text(),'Spam')]/preceding-sibling::input",
            "//span[text()='Spam']",
            "//div[contains(text(),'Spam')]",
        ], 3):
            return False, "No spam option"
        time.sleep(1.5 + random.uniform(0.3, 0.8))

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

    def mass_report_profiles(self, targets: List[str], count: int = 3, report_type: str = "adult") -> Dict:
        results = {}
        for t in targets:
            log.info(f"\n=== Processing target: {t} ===")
            # Use auto-report for each target
            r = self.auto_report_until_banned(
                t, 
                report_type=report_type,
                max_reports=count,
                delay_min=30,
                delay_max=90
            )
            results[t] = r
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
                log.info(f"  {'OK' if s else 'FAIL'}: {msg}")
                if i+1 < count: self.random_delay(15, 30)
            results[u] = (ok, fail)
        return results

def banner():
    print("\n" + "="*70)
    print("  FB Mass Report v5.0 — Auto-Report Until Banned with Rotating User Agents")
    print("="*70)

def menu():
    print("\n  📋 REPORTING OPTIONS:")
    print("  ─────────────────────")
    print("  1. Login")
    print("  2. Report profile (Adult content) - Single")
    print("  3. Report profile (Bullying/Harassment) - Single")
    print("  4. 🔥 AUTO-REPORT UNTIL BANNED (Adult)")
    print("  5. 🔥 AUTO-REPORT UNTIL BANNED (Bullying)")
    print("  6. Report post")
    print("  7. Mass report profiles (Adult)")
    print("  8. Mass report profiles (Bullying)")
    print("  9. Mass report posts")
    print("  10. Settings")
    print("  11. Exit")
    try: return int(input("\n> ").strip())
    except: return 11

def settings(config):
    print("\n=== SETTINGS ===")
    e = input(f"Email [{config.email}]: ").strip() or config.email
    p = input("Password: ").strip()
    h = input("Headless? (y/N): ").strip().lower() == 'y'
    max_r = input(f"Max reports per target [{config.max_reports}]: ").strip()
    delay_min = input(f"Min delay between reports (seconds) [{config.report_delay_min}]: ").strip()
    delay_max = input(f"Max delay between reports (seconds) [{config.report_delay_max}]: ").strip()
    
    config.email = e
    if p: config.password = p
    config.headless = h
    if max_r: config.max_reports = int(max_r)
    if delay_min: config.report_delay_min = int(delay_min)
    if delay_max: config.report_delay_max = int(delay_max)
    config.save()
    print("✅ Settings saved!")

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
                ok, msg = reporter.report_profile(t, "adult")
                log.info(f"{'✅' if ok else '❌'} {msg}")
        elif opt == 3:
            t = input("Profile (URL, ID, username): ").strip()
            if t:
                ok, msg = reporter.report_profile(t, "bullying")
                log.info(f"{'✅' if ok else '❌'} {msg}")
        elif opt == 4:
            t = input("Profile (URL, ID, username): ").strip()
            if t:
                max_r = int(input(f"Max reports [{config.max_reports}]: ").strip() or config.max_reports)
                delay_min = int(input(f"Min delay [{config.report_delay_min}]: ").strip() or config.report_delay_min)
                delay_max = int(input(f"Max delay [{config.report_delay_max}]: ").strip() or config.report_delay_max)
                results = reporter.auto_report_until_banned(t, "adult", max_r, delay_min, delay_max)
                # Save results to file
                with open(f"report_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
                    json.dump(results, f, indent=2)
                log.info(f"📁 Results saved to file")
        elif opt == 5:
            t = input("Profile (URL, ID, username): ").strip()
            if t:
                max_r = int(input(f"Max reports [{config.max_reports}]: ").strip() or config.max_reports)
                delay_min = int(input(f"Min delay [{config.report_delay_min}]: ").strip() or config.report_delay_min)
                delay_max = int(input(f"Max delay [{config.report_delay_max}]: ").strip() or config.report_delay_max)
                results = reporter.auto_report_until_banned(t, "bullying", max_r, delay_min, delay_max)
                with open(f"report_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
                    json.dump(results, f, indent=2)
                log.info(f"📁 Results saved to file")
        elif opt == 6:
            u = input("Post URL: ").strip()
            if u:
                ok, msg = reporter.report_post(u)
                log.info(f"{'✅' if ok else '❌'} {msg}")
        elif opt == 7:
            raw = input("Profiles (comma-sep): ").strip()
            if raw:
                targets = [x.strip() for x in raw.split(",") if x.strip()]
                max_r = int(input(f"Max reports per target [{config.max_reports}]: ").strip() or config.max_reports)
                results = reporter.mass_report_profiles(targets, max_r, "adult")
                with open(f"mass_report_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
                    json.dump(results, f, indent=2)
                print(json.dumps(results, indent=2))
        elif opt == 8:
            raw = input("Profiles (comma-sep): ").strip()
            if raw:
                targets = [x.strip() for x in raw.split(",") if x.strip()]
                max_r = int(input(f"Max reports per target [{config.max_reports}]: ").strip() or config.max_reports)
                results = reporter.mass_report_profiles(targets, max_r, "bullying")
                with open(f"mass_report_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
                    json.dump(results, f, indent=2)
                print(json.dumps(results, indent=2))
        elif opt == 9:
            raw = input("Post URLs (comma-sep): ").strip()
            if raw:
                targets = [x.strip() for x in raw.split(",") if x.strip()]
                cnt = int(input(f"Reports each [{config.report_count}]: ").strip() or config.report_count)
                r = reporter.mass_report_posts(targets, cnt)
                print(json.dumps(r, indent=2))
        elif opt == 10: settings(config)
        elif opt == 11: break

    engine.stop()

if __name__ == "__main__":
    main()
