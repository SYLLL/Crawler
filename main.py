#!/usr/bin/env python3
"""
Daily crawler: find Southeast Asia villa property management WhatsApp contacts,
save to CSV, and optionally send outreach via Twilio or WhatsApp Web (your number).
"""
import argparse
import time

from config import SEND_METHOD, TWILIO_ACCOUNT_SID
from crawler import run_crawl, Lead
from outreach import (
    append_leads,
    format_message,
    get_pending_leads_from_csv,
    record_sent,
    send_whatsapp,
)


def run_crawler_only() -> list[Lead]:
    """Run search + scrape; append new leads to CSV. Returns new leads."""
    print("Running crawler (SE Asia villa property management)...")
    leads = run_crawl()
    print(f"Found {len(leads)} new phone contacts.")
    if leads:
        append_leads(leads)
    elif not leads:
        print("Tip: Add SERPAPI_KEY to .env for more reliable search (see README).")
    return leads


def run_outreach_only(max_send: int = 100, dry_run: bool = False):
    """Send outreach to up to max_send pending leads. If dry_run, only print messages."""
    pending = get_pending_leads_from_csv(max_count=max_send)
    if not pending:
        print("No pending leads to contact.")
        return
    print(f"{'[DRY RUN] ' if dry_run else ''}Sending to {len(pending)} lead(s) via {SEND_METHOD}...")
    if dry_run:
        for lead in pending:
            print(f"To {lead.phone} ({lead.name}):\n{format_message(lead)}\n")
        return
    if SEND_METHOD == "whatsapp_web":
        from whatsapp_web_sender import send_bulk_via_whatsapp_web
        n = send_bulk_via_whatsapp_web(pending, on_sent=record_sent)
        print(f"Sent {n} message(s) via WhatsApp Web.")
        return
    for lead in pending:
        if send_whatsapp(lead):
            record_sent(lead)
            print(f"Sent to {lead.phone}")
            time.sleep(2)
        else:
            print(f"Skip or fail: {lead.phone}")


def main():
    parser = argparse.ArgumentParser(description="Villa property management contact crawler & outreach")
    parser.add_argument("--crawl-only", action="store_true", help="Only run crawler, do not send messages")
    parser.add_argument("--send-only", action="store_true", help="Only send to pending leads (no crawl)")
    parser.add_argument("--dry-run", action="store_true", help="Print messages only, do not send")
    parser.add_argument("--max-send", type=int, default=200, help="Max outreach messages per run (default 200)")
    args = parser.parse_args()

    if args.send_only:
        run_outreach_only(max_send=args.max_send, dry_run=args.dry_run)
        return

    run_crawler_only()

    if not args.crawl_only and not args.dry_run:
        if SEND_METHOD == "whatsapp_web" or TWILIO_ACCOUNT_SID:
            run_outreach_only(max_send=args.max_send, dry_run=False)
        else:
            print("Set SEND_METHOD=whatsapp_web in .env (default), or add Twilio credentials for SEND_METHOD=twilio.")
    elif args.dry_run:
        run_outreach_only(max_send=args.max_send, dry_run=True)


if __name__ == "__main__":
    main()
