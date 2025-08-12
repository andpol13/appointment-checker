import os
import smtplib
from email.mime.text import MIMEText
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# Email function
def send_email(message):
    sender = os.environ.get("GMAIL_SENDER")
    password = os.environ.get("GMAIL_PASSWORD")
    receiver = os.environ.get("GMAIL_RECEIVER")

    msg = MIMEText(message)
    msg["Subject"] = "Führerscheinstelle Appointment Checker"
    msg["From"] = sender
    msg["To"] = receiver

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())
        print("[✓] Email sent successfully.")
    except Exception as e:
        print(f"[!] Email send failed: {e}")

# Main check function
def check_appointment():
    print("[*] Checking appointment availability…")

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 15)

    try:
        # Step 1: Open main page
        driver.get("https://www.landkreis-muenchen.de/themen/mobilitaet/fuehrerschein/terminvereinbarung-der-fuehrerscheinstelle/")
        print(f"Page title: {driver.title}")

        # Step 2: Click 'Online-Terminvereinbarung'
        wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Online-Terminvereinbarung"))).click()

        # Step 3: Dismiss cookie banner if present
        try:
            cookie_btn = wait.until(EC.element_to_be_clickable((By.ID, "cookie_msg_btn_no")))
            cookie_btn.click()
            print("[✓] Cookie banner dismissed.")
        except TimeoutException:
            print("[i] No cookie banner or already accepted.")

        # Step 4: Click 'Fahrerlaubnis'
        wait.until(EC.element_to_be_clickable((By.ID, "buttonfunktionseinheit-5"))).click()
        print("[✓] Clicked 'Fahrerlaubnis'")

        # Step 5: Expand 'Persönliche Vorsprache (zur Abholung Führerschein)'
        wait.until(EC.element_to_be_clickable((By.ID, "sb_6"))).click()
        print("[✓] Expanded 'Persönliche Vorsprache (zur Abholung Führerschein)'")

        # Step 6: Select 'Führerschein Allgemein'
        wait.until(EC.element_to_be_clickable((By.ID, "span-cnc-1027"))).click()
        print("[✓] Selected 'Führerschein Allgemein'")

        # Step 7: First OK
        wait.until(EC.element_to_be_clickable((By.ID, "OKButton"))).click()
        print("[✓] Confirmed first OK.")

        # Step 8: Click Weiter
        wait.until(EC.element_to_be_clickable((By.ID, "weiterButton"))).click()
        print("[✓] Clicked 'Weiter'")

        # Step 9: Second OK (Hinweis modal)
        wait.until(EC.element_to_be_clickable((By.ID, "OKButton"))).click()
        print("[✓] Confirmed second OK (Hinweis modal).")

        # Step 10: Read 'Nächster Termin' field
        try:
            next_term_elem = wait.until(
                EC.presence_of_element_located((By.XPATH, "//dt[contains(text(),'Nächster Termin')]/following-sibling::dd[1]"))
            )
            next_term_text = next_term_elem.text.strip()

            if "Keine Zeiten verfügbar" in next_term_text or next_term_text == "":
                print("[i] No slots available.")
                send_email("No appointment slots available.")
            else:
                date_only = next_term_text.split(",")[0].replace("ab ", "").strip()
                print(f"[✓] Appointment slot found: {date_only}")
                send_email(f"Appointment slot available on {date_only}")

        except Exception as e:
            print(f"[!] Could not find 'Nächster Termin' field: {e}")
            send_email("Error: Could not retrieve appointment date.")

    except Exception as e:
        print(f"[!] Exception occurred: {e}")
        send_email(f"Error occurred during check: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    check_appointment()
