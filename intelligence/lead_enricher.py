import asyncio
import json
import os
import random
import re
import sys
from datetime import datetime
from playwright.async_api import async_playwright
from dotenv import load_dotenv
from groq import Groq
from anthropic import Anthropic

# Add project root to path for robust imports
sys.path.insert(0, os.getcwd())

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

class Symbol:
    """Clean logging symbols that work across all terminals"""
    USE_EMOJI = False # Set to True if your terminal supports UTF-8 emojis
    
    LIST = "📋" if USE_EMOJI else "[LIST]"
    LEAD = "💎" if USE_EMOJI else "[LEAD]"
    SEARCH = "🔍" if USE_EMOJI else "[SEARCH]"
    STOP = "🛑" if USE_EMOJI else "[STOP]"
    CHECK = "✅" if USE_EMOJI else "[OK]"
    WORLD = "🌍" if USE_EMOJI else "[WORLD]"
    WARN = "⚠️" if USE_EMOJI else "[WARN]"
    AI = "🧠" if USE_EMOJI else "[AI]"
    VIBE = "🎨" if USE_EMOJI else "[VIBE]"
    TONE = "🗣️" if USE_EMOJI else "[TONE]"
    PRIDE = "🆕" if USE_EMOJI else "[PRIDE]"
    TARGET = "🎯" if USE_EMOJI else "[TARGET]"
    TIME = "⏰" if USE_EMOJI else "[TIME]"
    NURTURE = "🌱" if USE_EMOJI else "[NURTURE]"
    REFERRAL = "🤝" if USE_EMOJI else "[REFERRAL]"
    EMAIL = "📧" if USE_EMOJI else "[EMAIL]"
    PHONE = "📞" if USE_EMOJI else "[PHONE]"
    WHATSAPP = "💬" if USE_EMOJI else "[WHATSAPP]"
    SOCIAL = "📱" if USE_EMOJI else "[SOCIAL]"
    INSTAGRAM = "📸" if USE_EMOJI else "[INSTAGRAM]"
    FACEBOOK = "📘" if USE_EMOJI else "[FACEBOOK]"
    RETRY = "🔄" if USE_EMOJI else "[RETRY]"
    BOT = "🛡️" if USE_EMOJI else "[BOT-WALL]"
    WAIT = "⏳" if USE_EMOJI else "[WAIT]"
    PITCH = "💡" if USE_EMOJI else "[PITCH]"
    PAGE = "📄" if USE_EMOJI else "[PAGE]"
    MAPS = "📍" if USE_EMOJI else "[MAPS]"
    ERROR = "❌" if USE_EMOJI else "[ERROR]"
    HUMAN = "🧑" if USE_EMOJI else "[USER]"

# ── Bot detection keywords ──────────────────────────────────────────────────
BOT_WALL_SIGNALS = [
    "captcha", "cloudflare", "hcaptcha", "recaptcha",
    "verify you are human", "access denied", "403 forbidden",
    "please enable javascript", "checking your browser",
    "ddos protection", "ray id", "security check",
    "just a moment", "attention required", "enable cookies"
]

def is_bot_wall(text: str, url: str) -> bool:
    """Detect if page is showing a bot protection wall"""
    text_lower = text.lower()
    return any(signal in text_lower for signal in BOT_WALL_SIGNALS)


async def try_google_cache(page, url: str) -> str | None:
    """Try to read Google's cached version of a blocked page"""
    try:
        cache_url = f"https://webcache.googleusercontent.com/search?q=cache:{url}"
        print(f"      {Symbol.RETRY} Trying Google cache: {url[:50]}...")
        await page.goto(cache_url, timeout=12000, wait_until="domcontentloaded")
        await handle_consent(page)
        await human_pause(2.0, 3.5)
        text = await page.evaluate("() => document.body.innerText")
        if text and len(text) > 200 and not is_bot_wall(text, cache_url):
            print(f"      {Symbol.CHECK} Cache hit — got content")
            return text
    except:
        pass
    return None


async def safe_goto(page, url: str, timeout: int = 15000) -> dict:
    """
    Safely navigate to a URL.
    Returns dict with success status, text content, and whether it was blocked.
    """
    result = {
        "success": False,
        "blocked": False,
        "text": "",
        "html": "",
        "source": "direct"
    }

    # Skip PDFs, CSVs and other non-HTML files
    if any(url.lower().endswith(ext) for ext in [
        '.pdf', '.csv', '.xlsx', '.doc', '.docx', '.zip', '.xml'
    ]):
        print(f"      — Skipping non-HTML file: {url[-50:]}")
        result["success"] = False
        return result

    try:
        await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        await handle_consent(page)
        await human_pause(2.0, 4.0)
        await human_scroll(page, scrolls=random.randint(2, 4))

        text = await page.evaluate("() => document.body.innerText")
        html = await page.evaluate("() => document.body.innerHTML")

        # Check for bot wall
        if is_bot_wall(text, url):
            print(f"      {Symbol.BOT}{Symbol.WARN}  Bot wall detected — trying cache once...")
            result["blocked"] = True

            # Try Google cache ONCE only
            cached_text = await try_google_cache(page, url)
            if cached_text and len(cached_text) > 300:
                result["success"] = True
                result["text"] = cached_text
                result["html"] = ""
                result["source"] = "google_cache"
            else:
                print(f"      {Symbol.ERROR}  Cache unavailable — skipping")
                result["success"] = False
            return result  # Always return after bot wall — don't retry
        else:
            result["success"] = True
            result["text"] = text
            result["html"] = html
            result["source"] = "direct"

    except Exception as e:
        error = str(e).lower()
        if "timeout" in error:
            print(f"      —  Timeout — site too slow, skipping")
        elif "net::err" in error:
            print(f"      {Symbol.WORLD}{Symbol.WARN} Network error — site unreachable")
        else:
            print(f"      {Symbol.ERROR}  Error: {str(e)[:60]}")
        result["success"] = False

    return result


def load_config(path: str = "ceo_config.json") -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

config = load_config()

# ── Nigerian public holidays and events for timing intelligence ───────────────
NIGERIAN_EVENTS = {
    "01-01": "New Year's Day",
    "04-18": "Good Friday",
    "05-01": "Workers Day",
    "06-12": "Democracy Day",
    "10-01": "Independence Day",
    "12-25": "Christmas Day",
    "12-26": "Boxing Day",
}

# ── Domains that are NOT official business websites ───────────────────────────
AGGREGATOR_DOMAINS = [
    'hotels.ng', 'chowdeck.com', 'jumia.com', 'yellowplate.ng',
    'goto-where.com', 'wordpress.com', 'blogspot.com', 'tripadvisor.com',
    'foursquare.com', 'zomato.com', 'waze.com', 'booking.com',
    'facebook.com', 'instagram.com', 'twitter.com', 'tiktok.com',
    'linkedin.com', 'google.com', 'yelp.com', 'metroaxs.com',
    'revphy.com', 'zeperoni.com', 'zabihah.com', 'thetravelhunters.com',
    'abujafoodtour.wordpress.com', 'restaurantfurnitureplus.com',
    'rocketreach.co', 'ng.linkedin.com', 'aboutus.org', 'bizapedia.com',
    'mindtrip.ai', 'placejoys.com', 'b2bhint.com',
    'dinesurf.com', 'yellowpages.com.ng', 'nigeriangalleria.com',
    'vconnect.com', 'businesslist.com.ng', 'whogohost.com',
    'nairaland.com', 'ngcareers.com', 'naijagoodies.com',
    'openrice.com', 'menupages.com', 'restaurantguru.com',
    'allmenus.com', 'grubhub.com', 'seamless.com',
    'directory.org.ng', 'ng.worldorgs.com', 'worldorgs.com',
    'halalfoodle.com', 'eatup.ng', 'pencom.gov.ng',
    'maptons.com', 'me.maptons.com', 'toasttab.com',
    'ncc.gov.ng', 'edostate.gov.ng', 'gov.ng',
    'viamichelin', 'michelin.net',
    'ng.infoaboutcompanies.com', 'infoaboutcompanies.com',
    'fidelitybank.ng', 'gtbank.com', 'zenithbank.com',
    'accessbankplc.com', 'firstbanknigeria.com',
    'rscn.org.jo', 'ijefm.co.in', 'budgit.org',
    'dj.maptons.com', 'co.in', 'org.jo',
    'mtn.ng', 'africabizinfo.com', 'researchgate.net',
    'viamichelin-app', 'glo.com', 'airtel.com.ng',
    '9mobile.com.ng', 'stanbicibtc.com', 'ubagroup.com',
]

# ── Hosted site builders — real content, not custom domain ───────────────────
HOSTED_BUILDERS = [
    'wixsite.com', 'squarespace.com', 'webflow.io', 'weebly.com',
    'godaddysites.com', 'site123.me', 'jimdo.com', 'strikingly.com',
]


# ─────────────────────────────────────────────────────────────────────────────
# AI CLIENT — Claude first, Groq fallback
# ─────────────────────────────────────────────────────────────────────────────
def get_ai_response(prompt: str, max_tokens: int = 800) -> str:
    from utils.ai_client import ai_response
    return ai_response(prompt, task="enrich", max_tokens=max_tokens)

from utils.ai_client import safe_json


# ─────────────────────────────────────────────────────────────────────────────
# HUMAN BEHAVIOUR HELPERS
# ─────────────────────────────────────────────────────────────────────────────
async def human_pause(min_s=2.0, max_s=5.0):
    await asyncio.sleep(random.uniform(min_s, max_s))


async def human_scroll(page, scrolls=4):
    # Halve the number of scrolls to save time
    actual_scrolls = max(1, scrolls // 2)
    for _ in range(actual_scrolls):
        distance = random.randint(250, 750)
        await page.evaluate(f"window.scrollBy(0, {distance})")
        await asyncio.sleep(random.uniform(0.2, 0.5))
    await page.evaluate(f"window.scrollBy(0, -{random.randint(80, 250)})")
    await asyncio.sleep(random.uniform(0.2, 0.4))


async def handle_consent(page):
    selectors = [
        'button[aria-label="Accept all"]',
        'button[jsname="b3VHJd"]',
        '#L2AGLb', '.QS5gu',
        'button:has-text("Accept all")',
        'button:has-text("I agree")',
        'button:has-text("Accept")',
        'button:has-text("Allow all")',
    ]
    for sel in selectors:
        try:
            btn = await page.query_selector(sel)
            if btn:
                await asyncio.sleep(random.uniform(0.3, 0.8))
                await btn.click()
                await asyncio.sleep(random.uniform(0.5, 1.2))
                return True
        except:
            continue
    return False


# ─────────────────────────────────────────────────────────────────────────────
# CONTACT EXTRACTION FROM RAW TEXT
# ─────────────────────────────────────────────────────────────────────────────
def extract_contacts(text: str) -> dict:
    # Emails
    email_re = r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'
    emails = list(set(re.findall(email_re, text)))
    emails = [
        e for e in emails
        if not re.search(r'\.(png|jpg|jpeg|gif|svg|webp|css|js|woff)$', e, re.I)
        and 'example' not in e
        and 'sentry' not in e
    ]

    # Nigerian phones
    phone_re = r'(\+?234[\s\-]?|0)([789][01][\s\-]?\d{4}[\s\-]?\d{4})'
    raw = re.findall(phone_re, text)
    phones = []
    for prefix, number in raw:
        clean = re.sub(r'[\s\-]', '', prefix + number)
        if len(clean) >= 11:
            phones.append(clean)
    phones = list(set(phones))[:5]

    # WhatsApp links
    wa_re = r'wa\.me/(\d+)'
    wa_matches = re.findall(wa_re, text)
    whatsapp_links = [f"https://wa.me/{m}" for m in wa_matches]

    return {
        "emails": emails[:5],
        "phones": phones,
        "whatsapp_links": whatsapp_links[:3]
    }


# ─────────────────────────────────────────────────────────────────────────────
# DOMAIN CLASSIFIER — Is this their official website?
# ─────────────────────────────────────────────────────────────────────────────
def classify_domain(url: str, business_name: str) -> dict:
    if not url:
        return {"score": 0, "type": "none", "reason": "No URL"}

    url_lower = url.lower()
    name_words = [
        w for w in re.sub(r'[^a-z0-9 ]', ' ', business_name.lower()).split()
        if len(w) > 3
    ]

    # Aggregator check
    if any(bad in url_lower for bad in AGGREGATOR_DOMAINS):
        return {
            "score": 2,
            "type": "aggregator",
            "reason": "Third-party directory or social platform"
        }

    # Hosted builder check
    if any(builder in url_lower for builder in HOSTED_BUILDERS):
        name_in_url = any(word in url_lower for word in name_words)
        return {
            "score": 7 if name_in_url else 5,
            "type": "hosted_builder",
            "reason": "Wix/Squarespace/Webflow — their content, not custom domain"
        }

    # Custom domain — does the business name appear in it?
    name_in_domain = any(word in url_lower for word in name_words)
    if name_in_domain:
        return {
            "score": 10,
            "type": "official",
            "reason": "Custom domain matching business name — confirmed official"
        }

    # Custom domain but name doesn't match
    return {
        "score": 6,
        "type": "possible_official",
        "reason": "Custom domain — name not in URL, needs AI verification"
    }


# ─────────────────────────────────────────────────────────────────────────────
# SMART SEARCH ENGINE — Google first, intelligent fallback chain
# ─────────────────────────────────────────────────────────────────────────────
import urllib.request
import time

# Track Google block status per session
_google_blocked = False
_last_search_time = 0
_search_count = 0

# Track SerpAPI key usage
_serpapi_keys = []
_serpapi_key_index = 0
_serpapi_exhausted_keys = set()


def load_serpapi_keys() -> list:
    """Load all available SerpAPI keys from environment"""
    keys = []
    for i in range(1, 10):  # Support up to 9 keys
        key = os.getenv(f"SERPAPI_KEY_{i}")
        if key and key.strip():
            keys.append(key.strip())
    # Also check plain SERPAPI_KEY for backward compatibility
    plain_key = os.getenv("SERPAPI_KEY")
    if plain_key and plain_key.strip() and plain_key not in keys:
        keys.append(plain_key.strip())
    return keys


async def _search_google_direct(page, query: str, max_links: int = 10) -> list:
    """
    Try Google Search directly via browser.
    Returns links if successful, empty list if blocked.
    """
    global _google_blocked, _last_search_time, _search_count

    # If already blocked this session, skip immediately
    if _google_blocked:
        return []

    # Enforce human-like minimum gap between Google searches
    now = time.time()
    elapsed = now - _last_search_time
    min_gap = random.uniform(30, 60)  # 30-60 seconds between Google searches
    if elapsed < min_gap and _search_count > 0:
        wait = min_gap - elapsed
        print(f"      — Google cooldown: {wait:.0f}s...")
        await asyncio.sleep(wait)

    _search_count += 1
    _last_search_time = time.time()

    try:
        encoded = query.replace(' ', '+')
        await page.goto(
            f"https://www.google.com/search?q={encoded}",
            timeout=25000,
            wait_until="domcontentloaded"
        )
        await human_pause(6.0, 12.0)
        await handle_consent(page)
        await human_pause(4.0, 8.0)
        await human_scroll(page, scrolls=random.randint(2, 4))
        await human_pause(2.0, 5.0)

        text = await page.evaluate("() => document.body.innerText")

        # Check for block
        if any(signal in text.lower() for signal in [
            "unusual traffic", "not a robot", "captcha",
            "verify you are human", "our systems have detected"
        ]):
            print(f"      — Google blocked this IP — activating fallback chain")
            _google_blocked = True
            return []

        links = await page.evaluate("""
            (bad) => {
                const links = [];
                document.querySelectorAll('a[href]').forEach(a => {
                    const href = a.href;
                    if (
                        href.startsWith('http') &&
                        !bad.some(b => href.includes(b)) &&
                        href.length > 15
                    ) links.push(href);
                });
                return [...new Set(links)];
            }
        """, [
            'google.', 'gstatic.', 'googleusercontent.',
            'schema.org', 'w3.org'
        ])

        if links:
            print(f"      {Symbol.CHECK} Google: {len(links[:max_links])} results")
            # Success — reset blocked status
            _google_blocked = False
            return links[:max_links]

    except Exception as e:
        print(f"      {Symbol.ERROR}  Google direct failed: {str(e)[:50]}")

    return []


async def _search_serpapi(query: str, max_links: int = 10) -> list:
    """
    Try SerpAPI with automatic key rotation.
    Rotates through all available keys before giving up.
    """
    global _serpapi_keys, _serpapi_key_index, _serpapi_exhausted_keys

    # Load keys if not loaded yet
    if not _serpapi_keys:
        _serpapi_keys = load_serpapi_keys()

    if not _serpapi_keys:
        return []  # No keys configured

    # Try each key in rotation
    attempts = 0
    while attempts < len(_serpapi_keys):
        # Find next non-exhausted key
        key = None
        for i in range(len(_serpapi_keys)):
            idx = (_serpapi_key_index + i) % len(_serpapi_keys)
            candidate = _serpapi_keys[idx]
            if candidate not in _serpapi_exhausted_keys:
                key = candidate
                _serpapi_key_index = (idx + 1) % len(_serpapi_keys)
                break

        if not key:
            print(f"      {Symbol.ERROR}  All SerpAPI keys exhausted")
            break

        try:
            from serpapi import GoogleSearch
            search = GoogleSearch({
                "q": query,
                "api_key": key,
                "num": max_links,
                "gl": "ng",
                "hl": "en",
                "safe": "off"
            })
            results = search.get_dict()

            # Check for errors
            if "error" in results:
                error_msg = results["error"].lower()
                if "credit" in error_msg or "limit" in error_msg or "quota" in error_msg:
                    print(f"      {Symbol.ERROR}  SerpAPI key exhausted — — rotating to next key")
                    _serpapi_exhausted_keys.add(key)
                    attempts += 1
                    continue
                else:
                    print(f"      {Symbol.ERROR}  SerpAPI error: {results['error'][:60]}")
                    attempts += 1
                    continue

            links = []
            for result in results.get("organic_results", []):
                link = result.get("link")
                if link and link.startswith("http"):
                    links.append(link)

            if links:
                key_num = _serpapi_keys.index(key) + 1
                print(f"      {Symbol.CHECK} SerpAPI key {key_num}: {len(links)} results")
                return links[:max_links]

        except ImportError:
            print(f"      {Symbol.ERROR}  serpapi not installed — run: pip install google-search-results")
            break
        except Exception as e:
            print(f"      {Symbol.ERROR}  SerpAPI failed: {str(e)[:50]}")
            attempts += 1
            continue

    return []


async def _search_duckduckgo(query: str, max_links: int = 10) -> list:
    """DuckDuckGo HTML search — no API, very bot-friendly"""
    try:
        await asyncio.sleep(random.uniform(3, 6))
        encoded = query.replace(' ', '+').replace('"', '%22')
        url = f"https://html.duckduckgo.com/html/?q={encoded}"

        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })

        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode('utf-8', errors='ignore')

        # Extract result URLs
        links = []

        # Method 1: result__url class
        url_matches = re.findall(r'class="result__url"[^>]*>([^<]+)<', html)
        for link in url_matches:
            link = link.strip()
            if not link.startswith('http'):
                link = 'https://' + link
            if 'duckduckgo' not in link:
                links.append(link)

        # Method 2: href attributes in results
        href_matches = re.findall(
            r'href="(https?://(?!.*duckduckgo)[^"]+)"', html
        )
        for link in href_matches:
            if link not in links and 'duckduckgo' not in link:
                links.append(link)

        clean = list(dict.fromkeys(links))  # deduplicate preserving order

        if clean:
            print(f"      {Symbol.CHECK} DuckDuckGo: {len(clean[:max_links])} results")
            return clean[:max_links]

    except Exception as e:
        print(f"      {Symbol.ERROR}  DuckDuckGo failed: {str(e)[:50]}")

    return []


async def _search_bing(query: str, max_links: int = 10) -> list:
    """Bing search — final fallback before giving up"""
    try:
        await asyncio.sleep(random.uniform(3, 6))
        encoded = query.replace(' ', '+')
        url = f"https://www.bing.com/search?q={encoded}&count={max_links}"

        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })

        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode('utf-8', errors='ignore')

        links = re.findall(r'<a[^>]+href="(https?://[^"]+)"', html)
        clean = [
            l for l in links
            if 'bing.com' not in l
            and 'microsoft.com' not in l
            and 'msn.com' not in l
            and len(l) > 15
        ]
        clean = list(dict.fromkeys(clean))

        if clean:
            print(f"      {Symbol.CHECK} Bing fallback: {len(clean[:max_links])} results")
            return clean[:max_links]

    except Exception as e:
        print(f"      {Symbol.ERROR}  Bing failed: {str(e)[:50]}")

    return []


async def smart_search(page, query: str, max_links: int = 10) -> list:
    """
    Master search function with full intelligent fallback chain:
    Google â†’ SerpAPI (with key rotation) â†’ DuckDuckGo â†’ Bing â†’ []

    Always tries Google first. If blocked, rotates through
    SerpAPI keys automatically. Never gives up until all options exhausted.
    """
    print(f"      {Symbol.SEARCH} Searching: {query[:60]}")

    # Step 1 — Google direct (primary, always try first unless blocked)
    if not _google_blocked:
        links = await _search_google_direct(page, query, max_links)
        if links:
            return links
        print(f"      {Symbol.RETRY} Google failed — trying SerpAPI...")
    else:
        print(f"      —  Google blocked this session — going to SerpAPI")

    # Step 2 — SerpAPI with automatic key rotation
    serpapi_keys = load_serpapi_keys()
    if serpapi_keys:
        links = await _search_serpapi(query, max_links)
        if links:
            return links
        print(f"      {Symbol.RETRY} SerpAPI exhausted — trying DuckDuckGo...")
    else:
        print(f"      —  No SerpAPI keys — trying DuckDuckGo")

    # Step 3 — DuckDuckGo (no API, no limit)
    links = await _search_duckduckgo(query, max_links)
    if links:
        return links
    print(f"      {Symbol.RETRY} DuckDuckGo failed — trying Bing...")

    # Step 4 — Bing (last resort)
    links = await _search_bing(query, max_links)
    if links:
        return links

    # Step 5 — All search engines failed
    print(f"      {Symbol.ERROR}  All search engines failed — working with direct sources only")
    return []


async def google_search(page, query: str, max_links=8, retry=2) -> list:
    """Backward-compatible wrapper — now uses smart_search"""
    return await smart_search(page, query, max_links)


async def collect_discovery_links(page, business_name: str, city: str) -> list:
    """ONE smart search per lead — full fallback chain handles everything"""
    query = f'{business_name} {city} Nigeria'

    links = await smart_search(page, query, max_links=15)

    # Always add Google Maps direct URL — no search needed
    maps_url = f"https://www.google.com/maps/search/{business_name.replace(' ', '+')}+{city}+Nigeria"
    if maps_url not in links:
        links.append(maps_url)

    return links


# ─────────────────────────────────────────────────────────────────────────────
async def find_official_website(page, business_name: str, city: str, links: list = None) -> dict:
    if not links:
        links = await google_search(page, f'"{business_name}" {city} Nigeria website')

    all_candidates = []
    for link in links:
        classification = classify_domain(link, business_name)
        all_candidates.append({
            "url": link,
            "classification": classification
        })

    # Sort by score descending
    all_candidates.sort(key=lambda x: x["classification"]["score"], reverse=True)

    # Remove duplicates
    seen = set()
    unique = []
    for c in all_candidates:
        domain = re.sub(r'https?://(www\.)?', '', c["url"]).split('/')[0]
        if domain not in seen:
            seen.add(domain)
            unique.append(c)

    best = unique[0] if unique else None

    # Hard reject obviously wrong domains
    def is_clearly_wrong(url: str, business_name: str, city: str) -> bool:
        url_lower = url.lower()
        name_lower = business_name.lower()
        city_lower = city.lower()

        # Foreign domains for Nigerian local businesses
        foreign_tlds = ['.co.in', '.org.jo', '.co.uk', '.com.au']
        if any(tld in url_lower for tld in foreign_tlds):
            # Only keep if business name is in the URL
            name_words = [w for w in re.sub(r'[^a-z0-9 ]', ' ', name_lower).split() if len(w) > 3]
            if not any(word in url_lower for word in name_words):
                return True

        # Banks, Telecoms, and government sites
        financial_gov_telco = [
            'fidelitybank', 'gtbank', 'zenithbank', 'accessbank',
            'firstbank', 'pencom', 'ncc.gov', 'budgit', 'gov.ng',
            'mtn.ng', 'glo.com', 'airtel', '9mobile', 'stanbic',
            'ubagroup', 'unionbank'
        ]
        if any(fgt in url_lower for fgt in financial_gov_telco):
            return True

        # Academic/journal/research sites
        academic = ['journal', 'academic', 'research', 'ijefm', 'rscn', 'researchgate', 'paper']
        if any(ac in url_lower for ac in academic):
            return True

        # Known Directories
        if 'africabizinfo' in url_lower or 'infoaboutcompanies' in url_lower:
            return True

        return False

    if best and is_clearly_wrong(best["url"], business_name, city):
        print(f"      — Rejected clearly wrong site: {best['url'][:60]}")
        best = None
        # Try next candidate
        for candidate in unique[1:]:
            if not is_clearly_wrong(candidate["url"], business_name, city) and candidate["classification"]["score"] >= 5:
                best = candidate
                print(f"      {Symbol.CHECK} Using next best: {best['url'][:60]}")
                break

    # AI verification for ambiguous cases
    if best and best["classification"]["score"] in [5, 6]:
        verdict = await ai_verify_website(best["url"], business_name, city)
        best["classification"]["ai_verdict"] = verdict
        if verdict == "aggregator":
            print(f"      — AI rejected as aggregator: {best['url'][:60]}")
            best = None

    # Even if no official site found, mine aggregators for contact data
    aggregator_contacts = {"emails": [], "phones": [], "whatsapp_links": []}
    for candidate in unique[:5]:
        if candidate["classification"]["score"] < 5:
            try:
                print(f"      {Symbol.SEARCH} Mining aggregator for contacts: {candidate['url'][:60]}")
                await page.goto(candidate["url"], timeout=12000, wait_until="domcontentloaded")
                await handle_consent(page)
                await human_pause(2.0, 3.5)
                await human_scroll(page, scrolls=3)
                text = await page.evaluate("() => document.body.innerText")
                html = await page.evaluate("() => document.body.innerHTML")
                contacts = extract_contacts(text + " " + html)
                aggregator_contacts["emails"] += contacts["emails"]
                aggregator_contacts["phones"] += contacts["phones"]
                aggregator_contacts["whatsapp_links"] += contacts["whatsapp_links"]
                await human_pause(2.0, 3.5)
            except:
                continue

    # Deduplicate
    aggregator_contacts["emails"] = list(set(aggregator_contacts["emails"]))[:5]
    aggregator_contacts["phones"] = list(set(aggregator_contacts["phones"]))[:5]
    aggregator_contacts["whatsapp_links"] = list(set(aggregator_contacts["whatsapp_links"]))[:3]

    return {
        "url": best["url"] if best and best["classification"]["score"] >= 5 else None,
        "type": best["classification"]["type"] if best else "none",
        "score": best["classification"]["score"] if best else 0,
        "aggregator_contacts": aggregator_contacts
    }


async def ai_verify_website(url: str, business_name: str, city: str) -> str:
    prompt = f"""
A URL was found that might be the official website for "{business_name}" in {city}, Nigeria.
URL: {url}

Based on the URL alone, is this likely their official website?
Consider: does the domain relate to the business name? Is it a known aggregator or directory?

Reply with ONLY one word: "official", "aggregator", or "uncertain"
"""
    try:
        return get_ai_response(prompt, max_tokens=10).strip().lower()
    except:
        return "uncertain"


# ─────────────────────────────────────────────────────────────────────────────
# DEEP WEBSITE SCRAPER
# ─────────────────────────────────────────────────────────────────────────────
async def deep_scrape_website(page, url: str) -> dict:
    all_data = {
        "emails": [], "phones": [], "whatsapp_links": [],
        "socials": {}, "description": None, "pages_visited": [],
        "raw_text": ""
    }

    if not url:
        return all_data

    # Safety: Never deep scrape an aggregator
    if any(bad in url.lower() for bad in AGGREGATOR_DOMAINS):
        return all_data

    base = url.rstrip("/").split("?")[0].split("#")[0]
    pages_to_try = [
        url,
        f"{base}/contact",
        f"{base}/contact-us",
        f"{base}/about",
        f"{base}/about-us",
        f"{base}/reach-us",
        f"{base}/get-in-touch",
    ]

    visited = set()
    domain_blocked = False
    consecutive_failures = 0

    for target in pages_to_try:
        if target in visited:
            continue
        visited.add(target)

        # If domain is blocked — stop trying more pages on same domain
        if domain_blocked:
            print(f"      —  Skipping {target[:50]} — domain is blocked")
            break

        # Stop after 3 consecutive failures
        if consecutive_failures >= 3:
            print(f"      —  Too many failures — stopping website scrape")
            break

        try:
            print(f"      {Symbol.PAGE} Visiting: {target[:60]}")
            nav = await safe_goto(page, target)

            if not nav["success"]:
                consecutive_failures += 1
                # If blocked on first page — mark entire domain as blocked
                if nav.get("blocked") and target == url:
                    domain_blocked = True
                    print(f"      — Domain blocked — skipping all subpages")
                    break
                continue

            # Reset failure counter on success
            consecutive_failures = 0

            text = nav["text"]
            html = nav["html"]
            all_data["raw_text"] += " " + text[:2000]
            all_data["pages_visited"].append(target)

            contacts = extract_contacts(text + " " + html)
            all_data["emails"] = list(set(all_data["emails"] + contacts["emails"]))
            all_data["phones"] = list(set(all_data["phones"] + contacts["phones"]))
            all_data["whatsapp_links"] = list(set(
                all_data["whatsapp_links"] + contacts["whatsapp_links"]
            ))

            # Social links
            for platform, pattern in {
                "facebook": r'facebook\.com/([a-zA-Z0-9._\-/]+)',
                "instagram": r'instagram\.com/([a-zA-Z0-9._\-/]+)',
                "twitter": r'twitter\.com/([a-zA-Z0-9._\-/]+)',
                "tiktok": r'tiktok\.com/@([a-zA-Z0-9._\-/]+)',
                "linkedin": r'linkedin\.com/([a-zA-Z0-9._\-/]+)',
                "youtube": r'youtube\.com/([a-zA-Z0-9._\-/@/]+)',
            }.items():
                match = re.search(pattern, html)
                if match and platform not in all_data["socials"]:
                    slug = match.group(1).split('?')[0].rstrip('/')
                    all_data["socials"][platform] = f"https://{platform}.com/{slug}"

            # Meta description
            if not all_data["description"] and nav["source"] == "direct":
                try:
                    meta = await page.query_selector('meta[name="description"]')
                    if meta:
                        all_data["description"] = await meta.get_attribute("content")
                except:
                    pass

            # Discover internal contact/about links
            if nav["source"] == "direct":
                try:
                    internal = await page.evaluate("""
                        () => {
                            const links = [];
                            document.querySelectorAll('a[href]').forEach(a => {
                                const h = a.href.toLowerCase();
                                if ((h.includes('contact') || h.includes('about') ||
                                     h.includes('reach') || h.includes('touch')) &&
                                    !h.includes('mailto') && h.startsWith('http'))
                                    links.push(a.href);
                            });
                            return [...new Set(links)].slice(0, 3);
                        }
                    """)
                    for link in internal:
                        if link not in visited and link not in pages_to_try:
                            pages_to_try.append(link)
                except:
                    pass

            await human_pause(2.0, 4.0)

            # Stop early if we have enough data
            if len(all_data["emails"]) >= 1 and len(all_data["phones"]) >= 1:
                print(f"      {Symbol.CHECK} Good data found — stopping early")
                break

        except Exception as e:
            consecutive_failures += 1
            err = str(e).lower()
            if "closed" in err or "disconnected" in err:
                print(f"      {Symbol.ERROR}  Browser issue — stopping website scrape")
                break
            print(f"      {Symbol.ERROR}  Could not load {target[:50]}: {str(e)[:50]}")
            continue

    return all_data


# ─────────────────────────────────────────────────────────────────────────────
# INSTAGRAM SCRAPER
# ─────────────────────────────────────────────────────────────────────────────
async def scrape_instagram(page, business_name: str, city: str, links: list = None) -> dict:
    data = {
        "found": False, "url": None, "bio": None,
        "email": None, "phone": None, "whatsapp": None,
        "followers": None, "posts_sample": []
    }

    try:
        if not links:
            links = await google_search(page, f'"{business_name}" {city} Nigeria instagram')

        ig_links = [
            l for l in links
            if 'instagram.com' in l
            and '/p/' not in l
            and '/reel' not in l
            and '/popular/' not in l
            and '/explore/' not in l
            and '/stories/' not in l
            and '/tv/' not in l
        ]
        if not ig_links:
            return data

        url = ig_links[0]
        print(f"      {Symbol.INSTAGRAM} Instagram: {url}")

        # Instagram needs extra time — it's heavily JS rendered
        await page.goto(url, timeout=20000, wait_until="domcontentloaded")
        await handle_consent(page)

        # Wait for Instagram to fully render
        await human_pause(5.0, 8.0)

        # Try to wait for the bio section specifically
        try:
            await page.wait_for_selector('header section', timeout=8000)
        except:
            pass

        await human_pause(3.0, 5.0)
        await human_scroll(page, scrolls=3)
        await human_pause(2.0, 4.0)

        text = await page.evaluate("() => document.body.innerText")
        html = await page.evaluate("() => document.body.innerHTML")

        # If Instagram is showing login wall — extract what we can
        if "log in" in text.lower() and len(text) < 500:
            print(f"      {Symbol.ERROR}  Instagram login wall — extracting from meta tags")
            meta_text = await page.evaluate("""
                () => {
                    const metas = document.querySelectorAll('meta');
                    let text = '';
                    metas.forEach(m => {
                        text += (m.getAttribute('content') || '') + ' ';
                    });
                    return text;
                }
            """)
            text = meta_text
            html = ""

        contacts = extract_contacts(text + " " + html)
        data["found"] = True
        data["url"] = url
        data["bio"] = text[:500]
        data["email"] = contacts["emails"][0] if contacts["emails"] else None
        data["phone"] = contacts["phones"][0] if contacts["phones"] else None
        data["whatsapp"] = contacts["whatsapp_links"][0] if contacts["whatsapp_links"] else None

        # Follower count — try multiple patterns
        follower_patterns = [
            r'([\d,\.]+[KkMm]?)\s*[Ff]ollower',
            r'([0-9,]+)\s*Followers',
            r'"edge_followed_by":\{"count":(\d+)\}',
            r'(\d[\d,\.]*[KkMm]?)\s*followers',
        ]
        for pattern in follower_patterns:
            match = re.search(pattern, text + html, re.I)
            if match:
                data["followers"] = match.group(1)
                break

        # Also try meta tags
        if not data["followers"]:
            try:
                meta_desc = await page.query_selector('meta[name="description"]')
                if meta_desc:
                    meta_content = await meta_desc.get_attribute("content")
                    if meta_content:
                        match = re.search(r'([\d,\.]+[KkMm]?)\s*[Ff]ollower', meta_content)
                        if match:
                            data["followers"] = match.group(1)
            except:
                pass

        await human_pause(2.0, 4.0)

    except Exception as e:
        print(f"      {Symbol.ERROR}  Instagram scrape failed: {str(e)[:60]}")

    return data


# ─────────────────────────────────────────────────────────────────────────────
# FACEBOOK SCRAPER
# ─────────────────────────────────────────────────────────────────────────────
async def scrape_facebook(page, business_name: str, city: str, links: list = None) -> dict:
    data = {
        "found": False, "url": None, "about": None,
        "email": None, "phone": None, "whatsapp": None,
        "likes": None
    }

    try:
        if not links:
            links = await google_search(page, f'"{business_name}" {city} Nigeria facebook')

        fb_links = [
            l for l in links
            if 'facebook.com' in l
            and '/posts/' not in l
            and '/photos/' not in l
            and '/events/' not in l
            and '/videos/' not in l
            and '/reel' not in l
            and '/watch' not in l
            and '/groups/' not in l
            and '/stories/' not in l
            and '/marketplace/' not in l
        ]

        # Prefer pages over personal profiles
        page_links = [l for l in fb_links if '/p/' in l or 'pages' in l.lower()]
        profile_links = [l for l in fb_links if l not in page_links]
        fb_links = page_links + profile_links

        if not fb_links:
            return data

        url = fb_links[0]
        print(f"      {Symbol.FACEBOOK} Facebook: {url}")

        await page.goto(url, timeout=20000, wait_until="domcontentloaded")
        await handle_consent(page)

        # Facebook needs time to render
        await human_pause(5.0, 8.0)

        # Try to dismiss any popups
        try:
            close_btn = await page.query_selector('[aria-label="Close"]')
            if close_btn:
                await close_btn.click()
                await human_pause(1.0, 2.0)
        except:
            pass

        # Wait for page content
        try:
            await page.wait_for_selector('div[role="main"]', timeout=8000)
        except:
            pass

        await human_pause(3.0, 5.0)
        await human_scroll(page, scrolls=4)
        await human_pause(2.0, 4.0)

        text = await page.evaluate("() => document.body.innerText")
        html = await page.evaluate("() => document.body.innerHTML")

        # Facebook often shows login wall — extract from meta tags too
        if len(text) < 500:
            print(f"      {Symbol.ERROR}  Facebook limited content — extracting from meta tags")
            meta_text = await page.evaluate("""
                () => {
                    const metas = document.querySelectorAll('meta');
                    let text = '';
                    metas.forEach(m => {
                        const content = m.getAttribute('content') || '';
                        const property = m.getAttribute('property') || '';
                        if (content) text += property + ': ' + content + ' ';
                    });
                    return text;
                }
            """)
            text = (text + " " + meta_text).strip()

        contacts = extract_contacts(text + " " + html)
        data["found"] = True
        data["url"] = url
        data["about"] = text[:800]
        data["email"] = contacts["emails"][0] if contacts["emails"] else None
        data["phone"] = contacts["phones"][0] if contacts["phones"] else None
        data["whatsapp"] = contacts["whatsapp_links"][0] if contacts["whatsapp_links"] else None

        # Likes/followers
        likes_match = re.search(r'([\d,\.]+[KkMm]?)\s*(?:people\s+)?like', text, re.I)
        if likes_match:
            data["likes"] = likes_match.group(1)

        await human_pause(2.0, 4.0)

    except Exception as e:
        print(f"      {Symbol.ERROR}  Facebook scrape failed: {str(e)[:60]}")

    return data


# ─────────────────────────────────────────────────────────────────────────────
# GOOGLE REVIEWS SENTIMENT ANALYSER
# ─────────────────────────────────────────────────────────────────────────────
async def scrape_google_reviews(page, business_name: str, city: str, links: list = None) -> dict:
    data = {
        "reviews_text": "",
        "praises": [],
        "complaints": [],
        "sentiment_summary": None,
        "active": False,
        "responds_to_reviews": False
    }

    try:
        # Go directly to Google Maps — no extra Google search needed
        maps_url = f"https://www.google.com/maps/search/{business_name.replace(' ', '+')}+{city}+Nigeria"
        
        # Check if we already have a maps link in our discovery links
        if links:
            maps_from_discovery = next((l for l in links if 'google.com/maps' in l), None)
            if maps_from_discovery:
                maps_url = maps_from_discovery

        await page.goto(maps_url, timeout=15000, wait_until="domcontentloaded")
        await handle_consent(page)
        await human_pause(3.0, 5.0)
        await human_scroll(page, scrolls=4)

        text = await page.evaluate("() => document.body.innerText")
        data["reviews_text"] = text[:5000]
        data["active"] = len(text) > 500

        # Ask AI to analyse sentiment
        if text.strip():
            prompt = f"""
Analyse this Google Maps page text for "{business_name}" in {city}, Nigeria.

Text:
{text[:4000]}

Extract and return ONLY valid JSON:
{{
  "top_praises": ["what customers love - 3 specific phrases"],
  "top_complaints": ["what customers wish was better - 3 specific phrases"],
  "sentiment_summary": "2 sentence human summary of overall reputation",
  "is_active_business": true or false,
  "responds_to_reviews": true or false,
  "estimated_years_active": "rough estimate or null"
}}
"""
            response = get_ai_response(prompt, max_tokens=400)
            parsed = safe_json(response)
            if parsed:
                data["praises"] = parsed.get("top_praises", [])
                data["complaints"] = parsed.get("top_complaints", [])
                data["sentiment_summary"] = parsed.get("sentiment_summary")
                data["active"] = parsed.get("is_active_business", True)
                data["responds_to_reviews"] = parsed.get("responds_to_reviews", False)

        await human_pause(2.0, 4.0)

    except Exception as e:
        print(f"      {Symbol.ERROR}  Reviews scrape failed: {str(e)[:60]}")

    return data


# ─────────────────────────────────────────────────────────────────────────────
# COMPETITOR FINDER
# ─────────────────────────────────────────────────────────────────────────────
async def find_competitors(page, business_name: str, category: str, city: str, links: list = None) -> list:
    """Use AI to infer competitors from what we already know — no extra Google search"""
    competitors = []
    try:
        print(f"      — Inferring competitors from existing data...")
        prompt = f"""
Based on your knowledge, name 3 likely direct competitors of "{business_name}" 
which is a {category} business in {city}, Nigeria.

Return ONLY valid JSON:
{{
  "competitors": [
    {{
      "name": "competitor name",
      "has_website": true or false,
      "has_online_booking": true or false,
      "notes": "one line about their likely digital presence"
    }}
  ]
}}
"""
        response = get_ai_response(prompt, max_tokens=300)
        parsed = safe_json(response)
        if parsed:
            competitors = [
                c for c in parsed.get("competitors", [])
                if c.get("name", "").lower() != business_name.lower()
            ][:3]
    except Exception as e:
        print(f"      {Symbol.ERROR}  Competitor inference failed: {str(e)[:60]}")
    return competitors


# ─────────────────────────────────────────────────────────────────────────────
# OWNER HUNTER — LinkedIn + Google
# ─────────────────────────────────────────────────────────────────────────────
async def hunt_owner(page, business_name: str, city: str, links: list = None) -> dict:
    info = {"owner_name": None, "email": None, "whatsapp": None,
            "owner_source": None, "email_source": None}

    all_text = ""

    # Only visit pages we already found — no new Google searches
    if links:
        linkedin_links = [l for l in links if 'linkedin.com' in l][:1]
        other_links = [l for l in links if 'linkedin.com' not in l
                      and 'instagram.com' not in l
                      and 'facebook.com' not in l][:2]
        
        for link in linkedin_links + other_links:
            try:
                print(f"      {Symbol.PAGE} Reading: {link[:70]}")
                nav = await safe_goto(page, link, timeout=12000)
                if nav["success"]:
                    all_text += " " + nav["text"][:2000]
                await human_pause(2.0, 4.0)
            except:
                continue

    if all_text.strip():
        contacts = extract_contacts(all_text)
        if contacts["emails"]:
            info["email"] = contacts["emails"][0]
            info["email_source"] = "web search"

        prompt = f"""
From this text about "{business_name}" in {city}, Nigeria, extract:
- Full name of the owner, founder, CEO, or manager
- Their email address
- Their WhatsApp or phone number

Text:
{all_text[:4000]}

Return ONLY valid JSON:
{{
  "owner_name": "full name or null",
  "owner_title": "their role or null",
  "email": "email or null",
  "whatsapp": "phone or null",
  "confidence": "high, medium, or low"
}}
"""
        try:
            response = get_ai_response(prompt, max_tokens=250)
            parsed = safe_json(response)
            if parsed:
                if parsed.get("owner_name") and parsed.get("owner_name") != "null":
                    info["owner_name"] = parsed["owner_name"]
                    info["owner_source"] = f"web ({parsed.get('confidence','?')} confidence)"
                if parsed.get("email") and parsed.get("email") != "null":
                    info["email"] = parsed["email"]
                if parsed.get("whatsapp") and parsed.get("whatsapp") != "null":
                    info["whatsapp"] = parsed["whatsapp"]
        except Exception as e:
            print(f"      —   AI owner extraction failed: {e}")

    return info


# ─────────────────────────────────────────────────────────────────────────────
# BUSINESS PERSONALITY PROFILER
# ─────────────────────────────────────────────────────────────────────────────
def profile_business_personality(lead: dict) -> dict:
    site_data = lead.get("website_details") or {}
    ig_data = lead.get("instagram") or {}
    fb_data = lead.get("facebook") or {}
    reviews = lead.get("reviews_analysis") or lead.get("reviews") or {}

    all_text = " ".join(filter(None, [
        site_data.get("description", ""),
        site_data.get("raw_text", "")[:1000],
        ig_data.get("bio", ""),
        fb_data.get("about", ""),
        (reviews or {}).get("sentiment_summary", ""),
    ]))

    city = lead.get("city", "Nigeria")
    prompt = f"""Analyse this business profile for "{lead['name']}" in {city}, Nigeria.
Available info: {all_text[:2500]}
Customer praises: {reviews.get('praises', [])}
Customer complaints: {reviews.get('complaints', [])}
Return ONLY valid JSON:
{{
  "vibe": "luxury, casual, family, corporate, street, cultural, modern, or traditional",
  "tone_to_use": "formal, semi-formal, or casual-warm",
  "key_pride": "what they seem most proud of in one sentence",
  "biggest_opportunity": "impactful digital gap they are missing",
  "compliment_hook": "genuine specific compliment to open with",
  "pain_hook": "specific pain point to solve"
}}"""
    try:
        response = get_ai_response(prompt, max_tokens=400)
        return safe_json(response)
    except:
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# TIMING INTELLIGENCE
# ─────────────────────────────────────────────────────────────────────────────
def get_contact_timing(business_type: str = "restaurant") -> dict:
    now = datetime.now()
    day = now.strftime("%A")
    month_day = now.strftime("%m-%d")
    hour = now.hour

    # Check Nigerian events
    upcoming_event = NIGERIAN_EVENTS.get(month_day)

    # Best contact days and times
    bad_days = ["Friday", "Saturday", "Sunday"]
    best_days = ["Tuesday", "Wednesday", "Thursday"]
    is_good_day = day not in bad_days
    is_good_time = 9 <= hour <= 12 or 14 <= hour <= 16

    # Seasonal opportunity
    month = now.month
    if month == 12:
        season_note = "December — peak spending season, perfect time to pitch"
    elif month in [3, 4]:
        season_note = "Easter season — restaurants especially busy, great time to reach out"
    elif month in [6, 7]:
        season_note = "Mid-year — good time for businesses to invest in growth"
    else:
        season_note = None

    return {
        "current_day": day,
        "is_good_day": is_good_day,
        "is_good_time": is_good_time,
        "best_send_time": "Tuesday–Thursday, 9am–12pm WAT",
        "upcoming_event": upcoming_event,
        "season_note": season_note,
        "recommendation": (
            "Send now — good timing" if is_good_day and is_good_time
            else "Queue for Tuesday–Thursday morning"
        )
    }


# ─────────────────────────────────────────────────────────────────────────────
# NURTURE PLAN GENERATOR
# ─────────────────────────────────────────────────────────────────────────────
def generate_nurture_plan(lead: dict, personality: dict) -> dict:
    prompt = f"""
Create a 90-day nurture plan for a business that said "not right now" to our digital services.

Business: {lead['name']}
Vibe: {personality.get('vibe', 'unknown')}
Key pride: {personality.get('key_pride', 'unknown')}
Biggest opportunity: {personality.get('biggest_opportunity', 'unknown')}

Create a plan with exactly 4 touchpoints over 90 days.
Each touchpoint should offer genuine value with zero pressure.

Return ONLY valid JSON:
{{
  "touchpoints": [
    {{
      "day": 14,
      "type": "email or whatsapp",
      "subject": "subject line",
      "message_preview": "first 2 sentences of the message",
      "value_offered": "what free value we give"
    }}
  ],
  "referral_message": "a warm 1-sentence referral ask with zero pressure"
}}
"""
    try:
        response = get_ai_response(prompt, max_tokens=500)
        return safe_json(response)
    except:
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# PITCH ANGLE GENERATOR
# ─────────────────────────────────────────────────────────────────────────────
def generate_pitch_angle(lead: dict, personality: dict) -> str:
    reviews = lead.get("reviews_analysis") or lead.get("reviews") or {}
    ig = lead.get("instagram") or {}
    fb = lead.get("facebook") or {}
    competitors = lead.get("competitors") or []

    competitor_context = ""
    better_competitors = [c for c in competitors if c.get("has_website") or c.get("has_online_booking")]
    if better_competitors:
        competitor_context = f"Competitor with better digital presence: {better_competitors[0]['name']}"

    city = lead.get("city", "Nigeria")
    prompt = f"""Write a 3-sentence personalized first-contact pitch for "{lead['name']}" in {city}, Nigeria.
Owner: {lead.get('owner_name', 'owner')}. Vibe: {personality.get('vibe')}.
Compliment: {personality.get('compliment_hook')}. Pain: {personality.get('pain_hook')}.
Missing: {personality.get('biggest_opportunity')}.
Sentence 1: Warm genuine compliment.
Sentence 2: Specific gap or opportunity noticed.
Sentence 3: Soft curious question.
No marketing jargon like "optimize" or "leverage"."""
    try:
        return get_ai_response(prompt, max_tokens=200)
    except:
        return "We noticed some great things about your business and a few opportunities worth exploring."


# ─────────────────────────────────────────────────────────────────────────────
# CONFIDENCE SCORER
# ─────────────────────────────────────────────────────────────────────────────
def score_confidence(value, sources: list) -> str:
    if not value:
        return "none"
    if len(sources) >= 2:
        return "high"
    if len(sources) == 1:
        return "medium"
    return "low"


# ─────────────────────────────────────────────────────────────────────────────
# MAIN ENRICHER
# ─────────────────────────────────────────────────────────────────────────────
async def enrich_all_leads(leads_file: str = "results/leads/leads.json"):
    with open(leads_file, "r", encoding="utf-8") as f:
        all_leads = json.load(f)

    # Load any previously enriched leads so we can merge, not overwrite
    enriched_file = "results/leads/enriched_leads.json"
    existing_enriched = {}
    if os.path.exists(enriched_file):
        try:
            with open(enriched_file, "r", encoding="utf-8") as f:
                prev = json.load(f)
            if isinstance(prev, list):
                existing_enriched = {l["name"]: l for l in prev if "name" in l}
        except Exception:
            pass

    # Only enrich leads that haven't been enriched yet
    leads = [l for l in all_leads if not l.get("enriched") and l.get("name") not in existing_enriched]

    if not leads:
        print(f"{Symbol.CHECK} All leads already enriched — nothing to do")
        return

    print(f"{Symbol.LIST} {len(all_leads)} total leads — enriching {len(leads)} new ones today")
    print("=" * 65)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="en-GB",
            timezone_id="Africa/Lagos"
        )
        page = await context.new_page()
        enriched_leads = []

        for i, lead in enumerate(leads, 1):
            name = lead["name"]
            category = lead.get("category", "restaurant")
            city = lead.get("city", "Nigeria")

            print(f"\n{'='*65}")
            print(f"{Symbol.LEAD} [{i}/{len(leads)}] {name} ({city})")
            print(f"{'='*65}")

            enriched = lead.copy()

            # ── DISCOVERY STEP
            discovery_links = await collect_discovery_links(page, name, city)
            google_blocked = not discovery_links

            if google_blocked:
                print(f"   — Google blocked — working with direct sources only")
                print(f"   — Will still try Maps, Instagram, Facebook directly")
            
            await human_pause(8.0, 15.0)

            # ── 1. Official website
            print(f"\n   {Symbol.WORLD}  STEP 1 — Finding official website...")
            website_result = await find_official_website(page, name, city, discovery_links)
            enriched["official_website"] = website_result

            # ── 2. Deep scrape website
            if website_result["url"] and website_result["score"] >= 5:
                print(f"\n   {Symbol.PAGE} STEP 2 — Deep scraping website...")
                try:
                    site_data = await deep_scrape_website(page, website_result["url"])
                    enriched["website_details"] = site_data
                    print(f"      {Symbol.EMAIL} Emails:   {site_data['emails'] or 'None'}")
                    print(f"      {Symbol.PHONE} Phones:   {site_data['phones'] or 'None'}")
                    print(f"      {Symbol.WHATSAPP} WhatsApp: {site_data['whatsapp_links'] or 'None'}")
                    print(f"      {Symbol.SOCIAL} Socials:  {list(site_data['socials'].keys()) or 'None'}")
                except Exception as e:
                    print(f"      — Website scrape failed: {str(e)[:60]} — continuing")
                    enriched["website_details"] = {}
            else:
                enriched["website_details"] = {}
                print(f"      — No official website — skipping scrape")

            await human_pause(3.0, 5.0)

            # ── 3. Instagram
            print(f"\n   {Symbol.INSTAGRAM} STEP 3 — Searching Instagram...")
            ig_data = await scrape_instagram(page, name, city, discovery_links)
            enriched["instagram"] = ig_data
            if ig_data["found"]:
                print(f"      {Symbol.CHECK} Found: {ig_data['url']}")
                print(f"      {Symbol.CHECK} Followers: {ig_data['followers'] or 'unknown'}")
                print(f"      {Symbol.EMAIL} Email: {ig_data['email'] or 'None'}")
            else:
                print(f"      — Not found on Instagram")

            await human_pause(3.0, 5.0)

            # ── 4. Facebook
            print(f"\n   {Symbol.FACEBOOK} STEP 4 — Searching Facebook...")
            fb_data = await scrape_facebook(page, name, city, discovery_links)
            enriched["facebook"] = fb_data
            if fb_data["found"]:
                print(f"      {Symbol.CHECK} Found: {fb_data['url']}")
                print(f"      {Symbol.CHECK} Likes: {fb_data['likes'] or 'unknown'}")
                print(f"      {Symbol.EMAIL} Email: {fb_data['email'] or 'None'}")
            else:
                print(f"      — Not found on Facebook")

            await human_pause(3.0, 5.0)

            # ── 5. Reviews & Sentiment
            print(f"\n   — STEP 5 — Analysing Google reviews...")
            reviews_data = await scrape_google_reviews(page, name, city, discovery_links)
            enriched["reviews_analysis"] = reviews_data
            if reviews_data["praises"]:
                print(f"      {Symbol.CHECK} Praises:    {reviews_data['praises'][:2]}")
            if reviews_data["complaints"]:
                print(f"      — Complaints: {reviews_data['complaints'][:2]}")

            await human_pause(3.0, 5.0)

            # ── 6. Competitors
            print(f"\n   {Symbol.PRIDE} STEP 6 — Finding competitors...")
            competitors = await find_competitors(page, name, category, city, discovery_links)
            enriched["competitors"] = competitors
            for c in competitors:
                print(f"      vs {c.get('name')} — website: {c.get('has_website')}, booking: {c.get('has_online_booking')}")

            await human_pause(3.0, 5.0)

            # ── 7. Owner hunt
            print(f"\n   {Symbol.PAGE} STEP 7 — Hunting owner info...")
            owner_data = await hunt_owner(page, name, city, discovery_links)
            enriched["owner_name"] = owner_data.get("owner_name")
            enriched["owner_source"] = owner_data.get("owner_source")
            print(f"      {Symbol.PAGE} Owner: {enriched['owner_name'] or 'Not found'}")

            # ── 8. Merge all contact data with confidence scoring
            # Pull aggregator contacts found during website search
            agg_contacts = enriched.get("official_website", {}).get("aggregator_contacts", {})

            all_emails = list(set(filter(None, [
                owner_data.get("email"),
                ig_data.get("email"),
                fb_data.get("email"),
                *(enriched.get("website_details", {}).get("emails", [])),
                *(agg_contacts.get("emails", [])),
            ])))
            all_phones = list(set(filter(None, [
                owner_data.get("whatsapp"),
                ig_data.get("phone"),
                ig_data.get("whatsapp"),
                fb_data.get("phone"),
                fb_data.get("whatsapp"),
                *(enriched.get("website_details", {}).get("phones", [])),
                *(enriched.get("website_details", {}).get("whatsapp_links", [])),
                *(agg_contacts.get("phones", [])),
                *(agg_contacts.get("whatsapp_links", [])),
            ])))

            # Filter emails for relevance before storing
            if all_emails:
                relevant_emails = [
                    e for e in all_emails
                    if not any(bad in e.lower() for bad in [
                        'fidelitybank', 'gtbank', 'zenithbank', 'accessbank',
                        'platgroupng', 'directory.org', 'ijefm', 'rscn',
                        'budgit', 'pencom', 'ncc.gov', 'example.com',
                        'halalfoodle', 'placejoys', 'mindtrip',
                        'your@email', 'test@', 'admin@ijefm',
                        'board@ijefm', 'info@platgroup', 'nmityasfood',
                        'mtn.ng', 'glo.com', 'airtel', 'researchgate',
                        'editor@', 'support@', 'admin@', 'info@africabiz',
                    ])
                ]
                all_emails = relevant_emails if relevant_emails else []

            enriched["contact_email"] = all_emails[0] if all_emails else None
            enriched["all_emails"] = all_emails
            enriched["contact_whatsapp"] = all_phones[0] if all_phones else None
            enriched["all_phones"] = all_phones

            # Confidence scores
            email_sources = [s for s in [
                "website" if enriched.get("website_details", {}).get("emails") else None,
                "instagram" if ig_data.get("email") else None,
                "facebook" if fb_data.get("email") else None,
                "web search" if owner_data.get("email") else None,
            ] if s]
            enriched["email_confidence"] = score_confidence(enriched["contact_email"], email_sources)
            enriched["email_sources"] = email_sources

            print(f"      {Symbol.EMAIL} Email ({enriched['email_confidence']}): {enriched['contact_email'] or 'Not found'}")
            print(f"      {Symbol.WHATSAPP} WhatsApp: {enriched['contact_whatsapp'] or 'Not found'}")

            await human_pause(2.0, 4.0)

            # ── 9. Business personality profile
            print(f"\n   {Symbol.AI} STEP 8 — Building personality profile...")
            personality = profile_business_personality(enriched)
            enriched["personality"] = personality
            if personality:
                print(f"      {Symbol.VIBE} Vibe:        {personality.get('vibe', '?')}")
                print(f"      {Symbol.TONE}  Tone:        {personality.get('tone_to_use', '?')}")
                print(f"      — Key pride:   {personality.get('key_pride', '?')[:60]}")
                print(f"      {Symbol.VIBE} Opportunity: {personality.get('biggest_opportunity', '?')[:60]}")

            # ── 10. Timing intelligence
            timing = get_contact_timing(category)
            enriched["contact_timing"] = timing
            print(f"\n   {Symbol.TIME} Best send time: {timing['recommendation']}")
            if timing.get("season_note"):
                print(f"   {Symbol.TIME}  {timing['season_note']}")

            # ── 11. Pitch angle
            print(f"\n   {Symbol.TARGET} STEP 9 — Crafting personalized pitch...")
            pitch = generate_pitch_angle(enriched, personality)
            enriched["pitch_angle"] = pitch
            print(f"   {Symbol.PITCH} {pitch}")

            # ── 12. Nurture plan
            print(f"\n   {Symbol.NURTURE} STEP 10 — Building nurture plan...")
            nurture = generate_nurture_plan(enriched, personality)
            enriched["nurture_plan"] = nurture
            if nurture.get("referral_message"):
                print(f"   {Symbol.REFERRAL} Referral: {nurture['referral_message'][:80]}...")

            # ── Business health score (10-point scale)
            health_score = sum([
                bool(enriched.get("official_website", {}).get("url")),
                bool(enriched.get("contact_email")),
                bool(enriched.get("contact_whatsapp")),
                bool(enriched.get("owner_name")),
                bool(enriched.get("instagram", {}).get("found")),
                bool(enriched.get("facebook", {}).get("found")),
                bool(enriched.get("reviews_analysis", {}).get("praises")),
                enriched["email_confidence"] == "high",
                bool(enriched.get("personality")),
                bool(enriched.get("pitch_angle"))
            ])
            enriched["enrichment_score"] = f"{health_score}/10"

            enriched["enriched"] = True
            enriched["enriched_date"] = datetime.now().strftime("%Y-%m-%d")

            enriched_leads.append(enriched)
            print(f"\n   {Symbol.CHECK} {name} complete — enrichment score: {health_score}/8")

            # Short human rest between leads
            rest = random.uniform(8.0, 15.0)
            print(f"   {Symbol.WAIT} Resting {rest:.0f}s before next lead...\n")
            await asyncio.sleep(rest)

        await browser.close()

    # ── Merge newly enriched leads with any previously enriched ones ──
    # Start from existing, overwrite with newer enriched data
    merged_enriched = dict(existing_enriched)  # copy of previous results
    for l in enriched_leads:
        if 'name' in l:
            merged_enriched[l['name']] = l  # new data wins
    all_enriched = list(merged_enriched.values())

    # ── Filter out uncontactable leads (no email AND no whatsapp contact) ──
    filtered_enriched = []
    removed_names = set()
    for l in all_enriched:
        has_email = bool(l.get("contact_email")) or bool(l.get("all_emails"))
        has_phone = bool(l.get("contact_whatsapp")) or bool(l.get("all_phones")) or bool(l.get("phone"))
        if not has_email and not has_phone:
            removed_names.add(l["name"])
            print(f"   {Symbol.WARN} Removing uncontactable lead (no email & no phone/whatsapp): {l['name']}")
        else:
            filtered_enriched.append(l)
    all_enriched = filtered_enriched

    # Save full results
    os.makedirs("results/leads", exist_ok=True)
    with open("results/leads/enriched_leads.json", "w", encoding="utf-8") as f:
        json.dump(all_enriched, f, indent=2, ensure_ascii=False)
    print(f"   {Symbol.CHECK} Saved {len(all_enriched)} total enriched leads to enriched_leads.json (removed {len(removed_names)} uncontactable leads)")

    # Write enriched:true back to leads.json so re-runs skip them, but filter out removed ones
    enriched_names = {l['name'] for l in all_enriched}
    filtered_all_leads = []
    for l in all_leads:
        if l.get('name') in removed_names:
            continue
        if l.get('name') in enriched_names:
            l['enriched'] = True
        filtered_all_leads.append(l)

    with open(leads_file, "w", encoding="utf-8") as f:
        json.dump(filtered_all_leads, f, indent=2, ensure_ascii=False)
    print(f"   {Symbol.CHECK} Updated leads.json — {len(enriched_names)} leads marked as enriched")

    # Save clean contact sheet
    contact_sheet = []
    for l in all_enriched:
        contact_sheet.append({
            "name": l["name"],
            "owner": l.get("owner_name"),
            "email": l.get("contact_email"),
            "email_confidence": l.get("email_confidence"),
            "whatsapp": l.get("contact_whatsapp"),
            "website": l.get("official_website", {}).get("url"),
            "website_type": l.get("official_website", {}).get("type"),
            "instagram": l.get("instagram", {}).get("url"),
            "facebook": l.get("facebook", {}).get("url"),
            "vibe": l.get("personality", {}).get("vibe"),
            "biggest_opportunity": l.get("personality", {}).get("biggest_opportunity"),
            "pitch_angle": l.get("pitch_angle"),
            "best_send_time": l.get("contact_timing", {}).get("recommendation"),
            "enrichment_score": l.get("enrichment_score"),
        })

    os.makedirs("results/audits", exist_ok=True)
    with open("results/audits/contact_sheet.json", "w", encoding="utf-8") as f:
        json.dump(contact_sheet, f, indent=2, ensure_ascii=False)

    # Summary
    print(f"\n" + "=" * 65)
    print(f"{Symbol.LEAD} DEEP ENRICHMENT COMPLETE")
    print("=" * 65)
    with_email = [l for l in all_enriched if l.get("contact_email")]
    with_owner = [l for l in all_enriched if l.get("owner_name")]
    with_ig = [l for l in all_enriched if l.get("instagram", {}).get("found")]
    with_fb = [l for l in all_enriched if l.get("facebook", {}).get("found")]
    high_conf = [l for l in all_enriched if l.get("email_confidence") == "high"]

    print(f"Total leads enriched:        {len(all_enriched)}")
    print(f"Emails found:                {len(with_email)}")
    print(f"High-confidence emails:      {len(high_conf)}")
    print(f"Owner names found:           {len(with_owner)}")
    print(f"Instagram profiles found:    {len(with_ig)}")
    print(f"Facebook pages found:        {len(with_fb)}")
    print(f"\nFiles saved:")
    print(f"  results/leads/enriched_leads.json  — full data per lead")
    print(f"  results/audits/contact_sheet.json  — clean contact summary")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(enrich_all_leads())
