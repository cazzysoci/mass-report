import random
import time
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import undetected_chromedriver as uc
from fake_useragent import UserAgent
import json

class StealthBrowser:
    def __init__(self, config_path='config.json'):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        self.driver = None
        self.wait = None
        self.ua = UserAgent()
        
    def _get_headers(self):
        return {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        }
        
    def init_driver(self, use_proxy=None):
        user_agent = self.ua.random
        options = uc.ChromeOptions()
        
        options.add_argument(f'--user-agent={user_agent}')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-features=IsolateOrigins,site-per-process')
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=BlockInsecurePrivateNetworkRequests')
        options.add_argument('--disable-features=OutOfBlinkCors')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_experimental_option('prefs', {
            'credentials_enable_service': False,
            'profile.password_manager_enabled': False,
            'profile.default_content_setting_values.notifications': 2,
            'profile.default_content_setting_values.automatic_downloads': 2,
            'profile.default_content_setting_values.media_stream': 2,
            'profile.default_content_setting_values.geolocation': 2
        })
        
        if use_proxy:
            options.add_argument(f'--proxy-server={use_proxy}')
            
        if self.config['browser'].get('disable_notifications'):
            options.add_argument('--disable-notifications')
        if self.config['browser'].get('disable_gpu'):
            options.add_argument('--disable-gpu')
        if self.config['browser'].get('no_sandbox'):
            options.add_argument('--no-sandbox')
        if self.config['browser'].get('disable_dev_shm_usage'):
            options.add_argument('--disable-dev-shm-usage')
            
        self.driver = uc.Chrome(options=options, version_main=None)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {'userAgent': user_agent})
        
        self.wait = WebDriverWait(self.driver, 15)
        
        return self.driver
    
    def random_delay(self, min_sec=0.5, max_sec=2.0):
        time.sleep(random.uniform(min_sec, max_sec))
    
    def human_mouse_movement(self, element):
        try:
            action = webdriver.ActionChains(self.driver)
            action.move_to_element(element).perform()
            self.random_delay(0.1, 0.3)
            return True
        except:
            return False
            
    def scroll_page(self, scrolls=3):
        for i in range(scrolls):
            scroll_distance = random.randint(100, 400)
            self.driver.execute_script(f"window.scrollBy(0, {scroll_distance})")
            time.sleep(random.uniform(0.5, 1.0))
            
    def close(self):
        if self.driver:
            self.driver.quit()