"""
Crawler that searches for Southeast Asia villa property management contacts
and extracts phone numbers (WhatsApp uses phone numbers) and business names.
"""
import re
import time
import warnings
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

warnings.filterwarnings("ignore", module="duckduckgo_search")
try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

from config import CRAWL_LIMIT, SEARCH_QUERIES, SEARCH_REGION, SERPAPI_KEY


@dataclass
class Lead:
    """A potential contact for outreach."""
    name: str
    phone: str
    source_url: str
    snippet: str = ""


# International phone: +country and digits, or local 0/8/9 start (SEA)
PHONE_PATTERN = re.compile(
    r"\+?[1-9]\d{0,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b"
)
# SEA local: 08..., 09..., 02..., 03... (e.g. Indonesia, Thailand)
PHONE_LOCAL_PATTERN = re.compile(
    r"\b(0[2-9]\d[-.\s]?\d{3}[-.\s]?\d{3,4}|\d{9,12})\b"
)

def normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("0"):
        digits = digits.lstrip("0")
    return digits.strip() or raw.strip()


# SEA country codes (Malaysia, Indonesia, Singapore, Thailand, Vietnam, etc.)
SEA_COUNTRY_CODES = ("60", "62", "63", "65", "66", "84", "855", "856", "95", "673", "670")

def is_likely_phone(digits: str) -> bool:
    """Reject digits that look like years/dates or junk (e.g. 20251123, 19901234)."""
    if len(digits) < 8 or len(digits) > 15:
        return False
    # 8-digit numbers that start with 19 or 20 are usually years or dates
    if len(digits) == 8 and digits[:2] in ("19", "20"):
        return False
    # 8+ digits starting with 20XX or 19XX where XX looks like month (01-12) -> skip
    if len(digits) >= 8 and digits[:2] in ("19", "20"):
        month = digits[2:4]
        if month in ("01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"):
            return False
    return True


def extract_phones_from_text(text: str) -> list[str]:
    """Extract phone numbers from any text; filter out date-like/junk numbers."""
    if not text:
        return []
    phones = set()
    for m in PHONE_PATTERN.findall(text):
        p = normalize_phone(m)
        if len(p) >= 8 and is_likely_phone(p):
            phones.add(p)
    for m in PHONE_LOCAL_PATTERN.findall(text):
        p = normalize_phone(m)
        if len(p) >= 9 and len(p) <= 12 and is_likely_phone(p):
            phones.add(p)
    for m in re.findall(r"\d{8,12}", text):
        p = normalize_phone(m)
        if len(p) >= 8 and is_likely_phone(p):
            phones.add(p)
    return list(phones)


def search_duckduckgo(query: str, max_results: int = 10, region: str = "wt-wt") -> list[dict]:
    """Return list of {title, href, body} from DuckDuckGo. region e.g. id-id, th-th, sg-en."""
    if not DDGS:
        return []
    results = []
    try:
        with DDGS() as ddgs:
            kwargs = {"max_results": max_results}
            if hasattr(ddgs, "text") and region:
                try:
                    # duckduckgo_search / ddgs may accept region=
                    it = ddgs.text(query, **kwargs, region=region)
                except TypeError:
                    it = ddgs.text(query, **kwargs)
            else:
                it = ddgs.text(query, **kwargs)
            for r in it:
                results.append({
                    "title": r.get("title", ""),
                    "href": (r.get("href") or r.get("link", "")),
                    "body": (r.get("body") or r.get("snippet", "")),
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
    """Extract phone numbers from HTML (tel: links + page text)."""
    soup = BeautifulSoup(html, "html.parser")
    phones = set()

    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if href.startswith("tel:"):
            num = href.replace("tel:", "").strip()
            p = normalize_phone(num)
            if len(p) >= 8 and is_likely_phone(p):
                phones.add(p)

    text = soup.get_text()
    phones.update(extract_phones_from_text(text))
    return list(phones)


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


def crawl_search_results(queries: list[str], max_per_query: int = 10, verbose: bool = True) -> list[Lead]:
    """Run search for each query, extract phones from snippets and crawled pages."""
    seen_phones = set()
    seen_urls = set()
    leads = []

    for query in queries:
        combined = []
        combined.extend(search_duckduckgo(query, max_results=max_per_query, region=SEARCH_REGION))
        if SERPAPI_KEY:
            combined.extend(search_serpapi(query, max_results=max_per_query))

        if verbose:
            print(f"  Query: '{query[:50]}...' -> {len(combined)} results")

        for item in combined[:max_per_query]:
            url = (item.get("href") or item.get("link", "")).strip()
            if not url or not url.startswith("http"):
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)
            title = item.get("title", "") or "Contact"
            body = item.get("body", "") or ""

            # 1) Extract phones from search snippet (no fetch needed)
            for phone in extract_phones_from_text(body):
                if phone not in seen_phones:
                    seen_phones.add(phone)
                    leads.append(Lead(
                        name=title[:100],
                        phone=phone,
                        source_url=url,
                        snippet=body[:200] if body else "",
                    ))
                    if verbose:
                        print(f"    [snippet] +{phone} from {url[:50]}...")
                if len(leads) >= CRAWL_LIMIT:
                    return leads

            # 2) Fetch page and extract from HTML
            html = fetch_page(url)
            if not html:
                continue
            time.sleep(0.6)

            page_phones = extract_phones(html)
            if verbose and page_phones:
                print(f"    [page] {url[:50]}... -> {len(page_phones)} phone(s)")
            names = [title]
            page_name = extract_name_from_page(html, url)
            if page_name and page_name != "Contact":
                names.append(page_name)

            for phone in page_phones:
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


def run_crawl(verbose: bool = True) -> list[Lead]:
    """Run one crawl using config queries and limit."""
    max_per = max(5, CRAWL_LIMIT // len(SEARCH_QUERIES))
    leads = crawl_search_results(SEARCH_QUERIES, max_per_query=max_per, verbose=verbose)
    if verbose and not leads:
        print("No contacts found. Tips: 1) pip install duckduckgo-search  2) Set SERPAPI_KEY in .env for more results  3) Try SEARCH_REGION=id-id in .env")
    return leads
