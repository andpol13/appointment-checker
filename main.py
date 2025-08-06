import time
import smtplib
from email.mime.text import MIMEText
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os

# ====== Load secrets from GitHub ======
GMAIL_SENDER = os.getenv("GMAIL_SENDER")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
GMAIL_RECEIVER = os.getenv("GMAIL_RECEIVER")

TARGET_URL = 'https://www.landkreis-muenchen.de/themen/mobilitaet/fuehrerschein/terminvereinbarung-der-fuehrerscheinstelle/'

def send_email_notification():
    subject = "🚗 Slot Available at Führerscheinstelle!"
    body = f"Visit the page now: {TARGET_URL}"

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = GMAIL_SENDER
    msg["To"] = GMAIL_RECEIVER

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_SENDER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_SENDER, GMAIL_RECEIVER, msg.as_string())
            print("[✓] Email sent!")
    except Exception as e:
        print(f"[!] Failed to send email: {e}")

def check_appointment():
    print("[*] Checking appointment availability...")

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 30)

    try:
        # ✅ Go directly to the real booking site
        driver.get("https://termine-reservieren.de/termine/lramuenchen/efa/")
        print("Page title:", driver.title)

        # Wait for the actual site to load
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

# Accept or reject cookies if the popup is present
        try:
            wait.until(EC.element_to_be_clickable((By.ID, "cookie_msg_btn_no"))).click()
            print("[✓] Cookie banner dismissed (Ablehnen).")
        except:
            print("[i] No cookie banner to dismiss.")

        # Continue as before
        wait.until(EC.element_to_be_clickable((By.ID, "buttonfunktionseinheit-5"))).click()
        wait.until(EC.element_to_be_clickable((By.ID, "header_concerns_accordion-170"))).click()
        wait.until(EC.element_to_be_clickable((By.ID, "span-cnc-1024"))).click()
        wait.until(EC.element_to_be_clickable((By.ID, "OKButton"))).click()
        wait.until(EC.element_to_be_clickable((By.ID, "WeiterButton"))).click()
        wait.until(EC.element_to_be_clickable((By.NAME, "select_location"))).click()

        page_source = driver.page_source
        if "Keine Zeiten verfügbar" not in page_source:
            print("[+] Slot may be available — sending email!")
            send_email_notification()
        else:
            print("[-] No appointments available.")

    except Exception as e:
        import traceback
        print("[!] Exception occurred:")
        traceback.print_exc()
        print("Current page title:", driver.title)
        print("Current URL:", driver.current_url)
        try:
            with open("debug.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            driver.save_screenshot("error.png")
            print("[!] Saved screenshot and HTML for debugging.")
        except Exception as inner:
            print(f"[!] Failed to save debug files: {inner}")
    finally:
        driver.quit()

if __name__ == "__main__":
    check_appointment()
