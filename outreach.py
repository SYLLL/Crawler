"""
Outreach message template and optional WhatsApp send via Twilio.
"""
import csv
from pathlib import Path

from config import LEADS_CSV, SENT_CSV, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM, DATA_DIR
from crawler import Lead

OUTREACH_TEMPLATE = """Hi [Name], I'm Katie, a Stanford grad running a research project on professional cleaning. We're looking for cleaning companies to partner with. Your cleaners wear a small body camera during their normal work and we capture the process. They get paid extra per session, your company gets a location fee and a free professional video of your team's work. All equipment and waivers handled by us. Would you be open to a quick call?"""


def format_message(lead: Lead) -> str:
    """Replace [Name] with lead name (or 'there' if missing)."""
    name = (lead.name or "there").strip()
    if not name or name == "Contact":
        name = "there"
    return OUTREACH_TEMPLATE.replace("[Name]", name)


def ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def existing_phones() -> set[str]:
    """Return set of phones already in leads CSV."""
    if not LEADS_CSV.exists():
        return set()
    phones = set()
    with open(LEADS_CSV, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            phones.add((row.get("phone") or "").strip())
    return phones


def append_leads(leads: list[Lead]):
    """Append new leads to CSV (skip duplicates by phone), with header if file is new."""
    ensure_data_dir()
    existing = existing_phones()
    new_leads = [l for l in leads if (l.phone or "").strip() and (l.phone or "").strip() not in existing]
    if not new_leads:
        return
    file_exists = LEADS_CSV.exists()
    with open(LEADS_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not file_exists:
            w.writerow(["name", "phone", "source_url", "snippet"])
        for lead in new_leads:
            w.writerow([lead.name, lead.phone, lead.source_url, lead.snippet])
            existing.add(lead.phone)


def load_sent_phones() -> set[str]:
    """Return set of phone numbers we already sent to."""
    if not SENT_CSV.exists():
        return set()
    phones = set()
    with open(SENT_CSV, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            phones.add(row.get("phone", "").strip())
    return phones


def record_sent(lead: Lead):
    """Record that we sent outreach to this lead."""
    ensure_data_dir()
    file_exists = SENT_CSV.exists()
    with open(SENT_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not file_exists:
            w.writerow(["name", "phone", "source_url"])
        w.writerow([lead.name, lead.phone, lead.source_url])


def send_whatsapp(lead: Lead) -> bool:
    """
    Send outreach via Twilio WhatsApp. Returns True if sent, False otherwise.
    Requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_WHATSAPP_FROM.
    """
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        return False
    try:
        from twilio.rest import Client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        to = lead.phone
        if not to.startswith("+"):
            to = "+" + to
        body = format_message(lead)
        client.messages.create(
            from_=TWILIO_WHATSAPP_FROM,
            to=f"whatsapp:{to}",
            body=body,
        )
        return True
    except Exception as e:
        print(f"Twilio send error for {lead.phone}: {e}")
        return False


def get_pending_leads_from_csv(max_count: int = 50) -> list[Lead]:
    """Load leads from CSV that we haven't sent to yet."""
    if not LEADS_CSV.exists():
        return []
    sent = load_sent_phones()
    pending = []
    with open(LEADS_CSV, "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            phone = (row.get("phone") or "").strip()
            if phone and phone not in sent:
                pending.append(Lead(
                    name=(row.get("name") or "there").strip(),
                    phone=phone,
                    source_url=(row.get("source_url") or "").strip(),
                    snippet=(row.get("snippet") or "").strip(),
                ))
                if len(pending) >= max_count:
                    break
    return pending
