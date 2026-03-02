"""
Send WhatsApp messages via WhatsApp Web (your own number).
You scan the QR code once; the session is saved so you don't need to scan again.
No Twilio or Business API required.
"""
import time
import urllib.parse
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import DATA_DIR
from crawler import Lead
from outreach import format_message


# Chrome profile dir: after first QR scan, session is kept here
WHATSAPP_PROFILE_DIR = DATA_DIR / "whatsapp_web_profile"
# Seconds to wait for page/send button per contact (then skip if not reachable)
WAIT_TIMEOUT = 30
# Max seconds to wait for send button for one contact before skipping to next
CONTACT_LOAD_TIMEOUT = 12
# Delay between sending to different contacts (avoid spam detection)
DELAY_BETWEEN_SENDS = 15

# Text on page when number is invalid / not on WhatsApp (skip and continue)
UNREACHABLE_PHRASES = (
    "phone number shared via url is invalid",
    "not on whatsapp",
    "invalid phone number",
    "number is not on whatsapp",
)


def _phone_digits(phone: str) -> str:
    """Return digits only for WhatsApp URL (no +)."""
    return "".join(c for c in (phone or "") if c.isdigit()).strip()


def _get_driver(profile_dir: Path, headless: bool = False):
    """Create Chrome driver with persistent profile for WhatsApp Web session."""
    profile_dir = Path(profile_dir)
    profile_dir.mkdir(parents=True, exist_ok=True)

    options = Options()
    options.add_argument(f"--user-data-dir={profile_dir}")
    options.add_argument("--profile-directory=Default")
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    try:
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)
    except Exception:
        return webdriver.Chrome(options=options)


def _wait_for_logged_in(driver, timeout: int = 120) -> bool:
    """Wait until user is logged in (QR scanned). Returns True when ready."""
    try:
        # When logged in, the main panel or search box appears
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='chat-list'], [data-testid='search'], #side, [aria-label='Search input textbox']"))
        )
        return True
    except Exception:
        return False


def _is_unreachable(driver) -> bool:
    """Check if the current page says the number is invalid / not on WhatsApp."""
    try:
        body = driver.find_element(By.TAG_NAME, "body").text.lower()
        return any(p in body for p in UNREACHABLE_PHRASES)
    except Exception:
        return False


def send_via_whatsapp_web(lead: Lead, driver=None, close_driver: bool = True) -> bool:
    """
    Send one message via WhatsApp Web using the default browser profile.
    If the number is not reachable (invalid / not on WhatsApp), returns False
    so the bulk sender can move to the next contact.
    """
    phone = _phone_digits(lead.phone)
    if not phone:
        print("Invalid phone for WhatsApp Web:", lead.phone)
        return False

    body = format_message(lead)
    url = f"https://web.whatsapp.com/send?phone={phone}&text={urllib.parse.quote(body)}"

    own_driver = driver is None
    if own_driver:
        driver = _get_driver(WHATSAPP_PROFILE_DIR, headless=False)
        driver.get("https://web.whatsapp.com")
        print("If you see the QR code, scan it with WhatsApp on your phone. Waiting for login...")
        if not _wait_for_logged_in(driver):
            print("Login timeout. Scan the QR code and run again.")
            if close_driver:
                driver.quit()
            return False
        time.sleep(2)

    try:
        driver.get(url)
        time.sleep(3)

        if _is_unreachable(driver):
            print(f"Skipping +{phone} (number not on WhatsApp or invalid).")
            return False

        # Try to find and click send; use short timeout per try so we skip unreachable quickly
        send_selectors = [
            "span[data-icon='send']",
            "button[data-testid='send']",
            "[data-testid='send']",
            "span[data-icon='send-light']",
            "button[aria-label='Send']",
        ]
        sent = False
        per_try = max(2, CONTACT_LOAD_TIMEOUT // 6)
        for sel in send_selectors:
            try:
                btn = WebDriverWait(driver, per_try).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                )
                btn.click()
                sent = True
                break
            except Exception:
                continue

        if not sent:
            try:
                inp = WebDriverWait(driver, per_try).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[contenteditable='true'][data-tab='10'], div[contenteditable='true'][role='textbox']"))
                )
                inp.send_keys("\n")
                sent = True
            except Exception:
                pass

        if not sent:
            print(f"Skipping +{phone} (not reachable / send button not found).")
        else:
            time.sleep(2)

        if own_driver and close_driver:
            driver.quit()
        return sent
    except Exception as e:
        print(f"Skipping +{phone} (error: {e}).")
        if own_driver and close_driver:
            try:
                driver.quit()
            except Exception:
                pass
        return False


def send_bulk_via_whatsapp_web(leads: list[Lead], delay_seconds: int = DELAY_BETWEEN_SENDS, on_sent=None) -> int:
    """
    Open WhatsApp Web once, then send to each lead. You scan QR once if needed.
    on_sent(lead) is called after each successful send (e.g. to record_sent).
    Returns count of messages sent.
    """
    driver = _get_driver(WHATSAPP_PROFILE_DIR, headless=False)
    driver.get("https://web.whatsapp.com")
    print("If you see the QR code, scan it with WhatsApp on your phone. Waiting for login...")
    if not _wait_for_logged_in(driver):
        print("Login timeout. Scan the QR code and run again.")
        driver.quit()
        return 0

    time.sleep(2)
    sent_count = 0
    for i, lead in enumerate(leads):
        ok = send_via_whatsapp_web(lead, driver=driver, close_driver=False)
        if ok:
            sent_count += 1
            if callable(on_sent):
                on_sent(lead)
        if i < len(leads) - 1:
            time.sleep(delay_seconds)
    driver.quit()
    return sent_count
