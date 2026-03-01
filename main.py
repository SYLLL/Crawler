#!/usr/bin/env python3
"""
Daily crawler: find Southeast Asia villa property management WhatsApp contacts,
save to CSV, and optionally send outreach via Twilio WhatsApp.
"""
import argparse
import time

from config import TWILIO_ACCOUNT_SID
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


def run_outreach_only(max_send: int = 10, dry_run: bool = False):
    """Send outreach to up to max_send pending leads. If dry_run, only print messages."""
    pending = get_pending_leads_from_csv(max_count=max_send)
    if not pending:
        print("No pending leads to contact.")
        return
    print(f"{'[DRY RUN] ' if dry_run else ''}Sending to {len(pending)} lead(s)...")
    for lead in pending:
        msg = format_message(lead)
        if dry_run:
            print(f"To {lead.phone} ({lead.name}):\n{msg}\n")
            continue
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
    parser.add_argument("--max-send", type=int, default=10, help="Max outreach messages per run (default 10)")
    args = parser.parse_args()

    if args.send_only:
        run_outreach_only(max_send=args.max_send, dry_run=args.dry_run)
        return

    run_crawler_only()

    if not args.crawl_only and not args.dry_run:
        if TWILIO_ACCOUNT_SID:
            run_outreach_only(max_send=args.max_send, dry_run=False)
        else:
            print("Twilio not configured. Add TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN to send messages.")
    elif args.dry_run:
        run_outreach_only(max_send=args.max_send, dry_run=True)


if __name__ == "__main__":
    main()
