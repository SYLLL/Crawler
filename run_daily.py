#!/usr/bin/env python3
"""
Run the full daily job: crawl for new leads, then send outreach to pending leads.
Schedule this with cron for daily execution, e.g.:

  crontab -e
  0 9 * * * cd /Users/suyiliu/Crawler && /usr/bin/env python3 run_daily.py

Or run once: python run_daily.py
"""
import schedule
import time

from main import run_crawler_only, run_outreach_only
from config import TWILIO_ACCOUNT_SID


def job():
    run_crawler_only()
    if TWILIO_ACCOUNT_SID:
        run_outreach_only(max_send=10)
    else:
        print("Twilio not configured; skipping outreach.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        job()
        sys.exit(0)
    # Default: run once now, then daily at 9:00
    job()
    schedule.every().day.at("09:00").do(job)
    print("Next scheduled run: daily at 09:00. Ctrl+C to stop.")
    while True:
        schedule.run_pending()
        time.sleep(60)
