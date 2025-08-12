import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Email sending
import smtplib
from email.mime.text import MIMEText

# Load secrets from GitHub Actions
GMAIL_SENDER = os.getenv("GMAIL_SENDER")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
GMAIL_RECEIVER = os.getenv("GMAIL_RECEIVER")

URL = "https://www.landkreis-muenchen.de/themen/mobilitaet/fuehrerschein/terminvereinbarung-der-fuehrerscheinstelle/"

def send_email(subject, body):
    """Send notification email."""
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = GMAIL_SENDER
    msg["To"] = GMAIL_RECEIVER

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_SENDER, GMAIL_PASSWORD)
        server.sendmail(GMAIL_SENDER, GMAIL_RECEIVER, msg.as_string())
    print(f"[✓] Email sent: {subject}")

def check_appointment():
    print("[*] Checking appointment availability...")

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 15)

    try:
        driver.get(URL)
        print("Page title:", driver.title)

        # Accept or decline cookies
        try:
            cookie_button = wait.until(EC.element_to_be_clickable((By.ID, "cookie_msg_btn_no")))
            cookie_button.click()
            print("[✓] Cookie banner dismissed (Ablehnen).")
        except:
            print("[i] No cookie banner or already accepted.")

        # Step 1: Click "Online-Terminvereinbarung"
        wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Online-Terminvereinbarung"))).click()

        # Step 2: Click "Fahrerlaubnis"
        wait.until(EC.element_to_be_clickable((By.ID, "buttonfunktionseinheit-5"))).click()

        # Step 3: Expand "Persönliche Vorsprache (zur Abholung Führerschein)"
        wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//h3[contains(., 'Persönliche Vorsprache (zur Abholung Führerschein)')]")
            )
        ).click()
        print("[✓] Expanded 'Persönliche Vorsprache (zur Abholung Führerschein)'")

        # Step 4: Tick "Führerschein Allgemein"
        wait.until(EC.element_to_be_clickable((By.ID, "span-cnc-1027"))).click()
        print("[✓] Selected 'Führerschein Allgemein'")

        # Step 5: Click OK in popup (if it appears)
        try:
            wait.until(EC.element_to_be_clickable((By.ID, "OKButton"))).click()
        except:
            print("[i] No confirmation popup appeared.")

        # Step 6: Click Weiter
        wait.until(EC.element_to_be_clickable((By.ID, "WeiterButton"))).click()

        # Step 7: Click "Führerscheinstelle auswählen"
        wait.until(EC.element_to_be_clickable((By.NAME, "select_location"))).click()

        # Step 8: Check if there are available slots
        time.sleep(2)
        page_source = driver.page_source

        if "Keine Zeiten verfügbar" in page_source:
            print("[✗] No appointment slots available.")
        else:
            print("[✓] Appointment slots FOUND!")
            send_email("Führerscheinstelle Slot Available", "A slot is available! Go to the website now.")

    except Exception as e:
        print(f"[!] Exception occurred: {e}")
        print("Current page title:", driver.title)
        print("Current URL:", driver.current_url)
        with open("debug_page.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print("[!] Saved HTML for debugging.")

    finally:
        driver.quit()

if __name__ == "__main__":
    check_appointment()
