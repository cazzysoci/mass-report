#!/usr/bin/env python3
"""
Mass Facebook Profile Reporter - FOR AUTHORIZED PENTESTING ONLY
Advanced version with:
- Human-like mouse movements and typing patterns
- Random browser fingerprinting
- Multiple reporting angles per profile
- Session rotation and cookie management
- CAPTCHA solving (2Captcha)
- Proxy rotation
- Stealth mode with undetected-chromedriver
- Detailed reporting with multiple reason pathways
"""

import time
import json
import csv
import sys
import os
import random
import threading
import pickle
import hashlib
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException, ElementClickInterceptedException

# Auto-manage ChromeDriver
try:
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
    WEBDRIVER_MANAGER = True
except ImportError:
    WEBDRIVER_MANAGER = False

try:
    from twocaptcha import TwoCaptcha
    TWOCAPTCHA_AVAILABLE = True
except ImportError:
    TWOCAPTCHA_AVAILABLE = False


class HumanBehavior:
    """Simulate human-like behavior to avoid detection"""
    
    @staticmethod
    def random_delay(min_s=0.3, max_s=1.5):
        time.sleep(random.uniform(min_s, max_s))
    
    @staticmethod
    def human_type(element, text, min_delay=0.03, max_delay=0.12):
        """Type like a human - random delays between keystrokes"""
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(min_delay, max_delay))
            # Occasionally pause longer (like thinking)
            if random.random() < 0.05:
                time.sleep(random.uniform(0.3, 0.8))
    
    @staticmethod
    def move_mouse_to(driver, element, offset_x=0, offset_y=0):
        """Move mouse to element with human-like path"""
        actions = ActionChains(driver)
        # Random offset within element
        ox = offset_x if offset_x else random.randint(-10, 10)
        oy = offset_y if offset_y else random.randint(-10, 10)
        actions.move_to_element_with_offset(element, ox, oy)
        actions.perform()
        time.sleep(random.uniform(0.1, 0.3))
    
    @staticmethod
    def human_click(driver, element):
        """Click like a human - move to element first, slight pause, then click"""
        HumanBehavior.move_mouse_to(driver, element)
        time.sleep(random.uniform(0.05, 0.15))
        try:
            element.click()
        except ElementClickInterceptedException:
            driver.execute_script("arguments[0].click();", element)
        HumanBehavior.random_delay(0.2, 0.5)
    
    @staticmethod
    def scroll_page(driver):
        """Scroll down slightly like a human reading"""
        scroll_amount = random.randint(100, 400)
        driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        time.sleep(random.uniform(0.5, 1.5))
        # Maybe scroll back up a bit
        if random.random() < 0.3:
            driver.execute_script(f"window.scrollBy(0, -{random.randint(50, 150)});")
            time.sleep(random.uniform(0.3, 0.8))


class StealthBrowser:
    """Create a browser with stealth properties"""
    
    @staticmethod
    def create_driver(proxy=None, user_agent=None, headless=False):
        options = webdriver.ChromeOptions()
        
        # Random user agent
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        ]
        ua = user_agent or random.choice(user_agents)
        
        # Anti-detection flags
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument(f'user-agent={ua}')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--lang=en-US')
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        
        # Random window position to avoid fingerprinting
        options.add_argument(f'--window-position={random.randint(0, 200)},{random.randint(0, 200)}')
        
        if proxy:
            options.add_argument(f'--proxy-server={proxy}')
        
        if headless:
            options.add_argument('--headless=new')
        
        # Use webdriver-manager or fallback
        if WEBDRIVER_MANAGER:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        else:
            driver = webdriver.Chrome(options=options)
        
        # Execute stealth scripts
        StealthBrowser._inject_stealth_js(driver)
        
        return driver
    
    @staticmethod
    def _inject_stealth_js(driver):
        """Inject JavaScript to hide automation traces"""
        stealth_js = """
        // Override webdriver property
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
            configurable: true,
        });
        
        // Override plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
            configurable: true,
        });
        
        // Override languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
            configurable: true,
        });
        
        // Override chrome runtime
        window.chrome = {
            runtime: {},
            loadTimes: function() {},
            csi: function() {},
            app: {},
        };
        
        // Override permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // Override connection
        Object.defineProperty(navigator, 'connection', {
            get: () => ({
                rtt: Math.floor(Math.random() * 200) + 50,
                downlink: Math.random() * 10 + 5,
                effectiveType: '4g',
            }),
            configurable: true,
        });
        """
        driver.execute_script(stealth_js)


class SessionRotator:
    """Manage multiple Facebook sessions"""
    
    def __init__(self, cookie_dir="fb_sessions"):
        self.cookie_dir = cookie_dir
        if not os.path.exists(cookie_dir):
            os.makedirs(cookie_dir)
    
    def save_session(self, driver, identifier):
        """Save browser cookies"""
        cookie_file = os.path.join(self.cookie_dir, f"{identifier}.pkl")
        try:
            with open(cookie_file, 'wb') as f:
                pickle.dump(driver.get_cookies(), f)
            return True
        except:
            return False
    
    def load_session(self, driver, identifier):
        """Load browser cookies"""
        cookie_file = os.path.join(self.cookie_dir, f"{identifier}.pkl")
        if not os.path.exists(cookie_file):
            return False
        try:
            with open(cookie_file, 'rb') as f:
                cookies = pickle.load(f)
            driver.get("https://www.facebook.com")
            time.sleep(2)
            for cookie in cookies:
                cookie.pop('sameSite', None)
                cookie.pop('httpOnly', None)
                cookie.pop('secure', None)
                try:
                    driver.add_cookie(cookie)
                except:
                    pass
            driver.get("https://www.facebook.com")
            time.sleep(2)
            return True
        except:
            return False
    
    def clear_session(self, identifier):
        cookie_file = os.path.join(self.cookie_dir, f"{identifier}.pkl")
        if os.path.exists(cookie_file):
            os.remove(cookie_file)


class CaptchaHandler:
    """Handle CAPTCHA solving via 2Captcha"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("TWOCAPTCHA_API_KEY", "")
        self.solver = None
        if self.api_key and TWOCAPTCHA_AVAILABLE:
            self.solver = TwoCaptcha(self.api_key)
        self.total_solved = 0
    
    def is_available(self):
        return self.solver is not None
    
    def detect_and_solve(self, driver):
        """Detect and solve any CAPTCHA on page"""
        if not self.solver:
            return False
        
        # Check for reCAPTCHA
        try:
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                src = iframe.get_attribute("src") or ""
                if "recaptcha" in src and "render" in src:
                    from urllib.parse import parse_qs, urlparse
                    params = parse_qs(urlparse(src).query)
                    site_key = params.get('k', [None])[0]
                    if site_key:
                        print("[*] Solving reCAPTCHA...")
                        result = self.solver.recaptcha(sitekey=site_key, url=driver.current_url)
                        token = result.get('code')
                        if token:
                            driver.execute_script(f"""
                                document.getElementById('g-recaptcha-response').innerHTML = '{token}';
                                try {{ document.querySelector('form').submit(); }} catch(e) {{}}
                            """)
                            self.total_solved += 1
                            time.sleep(2)
                            return True
        except:
            pass
        
        # Check for image CAPTCHA
        try:
            captcha_img = driver.find_element(By.XPATH, "//img[contains(@src, 'captcha')]")
            img_src = captcha_img.get_attribute("src")
            if img_src:
                import requests
                img_data = requests.get(img_src).content
                temp = "/tmp/fb_captcha.png"
                with open(temp, "wb") as f:
                    f.write(img_data)
                result = self.solver.normal(temp)
                code = result.get('code')
                if code:
                    try:
                        inp = driver.find_element(By.NAME, "captcha_response")
                        inp.send_keys(code)
                        inp.send_keys(Keys.RETURN)
                    except:
                        try:
                            inp = driver.find_element(By.XPATH, "//input[contains(@aria-label, 'captcha')]")
                            inp.send_keys(code)
                            inp.send_keys(Keys.RETURN)
                        except:
                            pass
                    self.total_solved += 1
                    time.sleep(2)
                    return True
        except:
            pass
        
        return False


class CookieConsentManager:
    """Handle cookie consent and notification popups"""
    
    @staticmethod
    def dismiss_all(driver):
        """Dismiss ALL popups - cookies, notifications, save password, etc."""
        selectors = [
            # Cookie consent
            "//span[text()='Allow all cookies']/..",
            "//span[contains(text(), 'Allow all cookies')]/..",
            "//div[@role='button']//span[contains(text(), 'Allow')]",
            "//button[contains(text(), 'Allow')]",
            "//div[@role='button' and contains(., 'Allow all cookies')]",
            "//div[contains(@class, 'x1i10hfl') and contains(text(), 'Allow')]",
            "//span[contains(text(), 'Allow essential and optional cookies')]/..",
            # Notifications
            "//span[text()='Not Now']/..",
            "//span[contains(text(), 'Not now')]/..",
            "//span[text()='Later']/..",
            "//span[text()='Cancel']/..",
            "//div[@aria-label='Close']",
            "//div[@aria-label='Dismiss']",
            # Save password / save device
            "//span[text()='Save']/../../..//span[text()='Not Now']",
            "//span[text()='Save']/../../..//span[contains(text(), 'Not')]",
            # Turn on
            "//span[text()='Turn On']/../..//span[text()='Not Now']",
            "//span[contains(text(), 'Turn on')]/../..//span[contains(text(), 'Not')]",
        ]
        
        for selector in selectors:
            try:
                elements = driver.find_elements(By.XPATH, selector)
                for elem in elements:
                    try:
                        if elem.is_displayed():
                            driver.execute_script("arguments[0].click();", elem)
                            time.sleep(0.3)
                    except:
                        continue
            except:
                continue


class AdvancedReporter:
    """Main reporting engine with advanced features"""
    
    def __init__(self, email, password, captcha_api_key=None, proxies=None):
        self.email = email
        self.password = password
        self.captcha_api_key = captcha_api_key
        self.proxies = proxies or []
        self.driver = None
        self.wait = None
        self.session_rotator = SessionRotator()
        self.captcha_handler = CaptchaHandler(captcha_api_key)
        self.current_proxy = None
        self._running = False
        
        # Stats
        self.stats = {
            "success": 0, "failed": 0, "skipped": 0,
            "already": 0, "blocked": 0,
            "captchas_solved": 0, "total": 0,
            "start_time": None, "end_time": None
        }
    
    def _rotate_proxy(self):
        """Rotate to next proxy in list"""
        if self.proxies:
            self.current_proxy = random.choice(self.proxies)
            return self.current_proxy
        return None
    
    def _create_browser(self):
        """Create a new stealth browser"""
        proxy = self._rotate_proxy()
        self.driver = StealthBrowser.create_driver(proxy=proxy)
        self.wait = WebDriverWait(self.driver, 20)
        return self.driver
    
    def _navigate_and_purge(self, url, extra_wait=0):
        """Navigate to URL and purge all popups"""
        self.driver.get(url)
        time.sleep(3 + extra_wait)
        CookieConsentManager.dismiss_all(self.driver)
        time.sleep(0.5)
        CookieConsentManager.dismiss_all(self.driver)  # Second pass for nested popups
    
    def login(self):
        """Login with maximum evasion"""
        print("\n[*] Creating stealth browser...")
        self._create_browser()
        
        # Try loading saved session first
        session_id = f"session_{hashlib.md5(self.email.encode()).hexdigest()[:8]}"
        if self.session_rotator.load_session(self.driver, session_id):
            if "login" not in self.driver.current_url.lower():
                print("[+] Session restored successfully!")
                CookieConsentManager.dismiss_all(self.driver)
                return True
            else:
                print("[*] Session expired, re-logging...")
        
        print("[*] Navigating to login page...")
        self._navigate_and_purge("https://www.facebook.com/login", extra_wait=2)
        
        # Wait for page to fully render
        HumanBehavior.random_delay(1, 2)
        
        # Find and fill email
        print("[*] Entering credentials...")
        try:
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "email"))
            )
        except:
            email_field = self.driver.find_element(By.NAME, "email")
        
        # Human-like interaction with email field
        HumanBehavior.move_mouse_to(self.driver, email_field)
        email_field.click()
        HumanBehavior.random_delay(0.3, 0.7)
        email_field.clear()
        HumanBehavior.human_type(email_field, self.email, 0.04, 0.1)
        
        HumanBehavior.random_delay(0.5, 1.0)
        
        # Find and fill password
        try:
            pass_field = self.driver.find_element(By.ID, "pass")
        except:
            pass_field = self.driver.find_element(By.NAME, "pass")
        
        HumanBehavior.move_mouse_to(self.driver, pass_field)
        pass_field.click()
        HumanBehavior.random_delay(0.3, 0.6)
        pass_field.clear()
        HumanBehavior.human_type(pass_field, self.password, 0.03, 0.08)
        
        HumanBehavior.random_delay(0.5, 1.0)
        
        # Click login
        print("[*] Logging in...")
        login_btn = self.driver.find_element(By.NAME, "login")
        HumanBehavior.human_click(self.driver, login_btn)
        
        time.sleep(5)
        
        # Handle post-login
        CookieConsentManager.dismiss_all(self.driver)
        HumanBehavior.random_delay(0.5, 1)
        CookieConsentManager.dismiss_all(self.driver)
        
        # Check result
        current_url = self.driver.current_url.lower()
        
        if "checkpoint" in current_url:
            print("[!] Checkpoint/2FA detected!")
            self.driver.save_screenshot("checkpoint.png")
            
            # Check for 2FA code input
            try:
                if "approvals_code" in self.driver.page_source:
                    print("[*] 2FA required. Waiting 45s for manual entry...")
                    for i in range(45, 0, -1):
                        sys.stdout.write(f"\r[*] {i}s remaining for 2FA... ")
                        sys.stdout.flush()
                        time.sleep(1)
                    print()
                    if "login" not in self.driver.current_url.lower() and "checkpoint" not in self.driver.current_url.lower():
                        print("[+] Logged in after 2FA!")
                        self.session_rotator.save_session(self.driver, session_id)
                        return True
            except:
                pass
            
            # Try solving checkpoint CAPTCHA
            if self.captcha_handler.detect_and_solve(self.driver):
                time.sleep(5)
                if "checkpoint" not in self.driver.current_url.lower():
                    print("[+] Checkpoint bypassed!")
                    self.session_rotator.save_session(self.driver, session_id)
                    return True
            
            print("[-] Could not bypass checkpoint")
            return False
        
        if "login" in current_url:
            print("[-] Login failed - wrong credentials?")
            return False
        
        # Login successful
        print("[+] Login successful!")
        self.session_rotator.save_session(self.driver, session_id)
        return True
    
    def report_profile(self, profile_url, reason="harassment"):
        """Report a profile using multiple techniques for highest success rate"""
        print(f"\n[*] Processing: {profile_url}")
        
        # Navigate to profile
        self._navigate_and_purge(profile_url, extra_wait=1)
        
        # Check for blocks/errors
        if "checkpoint" in self.driver.current_url.lower():
            return "blocked"
        
        if "login" in self.driver.current_url.lower():
            # Session expired - try to re-login
            print("[!] Session expired during navigation")
            if self.login():
                self._navigate_and_purge(profile_url, extra_wait=1)
            else:
                return "blocked"
        
        # Check if profile exists
        page_source = self.driver.page_source
        if "Sorry" in self.driver.title or "content_placeholder" in page_source:
            return "skipped"
        
        # Scroll like a human first (makes the page load fully)
        HumanBehavior.scroll_page(self.driver)
        HumanBehavior.scroll_page(self.driver)
        
        # ===== METHOD 1: Try the three-dot menu =====
        print("[*] Attempting report via menu...")
        
        # Multiple selectors for the More button
        more_selectors = [
            "//div[@aria-label='More']",
            "//div[@aria-label='More actions']",
            "//div[@role='button']//span[contains(text(), 'More')]",
            "//div[contains(@class, 'x1i10hfl') and @tabindex='0']",
            "//div[@role='button']//span[text()='More']",
            # Cover photo more button
            "//div[contains(@class, 'x6s0dn4')]//div[@aria-label='More']",
            # Profile action button
            "//div[contains(@aria-label, 'More')]"
        ]
        
        menu_clicked = False
        for sel in more_selectors:
            try:
                elements = self.driver.find_elements(By.XPATH, sel)
                for elem in elements:
                    try:
                        if elem.is_displayed():
                            HumanBehavior.move_mouse_to(self.driver, elem)
                            time.sleep(random.uniform(0.2, 0.5))
                            HumanBehavior.human_click(self.driver, elem)
                            menu_clicked = True
                            break
                    except:
                        continue
                if menu_clicked:
                    break
            except:
                continue
        
        if not menu_clicked:
            # Try clicking on the profile area to reveal more options
            try:
                # Click on empty space to focus page
                body = self.driver.find_element(By.TAG_NAME, "body")
                body.click()
                time.sleep(0.5)
                # Try pressing tab key to navigate to menu
                body.send_keys(Keys.TAB, Keys.TAB, Keys.TAB, Keys.TAB)
                time.sleep(0.5)
                body.send_keys(Keys.ENTER)
                time.sleep(1)
            except:
                pass
            
            # Try again
            for sel in more_selectors[:3]:
                try:
                    elements = self.driver.find_elements(By.XPATH, sel)
                    for elem in elements:
                        try:
                            if elem.is_displayed():
                                self.driver.execute_script("arguments[0].click();", elem)
                                menu_clicked = True
                                break
                        except:
                            continue
                    if menu_clicked:
                        break
                except:
                    continue
        
        if not menu_clicked:
            print("[-] Could not find More menu")
            return "failed"
        
        HumanBehavior.random_delay(1.5, 2.5)
        
        # ===== Find and click Report =====
        print("[*] Finding report option...")
        
        report_selectors = [
            "//span[contains(text(), 'Find support')]",
            "//span[contains(text(), 'Find Support')]",
            "//span[contains(text(), 'Report')]",
            "//div[@role='menuitem']//span[contains(text(), 'Report')]",
            "//span[text()='Report profile']",
            "//span[text()='Report']",
            "//div[@role='menuitem' and contains(., 'Report')]",
            "//div[contains(@role, 'menuitem')]//span[text()='Report']"
        ]
        
        report_found = False
        for sel in report_selectors:
            try:
                report_btn = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, sel))
                )
                HumanBehavior.human_click(self.driver, report_btn)
                report_found = True
                break
            except:
                continue
        
        if not report_found:
            # Try JavaScript click
            for sel in report_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, sel)
                    for elem in elements:
                        if elem.is_displayed():
                            self.driver.execute_script("arguments[0].click();", elem)
                            report_found = True
                            break
                    if report_found:
                        break
                except:
                    continue
        
        if not report_found:
            print("[-] Could not find report option (already reported?)")
            return "already_reported"
        
        HumanBehavior.random_delay(2, 3)
        
        # ===== METHOD 2: Multiple reporting pathways =====
        # Facebook has different report flows depending on the profile type
        # Try different reason pathways
        
        reason_texts = {
            "harassment": ["Harassment", "Bullying", "Targeted harassment"],
            "fake_account": ["Fake account", "Pretending to be someone"],
            "hate_speech": ["Hate speech", "Hate speech or symbols"],
            "violence": ["Violence", "Violent content", "Dangerous organizations"],
            "nudity": ["Nudity", "Sexual activity", "Sexual content"],
            "pretending": ["Pretending to be me", "Fake identity"],
            "scam": ["Scam", "Fraud", "Financial scam"]
        }
        
        reason_group = reason_texts.get(reason, reason_texts["harassment"])
        
        reason_selected = False
        for reason_variant in reason_group:
            try:
                reason_selectors = [
                    f"//span[contains(text(), '{reason_variant}')]",
                    f"//div[@role='radio']//span[contains(text(), '{reason_variant}')]",
                    f"//label[contains(text(), '{reason_variant}')]",
                    f"//div[contains(text(), '{reason_variant}')]",
                    f"//span[text()='{reason_variant}']"
                ]
                
                for sel in reason_selectors:
                    try:
                        reason_elem = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, sel))
                        )
                        HumanBehavior.human_click(self.driver, reason_elem)
                        reason_selected = True
                        print(f"[+] Selected reason: {reason_variant}")
                        break
                    except:
                        continue
                
                if reason_selected:
                    break
            except:
                continue
        
        if not reason_selected:
            print("[-] Could not select report reason")
            return "failed"
        
        HumanBehavior.random_delay(1.5, 2.5)
        
        # ===== Submit the report =====
        # Sometimes there are sub-options after choosing a reason
        # Try to click "Next" or confirm sub-options first
        next_selectors = [
            "//span[text()='Next']/..",
            "//div[@role='button']//span[text()='Next']",
            "//span[text()='Continue']/.."
        ]
        
        for sel in next_selectors:
            try:
                next_btn = self.driver.find_element(By.XPATH, sel)
                if next_btn.is_displayed():
                    HumanBehavior.human_click(self.driver, next_btn)
                    HumanBehavior.random_delay(1, 2)
                    break
            except:
                continue
        
        # Now find the Submit/Done button
        print("[*] Submitting report...")
        
        submit_selectors = [
            "//span[text()='Submit']/..",
            "//span[text()='Done']/..",
            "//div[@role='button']//span[contains(text(), 'Submit')]",
            "//div[@role='button']//span[contains(text(), 'Done')]",
            "//span[text()='Send']/..",
            "//div[@role='button']//span[text()='Send']",
            "//span[text()='Report']/..",
            "//div[@role='button']//span[text()='Report']"
        ]
        
        submitted = False
        for sel in submit_selectors:
            try:
                submit_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, sel))
                )
                HumanBehavior.human_click(self.driver, submit_btn)
                submitted = True
                break
            except:
                continue
        
        if not submitted:
            # Try JavaScript click as last resort
            for sel in submit_selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, sel)
                    for elem in elements:
                        try:
                            if elem.is_displayed():
                                self.driver.execute_script("arguments[0].click();", elem)
                                submitted = True
                                break
                        except:
                            continue
                    if submitted:
                        break
                except:
                    continue
        
        HumanBehavior.random_delay(2, 3)
        
        # ===== METHOD 3: If standard report failed, try alternative =====
        if not submitted:
            print("[*] Standard flow failed, trying alternative...")
            
            # Sometimes the report flow requires selecting additional sub-options
            # Try clicking on more specific reasons first
            try:
                # Look for any unchecked radio buttons/checkboxes
                unchecked = self.driver.find_elements(By.XPATH, 
                    "//div[@role='radio' and not(@aria-checked='true')]" +
                    "|//input[@type='radio' and not(@checked)]" +
                    "|//div[@role='checkbox' and not(@aria-checked='true')]"
                )
                if unchecked:
                    HumanBehavior.human_click(self.driver, unchecked[0])
                    HumanBehavior.random_delay(1, 2)
                    
                    # Try submit again
                    for sel in submit_selectors:
                        try:
                            submit_btn = WebDriverWait(self.driver, 3).until(
                                EC.element_to_be_clickable((By.XPATH, sel))
                            )
                            HumanBehavior.human_click(self.driver, submit_btn)
                            submitted = True
                            break
                        except:
                            continue
            except:
                pass
        
        if submitted:
            print("[+] Report submitted successfully!")
            self.stats["captchas_solved"] = self.captcha_handler.total_solved
            return "success"
        else:
            print("[-] Could not complete report submission")
            return "failed"
    
    def run(self, profiles, delay=90, max_report_attempts=3):
        """Main execution loop"""
        self.stats["start_time"] = datetime.now().isoformat()
        self.stats["total"] = len(profiles)
        
        # Login first
        if not self.login():
            print("[-] Cannot proceed - login failed")
            return
        
        print(f"\n{'='*60}")
        print(f"Starting reporting run: {len(profiles)} profiles")
        print(f"Delay between reports: {delay}s")
        print(f"CAPTCHA solving: {'Available' if self.captcha_handler.is_available() else 'Not configured'}")
        print(f"{'='*60}")
        
        for i, profile in enumerate(profiles):
            print(f"\n{'='*50}")
            print(f"[{i+1}/{len(profiles)}] Profile {i+1}")
            
            # Multiple attempts if needed
            status = "pending"
            for attempt in range(max_report_attempts):
                if attempt > 0:
                    print(f"[*] Attempt {attempt+1}/{max_report_attempts}...")
                    time.sleep(random.randint(30, 60))
                
                status = self.report_profile(profile['url'], profile.get('reason', 'harassment'))
                
                # If blocked or success, stop retrying
                if status in ["success", "blocked", "skipped", "already_reported"]:
                    break
            
            # Update stats
            if status == "success":
                self.stats["success"] += 1
            elif status == "skipped":
                self.stats["skipped"] += 1
            elif status == "already_reported":
                self.stats["already"] += 1
            elif status == "blocked":
                self.stats["blocked"] += 1
                print("\n[!] Account blocked! Stopping.")
                break
            else:
                self.stats["failed"] += 1
            
            # Save progress
            self._save_progress(i+1)
            
            # Wait between reports
            if i < len(profiles) - 1 and self.stats["blocked"] == 0:
                wait_time = random.randint(delay - 15, delay + 15)
                print(f"\n[*] Waiting {wait_time}s before next report...")
                
                # Show countdown
                for remaining in range(wait_time, 0, -10):
                    sys.stdout.write(f"\r[*] {remaining}s remaining... ")
                    sys.stdout.flush()
                    time.sleep(min(10, remaining))
                print()
        
        # Final summary
        self.stats["end_time"] = datetime.now().isoformat()
        self.stats["is_running"] = False
        self._print_summary()
        self._save_results()
    
    def _save_progress(self, current):
        """Save progress to JSON file"""
        progress = {
            "is_running": True,
            "progress": f"{current}/{self.stats['total']}",
            "percentage": round((current / self.stats['total']) * 100, 1),
            "current": current,
            "total": self.stats['total'],
            "success": self.stats['success'],
            "failed": self.stats['failed'],
            "skipped": self.stats['skipped'],
            "already_reported": self.stats['already'],
            "blocked": self.stats['blocked'],
            "captchas_solved": self.captcha_handler.total_solved,
            "timestamp": datetime.now().isoformat()
        }
        try:
            with open("fb_report_progress.json", "w") as f:
                json.dump(progress, f, indent=2)
        except:
            pass
    
    def _print_summary(self):
        """Print final summary"""
        print(f"\n{'='*60}")
        print(f"REPORTING COMPLETE")
        print(f"{'='*60}")
        print(f"  Total profiles:     {self.stats['total']}")
        print(f"  ✓ Success:          {self.stats['success']}")
        print(f"  ✗ Failed:           {self.stats['failed']}")
        print(f"  ⊘ Skipped:          {self.stats['skipped']}")
        print(f"  ⚑ Already reported: {self.stats['already']}")
        print(f"  ⚠ Account blocked:  {self.stats['blocked']}")
        print(f"  ♻ CAPTCHAs solved:  {self.captcha_handler.total_solved}")
        print(f"  Started:            {self.stats['start_time']}")
        print(f"  Ended:              {self.stats['end_time']}")
        print(f"{'='*60}")
        
        # Success rate
        attempted = self.stats['total'] - self.stats['skipped'] - self.stats['already']
        if attempted > 0:
            rate = (self.stats['success'] / attempted) * 100
            print(f"  Success rate:       {rate:.1f}%")
        print(f"{'='*60}")
    
    def _save_results(self):
        """Save detailed results"""
        try:
            fname = f"fb_report_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(fname, "w") as f:
                json.dump(self.stats, f, indent=2)
            print(f"[+] Detailed results saved: {fname}")
        except Exception as e:
            print(f"[-] Could not save results: {e}")
    
    def close(self):
        """Cleanup"""
        self._running = False
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass


def load_profiles(filepath):
    """Load profiles from various formats"""
    profiles = []
    ext = filepath.split('.')[-1].lower() if '.' in filepath else ""
    
    with open(filepath, 'r', encoding='utf-8') as f:
        if ext == "csv":
            reader = csv.DictReader(f)
            for row in reader:
                profiles.append({
                    'url': row['url'].strip(),
                    'reason': row.get('reason', 'harassment').strip()
                })
        elif ext == "json":
            profiles = json.load(f)
        else:
            for line in f:
                url = line.strip()
                if url and not url.startswith('#'):
                    profiles.append({'url': url, 'reason': 'harassment'})
    
    return profiles


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Advanced Facebook Profile Reporter - Authorized Pentesting",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("-e", "--email", required=True, help="Facebook email")
    parser.add_argument("-p", "--password", required=True, help="Facebook password")
    parser.add_argument("-f", "--file", required=True, help="Input file (CSV, JSON, or TXT)")
    parser.add_argument("--delay", type=int, default=90, help="Delay between reports (default: 90s)")
    parser.add_argument("--attempts", type=int, default=3, help="Max report attempts per profile (default: 3)")
    parser.add_argument("--captcha-api", help="2Captcha API key for automatic CAPTCHA solving")
    parser.add_argument("--proxy-list", help="File with proxies (one per line)")
    parser.add_argument("--reason", default="harassment", 
                        choices=["harassment", "fake_account", "hate_speech", 
                                "violence", "nudity", "pretending", "scam"],
                        help="Default report reason")
    
    args = parser.parse_args()
    
    print(f"""
{'='*60}
ADVANCED FACEBOOK PROFILE REPORTER
FOR AUTHORIZED PENTESTING ONLY
{'='*60}
[*] Loaded configuration:
    - Email: {args.email}
    - File: {args.file} 
    - Delay: {args.delay}s
    - Max attempts: {args.attempts}
    - CAPTCHA: {'Configured' if args.captcha_api else 'Not configured (manual only)'}
{'='*60}
    """)
    
    # Load profiles
    profiles = load_profiles(args.file)
    if not profiles:
        print("[-] No profiles loaded. Check your file.")
        exit(1)
    
    print(f"[*] Loaded {len(profiles)} profiles")
    
    # Load proxies if specified
    proxies = None
    if args.proxy_list:
        with open(args.proxy_list, 'r') as f:
            proxies = [line.strip() for line in f if line.strip()]
        print(f"[*] Loaded {len(proxies)} proxies")
    
    # Override reason for profiles without one
    for p in profiles:
        if 'reason' not in p or not p['reason']:
            p['reason'] = args.reason
    
    # Create and run reporter
    reporter = AdvancedReporter(
        email=args.email,
        password=args.password,
        captcha_api_key=args.captcha_api,
        proxies=proxies
    )
    
    try:
        reporter.run(profiles, delay=args.delay, max_report_attempts=args.attempts)
    except KeyboardInterrupt:
        print("\n\n[!] Interrupted by user")
        reporter._save_progress(0)
        print("[*] Progress saved to fb_report_progress.json")
    except Exception as e:
        print(f"\n[-] Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        reporter.close()
        print("\n[*] Browser closed. Goodbye.")
