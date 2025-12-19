import winsound  # For playing sound on Windows
import re
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import undetected_chromedriver as uc
import time
import traceback
import os
from concurrent.futures import ThreadPoolExecutor
import threading
import keyboard  # for detecting keypresses
import sys
from datetime import datetime
import multiprocessing

stop_flag = False
login_page_url = None  # will be set in main()


def emergency_stop_listener():
    global stop_flag
    buffer = []
    while True:
        event = keyboard.read_event()
        if event.event_type == keyboard.KEY_DOWN and event.name == 's':
            buffer.append(time.time())
            buffer = [t for t in buffer if time.time() - t < 3]
            if len(buffer) >= 5:
                print("\n[EMERGENCY STOP] 's' pressed 5 times. Stopping script.")
                stop_flag = True
                os._exit(0)


def read_credentials(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        credentials = file.readlines()
    return [line.strip().split(':') for line in credentials]


def init_driver(block_images=False):
    options = uc.ChromeOptions()
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--headless=new")

    # 🔇 MUTE BROWSER AUDIO
    options.add_argument("--mute-audio")  # <- this mutes all Chrome audio

    if block_images:
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            # optional: hard-block sound permissions as well
            "profile.default_content_setting_values.sound": 2
        }
        options.add_experimental_option("prefs", prefs)

    version_main = 143
    driver = uc.Chrome(options=options, version_main=version_main)
    driver.set_window_size(1920, 1080)
    return driver

def close_popups(driver, timeout=2):
    """Close any modal popup if visible."""
    try:
        # WINBET modal close button (the one you pasted)
        close_btns = driver.find_elements(By.CSS_SELECTOR, ".modal-close__btn")
        for btn in close_btns:
            if btn.is_displayed():
                driver.execute_script("arguments[0].click();", btn)
                print("[INFO] Closed WINBET modal (Bonus Room).")
                time.sleep(0.5)
                return True
    except Exception as e:
        print("[DEBUG] Failed WINBET modal close:", e)

    try:
        # Reward popup "Затвори"
        close_btns = driver.find_elements(
            By.XPATH,
            '//div[contains(@class,"sc-eHujzY")]/span[text()="Затвори"]/..'
        )
        for btn in close_btns:
            if btn.is_displayed():
                driver.execute_script("arguments[0].click();", btn)
                print("[INFO] Closed reward popup.")
                time.sleep(0.5)
                return True
    except Exception as e:
        print("[DEBUG] Failed reward popup close:", e)

    try:
        # Generic modals
        close_btns = driver.find_elements(
            By.CSS_SELECTOR,
            ".close, .modal-close, .gmf-modal__close"
        )
        for btn in close_btns:
            if btn.is_displayed():
                driver.execute_script("arguments[0].click();", btn)
                print("[INFO] Closed generic popup.")
                time.sleep(0.5)
                return True
    except Exception as e:
        print("[DEBUG] Failed generic popup close:", e)

    return False


def extract_rewards_and_save(driver, username, password,
                             save_file="rewards.txt", timeout=30):
    """Extract reward texts and save to a file with timestamp and credentials."""
    try:
        wait = WebDriverWait(driver, timeout)

        # Wait for correct reward container
        container = wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "div.sc-jcHdAB.gnlAVS")
            )
        )

        # Extract all reward text elements
        reward_elements = container.find_elements(
            By.CSS_SELECTOR,
            "div.sc-euGpHm.fMVtx"
        )
        reward_texts = [el.text.strip()
                        for el in reward_elements if el.text.strip()]

        if reward_texts:
            rewards_line = "; ".join(reward_texts)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(save_file, "a", encoding="utf-8") as f:
                f.write(
                    f"{timestamp} | {username}:{password} | {rewards_line}\n"
                )
            print(f"[INFO] Saved rewards for {username}: {rewards_line}")
        else:
            print(f"[WARNING] No rewards found for {username}.")

    except Exception as e:
        print(f"[ERROR] Failed to extract rewards for {username}: {e}")


def handle_login_bonus(driver, username, password, timeout=15):
    """
    Directly after login, try to use the login bonus popup instead of going
    to Bonus Room. It:
      1) Clicks the bonus box (CSS .fEWbg or your XPath)
      2) Waits for the confirm/play button in the dialog
      3) Clicks it
      4) Extracts rewards and saves them
    """
    wait = WebDriverWait(driver, timeout)

    bonus_element = None

    # 1) Try by CSS class (more stable than full XPath)
    try:
        bonus_element = wait.until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "div.fEWbg")
            )
        )
        print(f"[INFO] Login bonus popup detected for {username} (CSS selector).")
    except TimeoutException:
        print(f"[DEBUG] Login bonus CSS selector not found for {username}, trying XPath...")

    # 2) If CSS failed, try absolute XPath you provided
    if bonus_element is None:
        try:
            bonus_element = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH,
                     "/html/body/div[2]/div[2]/div[2]/div/dialog/div/div[2]/div/div/"
                     "div/div/div/div[2]/div/div[3]/div[3]/div/div[1]")
                )
            )
            print(f"[INFO] Login bonus popup detected for {username} (XPath).")
        except TimeoutException:
            print(f"[INFO] No login bonus popup for {username}.")
            return

    # Click the bonus box
    try:
        driver.execute_script("arguments[0].click();", bonus_element)
        print(f"[INFO] Clicked login bonus box for {username}.")
    except Exception as e:
        print(f"[ERROR] Failed to click login bonus box for {username}: {e}")
        return

    # 3) After selecting the bonus, wait for the confirm/play button
    try:
        confirm_button = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH,
                 "/html/body/div[3]/div[2]/div[2]/div/dialog/div/div[2]/div/div/"
                 "div/div/div/div[2]/div/button")
            )
        )
        driver.execute_script("arguments[0].click();", confirm_button)
        print(f"[INFO] Clicked login bonus confirm button for {username}.")
    except TimeoutException:
        print(f"[WARNING] Confirm button not found after selecting bonus for {username}.")
        return
    except Exception as e:
        print(f"[ERROR] Failed to click confirm button for {username}: {e}")
        return

    # 4) After clicking the confirm button, wait for reward popup and extract rewards
    try:
        extract_rewards_and_save(driver, username, password)
        # Optionally close any remaining popup
        while close_popups(driver):
            pass
    except Exception as e:
        print(f"[WARNING] Problem while extracting rewards after confirm button "
              f"for {username}: {e}")

def login(credentials):
    """Perform the login process for a single username/password pair."""
    username, password = credentials
    driver = init_driver()

    try:
        driver.get(login_page_url)
        wait = WebDriverWait(driver, 30)

        # Accept Cookies
        try:
            allow_all_btn = wait.until(
                EC.presence_of_element_located(
                    (By.ID, "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll")
                )
            )
            try:
                allow_all_btn.click()
            except Exception:
                # Fallback: force click if normal click fails
                driver.execute_script("arguments[0].click();", allow_all_btn)
        except Exception:
            print(f"[WARNING] 'Allow All Cookies' button not found for "
                  f"{username}. Continuing...")

        # Login button
        login_button = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH,
                 "/html/body/div[3]/div[2]/div[1]/nav/div/div/div[3]/div/button[2]")
            )
        )
        driver.execute_script("arguments[0].click();", login_button)

        # Username
        username_field = wait.until(
            EC.visibility_of_element_located(
                (By.XPATH,
                 "//input[@name='username' or contains(@placeholder,'Потребител')]")
            )
        )
        username_field.send_keys(username)

        # Password
        password_field = wait.until(
            EC.visibility_of_element_located(
                (By.XPATH, "//input[@type='password']")
            )
        )
        password_field.send_keys(password)

        # Submit
        submit_button = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH,
                 "//form//button[contains(@class,'btn') and not(@disabled)]")
            )
        )
        submit_button.click()

        # Wait for successful login / balance element
        formatted_amount = '0.00'
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
                formatted_amount = f"{float(amount_str):.2f}"
        except Exception as e:
            print(f"[WARNING] Could not confirm login / balance for "
                  f"{username}: {e}")

        # === NEW: handle login bonus popup directly after login ===
        handle_login_bonus(driver, username, password)

        # Close any remaining popups
        while close_popups(driver):
            pass

        # Check balance and maybe play sound
        try:
            balance_value = float(formatted_amount)
        except ValueError:
            balance_value = 0.0

        if balance_value > 0.99:
            try:
                winsound.PlaySound(
                    r"C:\Inbet\inbet.wav",
                    winsound.SND_FILENAME | winsound.SND_ASYNC
                )
            except Exception:
                print("[WARNING] Could not play sound.")
            return

        # NOTE: We no longer go to Bonus Room here – we rely on the
        # login bonus popup only.

    except Exception:
        traceback.print_exc()
    finally:
        driver.quit()


def main():
    global login_page_url
    credentials_file = 'png_files.txt'
    login_page_url = "https://www.inbet.com/sports"
    credentials = read_credentials(credentials_file)

    listener_thread = threading.Thread(
        target=emergency_stop_listener,
        daemon=True
    )
    listener_thread.start()

    max_workers = 7
    # max_workers = min(multiprocessing.cpu_count(), len(credentials))
    print(f"[INFO] Starting with {max_workers} workers...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(lambda cred: login(cred), credentials)


if __name__ == "__main__":
    main()
