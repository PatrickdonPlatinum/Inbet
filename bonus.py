# file: bot_script.py
import winsound
import re
import random
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
import multiprocessing

stop_flag = False

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

    if block_images:
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)

    version_main = 142
    driver = uc.Chrome(options=options, version_main=version_main)
    driver.set_window_size(1920, 1080)
    return driver

def close_popups(driver):
    closed_any = False
    try:
        alert = driver.switch_to.alert
        alert_text = alert.text
        alert.dismiss()
        print(f"[INFO] Dismissed JS alert: {alert_text}")
        closed_any = True
    except:
        pass

    try:
        close_buttons = driver.find_elements(By.CSS_SELECTOR, ".close, .modal-close, .gmf-modal__close")
        for btn in close_buttons:
            try:
                if btn.is_displayed() and btn.is_enabled():
                    btn_text = btn.get_attribute("textContent") or "<no-text>"
                    driver.execute_script("arguments[0].click();", btn)
                    print(f"[INFO] Closed popup modal: {btn_text.strip()}")
                    time.sleep(0.3)
                    closed_any = True
            except:
                continue
    except:
        pass
    return closed_any

def click_first_visible_box_and_get_reward(driver, username, password, timeout=10, save_file="rewards.txt"):
    try:
        wait = WebDriverWait(driver, timeout)
        wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".fEWbg")))
        images = driver.find_elements(By.CSS_SELECTOR, ".fEWbg")
        print(f"[INFO] Found {len(images)} fEWbg layers.")

        attempts = 0
        while attempts < 3:
            close_popups(driver)
            for image in images:
                style = image.get_attribute("style")
                if "visibility: visible" in style:
                    bg_url = None
                    if "background-image:" in style:
                        bg_url = style.split("background-image: url(")[-1].split(")")[0].strip('"').strip("'")

                    driver.execute_script("arguments[0].scrollIntoView(true);", image)
                    time.sleep(0.3)

                    try:
                        driver.execute_script("arguments[0].click();", image)
                        print(f"[INFO] Clicked visible fEWbg layer: {bg_url}")
                    except Exception as e:
                        print(f"[WARNING] Failed to click box, retrying: {e}")
                        attempts += 1
                        break

                    try:
                        reward_elem = WebDriverWait(driver, timeout).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, ".gmf-modal__win"))
                        )
                        reward_text = reward_elem.text.strip()
                    except:
                        reward_text = "No reward"

                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    with open(save_file, "a", encoding="utf-8") as f:
                        f.write(f"{timestamp} | {username}:{password}\n")

                    print(f"[INFO] Saved reward for {username} to {save_file}")
                    return {"reward": reward_text, "image_url": bg_url, "timestamp": timestamp}
            else:
                break
        print("[WARNING] No visible fEWbg layer was found to click.")
        return None

    except Exception as e:
        print(f"[ERROR] Failed during visible fEWbg detection: {e}")
        return None

def click_spin_button(driver, username, password, timeout=15, save_file="rewards.txt"):
    """
    Clicks the spin button, waits for the reward text:
        <div class="hF8KG">Символът 'Слива' е добавен в Бонус колекциите ти.</div>
    Extracts the symbol name (e.g. Слива), saves it to rewards.txt,
    then clicks:
        <button class="kdTmI">Към Бонус Колекции</button>
    """
    try:
        wait = WebDriverWait(driver, timeout)

        # Locate and click "Завърти" button
        button = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//*[contains(@class,'_70LFH') and contains(normalize-space(),'Завърти')]")
            )
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", button)
        time.sleep(0.5)

        for attempt in range(3):
            try:
                driver.execute_script("arguments[0].click();", button)
                print("[INFO] Clicked 'Завърти' button.")
                break
            except Exception as e:
                print(f"[WARNING] Attempt {attempt+1} failed to click spin button: {e}")
                time.sleep(1)
        else:
            print("[ERROR] Could not click spin button after retries.")
            return None

        # Wait for the reward text div with class hF8KG
        try:
            reward_elem = wait.until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "div.hF8KG")
                )
            )
            reward_full_text = reward_elem.text.strip()
            print(f"[INFO] Reward raw text: {reward_full_text}")

            # Extract the symbol name between single quotes: 'Слива'
            symbol_name = reward_full_text
            m = re.search(r"'([^']+)'", reward_full_text)
            if m:
                symbol_name = m.group(1).strip()

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(save_file, "a", encoding="utf-8") as f:
                # Save both username, password and the symbol
                f.write(f"{timestamp} | {username}:{password} | {symbol_name} | {reward_full_text}\n")

            print(f"[INFO] Reward saved to {save_file}: {symbol_name}")

        except Exception as e:
            print(f"[WARNING] Reward element '.hF8KG' not found or no text: {e}")
            reward_full_text = "No reward text"
            symbol_name = ""
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Click "Към Бонус Колекции" button
        try:
            bonus_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(@class,'kdTmI') and normalize-space()='Към Бонус Колекции']")
                )
            )
            driver.execute_script("arguments[0].click();", bonus_btn)
            print("[INFO] Clicked 'Към Бонус Колекции' button.")
        except Exception as e:
            print(f"[WARNING] Could not click 'Към Бонус Колекции' button: {e}")

        return {"reward": symbol_name or reward_full_text, "timestamp": timestamp}

    except Exception as e:
        print(f"[ERROR] Could not complete spin+reward flow: {e}")
        return None

def login(credentials):
    username, password = credentials
    driver = init_driver()

    try:
        driver.get(login_page_url)
        wait = WebDriverWait(driver, 30)

        try:
            allow_all_btn = wait.until(
                EC.presence_of_element_located(
                    (By.ID, "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll")
                )
            )
            try:
                allow_all_btn.click()
            except Exception:
                driver.execute_script("arguments[0].click();", allow_all_btn)
        except Exception:
            print(f"[WARNING] 'Allow All Cookies' button not found for {username}. Continuing...")
            
            try:
                close_modal_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, 'div.d-flex-ac.modal-close.mb-1 div.modal-close__btn')
                    )
                )
                driver.execute_script("arguments[0].click();", close_modal_btn)
                print("[INFO] Closed post-cookie modal successfully.")
                time.sleep(0.5)
            except:
                print("[INFO] No post-cookie modal found.")
        except:
            print(f"[WARNING] Accept Cookies button not found for {username}. Continuing...")

        try:
            login_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, "/html/body/div[3]/div[2]/div/nav/div/div/div[3]/div[2]/button[2]"))
            )
            login_button.click()
        except:
            print(f"[ERROR] Login button not found for {username}.")
            return

        try:
            username_field = wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH, "/html/body/div[3]/div[2]/div[2]/div/div/div/div/form/div[1]/div/div/div/input")
                )
            )
            username_field.send_keys(username)
        except Exception:
            print(f"[ERROR] Username field not found for {username}.")
            return

        try:
            password_field = wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH, "/html/body/div[3]/div[2]/div[2]/div/div/div/div/form/div[2]/div/div/div/input")
                )
            )
            password_field.send_keys(password)
        except Exception:
            print(f"[ERROR] Password field not found for {username}.")
            return

        try:
            submit_button = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "/html/body/div[3]/div[2]/div[2]/div/div/div/div/form/button")
                )
            )
            submit_button.click()
        except Exception:
            print(f"[ERROR] Submit button not found for {username}.")
            return

        close_popups(driver)

        click_first_visible_box_and_get_reward(driver, username, password)
        click_spin_button(driver, username, password)

    except Exception as e:
        traceback.print_exc()
    finally:
        driver.quit()

def main():
    global login_page_url
    credentials_file = 'png_files.txt'
    login_page_url = "https://www.inbet.com/sports"
    credentials = read_credentials(credentials_file)

    listener_thread = threading.Thread(target=emergency_stop_listener, daemon=True)
    listener_thread.start()

    max_workers = 7
    print(f"[INFO] Starting with {max_workers} workers...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(lambda cred: login(cred), credentials)

if __name__ == "__main__":
    main()
