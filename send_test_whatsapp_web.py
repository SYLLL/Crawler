#!/usr/bin/env python3
"""
Send one test message via WhatsApp Web (your number).
Usage: python send_test_whatsapp_web.py +14437999993
"""
import sys
from crawler import Lead
from whatsapp_web_sender import send_via_whatsapp_web

def main():
    phone = (sys.argv[1] if len(sys.argv) > 1 else "").strip()
    if not phone:
        print("Usage: python send_test_whatsapp_web.py +1XXXXXXXXXX")
        sys.exit(1)
    lead = Lead(name="Test", phone=phone.replace("+", "").replace(" ", ""), source_url="", snippet="")
    print(f"Sending test message to {phone} via WhatsApp Web...")
    ok = send_via_whatsapp_web(lead)
    print("Done." if ok else "Send failed or incomplete. Check the browser window.")

if __name__ == "__main__":
    main()
