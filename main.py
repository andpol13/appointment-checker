import time
import smtplib
from email.mime.text import MIMEText
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import os

# ====== Load secrets from GitHub Actions ======
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

    try:
        driver.get(TARGET_URL)
        time.sleep(3)

        driver.find_element(By.ID, "buttonfunktionseinheit-5").click()
        time.sleep(2)

        driver.find_element(By.ID, "header_concerns_accordion-170").click()
        time.sleep(1)

        driver.find_element(By.ID, "span-cnc-1024").click()
        time.sleep(1)

        driver.find_element(By.ID, "OKButton").click()
        time.sleep(1)

        driver.find_element(By.ID, "WeiterButton").click()
        time.sleep(2)

        driver.find_element(By.NAME, "select_location").click()
        time.sleep(2)

        if "Keine Zeiten verfügbar" not in driver.page_source:
            send_email_notification()
        else:
            print("[-] No appointments found.")

    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    check_appointment()
