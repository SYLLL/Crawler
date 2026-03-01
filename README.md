# Southeast Asia Villa Property Management – WhatsApp Outreach Crawler

Daily crawler that finds WhatsApp-capable phone contacts for **villa property management** in Southeast Asia, saves them to CSV, and can send automatic outreach using a configurable template (e.g. cleaning research partnership).

## What it does

1. **Search** – Runs web search for queries like “villa property management Southeast Asia WhatsApp”, “villa management Thailand Bali Indonesia WhatsApp”, etc.
2. **Crawl** – Visits result URLs and extracts phone numbers (and page titles as names). Phone numbers work with WhatsApp.
3. **Store** – Appends new, deduplicated leads to `data/leads.csv`.
4. **Outreach** (optional) – Sends the template message via **Twilio WhatsApp** to pending leads, and records sent numbers in `data/sent_outreach.csv` so each contact is only messaged once.

## Setup

### 1. Install dependencies

```bash
cd /Users/suyiliu/Crawler
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment variables

Copy the example env file and edit as needed:

```bash
cp .env.example .env
```

- **Crawl only (no sending)**  
  Leave `TWILIO_*` empty. The script will only collect leads into `data/leads.csv`.

- **Optional: SerpAPI**  
  Set `SERPAPI_KEY` in `.env` for more search results (get a key at [serpapi.com](https://serpapi.com/)).

- **Sending WhatsApp**  
  Set Twilio WhatsApp credentials in `.env`:
  - `TWILIO_ACCOUNT_SID`
  - `TWILIO_AUTH_TOKEN`
  - `TWILIO_WHATSAPP_FROM` (e.g. `whatsapp:+14155238886` for Twilio sandbox)

  See [Twilio WhatsApp](https://www.twilio.com/docs/whatsapp) for setup. **Cold outreach** usually requires an approved **message template** in the WhatsApp Business API; the script sends the template as a text body—you may need to create and use an approved template name in production.

### 3. Message template

The default outreach text is in `outreach.py` as `OUTREACH_TEMPLATE`. It uses `[Name]` as placeholder (replaced with the lead name or “there”). Edit `OUTREACH_TEMPLATE` in `outreach.py` to change the message.

## Usage

- **Full run (crawl + send, if Twilio configured)**  
  `python main.py`

- **Crawl only (no WhatsApp send)**  
  `python main.py --crawl-only`

- **Send only (use existing leads in CSV)**  
  `python main.py --send-only`

- **Dry run (print messages, don’t send)**  
  `python main.py --dry-run`

- **Limit number of messages per run**  
  `python main.py --max-send 5`

### Daily run

- **One-off job**  
  `python run_daily.py --once`

- **Daily at 09:00 (and once on start)**  
  `python run_daily.py`  
  (Keeps running and schedules daily at 09:00.)

- **Cron (recommended)**  
  Run once per day via cron, e.g. 9:00 AM:

  ```bash
  0 9 * * * cd /Users/suyiliu/Crawler && /path/to/venv/bin/python run_daily.py --once
  ```

  Replace `/path/to/venv/bin/python` with your actual `python` or `venv` path.

## Output files

| File | Purpose |
|------|--------|
| `data/leads.csv` | All discovered leads (name, phone, source_url, snippet). |
| `data/sent_outreach.csv` | Leads already sent the template (no duplicate sends). |

## Compliance and best practices

- **WhatsApp policies** – Sending to users who haven’t opted in can violate WhatsApp’s terms. Use the WhatsApp Business API with **approved templates** for first-time outreach and follow Meta’s policies.
- **Rate limiting** – The script sends at most `--max-send` per run and waits 2 seconds between Twilio sends to reduce risk of blocks.
- **Data** – You are responsible for handling personal data (phone numbers, names) in line with GDPR and local privacy laws.

## Troubleshooting: "Found 0 new phone contacts"

- **Install the search dependency** – Ensure `duckduckgo-search` is installed: `pip install duckduckgo-search`. Without it, search returns no results.
- **Use SerpAPI for reliable search** – DuckDuckGo can return 0 results (rate limiting or region). Add `SERPAPI_KEY` to `.env` (get a key at [serpapi.com](https://serpapi.com/)); the crawler will use both DuckDuckGo and SerpAPI.
- **Bias results to Southeast Asia** – In `.env` set `SEARCH_REGION=id-id` (Indonesia) or `SEARCH_REGION=th-th` (Thailand). Default is `wt-wt` (no region).
- **Run with verbose output** – The crawler prints how many results each query returns and when it finds phones in snippets vs. pages. If you see "0 results" for every query, fix the above.

## Customization

- **Search queries** – Edit `SEARCH_QUERIES` in `config.py`.
- **Crawl size** – Set `CRAWL_LIMIT` in `.env` or `config.py`.
- **Template** – Edit `OUTREACH_TEMPLATE` in `outreach.py`.
