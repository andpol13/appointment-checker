import os
import time
import smtplib
from email.mime.text import MIMEText

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# === Secrets from GitHub Actions ===
GMAIL_SENDER   = os.getenv("GMAIL_SENDER")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
GMAIL_RECEIVER = os.getenv("GMAIL_RECEIVER")

BOOKING_URL = "https://termine-reservieren.de/termine/lramuenchen/efa/"

def send_email(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = GMAIL_SENDER
    msg["To"] = GMAIL_RECEIVER
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(GMAIL_SENDER, GMAIL_PASSWORD)
            s.sendmail(GMAIL_SENDER, GMAIL_RECEIVER, msg.as_string())
        print("[✓] Email sent.")
    except Exception as e:
        print(f"[!] Email send failed: {e}")

def check_appointment():
    print("[*] Checking appointment availability…")

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=opts)
    wait = WebDriverWait(driver, 30)

    try:
        # 1) Go straight to the booking system
        driver.get(BOOKING_URL)
        print("Page title:", driver.title)

        # 2) Dismiss cookie banner on booking site if present
        try:
            # “Ablehnen” (reject) button ID (observed): cookie_msg_btn_no
            wait.until(EC.element_to_be_clickable((By.ID, "cookie_msg_btn_no"))).click()
            print("[✓] Cookie banner dismissed.")
        except Exception:
            print("[i] No cookie banner to dismiss.")

        # 3) Click “Fahrerlaubnis”
        wait.until(EC.element_to_be_clickable((By.ID, "buttonfunktionseinheit-5"))).click()
        print("[✓] Clicked 'Fahrerlaubnis'")

        # 4) Expand “Persönliche Vorsprache (zur Abholung Führerschein)”
        # Prefer the known ID; fall back to text-based XPath if ID changes.
        try:
            wait.until(EC.element_to_be_clickable((By.ID, "header_concerns_accordion-170"))).click()
        except Exception:
            wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//h3[contains(., 'Persönliche Vorsprache (zur Abholung Führerschein)')]")
            )).click()
        print("[✓] Expanded 'Persönliche Vorsprache (zur Abholung Führerschein)'")

        # 5) Tick “Führerschein Allgemein”  (you confirmed ID = span-cnc-1027)
        wait.until(EC.element_to_be_clickable((By.ID, "span-cnc-1027"))).click()
        print("[✓] Selected 'Führerschein Allgemein'")

        # 6) Confirm OK (modal)
        try:
            wait.until(EC.element_to_be_clickable((By.ID, "OKButton"))).click()
            print("[✓] Confirmed selection (OK).")
        except Exception:
            print("[i] No confirmation modal.")

        # 7) Click “Weiter”
        wait.until(EC.element_to_be_clickable((By.ID, "WeiterButton"))).click()
        print("[✓] Clicked 'Weiter'")

        # 8) Click “Führerscheinstelle auswählen” if present on this step
        try:
            btn = wait.until(EC.presence_of_element_located((By.NAME, "select_location")))
            if btn.is_displayed() and btn.is_enabled():
                btn.click()
                print("[✓] Clicked 'Führerscheinstelle auswählen'")
        except Exception:
            print("[i] 'Führerscheinstelle auswählen' button not present — proceeding.")

        # 9) Final status check on the current page
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(2)  # small settle time for dynamic content
        html = driver.page_source

        if "Keine Zeiten verfügbar" in html:
            print("[✗] No appointment slots available.")
        else:
            print("[✓] Appointment slots FOUND! Sending email…")
            send_email(
                "Führerscheinstelle Slot Available",
                "A slot seems available. Open:\nhttps://termine-reservieren.de/termine/lramuenchen/efa/"
            )

    except Exception as e:
        print("[!] Exception occurred:")
        import traceback; traceback.print_exc()
        print("Current page title:", driver.title)
        print("Current URL:", driver.current_url)
        try:
            with open("debug.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            driver.save_screenshot("error.png")
            print("[!] Saved debug.html and error.png")
        except Exception as e2:
            print(f"[!] Failed to save debug artifacts: {e2}")
    finally:
        driver.quit()

if __name__ == "__main__":
    check_appointment()
