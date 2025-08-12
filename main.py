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

BOOKING_URL = "https://termine-reservieren.de/termine/lramuenchen/efa/"

GMAIL_SENDER   = os.getenv("GMAIL_SENDER")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
GMAIL_RECEIVER = os.getenv("GMAIL_RECEIVER")

def send_email(subject: str, body: str):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = GMAIL_SENDER
    msg["To"] = GMAIL_RECEIVER
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(GMAIL_SENDER, GMAIL_PASSWORD)
        s.sendmail(GMAIL_SENDER, GMAIL_RECEIVER, msg.as_string())
    print("[✓] Email sent.")

def js_click(driver, elem):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
    try:
        elem.click()
    except Exception:
        driver.execute_script("arguments[0].click();", elem)

def check_appointment():
    print("[*] Checking appointment availability…")

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=opts)
    wait = WebDriverWait(driver, 30)

    try:
        # 1) Open booking site
        driver.get(BOOKING_URL)
        print("Page title:", driver.title)

        # 2) Cookie banner (Ablehnen)
        try:
            btn_cookie = wait.until(EC.element_to_be_clickable((By.ID, "cookie_msg_btn_no")))
            js_click(driver, btn_cookie)
            print("[✓] Cookie banner dismissed.")
        except Exception:
            print("[i] No cookie banner to dismiss.")

        # 3) Click “Fahrerlaubnis”
        fahrerlaubnis = wait.until(EC.element_to_be_clickable((By.ID, "buttonfunktionseinheit-5")))
        js_click(driver, fahrerlaubnis)
        print("[✓] Clicked 'Fahrerlaubnis'")

        # 4) Expand “Persönliche Vorsprache (zur Abholung Führerschein)”
        try:
            accordion = wait.until(EC.element_to_be_clickable((By.ID, "header_concerns_accordion-170")))
        except Exception:
            accordion = wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//h3[contains(., 'Persönliche Vorsprache (zur Abholung Führerschein)')]")
            ))
        js_click(driver, accordion)
        print("[✓] Expanded 'Persönliche Vorsprache (zur Abholung Führerschein)'")

        # 5) Tick “Führerschein Allgemein”
        chk = wait.until(EC.element_to_be_clickable((By.ID, "span-cnc-1027")))
        js_click(driver, chk)
        print("[✓] Selected 'Führerschein Allgemein'")

        # 6) First OK (Anliegen confirmation)
        try:
            ok1 = wait.until(EC.element_to_be_clickable((By.ID, "OKButton")))
            js_click(driver, ok1)
            print("[✓] Confirmed first OK.")
        except Exception:
            print("[i] No first OK modal.")

        # 7) Click “Weiter”
        weiter = wait.until(EC.element_to_be_clickable((By.ID, "WeiterButton")))
        js_click(driver, weiter)
        print("[✓] Clicked 'Weiter'")

        # 8) Second OK (Hinweis modal)
        try:
            ok2 = wait.until(EC.element_to_be_clickable((By.ID, "OKButton")))
            js_click(driver, ok2)
            print("[✓] Confirmed second OK (Hinweis).")
        except Exception:
            print("[i] No Hinweis modal.")

        # 9) Read “Nächster Termin” on the same page (no further clicks)
        #    <dt>Nächster Termin</dt><dd>ab 24.09.2025, 10:45 Uhr</dd>
        try:
            next_term = wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//dt[contains(normalize-space(.), 'Nächster Termin')]/following-sibling::dd[1]")
                )
            )
            next_text = (next_term.text or "").strip()
            print("Nächster Termin raw:", repr(next_text))

            if not next_text or "Keine Zeiten verfügbar" in next_text:
                print("[✗] No appointment slots available.")
                return

            # Extract only the date (dd.mm.yyyy)
            m = re.search(r"(\d{2}\.\d{2}\.\d{4})", next_text)
            if m:
                date_only = m.group(1)
                print(f"[✓] Appointment slot found: {date_only}")
                subject = f"Führerscheinstelle Slot: {date_only}"
                body = f"First available date: {date_only}\nBooking page: {BOOKING_URL}"
                send_email(subject, body)
            else:
                print("[!] Slot text present but date not parsed. (Check debug.html)")
        except Exception as e:
            print(f"[!] Could not find 'Nächster Termin' field: {e}")

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
