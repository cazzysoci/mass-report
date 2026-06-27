import time
import json
import csv
import random
import logging
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .browser import StealthBrowser
from .stealth import StealthTechniques

class FacebookReporterAdvanced:
    def __init__(self, email, password, config_path='config.json', captcha_api_key=None):
        self.email = email
        self.password = password
        self.captcha_api_key = captcha_api_key
        self.config_path = config_path
        self.browser = StealthBrowser(config_path)
        self.stealth = None
        
        with open(config_path, 'r') as f:
            self.config = json.load(f)
            
        self.setup_logging()
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/report.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def login(self):
        self.logger.info("Initializing stealth browser...")
        self.browser.init_driver()
        self.stealth = StealthTechniques(self.browser.driver)
        
        self.logger.info("Navigating to Facebook login...")
        self.browser.driver.get("https://www.facebook.com/login")
        
        self.browser.random_delay(3, 5)
        self.handle_popups()
        self.browser.random_delay(1, 2)
        
        self.logger.info("Entering credentials...")
        try:
            email_field = WebDriverWait(self.browser.driver, 10).until(
                EC.presence_of_element_located((By.ID, "email"))
            )
            self.browser.human_mouse_movement(email_field)
            email_field.clear()
            for char in self.email:
                email_field.send_keys(char)
                time.sleep(random.uniform(0.02, 0.05))
                
            pass_field = self.browser.driver.find_element(By.ID, "pass")
            self.browser.human_mouse_movement(pass_field)
            pass_field.clear()
            for char in self.password:
                pass_field.send_keys(char)
                time.sleep(random.uniform(0.02, 0.05))
                
            login_btn = self.browser.driver.find_element(By.NAME, "login")
            self.browser.human_mouse_movement(login_btn)
            login_btn.click()
            
            self.browser.random_delay(5, 8)
            self.handle_popups()
            self.browser.random_delay(2, 4)
            
            if "login" not in self.browser.driver.current_url.lower():
                self.logger.info("Login successful!")
                return True
            else:
                if "checkpoint" in self.browser.driver.current_url.lower():
                    self.logger.info("2FA checkpoint detected")
                    return False
                self.logger.error("Login failed - wrong credentials?")
                return False
                
        except Exception as e:
            self.logger.error(f"Login error: {e}")
            return False
            
    def handle_popups(self):
        selectors = [
            "//span[text()='Allow all cookies']/..",
            "//span[contains(text(), 'Allow all cookies')]/..",
            "//div[@role='button']//span[contains(text(), 'Allow')]",
            "//button[contains(text(), 'Allow')]",
            "//button[contains(text(), 'Accept')]",
            "//div[@aria-label='Close']",
            "//span[text()='Not Now']/..",
            "//span[contains(text(), 'Not now')]/.."
        ]
        
        for selector in selectors:
            try:
                elements = self.browser.driver.find_elements(By.XPATH, selector)
                for elem in elements:
                    if elem.is_displayed():
                        self.browser.human_mouse_movement(elem)
                        elem.click()
                        self.browser.random_delay(0.3, 0.8)
            except:
                continue
                
    def report_profile(self, profile_url, reason="harassment"):
        self.logger.info(f"Opening profile: {profile_url}")
        self.browser.driver.get(profile_url)
        self.browser.random_delay(4, 6)
        
        self.handle_popups()
        self.stealth.emulate_human_behavior()
        
        if "checkpoint" in self.browser.driver.current_url.lower():
            return "blocked"
            
        if "Sorry" in self.browser.driver.title or "content_placeholder" in self.browser.driver.page_source:
            return "skipped"
            
        self.browser.scroll_page(random.randint(2, 4))
        
        self.logger.info("Finding menu button...")
        more_selectors = [
            "//div[@aria-label='More']",
            "//div[@aria-label='More actions']",
            "//div[@role='button']//span[contains(text(), 'More')]",
            "//div[contains(@class, 'x1i10hfl') and @tabindex='0']"
        ]
        
        for selector in more_selectors:
            try:
                btn = WebDriverWait(self.browser.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                self.browser.human_mouse_movement(btn)
                btn.click()
                self.browser.random_delay(1, 2)
                
                self.logger.info("Finding report option...")
                report_selectors = [
                    "//span[contains(text(), 'Find support')]",
                    "//span[contains(text(), 'Report')]",
                    "//span[text()='Report profile']",
                    "//div[@role='menuitem']//span[contains(text(), 'Report')]"
                ]
                
                for rep_sel in report_selectors:
                    try:
                        report_btn = WebDriverWait(self.browser.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, rep_sel))
                        )
                        self.browser.human_mouse_movement(report_btn)
                        report_btn.click()
                        self.browser.random_delay(2, 3)
                        
                        self.logger.info(f"Selecting reason: {reason}")
                        reason_map = {
                            "harassment": "Harassment",
                            "fake_account": "Fake account",
                            "hate_speech": "Hate speech",
                            "violence": "Violence",
                            "nudity": "Nudity",
                            "pretending": "Pretending",
                            "scam": "Scam"
                        }
                        reason_text = reason_map.get(reason, "Harassment")
                        
                        try:
                            reason_elem = WebDriverWait(self.browser.driver, 5).until(
                                EC.element_to_be_clickable((By.XPATH, f"//span[contains(text(), '{reason_text}')]"))
                            )
                            self.browser.human_mouse_movement(reason_elem)
                            reason_elem.click()
                            self.browser.random_delay(1, 2)
                        except:
                            return "failed"
                            
                        self.logger.info("Submitting report...")
                        submit_selectors = [
                            "//span[text()='Submit']/..",
                            "//span[text()='Done']/..",
                            "//div[@role='button']//span[contains(text(), 'Submit')]",
                            "//div[@role='button']//span[contains(text(), 'Done')]"
                        ]
                        
                        for sub_sel in submit_selectors:
                            try:
                                sub_btn = WebDriverWait(self.browser.driver, 3).until(
                                    EC.element_to_be_clickable((By.XPATH, sub_sel))
                                )
                                self.browser.human_mouse_movement(sub_btn)
                                sub_btn.click()
                                self.browser.random_delay(2, 3)
                                self.logger.info("Report submitted successfully!")
                                return "success"
                            except:
                                continue
                        return "failed"
                        
                    except Exception as e:
                        continue
                return "already_reported"
            except:
                continue
        return "failed"
        
    def run(self, profiles, delay=90):
        if not self.login():
            self.logger.error("Cannot proceed - login failed")
            return
            
        results = {
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "already": 0,
            "blocked": 0,
            "total": len(profiles)
        }
        
        for i, profile in enumerate(profiles):
            self.logger.info(f"[{i+1}/{len(profiles)}] Reporting...")
            status = self.report_profile(profile['url'], profile.get('reason', 'harassment'))
            
            if status == "success":
                results["success"] += 1
                self.logger.info("✓ SUCCESS")
            elif status == "skipped":
                results["skipped"] += 1
                self.logger.info("- Skipped - profile not found")
            elif status == "already_reported":
                results["already"] += 1
                self.logger.info("- Already reported")
            elif status == "blocked":
                results["blocked"] += 1
                self.logger.info("! Account blocked!")
                break
            else:
                results["failed"] += 1
                self.logger.info("✗ FAILED")
                
            self.save_status(results, i+1)
            
            if i < len(profiles) - 1 and results["blocked"] == 0:
                wait = random.randint(delay - 10, delay + 10)
                self.logger.info(f"Waiting {wait}s...")
                time.sleep(wait)
                
        self.logger.info("="*50)
        self.logger.info("COMPLETE!")
        self.logger.info(f"Success: {results['success']}")
        self.logger.info(f"Failed: {results['failed']}")
        self.logger.info(f"Skipped: {results['skipped']}")
        self.logger.info(f"Already: {results['already']}")
        self.logger.info(f"Blocked: {results['blocked']}")
        self.logger.info("="*50)
        
        self.save_results(results)
        
    def save_status(self, results, current):
        status = {
            "is_running": True,
            "progress": f"{current}/{results['total']}",
            "success": results['success'],
            "failed": results['failed'],
            "skipped": results['skipped'],
            "already_reported": results['already'],
            "blocked": results['blocked'],
            "timestamp": datetime.now().isoformat()
        }
        with open("fb_status.json", "w") as f:
            json.dump(status, f)
            
    def save_results(self, results):
        results['is_running'] = False
        results['end_time'] = datetime.now().isoformat()
        fname = f"results/fb_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(fname, "w") as f:
            json.dump(results, f, indent=2)
        self.logger.info(f"Results saved: {fname}")