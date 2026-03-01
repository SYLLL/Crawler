"""
Crawler that searches for Southeast Asia villa property management contacts
and extracts phone numbers (WhatsApp uses phone numbers) and business names.
"""
import re
import time
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

from config import CRAWL_LIMIT, SEARCH_QUERIES, SERPAPI_KEY


@dataclass
class Lead:
    """A potential contact for outreach."""
    name: str
    phone: str
    source_url: str
    snippet: str = ""


# International phone regex: +country code and digits, optional spaces/dashes
PHONE_PATTERN = re.compile(
    r"\+?[1-9]\d{0,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b"
)
# Normalize to digits only for dedup and WhatsApp (E.164-ish)
def normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("0"):
        digits = digits.lstrip("0")
    return digits.strip() or raw.strip()


def search_duckduckgo(query: str, max_results: int = 10) -> list[dict]:
    """Return list of {title, href, body} from DuckDuckGo."""
    if not DDGS:
        return []
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "href": r.get("href", ""),
                    "body": r.get("body", ""),
                })
    except Exception as e:
        print(f"DuckDuckGo search error: {e}")
    return results


def search_serpapi(query: str, max_results: int = 10) -> list[dict]:
    """Return list of {title, href, body} from SerpAPI if key is set."""
    if not SERPAPI_KEY:
        return []
    results = []
    try:
        resp = requests.get(
            "https://serpapi.com/search",
            params={"q": query, "api_key": SERPAPI_KEY, "num": max_results},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        for obj in data.get("organic_results", [])[:max_results]:
            results.append({
                "title": obj.get("title", ""),
                "href": obj.get("link", ""),
                "body": obj.get("snippet", ""),
            })
    except Exception as e:
        print(f"SerpAPI search error: {e}")
    return results


def fetch_page(url: str) -> str | None:
    """Fetch HTML of a URL. Returns None on failure."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"Fetch error {url}: {e}")
        return None


def extract_phones(html: str) -> list[str]:
    """Extract phone numbers from HTML (incl. tel: links and text)."""
    soup = BeautifulSoup(html, "html.parser")
    phones = set()

    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if href.startswith("tel:"):
            num = href.replace("tel:", "").strip()
            if PHONE_PATTERN.search(num) or re.search(r"\d{8,}", num):
                phones.add(normalize_phone(num))

    text = soup.get_text()
    for m in PHONE_PATTERN.findall(text):
        phones.add(normalize_phone(m))
    for m in re.findall(r"\d{8,}", text):
        if len(m) >= 8 and len(m) <= 15:
            phones.add(normalize_phone(m))

    return [p for p in phones if len(p) >= 8]


def extract_name_from_page(html: str, url: str) -> str:
    """Try to get a contact or business name from the page."""
    soup = BeautifulSoup(html, "html.parser")
    # Prefer title or og:title
    title = soup.find("title")
    if title and title.get_text(strip=True):
        return title.get_text(strip=True)[:80]
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return og.get("content")[:80]
    # Fallback: domain name
    try:
        return urlparse(url).netloc or "Contact"
    except Exception:
        return "Contact"


def crawl_search_results(queries: list[str], max_per_query: int = 10) -> list[Lead]:
    """Run search for each query, crawl result URLs, extract leads."""
    seen_phones = set()
    leads = []

    for query in queries:
        combined = []
        combined.extend(search_duckduckgo(query, max_results=max_per_query))
        if SERPAPI_KEY:
            combined.extend(search_serpapi(query, max_results=max_per_query))

        for item in combined[:max_per_query]:
            url = item.get("href", "").strip()
            if not url or not url.startswith("http"):
                continue
            title = item.get("title", "") or "Contact"
            body = item.get("body", "")

            html = fetch_page(url)
            if not html:
                continue
            time.sleep(0.5)

            names = [title]
            page_name = extract_name_from_page(html, url)
            if page_name and page_name != "Contact":
                names.append(page_name)

            for phone in extract_phones(html):
                if phone in seen_phones:
                    continue
                seen_phones.add(phone)
                name = names[0] if names else "Contact"
                leads.append(Lead(
                    name=name[:100],
                    phone=phone,
                    source_url=url,
                    snippet=body[:200] if body else "",
                ))
            if len(leads) >= CRAWL_LIMIT:
                return leads

    return leads


def run_crawl() -> list[Lead]:
    """Run one crawl using config queries and limit."""
    max_per = max(5, CRAWL_LIMIT // len(SEARCH_QUERIES))
    return crawl_search_results(SEARCH_QUERIES, max_per_query=max_per)
