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

# ---------- helpers ----------

def send_email(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = GMAIL_SENDER
    msg["To"] = GMAIL_RECEIVER
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(GMAIL_SENDER, GMAIL_PASSWORD)
        s.sendmail(GMAIL_SENDER, GMAIL_RECEIVER, msg.as_string())
    print("[✓] Email sent.")

def is_present(driver, by, sel):
    try:
        driver.find_element(by, sel)
        return True
    except Exception:
        return False

def try_click(driver, elem):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", elem)
    try:
        elem.click()
    except Exception:
        # Fallback to JS click if intercepted
        driver.execute_script("arguments[0].click();", elem)

def extract_first_slot_date(driver) -> str | None:
    """Find and return only the date from the first available slot summary."""
    # 1) Exact ID
    try:
        el = WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.ID, "suggest_location_summary"))
        )
        txt = (el.text or "").strip()
    except Exception:
        txt = ""

    # 2) Fallback: any <summary> that contains 'Termine ab'
    if not txt:
        try:
            for c in driver.find_elements(By.CSS_SELECTOR, "summary"):
                t = (c.text or "").strip()
                if "Termine ab" in t:
                    txt = t
                    break
        except Exception:
            pass

    if not txt:
        return None

    m = re.search(r"Termine ab\s+(\d{2}\.\d{2}\.\d{4})", txt)
    return m.group(1) if m else None

# ---------- main flow ----------

def check_appointment():
    print("[*] Checking appointment availability…")

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=opts)
    wait = WebDriverWait(driver, 30)

    try:
        # 1) Booking start
        driver.get(BOOKING_URL)
        print("Page title:", driver.title)

        # 2) Cookie banner
        try:
            wait.until(EC.element_to_be_clickable((By.ID, "cookie_msg_btn_no"))).click()
            print("[✓] Cookie banner dismissed.")
        except Exception:
            print("[i] No cookie banner to dismiss.")

        # 3) Fahrerlaubnis
        wait.until(EC.element_to_be_clickable((By.ID, "buttonfunktionseinheit-5"))).click()
        print("[✓] Clicked 'Fahrerlaubnis'")

        # 4) Persönliche Vorsprache (zur Abholung Führerschein)
        try:
            wait.until(EC.element_to_be_clickable((By.ID, "header_concerns_accordion-170"))).click()
        except Exception:
            wait.until(EC.element_to_be_clickable(
                (By.XPATH, "//h3[contains(., 'Persönliche Vorsprache (zur Abholung Führerschein)')]")
            )).click()
        print("[✓] Expanded 'Persönliche Vorsprache (zur Abholung Führerschein)'")

        # 5) Führerschein Allgemein
        wait.until(EC.element_to_be_clickable((By.ID, "span-cnc-1027"))).click()
        print("[✓] Selected 'Führerschein Allgemein'")

        # 6) First OK
        try:
            ok1 = wait.until(EC.element_to_be_clickable((By.ID, "OKButton")))
            try_click(driver, ok1)
            print("[✓] Confirmed first OK.")
        except Exception:
            print("[i] No first OK modal.")

        # 7) Weiter
        wbtn = wait.until(EC.element_to_be_clickable((By.ID, "WeiterButton")))
        try_click(driver, wbtn)
        print("[✓] Clicked 'Weiter'")

        # 8) Hinweis OK (second modal)
        try:
            ok2 = wait.until(EC.element_to_be_clickable((By.ID, "OKButton")))
            try_click(driver, ok2)
            print("[✓] Confirmed second OK (Hinweis).")
        except Exception:
            print("[i] No Hinweis modal.")

        # 9) Standortauswahl: try to click “Führerscheinstelle auswählen”, but don’t insist.
        # Try several selectors that we’ve seen on this step.
        clicked_location = False

        # a) By name
        try:
            btn = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.NAME, "select_location"))
            )
            if btn.is_displayed() and btn.is_enabled():
                try_click(driver, btn)
                clicked_location = True
                print("[✓] Clicked 'Führerscheinstelle auswählen' (name=select_location)")
        except Exception:
            pass

        # b) By input[value*='Führerscheinstelle auswählen']
        if not clicked_location:
            try:
                btn2 = driver.find_element(
                    By.CSS_SELECTOR, "input[type='submit'][value*='Führerscheinstelle auswählen']"
                )
                if btn2.is_displayed() and btn2.is_enabled():
                    try_click(driver, btn2)
                    clicked_location = True
                    print("[✓] Clicked 'Führerscheinstelle auswählen' (value selector)")
            except Exception:
                pass

        # c) By visible text as a button or link (rare fallback)
        if not clicked_location:
            try:
                btn3 = driver.find_element(
                    By.XPATH, "//*[self::button or self::a or self::input][contains(., 'Führerscheinstelle auswählen')]"
                )
                try_click(driver, btn3)
                clicked_location = True
                print("[✓] Clicked 'Führerscheinstelle auswählen' (text fallback)")
            except Exception:
                print("[i] 'Führerscheinstelle auswählen' control not found; proceeding to check results anyway.")

        # 10) Check results (either after click or if page already shows them)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(2)  # allow dynamic content to settle
        html = driver.page_source

        if "Keine Zeiten verfügbar" in html:
            print("[✗] No appointment slots available.")
            return

        # If slots exist, extract the first date only
        slot_date = extract_first_slot_date(driver)
        if slot_date:
            print(f"[✓] Appointment slot found: {slot_date}")
            subject = f"Führerscheinstelle Slot: {slot_date}"
            body = f"First available date: {slot_date}\nBooking page: {BOOKING_URL}"
            send_email(subject, body)
        else:
            print("[!] Slot(s) likely present but date text was not found. (Check debug.html)")

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
