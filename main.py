import os
import re
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
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(GMAIL_SENDER, GMAIL_PASSWORD)
        s.sendmail(GMAIL_SENDER, GMAIL_RECEIVER, msg.as_string())
    print("[✓] Email sent.")

def extract_first_slot_date(driver) -> str | None:
    """Find and return only the date from the first available slot."""
    try:
        el = WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.ID, "suggest_location_summary"))
        )
        txt = (el.text or "").strip()
    except Exception:
        txt = ""

    if not txt:
        try:
            candidates = driver.find_elements(By.CSS_SELECTOR, "summary")
            for c in candidates:
                if "Termine ab" in c.text:
                    txt = c.text.strip()
                    break
        except Exception:
            pass

    if not txt:
        return None

    m = re.search(r"Termine ab\s+(\d{2}\.\d{2}\.\d{4})", txt)
    if m:
        return m.group(1)
    return None

def check_appointment():
    print("[*] Checking appointment availability…")

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=opts)
    wait = WebDriverWait(driver, 30)

    try:
        driver.get(BOOKING_URL)
        print("Page title:", driver.title)

        # Cookie banner
        try:
            wait.until(EC.element_to_be_clickable((By.ID, "cookie_msg_btn_no"))).click()
            print("[✓] Cookie banner dismissed.")
        except Exception:
            print("[i] No cookie banner to dismiss.")

        # Click Fahrerlaubnis
        wait.until(EC.element_to_be_clickable((By.ID, "buttonfunktionseinheit-5"))).click()
        print("[✓] Clicked 'Fahrerlaubnis'")

        # Expand Persönliche Vorsprache (zur Abholung Führerschein)
        try:
            wait.until(EC.element_to_be_clickable((By.ID, "header_concerns_accordion-170"))).click()
        except Exception:
            wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//h3[contains(., 'Persönliche Vorsprache (zur Abholung Führerschein)')]")
            )).click()
        print("[✓] Expanded 'Persönliche Vorsprache (zur Abholung Führerschein)'")

        # Tick Führerschein Allgemein
        wait.until(EC.element_to_be_clickable((By.ID, "span-cnc-1027"))).click()
        print("[✓] Selected 'Führerschein Allgemein'")

        # First OK confirmation
        try:
            wait.until(EC.element_to_be_clickable((By.ID, "OKButton"))).click()
            print("[✓] Confirmed first OK.")
        except Exception:
            print("[i] No first OK modal.")

        # Click Weiter
        wait.until(EC.element_to_be_clickable((By.ID, "WeiterButton"))).click()
        print("[✓] Clicked 'Weiter'")

        # Second OK (Hinweis modal)
        try:
            wait.until(EC.element_to_be_clickable((By.ID, "OKButton"))).click()
            print("[✓] Confirmed second OK (Hinweis modal).")
        except Exception:
            print("[i] No Hinweis modal.")

        # Click Führerscheinstelle auswählen
        wait.until(EC.element_to_be_clickable((By.NAME, "select_location"))).click()
        print("[✓] Clicked 'Führerscheinstelle auswählen'")

        # Check availability
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(2)
        html = driver.page_source

        if "Keine Zeiten verfügbar" in html:
            print("[✗] No appointment slots available.")
            return

        slot_date = extract_first_slot_date(driver)

        if slot_date:
            print(f"[✓] Appointment slot found: {slot_date}")
            subject = f"Führerscheinstelle Slot: {slot_date}"
            body = f"First available date: {slot_date}\nBooking page: {BOOKING_URL}"
            send_email(subject, body)
        else:
            print("[!] Slot found but could not extract date.")

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
