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
CRAWL_LIMIT = int(os.getenv("CRAWL_LIMIT", "20"))
SEARCH_QUERIES = [
    "villa property management Southeast Asia WhatsApp",
    "villa management company Thailand Bali Indonesia WhatsApp",
    "luxury villa management Singapore Malaysia contact",
]

# Twilio WhatsApp (optional)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

# SerpAPI (optional, for more results)
SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
