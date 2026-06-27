import random
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains

class StealthTechniques:
    def __init__(self, driver):
        self.driver = driver
        
    def random_mouse_movement(self):
        try:
            actions = ActionChains(self.driver)
            x = random.randint(100, 900)
            y = random.randint(100, 700)
            actions.move_by_offset(x, y).perform()
            return True
        except:
            return False
            
    def random_key_press(self):
        try:
            from selenium.webdriver.common.keys import Keys
            random_keys = [Keys.ARROW_DOWN, Keys.ARROW_UP, Keys.ARROW_LEFT, Keys.ARROW_RIGHT]
            key = random.choice(random_keys)
            actions = ActionChains(self.driver)
            actions.send_keys(key).perform()
            return True
        except:
            return False
            
    def emulate_human_behavior(self):
        actions = [
            self.random_mouse_movement,
            self.random_key_press,
            self.random_mouse_movement,
        ]
        for action in random.sample(actions, random.randint(1, 2)):
            action()
            time.sleep(random.uniform(0.3, 0.7))
            
    def handle_captcha(self, captcha_api_key=None):
        if captcha_api_key:
            try:
                import requests
                from twocaptcha import TwoCaptcha
                solver = TwoCaptcha(captcha_api_key)
                return True
            except:
                pass
        return False