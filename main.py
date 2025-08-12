import os
import smtplib
from email.mime.text import MIMEText
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Email configuration
EMAIL_SENDER = os.environ.get("GMAIL_SENDER")
EMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD")
EMAIL_RECEIVER = os.environ.get("GMAIL_RECEIVER")

def send_email_notification():
    subject = "🚗 Führerscheinstelle: Appointment Available!"
    body = "An appointment may be available. Go to:\nhttps://termine-reservieren.de/termine/lramuenchen/efa/"

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        print("[✓] Email notification sent.")
    except Exception as e:
        print("[!] Failed to send email:", e)

def check_appointment():
    print("[*] Checking appointment availability...")

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 30)

    try:
        # Step 1: Go directly to the booking page
        driver.get("https://termine-reservieren.de/termine/lramuenchen/efa/")
        print("Page title:", driver.title)

        # Step 2: Dismiss cookie banner
        try:
            wait.until(EC.element_to_be_clickable((By.ID, "cookie_msg_btn_no"))).click()
            print("[✓] Cookie banner dismissed (Ablehnen).")
        except:
            print("[i] No cookie banner to dismiss.")

        # Step 3: Click Fahrerlaubnis
        wait.until(EC.element_to_be_clickable((By.ID, "buttonfunktionseinheit-5"))).click()

        # Step 4: Expand Persönliche Vorsprache (zur Abholung Führerschein)
        section = wait.until(EC.presence_of_element_located((By.ID, "header_concerns_accordion-170")))
        assert "zur Abholung Führerschein" in section.text
        section.click()

        # Step 5: Select "Führerschein Allgemein" (ID changed here)
        wait.until(EC.element_to_be_clickable((By.ID, "span-cnc-1027"))).click()
        print("[✓] Selected 'Führerschein Allgemein'")

        # Step 6: Click OK in modal
        wait.until(EC.element_to_be_clickable((By.ID, "OKButton"))).click()

        # Step 7: Click Weiter
        wait.until(EC.element_to_be_clickable((By.ID, "WeiterButton"))).click()

        # Step 8: Click "Führerscheinstelle auswählen" if present
        try:
            select_btn = wait.until(
                EC.presence_of_element_located((By.NAME, "select_location"))
            )
            if select_btn.is_displayed():
                select_btn.click()
                print("[✓] Clicked 'Führerscheinstelle auswählen'")
        except:
            print("[i] 'Führerscheinstelle auswählen' button not found — continuing")


        # Step 9: Check availability
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        page_source = driver.page_source

        if "Keine Zeiten verfügbar" not in page_source:
            print("[+] Slot may be available — sending email!")
            send_email_notification()
        else:
            print("[-] 'Keine Zeiten verfügbar' detected — no slots.")

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
