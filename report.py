#!/usr/bin/env python3
"""
Advanced Facebook Profile Reporter - FOR AUTHORIZED PENTESTING ONLY
Enhanced anti-detection, better success rates, intelligent automation
"""

import time
import json
import csv
import sys
import os
import random
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.proxy import Proxy, ProxyType
import undetected_chromedriver as uc
from fake_useragent import UserAgent
import logging
import requests
from urllib.parse import urlparse, parse_qs
import hashlib
import pickle
import threading
from queue import Queue
import concurrent.futures

# Disable logging
logging.basicConfig(level=logging.ERROR)

try:
    from twocaptcha import TwoCaptcha
    TWOCAPTCHA_AVAILABLE = True
except ImportError:
    TWOCAPTCHA_AVAILABLE = False

class ProxyManager:
    """Manage proxies with rotation"""
    def __init__(self, proxy_list=None):
        self.proxies = proxy_list or []
        self.current_index = 0
        self.used_proxies = set()
        
    def get_proxy(self):
        if not self.proxies:
            return None
        # Rotate through proxies
        proxy = self.proxies[self.current_index % len(self.proxies)]
        self.current_index += 1
        return proxy
    
    def add_proxy(self, proxy):
        if proxy not in self.proxies:
            self.proxies.append(proxy)

class AdvancedFacebookReporter:
    def __init__(self, email, password, captcha_api_key=None, proxy_list=None, headless=False):
        self.email = email
        self.password = password
        self.captcha_api_key = captcha_api_key
        self.proxy_manager = ProxyManager(proxy_list)
        self.headless = headless
        self.driver = None
        self.wait = None
        self.actions = None
        self.user_agent = UserAgent()
        self.session_id = hashlib.md5(f"{email}{time.time()}".encode()).hexdigest()[:8]
        self.cookies_file = f"cookies_{self.session_id}.pkl"
        self.successful_reports = set()
        self.failed_attempts = {}
        self.report_confidence = {}
        self.total_reports = 0
        
        # Enhanced user behavior patterns
        self.mouse_movements = []
        self.scroll_positions = []
        self.typing_speed = (0.05, 0.15)  # Seconds between keystrokes
        
    def _create_driver(self):
        """Create undetectable Chrome driver with advanced features"""
        options = uc.ChromeOptions()
        
        # Advanced anti-detection
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--disable-ipc-flooding-protection')
        options.add_argument('--disable-renderer-backgrounding')
        options.add_argument('--disable-backgrounding-occluded-windows')
        options.add_argument('--disable-site-isolation-trials')
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=IsolateOrigins,site-per-process')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-extensions')
        options.add_argument('--no-default-browser-check')
        options.add_argument('--no-first-run')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--disable-logging')
        options.add_argument('--log-level=3')
        options.add_argument('--silent')
        options.add_argument('--mute-audio')
        options.add_argument('--disable-breakpad')
        options.add_argument('--disable-crash-reporter')
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-popup-blocking')
        options.add_argument('--disable-prompt-on-repost')
        options.add_argument('--disable-hang-monitor')
        options.add_argument('--disable-background-networking')
        
        # Window size randomization
        window_sizes = [
            (1920, 1080), (1366, 768), (1536, 864), (1440, 900), 
            (1280, 720), (1600, 900), (1680, 1050)
        ]
        width, height = random.choice(window_sizes)
        options.add_argument(f'--window-size={width},{height}')
        
        # User agent spoofing
        ua = self.user_agent.random
        options.add_argument(f'--user-agent={ua}')
        
        # Languages
        languages = ['en-US,en;q=0.9', 'en-GB,en;q=0.8', 'en-CA,en;q=0.7']
        options.add_argument(f'--lang={random.choice(languages)}')
        
        # Proxy if available
        proxy = self.proxy_manager.get_proxy()
        if proxy:
            options.add_argument(f'--proxy-server={proxy}')
            print(f"[*] Using proxy: {proxy}")
        
        # Headless mode
        if self.headless:
            options.add_argument('--headless=new')
        
        # Additional experimental options
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_experimental_option("prefs", {
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_settings.popups": 0,
            "profile.password_manager_enabled": False,
            "credentials_enable_service": False
        })
        
        # Create driver with undetected_chromedriver
        try:
            driver = uc.Chrome(options=options)
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": ua})
            driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en']
                    });
                    window.chrome = {
                        runtime: {}
                    };
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );
                '''
            })
            return driver
        except Exception as e:
            print(f"[-] Failed to create driver: {e}")
            raise

    def _human_like_typing(self, element, text):
        """Type text with human-like delays and errors"""
        element.click()
        time.sleep(random.uniform(0.2, 0.5))
        
        for char in text:
            # Random typing speed with occasional pauses
            delay = random.uniform(self.typing_speed[0], self.typing_speed[1])
            
            # Simulate occasional typo and correction (5% chance)
            if random.random() < 0.02:
                wrong_char = random.choice('abcdefghijklmnopqrstuvwxyz')
                element.send_keys(wrong_char)
                time.sleep(random.uniform(0.1, 0.3))
                element.send_keys(Keys.BACKSPACE)
                time.sleep(random.uniform(0.05, 0.15))
            
            element.send_keys(char)
            time.sleep(delay)
            
            # Random pause at punctuation
            if char in '.!?,' and random.random() < 0.3:
                time.sleep(random.uniform(0.3, 0.8))
        
        # Random pause after typing
        time.sleep(random.uniform(0.2, 0.6))

    def _random_mouse_movement(self, start_x, start_y, end_x, end_y):
        """Move mouse with human-like path"""
        if not self.actions:
            return
            
        # Generate bezier curve points
        steps = random.randint(15, 30)
        for i in range(steps):
            t = i / steps
            # Ease in-out curve
            t = t * t * (3 - 2 * t)
            
            x = start_x + (end_x - start_x) * t + random.randint(-5, 5)
            y = start_y + (end_y - start_y) * t + random.randint(-5, 5)
            
            self.actions.move_by_offset(x - start_x, y - start_y)
            time.sleep(random.uniform(0.01, 0.03))

    def _scroll_like_human(self, scroll_amount):
        """Scroll with human-like behavior"""
        if not self.driver:
            return
            
        current_scroll = 0
        while current_scroll < abs(scroll_amount):
            scroll_step = random.randint(50, 150)
            if scroll_amount < 0:
                scroll_step = -scroll_step
            current_scroll += scroll_step
            
            self.driver.execute_script(f"window.scrollBy(0, {scroll_step});")
            time.sleep(random.uniform(0.05, 0.15))
        
        # Random pause after scrolling
        time.sleep(random.uniform(0.2, 0.5))

    def _load_cookies(self):
        """Load saved cookies if available"""
        if os.path.exists(self.cookies_file):
            try:
                with open(self.cookies_file, 'rb') as f:
                    cookies = pickle.load(f)
                    for cookie in cookies:
                        try:
                            self.driver.add_cookie(cookie)
                        except:
                            continue
                print("[*] Loaded saved cookies")
                return True
            except:
                return False
        return False

    def _save_cookies(self):
        """Save cookies for future sessions"""
        try:
            cookies = self.driver.get_cookies()
            with open(self.cookies_file, 'wb') as f:
                pickle.dump(cookies, f)
            return True
        except:
            return False

    def _handle_captcha(self, driver):
        """Handle CAPTCHA if encountered"""
        if not TWOCAPTCHA_AVAILABLE or not self.captcha_api_key:
            print("[!] CAPTCHA detected but no API key provided")
            return False
        
        try:
            # Check for CAPTCHA
            captcha_elements = driver.find_elements(By.XPATH, "//img[contains(@src, 'captcha')]")
            if not captcha_elements:
                return True
            
            print("[*] CAPTCHA detected - solving...")
            solver = TwoCaptcha(self.captcha_api_key)
            
            # Get CAPTCHA image
            captcha_img = captcha_elements[0]
            img_url = captcha_img.get_attribute('src')
            
            # Download CAPTCHA
            response = requests.get(img_url)
            with open('temp_captcha.png', 'wb') as f:
                f.write(response.content)
            
            # Solve CAPTCHA
            result = solver.normal('temp_captcha.png')
            
            # Enter solution
            captcha_input = driver.find_element(By.ID, "captcha_input")
            captcha_input.clear()
            captcha_input.send_keys(result['code'])
            
            # Submit
            submit_btn = driver.find_element(By.ID, "captcha_submit")
            submit_btn.click()
            
            time.sleep(3)
            os.remove('temp_captcha.png')
            return True
            
        except Exception as e:
            print(f"[-] CAPTCHA solving failed: {e}")
            return False

    def login(self):
        """Advanced login with anti-detection"""
        print("[*] Creating undetectable browser...")
        self.driver = self._create_driver()
        self.wait = WebDriverWait(self.driver, 20)
        self.actions = ActionChains(self.driver)
        
        # Navigate to Facebook with delay
        print("[*] Navigating to Facebook...")
        self.driver.get("https://www.facebook.com/")
        time.sleep(random.uniform(3, 6))
        
        # Try to load cookies
        if self._load_cookies():
            self.driver.refresh()
            time.sleep(3)
            
            # Check if cookies worked
            if "login" not in self.driver.current_url.lower():
                print("[+] Login successful using cookies!")
                return True
        
        # Manual login with human-like behavior
        print("[*] Performing manual login...")
        
        # Random initial scroll
        self._scroll_like_human(random.randint(100, 300))
        time.sleep(random.uniform(0.5, 1.5))
        
        # Click on login button if on homepage
        try:
            login_button = self.driver.find_element(By.XPATH, "//a[contains(@href, 'login')]")
            login_button.click()
            time.sleep(random.uniform(2, 4))
        except:
            pass
        
        # Enter email
        try:
            email_field = self.wait.until(EC.presence_of_element_located((By.ID, "email")))
            self._human_like_typing(email_field, self.email)
        except:
            try:
                email_field = self.driver.find_element(By.NAME, "email")
                self._human_like_typing(email_field, self.email)
            except Exception as e:
                print(f"[-] Cannot find email field: {e}")
                return False
        
        time.sleep(random.uniform(0.5, 1.5))
        
        # Enter password
        try:
            pass_field = self.driver.find_element(By.ID, "pass")
            self._human_like_typing(pass_field, self.password)
        except:
            try:
                pass_field = self.driver.find_element(By.NAME, "pass")
                self._human_like_typing(pass_field, self.password)
            except:
                return False
        
        time.sleep(random.uniform(0.5, 1.5))
        
        # Click login with human-like movement
        try:
            login_btn = self.driver.find_element(By.NAME, "login")
            self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", login_btn)
            time.sleep(random.uniform(0.3, 0.7))
            login_btn.click()
        except:
            try:
                login_btn = self.driver.find_element(By.XPATH, "//button[@type='submit']")
                login_btn.click()
            except:
                pass_field.send_keys(Keys.RETURN)
        
        # Wait for login
        time.sleep(random.uniform(5, 10))
        
        # Handle login challenges
        if "checkpoint" in self.driver.current_url.lower():
            print("[!] Checkpoint detected - attempting to bypass...")
            self._handle_checkpoint()
        elif "login" in self.driver.current_url.lower():
            print("[!] Login failed - checking for 2FA...")
            if "two_step" in self.driver.page_source.lower():
                print("[!] 2FA required - needs manual intervention")
                return False
        
        # Save cookies if login successful
        if "login" not in self.driver.current_url.lower():
            self._save_cookies()
            print("[+] Login successful!")
            return True
        
        return False

    def _handle_checkpoint(self):
        """Handle Facebook checkpoint challenges"""
        try:
            # Check for different checkpoint types
            if "confirm" in self.driver.page_source.lower():
                # Try to bypass with save browser
                try:
                    save_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Continue')]")
                    save_btn.click()
                    time.sleep(3)
                except:
                    pass
        except:
            pass

    def _click_with_confidence(self, element, retries=3):
        """Click element with confidence and error handling"""
        for attempt in range(retries):
            try:
                # Scroll to element
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                time.sleep(random.uniform(0.2, 0.5))
                
                # Random hover before clicking
                self.actions.move_to_element(element).pause(random.uniform(0.1, 0.3))
                
                # Click with JavaScript as fallback
                try:
                    element.click()
                except:
                    self.driver.execute_script("arguments[0].click();", element)
                
                time.sleep(random.uniform(0.5, 1))
                return True
                
            except StaleElementReferenceException:
                time.sleep(random.uniform(0.5, 1))
                continue
            except Exception as e:
                if attempt == retries - 1:
                    print(f"[-] Failed to click element: {e}")
                    return False
                time.sleep(random.uniform(0.5, 1))
        return False

    def _find_element_with_fallback(self, selectors, timeout=10):
        """Find element using multiple selectors with fallback"""
        for selector in selectors:
            try:
                if selector.startswith('//'):
                    element = WebDriverWait(self.driver, timeout).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                elif selector.startswith('.'):
                    element = WebDriverWait(self.driver, timeout).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                else:
                    element = WebDriverWait(self.driver, timeout).until(
                        EC.element_to_be_clickable((By.ID, selector))
                    )
                return element
            except:
                continue
        return None

    def report_profile(self, profile_url, reason="harassment", additional_notes=""):
        """Advanced profile reporting with higher success rate"""
        print(f"[*] Opening profile: {profile_url}")
        
        # Check if already reported
        if profile_url in self.successful_reports:
            return "already_reported"
        
        try:
            self.driver.get(profile_url)
            time.sleep(random.uniform(3, 6))
            
            # Human-like behavior on page load
            self._scroll_like_human(random.randint(100, 300))
            time.sleep(random.uniform(0.3, 0.8))
            
            # Handle popups
            self._handle_popups()
            
            # Check for checkpoint
            if "checkpoint" in self.driver.current_url.lower():
                return "blocked"
            
            # Check if profile exists
            if "Sorry" in self.driver.title or "content_placeholder" in self.driver.page_source:
                return "skipped"
            
            # Enhanced reporting flow
            if self._perform_report_flow(reason):
                self.successful_reports.add(profile_url)
                self.total_reports += 1
                return "success"
            
            return "failed"
            
        except Exception as e:
            print(f"[-] Error reporting profile: {e}")
            return "failed"

    def _perform_report_flow(self, reason):
        """Perform the complete report flow with retries"""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Step 1: Find and click More button
                more_selectors = [
                    "//div[@aria-label='More']",
                    "//div[@aria-label='More actions']",
                    "//div[@role='button']//span[contains(text(), 'More')]",
                    "//div[contains(@class, 'x1i10hfl') and @tabindex='0']",
                    "//span[text()='More']",
                    "//div[contains(@aria-label, 'More')]"
                ]
                
                more_btn = self._find_element_with_fallback(more_selectors, 5)
                if not more_btn:
                    print("[-] More button not found")
                    continue
                
                if not self._click_with_confidence(more_btn):
                    continue
                
                time.sleep(random.uniform(1, 2.5))
                
                # Step 2: Find and click Report
                report_selectors = [
                    "//span[contains(text(), 'Find support')]",
                    "//span[contains(text(), 'Report')]",
                    "//span[text()='Report profile']",
                    "//div[@role='menuitem']//span[contains(text(), 'Report')]",
                    "//div[contains(@role, 'menu')]//span[contains(text(), 'Report')]"
                ]
                
                report_btn = self._find_element_with_fallback(report_selectors, 3)
                if not report_btn:
                    return False
                
                if not self._click_with_confidence(report_btn):
                    return False
                
                time.sleep(random.uniform(1, 2.5))
                
                # Step 3: Select reason with expanded options
                reason_map = {
                    "harassment": ["Harassment", "Bullying", "Harassment or bullying"],
                    "fake_account": ["Fake account", "Fake profile", "Pretending to be someone"],
                    "hate_speech": ["Hate speech", "Hate speech or symbols"],
                    "violence": ["Violence", "Violence or dangerous organizations"],
                    "nudity": ["Nudity", "Sexual activity", "Nudity or sexual activity"],
                    "pretending": ["Pretending", "Fake account", "Pretending to be someone"],
                    "scam": ["Scam", "Fraud", "Scam or fraud"]
                }
                
                reason_options = reason_map.get(reason, reason_map["harassment"])
                reason_selected = False
                
                for reason_text in reason_options:
                    try:
                        reason_elem = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, f"//span[contains(text(), '{reason_text}')]"))
                        )
                        if reason_elem:
                            self._click_with_confidence(reason_elem)
                            reason_selected = True
                            break
                    except:
                        continue
                
                if not reason_selected:
                    return False
                
                time.sleep(random.uniform(1, 2))
                
                # Step 4: Add additional details if needed
                try:
                    details_field = self.driver.find_element(By.XPATH, "//textarea[contains(@placeholder, 'Details')]")
                    if details_field:
                        details = self._generate_report_details(reason)
                        self._human_like_typing(details_field, details)
                        time.sleep(random.uniform(0.5, 1))
                except:
                    pass
                
                # Step 5: Submit report
                submit_selectors = [
                    "//span[text()='Submit']/..",
                    "//span[text()='Done']/..",
                    "//div[@role='button']//span[contains(text(), 'Submit')]",
                    "//div[@role='button']//span[contains(text(), 'Done')]",
                    "//button[contains(text(), 'Submit')]",
                    "//button[contains(text(), 'Done')]"
                ]
                
                submit_btn = self._find_element_with_fallback(submit_selectors, 3)
                if submit_btn:
                    if self._click_with_confidence(submit_btn):
                        print("[+] Report submitted successfully!")
                        return True
                
                return False
                
            except Exception as e:
                print(f"[-] Report attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(random.uniform(2, 4))
                continue
        
        return False

    def _generate_report_details(self, reason):
        """Generate human-like report details"""
        templates = {
            "harassment": [
                "This person has been sending harassing messages and making me feel unsafe. They continue to contact me despite being asked to stop.",
                "I'm being targeted with harassment from this profile. They're posting threatening comments and sending unwanted messages.",
                "This individual is engaging in persistent harassment and making inappropriate comments that violate community standards."
            ],
            "fake_account": [
                "This account appears to be fake. They're using someone else's photos and pretending to be someone they're not.",
                "I believe this is a fake account designed to impersonate a real person and potentially scam others.",
                "This profile is suspicious - they're using stolen photos and claiming to be someone I know personally."
            ],
            "hate_speech": [
                "This account is posting hate speech and discriminatory content that targets specific groups.",
                "I've observed this profile sharing hate speech and promoting discrimination against protected groups.",
                "This individual regularly posts content that constitutes hate speech and violates community standards."
            ],
            "violence": [
                "This profile contains content that promotes violence and could potentially incite harm to others.",
                "I've seen this account posting threats and content that glorifies violence.",
                "This individual is sharing violent content and making threatening statements."
            ],
            "nudity": [
                "This account is sharing explicit content without age restrictions or warnings.",
                "I've encountered inappropriate sexual content on this profile that violates community standards.",
                "This profile contains explicit material that should be restricted."
            ],
            "pretending": [
                "This person is pretending to be someone else and potentially running a scam.",
                "I believe this account is impersonating a real person and could be used for fraudulent activities.",
                "This profile is deceptive - they're pretending to be someone they're not."
            ],
            "scam": [
                "This account appears to be engaged in fraudulent activities and scams.",
                "I've received suspicious messages from this profile attempting to scam me or others.",
                "This individual is running a scam and targeting vulnerable users."
            ]
        }
        
        details = random.choice(templates.get(reason, templates["harassment"]))
        
        # Add some variation
        variations = [
            "",
            " I've reported this to the authorities as well.",
            " This behavior is concerning and should be addressed immediately.",
            " This is a serious violation of community standards.",
            " This person has been doing this repeatedly."
        ]
        
        details += random.choice(variations)
        
        return details

    def _handle_popups(self):
        """Handle various popups intelligently"""
        popup_selectors = [
            "//span[text()='Allow all cookies']/..",
            "//span[contains(text(), 'Allow all cookies')]/..",
            "//div[@role='button']//span[contains(text(), 'Allow')]",
            "//button[contains(text(), 'Allow')]",
            "//button[contains(text(), 'Accept')]",
            "//div[@aria-label='Close']",
            "//span[text()='Not Now']/..",
            "//span[contains(text(), 'Not now')]/..",
            "//span[text()='Later']/..",
            "//span[text()='Skip']/..",
            "//div[@role='button']//span[contains(text(), 'Dismiss')]"
        ]
        
        for selector in popup_selectors:
            try:
                elements = self.driver.find_elements(By.XPATH, selector)
                for elem in elements:
                    if elem.is_displayed() and elem.is_enabled():
                        self._click_with_confidence(elem)
                        time.sleep(random.uniform(0.3, 0.7))
            except:
                continue

    def _analyze_report_confidence(self):
        """Analyze current session confidence score"""
        confidence_score = 100
        
        # Reduce confidence based on failed attempts
        confidence_score -= len(self.failed_attempts) * 5
        
        # Reduce confidence if too many reports in short time
        if self.total_reports > 10:
            confidence_score -= (self.total_reports - 10) * 2
        
        # Increase confidence with successful reports
        confidence_score += len(self.successful_reports) * 2
        
        return max(0, min(100, confidence_score))

    def run(self, profiles, delay=90, max_reports=50):
        """Enhanced main run loop with smart scheduling"""
        if not self.login():
            print("[-] Cannot proceed - login failed")
            return
        
        results = {
            "success": 0, 
            "failed": 0, 
            "skipped": 0,
            "already": 0, 
            "blocked": 0, 
            "total": len(profiles),
            "confidence_score": 0
        }
        
        # Smart delay calculation based on time of day
        current_hour = datetime.now().hour
        if 6 <= current_hour <= 9:  # Morning
            base_delay = 120
        elif 10 <= current_hour <= 17:  # Daytime
            base_delay = 90
        else:  # Night
            base_delay = 150
        
        # Don't exceed max reports
        profiles_to_report = profiles[:max_reports]
        
        print(f"[*] Will report up to {max_reports} profiles")
        print(f"[*] Base delay: {base_delay}s")
        
        for i, profile in enumerate(profiles_to_report):
            # Check confidence before each report
            confidence = self._analyze_report_confidence()
            results["confidence_score"] = confidence
            
            print(f"\n{'='*50}")
            print(f"[{i+1}/{len(profiles_to_report)}] Reporting... (Confidence: {confidence}%)")
            
            if confidence < 30:
                print("[!] Confidence score too low - pausing for safety")
                self._save_status(results, i+1)
                time.sleep(random.uniform(180, 300))
                continue
            
            # Adjust delay based on confidence
            adjusted_delay = delay + (100 - confidence)
            
            status = self.report_profile(
                profile['url'], 
                profile.get('reason', 'harassment'),
                profile.get('notes', '')
            )
            
            if status == "success":
                results["success"] += 1
                print("[✓] SUCCESS")
            elif status == "skipped":
                results["skipped"] += 1
                print("[-] Skipped - profile not found")
            elif status == "already_reported":
                results["already"] += 1
                print("[-] Already reported")
            elif status == "blocked":
                results["blocked"] += 1
                print("[!] Account blocked!")
                break
            else:
                results["failed"] += 1
                print("[✗] FAILED")
                self.failed_attempts[profile['url']] = datetime.now().isoformat()
            
            # Save status
            self._save_status(results, i+1)
            
            # Intelligent wait time
            if i < len(profiles_to_report) - 1 and results["blocked"] == 0:
                # Random wait with human-like patterns
                if random.random() < 0.3:  # 30% chance of longer break
                    wait = random.randint(adjusted_delay + 30, adjusted_delay + 60)
                else:
                    wait = random.randint(adjusted_delay - 10, adjusted_delay + 10)
                
                print(f"[*] Waiting {wait}s...")
                
                # Break the wait into segments to avoid detection
                for _ in range(wait // 30):
                    time.sleep(25)
                    # Random mouse movement to appear active
                    if self.driver:
                        try:
                            self.driver.execute_script("window.scrollBy(0, 10);")
                        except:
                            pass
                    time.sleep(5)
        
        # Print summary
        print(f"\n{'='*50}")
        print(f"REPORT COMPLETE!")
        print(f"  Success:      {results['success']}")
        print(f"  Failed:       {results['failed']}")
        print(f"  Skipped:      {results['skipped']}")
        print(f"  Already:      {results['already']}")
        print(f"  Blocked:      {results['blocked']}")
        print(f"  Confidence:   {results['confidence_score']}%")
        print(f"{'='*50}")
        
        self._save_results(results)

    def _save_status(self, results, current):
        """Save current status"""
        status = {
            "is_running": True,
            "progress": f"{current}/{results['total']}",
            "success": results['success'],
            "failed": results['failed'],
            "skipped": results['skipped'],
            "already_reported": results['already'],
            "blocked": results['blocked'],
            "confidence_score": results['confidence_score'],
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id
        }
        with open(f"fb_status_{self.session_id}.json", "w") as f:
            json.dump(status, f, indent=2)

    def _save_results(self, results):
        """Save final results"""
        results['is_running'] = False
        results['end_time'] = datetime.now().isoformat()
        results['session_id'] = self.session_id
        results['successful_reports'] = list(self.successful_reports)
        
        fname = f"fb_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.session_id}.json"
        with open(fname, "w") as f:
            json.dump(results, f, indent=2)
        print(f"[+] Results saved: {fname}")
        
        # Clean up cookies
        try:
            os.remove(self.cookies_file)
        except:
            pass

    def close(self):
        """Clean up resources"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

def load_profiles(file_path):
    """Load profiles from various file formats"""
    profiles = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        ext = file_path.split('.')[-1].lower()
        
        if ext == "csv":
            reader = csv.DictReader(f)
            for row in reader:
                profile = {
                    'url': row.get('url', '').strip(),
                    'reason': row.get('reason', 'harassment').strip(),
                    'notes': row.get('notes', '').strip()
                }
                if profile['url']:
                    profiles.append(profile)
                    
        elif ext == "json":
            data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        profile = {
                            'url': item.get('url', '').strip(),
                            'reason': item.get('reason', 'harassment').strip(),
                            'notes': item.get('notes', '').strip()
                        }
                        if profile['url']:
                            profiles.append(profile)
            elif isinstance(data, dict):
                for key, value in data.items():
                    if isinstance(value, dict) and 'url' in value:
                        profile = {
                            'url': value.get('url', '').strip(),
                            'reason': value.get('reason', 'harassment').strip(),
                            'notes': value.get('notes', '').strip()
                        }
                        if profile['url']:
                            profiles.append(profile)
        else:
            # Text file - one URL per line
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Parse if line contains URL and reason
                    parts = line.split(',')
                    profile = {'url': parts[0].strip(), 'reason': 'harassment'}
                    if len(parts) > 1:
                        profile['reason'] = parts[1].strip()
                    if len(parts) > 2:
                        profile['notes'] = ','.join(parts[2:]).strip()
                    profiles.append(profile)
    
    return profiles

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Advanced Facebook Profile Reporter',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("-e", "--email", required=True, help="Facebook email")
    parser.add_argument("-p", "--password", required=True, help="Facebook password")
    parser.add_argument("-f", "--file", required=True, help="File with profiles")
    parser.add_argument("--delay", type=int, default=90, help="Delay between reports")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--max-reports", type=int, default=50, help="Maximum reports to send")
    parser.add_argument("--captcha-key", help="2Captcha API key for CAPTCHA solving")
    parser.add_argument("--proxies", help="Comma-separated list of proxies (e.g., proxy1:8080,proxy2:8080)")
    
    args = parser.parse_args()
    
    # Load profiles
    profiles = load_profiles(args.file)
    
    if not profiles:
        print("[-] No profiles loaded")
        sys.exit(1)
    
    print(f"[*] Loaded {len(profiles)} profiles")
    
    # Parse proxies
    proxy_list = None
    if args.proxies:
        proxy_list = [p.strip() for p in args.proxies.split(',') if p.strip()]
    
    # Create reporter
    reporter = AdvancedFacebookReporter(
        email=args.email,
        password=args.password,
        captcha_api_key=args.captcha_key,
        proxy_list=proxy_list,
        headless=args.headless
    )
    
    try:
        reporter.run(profiles, delay=args.delay, max_reports=args.max_reports)
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user")
    except Exception as e:
        print(f"\n[-] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        reporter.close()
        print("[*] Browser closed")