#!/usr/bin/env python3
"""
Mass Facebook Profile Reporter - FOR AUTHORIZED PENTESTING ONLY
Zero config - auto manages ChromeDriver
"""


import time
import json
import csv
import sys
import os
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


# Auto-manage ChromeDriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service


try:
    from twocaptcha import TwoCaptcha
    TWOCAPTCHA_AVAILABLE = True
except ImportError:
    TWOCAPTCHA_AVAILABLE = False



class FacebookReporter:
    def __init__(self, email, password, captcha_api_key=None):
        self.email = email
        self.password = password
        self.captcha_api_key = captcha_api_key
        self.driver = None
        self.wait = None


    def _init_driver(self):
        """Auto-setup ChromeDriver - no manual download needed"""
        options = webdriver.ChromeOptions()
        
        # Anti-detection
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--lang=en-US')
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # Auto-download and use correct ChromeDriver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # Remove webdriver flag
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        self.driver = driver
        self.wait = WebDriverWait(driver, 15)
        return driver


    def _click_cookies(self):
        """Click ALL cookie/notification popups"""
        try:
            # Try multiple cookie button selectors
            selectors = [
                "//span[text()='Allow all cookies']/..",
                "//span[contains(text(), 'Allow all cookies')]/..",
                "//div[@role='button']//span[contains(text(), 'Allow')]",
                "//button[contains(text(), 'Allow')]",
                "//button[contains(text(), 'Accept')]",
                "//div[@aria-label='Close']",
                "//span[text()='Not Now']/..",
                "//span[contains(text(), 'Not now')]/..",
                "//span[text()='Later']/..",
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for elem in elements:
                        try:
                            if elem.is_displayed():
                                elem.click()
                                print("[+] Clicked popup:", selector[:50])
                                time.sleep(0.5)
                        except:
                            continue
                except:
                    continue
        except Exception as e:
            pass  # No popup found - that's fine


    def login(self):
        """Login to Facebook"""
        print("[*] Opening Chrome...")
        self._init_driver()
        
        print("[*] Going to Facebook login page...")
        self.driver.get("https://www.facebook.com/login")
        time.sleep(4)
        
        # Click any cookie popups
        self._click_cookies()
        time.sleep(1)
        
        print("[*] Entering email...")
        try:
            email_field = self.wait.until(EC.presence_of_element_located((By.ID, "email")))
            email_field.clear()
            email_field.send_keys(self.email)
        except:
            try:
                email_field = self.driver.find_element(By.NAME, "email")
                email_field.clear()
                email_field.send_keys(self.email)
            except Exception as e:
                print(f"[-] Cannot find email field: {e}")
                self.driver.save_screenshot("error_email.png")
                return False
        
        time.sleep(0.5)
        
        print("[*] Entering password...")
        try:
            pass_field = self.driver.find_element(By.ID, "pass")
            pass_field.clear()
            pass_field.send_keys(self.password)
        except:
            pass_field = self.driver.find_element(By.NAME, "pass")
            pass_field.clear()
            pass_field.send_keys(self.password)
        
        time.sleep(0.5)
        
        print("[*] Clicking login...")
        try:
            login_btn = self.driver.find_element(By.NAME, "login")
            login_btn.click()
        except:
            try:
                login_btn = self.driver.find_element(By.XPATH, "//button[@type='submit']")
                login_btn.click()
            except:
                pass_field.send_keys(Keys.RETURN)
        
        time.sleep(5)
        
        # Handle post-login popups
        self._click_cookies()
        
        # Check if logged in
        if "login" not in self.driver.current_url.lower():
            print("[+] Login successful!")
            return True
        else:
            # Check for 2FA
            if "checkpoint" in self.driver.current_url.lower():
                print("[!] 2FA/Checkpoint detected!")
                print("[*] Checkpoint URL:", self.driver.current_url)
                self.driver.save_screenshot("checkpoint.png")
                print("[*] Screenshot saved: checkpoint.png")
                return False
            print("[-] Login failed - wrong credentials?")
            return False


    def report_profile(self, profile_url, reason="harassment"):
        """Report a single profile"""
        print(f"[*] Opening profile...")
        self.driver.get(profile_url)
        time.sleep(4)
        
        # Handle popups
        self._click_cookies()
        
        # Check if blocked
        if "checkpoint" in self.driver.current_url.lower():
            return "blocked"
        
        # Check if page exists
        if "Sorry" in self.driver.title or "content_placeholder" in self.driver.page_source:
            return "skipped"
        
        # Click the three dots menu
        print("[*] Clicking More button...")
        clicked = False
        more_selectors = [
            "//div[@aria-label='More']",
            "//div[@aria-label='More actions']",
            "//div[@role='button']//span[contains(text(), 'More')]",
            "//div[contains(@class, 'x1i10hfl') and @tabindex='0']"
        ]
        for sel in more_selectors:
            try:
                btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, sel))
                )
                btn.click()
                clicked = True
                break
            except:
                continue
        
        if not clicked:
            return "failed"
        
        time.sleep(2)
        
        # Click Report
        print("[*] Clicking Report...")
        clicked = False
        report_selectors = [
            "//span[contains(text(), 'Find support')]",
            "//span[contains(text(), 'Report')]",
            "//span[text()='Report profile']",
            "//div[@role='menuitem']//span[contains(text(), 'Report')]"
        ]
        for sel in report_selectors:
            try:
                btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, sel))
                )
                btn.click()
                clicked = True
                break
            except:
                continue
        
        if not clicked:
            return "already_reported"
        
        time.sleep(2)
        
        # Select reason
        print(f"[*] Selecting reason: {reason}...")
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
            reason_elem = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, f"//span[contains(text(), '{reason_text}')]"))
            )
            reason_elem.click()
            time.sleep(1)
        except:
            return "failed"
        
        # Submit
        print("[*] Submitting report...")
        submit_selectors = [
            "//span[text()='Submit']/..",
            "//span[text()='Done']/..",
            "//div[@role='button']//span[contains(text(), 'Submit')]",
            "//div[@role='button']//span[contains(text(), 'Done')]"
        ]
        for sel in submit_selectors:
            try:
                btn = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, sel))
                )
                btn.click()
                time.sleep(2)
                print("[+] Report submitted!")
                return "success"
            except:
                continue
        
        return "failed"


    def run(self, profiles, delay=90):
        """Run the full reporting cycle"""
        if not self.login():
            print("[-] Cannot proceed - login failed")
            return
        
        results = {"success": 0, "failed": 0, "skipped": 0, 
                   "already": 0, "blocked": 0, "total": len(profiles)}
        
        for i, profile in enumerate(profiles):
            print(f"\n{'='*50}")
            print(f"[{i+1}/{len(profiles)}] Reporting...")
            
            status = self.report_profile(profile['url'], profile.get('reason', 'harassment'))
            
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
            
            # Save status
            self._save_status(results, i+1)
            
            # Wait between reports
            if i < len(profiles) - 1 and results["blocked"] == 0:
                wait = random.randint(delay - 10, delay + 10)
                print(f"[*] Waiting {wait}s...")
                time.sleep(wait)
        
        # Print summary
        print(f"\n{'='*50}")
        print(f"COMPLETE!")
        print(f"  Success:      {results['success']}")
        print(f"  Failed:       {results['failed']}")
        print(f"  Skipped:      {results['skipped']}")
        print(f"  Already:      {results['already']}")
        print(f"  Blocked:      {results['blocked']}")
        print(f"{'='*50}")
        
        self._save_results(results)


    def _save_status(self, results, current):
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


    def _save_results(self, results):
        results['is_running'] = False
        results['end_time'] = datetime.now().isoformat()
        fname = f"fb_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(fname, "w") as f:
            json.dump(results, f, indent=2)
        print(f"[+] Results saved: {fname}")


    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--email", required=True)
    parser.add_argument("-p", "--password", required=True)
    parser.add_argument("-f", "--file", required=True)
    parser.add_argument("--delay", type=int, default=90)
    args = parser.parse_args()


    # Load profiles
    profiles = []
    with open(args.file, 'r', encoding='utf-8') as f:
        ext = args.file.split('.')[-1].lower()
        if ext == "csv":
            reader = csv.DictReader(f)
            for row in reader:
                profiles.append({'url': row['url'].strip(), 'reason': row.get('reason', 'harassment').strip()})
        elif ext == "json":
            profiles = json.load(f)
        else:
            for line in f:
                url = line.strip()
                if url and not url.startswith('#'):
                    profiles.append({'url': url, 'reason': 'harassment'})


    if not profiles:
        print("[-] No profiles loaded")
        exit(1)


    print(f"[*] Loaded {len(profiles)} profiles")


    reporter = FacebookReporter(
        email=args.email,
        password=args.password
    )


    try:
        reporter.run(profiles, delay=args.delay)
    except KeyboardInterrupt:
        print("\n[!] Interrupted")
    except Exception as e:
        print(f"\n[-] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        reporter.close() 
