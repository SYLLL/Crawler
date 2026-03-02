"""Configuration loaded from environment."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Paths
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
LEADS_CSV = DATA_DIR / "leads.csv"
SENT_CSV = DATA_DIR / "sent_outreach.csv"

# Search / crawl
CRAWL_LIMIT = int(os.getenv("CRAWL_LIMIT", "100"))
# Queries tuned for SEA villa/property management with contact info
SEARCH_QUERIES = [
    "villa property management Southeast Asia WhatsApp",
    "villa management company Thailand Bali Indonesia WhatsApp",
    "luxury villa management Singapore Malaysia contact",
    "villa management Bali phone number contact",
    "villa rental Thailand contact number",
    "property management Phuket Seminyak WhatsApp",
]
# DuckDuckGo region: id-id (Indonesia), th-th (Thailand), sg-en (Singapore), wt-wt (no region)
SEARCH_REGION = os.getenv("SEARCH_REGION", "wt-wt")

# How to send WhatsApp: "twilio" (API) or "whatsapp_web" (your number via browser)
SEND_METHOD = os.getenv("SEND_METHOD", "whatsapp_web").strip().lower() or "whatsapp_web"

# Twilio WhatsApp (optional; used when SEND_METHOD=twilio)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

# SerpAPI (optional, for more results)
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
