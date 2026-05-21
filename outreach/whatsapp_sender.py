import asyncio
import json
import os
import re
import random
import time
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()
import sys
import pathlib
# Ensure project root is on sys.path so 'from outreach.x import ...' always works
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding='utf-8')

os.makedirs("results/sent/whatsapp", exist_ok=True)
os.makedirs("results/logs", exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# INVALID NUMBER CACHE & LANDLINE PRE-VALIDATION
# ─────────────────────────────────────────────────────────────────────────────
INVALID_CACHE_PATH = "results/logs/invalid_wa_numbers.json"

def load_invalid_cache() -> set:
    if os.path.exists(INVALID_CACHE_PATH):
        try:
            with open(INVALID_CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return set(data.get("numbers", []))
        except Exception:
            pass
    return set()

def save_invalid_cache(cache: set):
    os.makedirs(os.path.dirname(INVALID_CACHE_PATH), exist_ok=True)
    with open(INVALID_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump({"numbers": list(cache), "updated": datetime.now().isoformat()}, f, indent=2)

# Nigerian landline prefixes (area codes that are NOT mobile)
NIGERIAN_LANDLINE_PREFIXES = {
    '01', '02', '030', '031', '032', '033', '034', '035', '036', '037', '038', '039',
    '040', '041', '042', '043', '044', '045', '046', '047', '048', '049',
    '050', '051', '052', '053', '054', '055', '056', '057', '058', '059',
    '060', '061', '062', '063', '064', '065', '066', '067', '068', '069',
    '070',  # Note: 070 is actually mobile in Nigeria, but 0700 is a special line
    '071', '072', '073', '074', '075', '076', '077', '078', '079',
    '082', '083', '084', '085', '086', '087', '088', '089',
}

# Nigerian MOBILE prefixes (these are valid WhatsApp candidates)
NIGERIAN_MOBILE_PREFIXES = {
    '0703', '0704', '0705', '0706', '0707', '0708',
    '0802', '0803', '0804', '0805', '0806', '0807', '0808', '0809', '0810', '0811',
    '0812', '0813', '0814', '0815', '0816', '0817', '0818', '0819',
    '0901', '0902', '0903', '0904', '0905', '0906', '0907', '0908', '0909', '0910',
    '0911', '0912', '0913', '0914', '0915', '0916',
}

def is_likely_landline(number: str) -> bool:
    """Check if a Nigerian number is likely a landline (not WhatsApp-capable)."""
    if not number:
        return True
    
    clean = re.sub(r'[^\d]', '', str(number))
    
    # Convert international to local format for checking
    local = clean
    if clean.startswith('234'):
        local = '0' + clean[3:]
    
    # Too short to be a valid phone number
    if len(local) < 7:
        return True
    
    # Check if it matches a known mobile prefix (4-digit check)
    prefix4 = local[:4]
    if prefix4 in NIGERIAN_MOBILE_PREFIXES:
        return False  # It's a mobile number
    
    # Check if it starts with a known landline prefix
    for lp in sorted(NIGERIAN_LANDLINE_PREFIXES, key=len, reverse=True):
        if local.startswith(lp) and prefix4 not in NIGERIAN_MOBILE_PREFIXES:
            return True
    
    # If we can't determine, assume it's mobile (don't block)
    return False

def should_skip_number(number: str, invalid_cache: set) -> tuple:
    """Check if a number should be skipped. Returns (should_skip, reason)."""
    formatted = format_wa_number(number)
    if not formatted:
        return True, "Invalid phone number format"
    
    if formatted in invalid_cache:
        return True, "Previously failed — cached as invalid"
    
    if is_likely_landline(number):
        return True, "Likely a landline number"
    
    return False, None


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
def load_config() -> dict:
    with open("ceo_config.json", "r", encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────────────
# SEND LOG
# ─────────────────────────────────────────────────────────────────────────────
def load_wa_log() -> dict:
    log_path = "results/logs/whatsapp_log.json"
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"messages": [], "stats": {"sent": 0, "failed": 0, "skipped": 0}}


def save_wa_log(log: dict):
    with open("results/logs/whatsapp_log.json", "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def already_sent_wa(log: dict, number: str, business: str, msg_key: str) -> bool:
    for entry in log["messages"]:
        if (entry.get("number") == number and
                entry.get("business") == business and
                entry.get("msg_key") == msg_key):
            return True
    return False


def get_todays_wa_count(log: dict) -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    return sum(
        1 for e in log["messages"]
        if e.get("date", "").startswith(today) and e.get("success")
    )


# ─────────────────────────────────────────────────────────────────────────────
# NUMBER FORMATTER
# ─────────────────────────────────────────────────────────────────────────────
def format_wa_number(number: str) -> str:
    """Format any Nigerian number to international WhatsApp format"""
    if not number:
        return None

    # Strip everything except digits and +
    clean = re.sub(r'[^\d+]', '', str(number))

    # Handle wa.me links
    if 'wa.me' in str(number):
        match = re.search(r'wa\.me/(\d+)', str(number))
        if match:
            clean = match.group(1)

    # Remove leading +
    clean = clean.lstrip('+')

    # Drop leading 0 if country code is present (e.g. 2340819...)
    if clean.startswith('2340'):
        clean = '234' + clean[4:]

    # Nigerian number conversions
    if clean.startswith('234'):
        return '+' + clean
    elif clean.startswith('0') and len(clean) == 11:
        return '+234' + clean[1:]
    elif len(clean) == 10 and clean[0] in '789':
        return '+234' + clean
    elif clean.startswith('234') and len(clean) >= 13:
        return '+' + clean

    return '+' + clean if clean else None


# ─────────────────────────────────────────────────────────────────────────────
# HUMAN BEHAVIOUR
# ─────────────────────────────────────────────────────────────────────────────
async def human_pause(min_s: float = 2.0, max_s: float = 5.0):
    await asyncio.sleep(random.uniform(min_s, max_s))


async def human_type(element, text: str):
    """Type like a human — character by character with variable speed"""
    for char in text:
        await element.type(char)
        await asyncio.sleep(random.uniform(0.03, 0.12))
    await human_pause(0.5, 1.5)


async def handle_consent(page):
    for sel in [
        'button[aria-label="Accept all"]',
        'button:has-text("Accept all")',
        'button:has-text("I agree")',
        'button:has-text("Accept")',
    ]:
        try:
            btn = await page.query_selector(sel)
            if btn:
                await asyncio.sleep(random.uniform(0.8, 1.8))
                await btn.click()
                await asyncio.sleep(random.uniform(1.0, 2.0))
                return True
        except:
            continue
    return False


# ─────────────────────────────────────────────────────────────────────────────
# WHATSAPP WEB SESSION MANAGER
# ─────────────────────────────────────────────────────────────────────────────
async def ensure_wa_session(page) -> bool:
    """
    Make sure WhatsApp Web is logged in.
    Waits for QR scan if needed.
    Returns True if session is active.
    """
    print("   📱 Loading WhatsApp Web...")
    await page.goto("https://web.whatsapp.com", timeout=30000, wait_until="domcontentloaded")
    await human_pause(3.0, 5.0)

    # Wait up to 180 seconds for either QR code or chat list
    for attempt in range(180):
        await asyncio.sleep(1)

        # Check if logged in
        chat_list = None
        for sel in [
            'div[aria-label="Chat list"]',
            'div[data-testid="chat-list"]',
            'div[contenteditable="true"]',
            'span[data-icon="chat"]',
            '#pane-side'
        ]:
            try:
                chat_list = await page.query_selector(sel)
                if chat_list:
                    break
            except:
                continue

        if chat_list:
            print("   ✅ WhatsApp Web session active")
            return True

        # Check for QR code
        qr_code = None
        for sel in [
            'canvas[aria-label="Scan me!"]',
            'div[data-testid="qrcode"]',
            'canvas'
        ]:
            try:
                qr_code = await page.query_selector(sel)
                if qr_code:
                    break
            except:
                continue

        if qr_code and attempt == 0:
            print("   📷 QR Code detected — please scan with your phone")
            print("   ⏳ Waiting up to 180 seconds for scan...")

        if attempt == 179:
            print("   ❌ WhatsApp Web login timeout")
            return False

    return False


# ─────────────────────────────────────────────────────────────────────────────
# SEND SINGLE WHATSAPP MESSAGE
# ─────────────────────────────────────────────────────────────────────────────
async def send_whatsapp_message(
    page,
    number: str,
    message: str,
    business_name: str
) -> dict:
    result = {
        "success": False,
        "number": number,
        "business": business_name,
        "error": None
    }

    try:
        # Format number
        formatted = format_wa_number(number)
        if not formatted:
            result["error"] = "Invalid phone number"
            return result

        # Remove + for URL
        number_clean = formatted.replace('+', '')

        print(f"   📤 Sending to {formatted}...")

        # Navigate to direct chat URL
        chat_url = f"https://web.whatsapp.com/send?phone={number_clean}"
        await page.goto(chat_url, timeout=20000, wait_until="domcontentloaded")
        await human_pause(4.0, 7.0)

        # Handle any consent popups
        await handle_consent(page)
        await human_pause(2.0, 4.0)

        # Wait for message input box
        input_selectors = [
            'div[aria-label="Type a message"]',
            'div[data-tab="10"]',
            'div[contenteditable="true"][data-tab="10"]',
            'footer div[contenteditable="true"]',
        ]

        msg_box = None
        for selector in input_selectors:
            try:
                await page.wait_for_selector(selector, timeout=10000)
                msg_box = await page.query_selector(selector)
                if msg_box:
                    break
            except:
                continue

        if not msg_box:
            # Check if number is invalid
            content = await page.content()
            is_invalid = "isn't on WhatsApp" in content or "is not on WhatsApp" in content or "isn't on whatsapp" in content or "is not on whatsapp" in content
            
            # Also fallback to modal checking
            if not is_invalid:
                modal = await page.query_selector('div[data-animate-modal-popup="true"]')
                if modal:
                    modal_text = await modal.text_content()
                    if modal_text and ("isn't" in modal_text or "not on" in modal_text):
                        is_invalid = True
            
            if is_invalid:
                result["error"] = "Phone number not on WhatsApp"
                print(f"   ⚠️  Detected 'number not on WhatsApp' popup.")
                # Try to click the OK button to dismiss it
                for sel in [
                    'div[role="button"]:has-text("OK")',
                    'button:has-text("OK")',
                    'div[role="button"]:has-text("Ok")',
                    'button:has-text("Ok")',
                    'div[data-animate-modal-popup="true"] button'
                ]:
                    try:
                        ok_btn = await page.query_selector(sel)
                        if ok_btn:
                            await ok_btn.click()
                            print("   Dismissed the invalid number modal.")
                            await human_pause(1.0, 2.0)
                            break
                    except:
                        continue
                return result

            result["error"] = "Could not find message input box"
            return result

        # Click the message box
        await msg_box.click()
        await human_pause(1.0, 2.0)

        # Type message like a human
        # Split long messages into chunks to avoid issues
        if len(message) > 500:
            chunks = [message[i:i+500] for i in range(0, len(message), 500)]
        else:
            chunks = [message]

        for chunk in chunks:
            await human_type(msg_box, chunk)
            await human_pause(0.5, 1.0)

        # Random pause before sending — like a human re-reading
        await human_pause(2.0, 5.0)

        # Send the message
        send_selectors = [
            'button[aria-label="Send"]',
            'span[data-icon="send"]',
            'button[data-tab="11"]',
        ]

        sent = False
        for selector in send_selectors:
            try:
                send_btn = await page.query_selector(selector)
                if send_btn:
                    await send_btn.click()
                    sent = True
                    break
            except:
                continue

        if not sent:
            # Try Enter key
            await msg_box.press("Enter")
            sent = True

        if sent:
            await human_pause(2.0, 4.0)

            # Verify message was sent by checking for tick marks
            verified = False
            for _ in range(5):  # Check up to 5 times over ~5 seconds
                await asyncio.sleep(1)
                # Look for message status indicators (single tick = sent, double tick = delivered)
                for tick_sel in [
                    'span[data-icon="msg-check"]',   # single tick
                    'span[data-icon="msg-dblcheck"]', # double tick
                    'span[aria-label=" Sent "]',
                    'span[aria-label=" Delivered "]',
                ]:
                    try:
                        tick = await page.query_selector(tick_sel)
                        if tick:
                            verified = True
                            break
                    except:
                        pass
                if verified:
                    break

            result["success"] = True
            if verified:
                print(f"   ✅ Message sent and verified with tick icon to {formatted}")
            else:
                print(f"   ⚠️ Message sent to {formatted} but tick icon verification timed out (assumed sent)")
        else:
            result["error"] = "Could not find send button"

    except Exception as e:
        result["error"] = str(e)[:100]
        print(f"   ❌ Failed: {result['error']}")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# DETERMINE NEXT MESSAGE IN SEQUENCE
# ─────────────────────────────────────────────────────────────────────────────
def get_next_wa_message(lead_name: str, log: dict, force: bool = False) -> tuple:
    """Returns (msg_key, message_text) or (None, None)"""
    safe_name = lead_name.replace(" ", "_").replace("/", "_").replace("&", "and")
    wa_file = f"results/messages/whatsapp/{safe_name}_whatsapp.json"

    if not os.path.exists(wa_file):
        return None, None

    with open(wa_file, "r", encoding="utf-8") as f:
        messages = json.load(f)

    # Load sequence for human review check
    seq_path = f"results/messages/sequences/{safe_name}_sequence.json"
    sequence = []
    if os.path.exists(seq_path):
        with open(seq_path, "r", encoding="utf-8") as f:
            sequence = json.load(f)
    wa_seq_items = [m for m in sequence if m.get("channel") == "whatsapp"]
    
    config = {}
    if os.path.exists("ceo_config.json"):
        with open("ceo_config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
    require_human = config.get("quality", {}).get("require_human_review", True)

    msg_order = ["wa_1", "wa_2", "wa_3"]
    min_days = {"wa_1": 0, "wa_2": 3, "wa_3": 7}

    for key in msg_order:
        if key not in messages:
            continue

        msg_data = messages[key]
        if not msg_data.get("message"):
            continue

        number = msg_data.get("to", "")
        if not number:
            continue

        formatted = format_wa_number(number)
        if not formatted:
            continue

        if already_sent_wa(log, formatted, lead_name, key):
            # Check how long ago
            continue

        # Check human approval if required
        if require_human and not force:
            wa_idx = int(key.split("_")[1]) - 1
            if wa_idx < len(wa_seq_items):
                status = wa_seq_items[wa_idx].get("status", "queued")
                if status != "approved":
                    return "skipped_awaiting_approval", f"Awaiting human approval (status is '{status}')"

        # Check days gap since last message
        last_sent = None
        for entry in reversed(log["messages"]):
            if entry.get("business") == lead_name and entry.get("success"):
                last_sent = entry.get("date")
                break

        if last_sent:
            last_dt = datetime.fromisoformat(last_sent)
            days_since = (datetime.now() - last_dt).days
            needed = min_days.get(key, 0)
            if days_since < needed:
                return "too_soon", f"Need {needed} days — only {days_since} passed"

        return key, msg_data

    return "complete", None


# ─────────────────────────────────────────────────────────────────────────────
# BATCH WHATSAPP SENDER — session-based: 2 per session, 30-60 min between sessions
# ─────────────────────────────────────────────────────────────────────────────
async def send_all_whatsapp(dry_run: bool = False, force: bool = False, ignore_timing: bool = False):
    config = load_config()
    daily_limit = config["outreach"]["daily_whatsapp_limit"]
    session_size = 2              # messages per session
    session_wait_min = 30 * 60   # 30 minutes in seconds
    session_wait_max = 60 * 60   # 60 minutes in seconds

    invalid_cache = load_invalid_cache()

    # Load leads
    enriched_file = "results/leads/enriched_leads.json"
    if not os.path.exists(enriched_file):
        print("❌ No enriched leads found")
        return

    with open(enriched_file, "r", encoding="utf-8") as f:
        leads = json.load(f)

    leads_with_wa = [
        l for l in leads
        if l.get("contact_whatsapp") or l.get("all_phones")
    ]

    print(f"\n💬 WHATSAPP SENDER")
    print(f"{'='*55}")
    print(f"Leads with WhatsApp:  {len(leads_with_wa)}")
    print(f"Daily limit:          {daily_limit}")
    print(f"Session size:         {session_size}")
    print(f"Session wait:         30-60 min")
    print(f"Dry run:              {dry_run}")
    print(f"{'='*55}\n")

    def _is_good_time():
        """Check timing using config. Returns (ok, reason)."""
        now = datetime.now()
        day = now.strftime("%A")
        hour = now.hour
        send_days = config["outreach"].get("send_days", ["Monday","Tuesday","Wednesday","Thursday","Friday"])
        send_start = config["outreach"].get("send_hours", {}).get("start", 9)
        send_end = config["outreach"].get("send_hours", {}).get("end", 18)
        if day not in send_days:
            return False, f"Today is {day} — not a send day"
        if not (send_start <= hour <= send_end):
            return False, f"Hour {hour}:00 outside send window ({send_start}:00-{send_end}:00)"
        return True, "OK"

    # Initial timing check
    if not force and not ignore_timing and not dry_run:
        ok, reason = _is_good_time()
        if not ok:
            print(f"⏰ {reason}")
            return

    stats = {"sent": 0, "failed": 0, "skipped": 0, "complete": 0}

    if dry_run:
        log = load_wa_log()
        print("🔍 DRY RUN PREVIEW:\n")
        for i, lead in enumerate(leads_with_wa, 1):
            name = lead["name"]
            number = lead.get("contact_whatsapp") or (lead.get("all_phones") or [None])[0]
            if not number:
                continue
            msg_key, msg_data = get_next_wa_message(name, log, force=force)
            if msg_key in [None, "complete", "too_soon", "skipped_awaiting_approval"]:
                print(f"[{i}] {name} — {msg_key or 'no message'} ({msg_data or ''})")
                continue
            formatted = format_wa_number(number)
            from outreach.message_writer import clean_message_content
            message = clean_message_content(msg_data.get("message", ""), default_option=3)
            print(f"[{i}] {name}")
            print(f"     To: {formatted}")
            print(f"     Key: {msg_key}")
            print(f"     Message: {message[:100]}...")
            print()
        return

    # Real sending — launch WhatsApp Web once, run sessions inside
    async with async_playwright() as p:
        user_data_dir = os.path.join(os.getcwd(), ".wa_session")
        os.makedirs(user_data_dir, exist_ok=True)

        print("   🚀 Launching browser...")
        try:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False,
                channel="chrome",
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--start-maximized",
                ],
                no_viewport=True,
            )
        except Exception as e:
            print(f"   ⚠️  Could not launch Chrome channel: {e}. Falling back to default Chromium.")
            context = await p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--start-maximized",
                ],
                viewport={"width": 1366, "height": 768},
            )

        if context.pages:
            page = context.pages[0]
        else:
            page = await context.new_page()

        session_ok = await ensure_wa_session(page)
        if not session_ok:
            print("❌ WhatsApp Web session failed")
            await context.close()
            return

        await human_pause(3.0, 5.0)

        lead_index = 0
        session_num = 0

        while lead_index < len(leads_with_wa):
            # Re-read log fresh each session
            log = load_wa_log()
            todays_count = get_todays_wa_count(log)

            # Daily limit always enforced
            if todays_count >= daily_limit and not force:
                print(f"\n🛑 Daily WhatsApp limit reached ({todays_count}/{daily_limit}) — stopping")
                break

            # Timing guard at session start
            if not force and not ignore_timing:
                ok, reason = _is_good_time()
                if not ok:
                    print(f"\n⏰ Outside send window — {reason} — stopping")
                    break

            session_num += 1
            remaining_today = daily_limit - todays_count
            this_session = min(session_size, remaining_today)
            print(f"\n{'─'*55}")
            print(f"💬 Session {session_num}  |  Sent today: {todays_count}/{daily_limit}  |  Sending up to {this_session} now")
            print(f"{'─'*55}")

            sent_this_session = 0

            while sent_this_session < this_session and lead_index < len(leads_with_wa):
                lead = leads_with_wa[lead_index]
                lead_index += 1
                name = lead["name"]
                number = lead.get("contact_whatsapp") or (lead.get("all_phones") or [None])[0]

                if not number:
                    stats["skipped"] += 1
                    continue

                print(f"\n  [{lead_index}/{len(leads_with_wa)}] {name}")

                msg_key, msg_data = get_next_wa_message(name, log, force=force)

                if msg_key == "complete":
                    print(f"   ✅ Sequence complete for {name}")
                    stats["complete"] += 1
                    continue

                if msg_key in ["too_soon", "skipped_awaiting_approval"] or msg_key is None:
                    print(f"   ⏭️  Skipping: {msg_data or 'no message available'}")
                    stats["skipped"] += 1
                    continue

                from outreach.message_writer import clean_message_content
                message = clean_message_content(msg_data.get("message", ""), default_option=3)

                if not message:
                    stats["skipped"] += 1
                    continue

                # Build full deduplicated number list
                _seen_nums = set()
                numbers_to_try = []
                _raw = []
                _msg_to = msg_data.get("to")
                if isinstance(_msg_to, list):
                    _raw.extend(_msg_to)
                elif _msg_to:
                    _raw.append(_msg_to)
                _all_phones = lead.get("all_phones") or []
                if isinstance(_all_phones, list):
                    _raw.extend(_all_phones)
                elif _all_phones:
                    _raw.append(_all_phones)
                _wa_num = lead.get("contact_whatsapp")
                if _wa_num:
                    _raw.append(_wa_num)
                for _n in _raw:
                    if not _n:
                        continue
                    _fmt = format_wa_number(str(_n))
                    if _fmt and _fmt not in _seen_nums:
                        _seen_nums.add(_fmt)
                        numbers_to_try.append(_n)
                if not numbers_to_try:
                    numbers_to_try = [number]

                # Filter out numbers that already received this message key
                final_numbers_to_try = []
                for num in numbers_to_try:
                    formatted = format_wa_number(str(num))
                    if formatted and not already_sent_wa(log, formatted, name, msg_key):
                        final_numbers_to_try.append(num)

                print(f"   📋 Numbers to try: {len(final_numbers_to_try)} (out of {len(numbers_to_try)} total)")
                sent_successfully = False
                invalid_count = 0
                last_send_result = None
                sends_attempted = 0

                for idx, num in enumerate(final_numbers_to_try):
                    if not num:
                        continue
                    
                    # Pre-validate number
                    skip, skip_reason = should_skip_number(num, invalid_cache)
                    if skip:
                        print(f"   ⏭️  Skipping {num}: {skip_reason}")
                        continue
                    
                    # Human-like delay between numbers of the same business
                    if sends_attempted > 0:
                        delay = random.uniform(15, 30)
                        print(f"   ⏳ Waiting {delay:.0f}s before trying next number {num}...")
                        await asyncio.sleep(delay)

                    send_result = await send_whatsapp_message(
                        page=page,
                        number=num,
                        message=message,
                        business_name=name
                    )
                    last_send_result = send_result
                    formatted = format_wa_number(num) or num
                    log_entry = {
                        "business": name,
                        "number": formatted,
                        "msg_key": msg_key,
                        "message_preview": message[:100],
                        "message": message,  # SAVE FULL MESSAGE TEXT
                        "date": datetime.now().isoformat(),
                        "success": send_result["success"],
                        "error": send_result.get("error")
                    }
                    log["messages"].append(log_entry)
                    sends_attempted += 1

                    if send_result["success"]:
                        sent_successfully = True
                        print(f"   ✅ Sent successfully to {formatted}")
                    else:
                        if send_result.get("error") == "Phone number not on WhatsApp":
                            invalid_count += 1
                            # Cache this number so we never try it again
                            invalid_cache.add(formatted)
                            save_invalid_cache(invalid_cache)
                            print(f"   ↪️  Not on WhatsApp — cached & trying next number...")
                        else:
                            print(f"   ↪️  Failed ({send_result.get('error', '?')}) — trying next number...")

                if sends_attempted > 0:
                    if sent_successfully:
                        stats["sent"] += 1
                        sent_this_session += 1
                        log["stats"]["sent"] = log["stats"].get("sent", 0) + 1
                        try:
                            safe_name = name.replace(" ", "_").replace("/", "_").replace("&", "and")
                            seq_path = f"results/messages/sequences/{safe_name}_sequence.json"
                            if os.path.exists(seq_path):
                                with open(seq_path, "r", encoding="utf-8") as f:
                                    seq_data = json.load(f)
                                wa_idx = int(msg_key.split("_")[1]) - 1
                                curr_idx = 0
                                for m in seq_data:
                                    if m.get("channel") == "whatsapp":
                                        if curr_idx == wa_idx:
                                            m["status"] = "sent"
                                            break
                                        curr_idx += 1
                                with open(seq_path, "w", encoding="utf-8") as f:
                                    json.dump(seq_data, f, indent=2, ensure_ascii=False)
                            master_seq_path = "results/messages/sequences/master_sequence.json"
                            if os.path.exists(master_seq_path):
                                with open(master_seq_path, "r", encoding="utf-8") as f:
                                    master_seq = json.load(f)
                                for lead_seq in master_seq:
                                    if lead_seq.get("lead") == name:
                                        wa_idx = int(msg_key.split("_")[1]) - 1
                                        curr_idx = 0
                                        for m in lead_seq.get("sequence", []):
                                            if m.get("channel") == "whatsapp":
                                                if curr_idx == wa_idx:
                                                    m["status"] = "sent"
                                                    break
                                                curr_idx += 1
                                with open(master_seq_path, "w", encoding="utf-8") as f:
                                    json.dump(master_seq, f, indent=2, ensure_ascii=False)
                        except Exception as e:
                            print(f"   ⚠️  Failed to update sequence status: {e}")
                    else:
                        stats["failed"] += 1
                        log["stats"]["failed"] = log["stats"].get("failed", 0) + 1
                        all_invalid = (invalid_count == len(final_numbers_to_try))
                        if all_invalid:
                            print(f"   ⚠️  All {len(final_numbers_to_try)} number(s) not on WhatsApp. Marking as 'failed_invalid_number'.")
                            try:
                                safe_name = name.replace(" ", "_").replace("/", "_").replace("&", "and")
                                seq_path = f"results/messages/sequences/{safe_name}_sequence.json"
                                if os.path.exists(seq_path):
                                    with open(seq_path, "r", encoding="utf-8") as f:
                                        seq_data = json.load(f)
                                    for m in seq_data:
                                        if m.get("channel") == "whatsapp" and m.get("status") != "sent":
                                            m["status"] = "failed_invalid_number"
                                    with open(seq_path, "w", encoding="utf-8") as f:
                                        json.dump(seq_data, f, indent=2, ensure_ascii=False)
                                master_seq_path = "results/messages/sequences/master_sequence.json"
                                if os.path.exists(master_seq_path):
                                    with open(master_seq_path, "r", encoding="utf-8") as f:
                                        master_seq = json.load(f)
                                    for lead_seq in master_seq:
                                        if lead_seq.get("lead") == name:
                                            for m in lead_seq.get("sequence", []):
                                                if m.get("channel") == "whatsapp" and m.get("status") != "sent":
                                                    m["status"] = "failed_invalid_number"
                                    with open(master_seq_path, "w", encoding="utf-8") as f:
                                        json.dump(master_seq, f, indent=2, ensure_ascii=False)
                            except Exception as e:
                                print(f"   ⚠️  Failed to update sequence status: {e}")
                        else:
                            _last_err = (last_send_result or {}).get("error", "unknown error")
                            print(f"   ❌ All numbers failed. Last error: {_last_err}")
                else:
                    # final_numbers_to_try was empty (already sent to all numbers)
                    print(f"   ℹ️ Already sent to all active numbers for {name}")
                    # Update status to sent since it is fully complete
                    sent_successfully = True

                save_wa_log(log)

                # Short gap within session
                if sent_this_session < this_session and lead_index < len(leads_with_wa):
                    gap = random.uniform(20, 60)
                    print(f"   ⏳ {gap:.0f}s before next in session...")
                    await asyncio.sleep(gap)

            print(f"\n  ✔ Session {session_num} done — sent {sent_this_session} message(s)")

            # Between-session wait
            if lead_index < len(leads_with_wa):
                log = load_wa_log()
                if get_todays_wa_count(log) >= daily_limit and not force:
                    print(f"🛑 Daily limit reached — no more sessions today")
                    break
                wait_secs = random.uniform(session_wait_min, session_wait_max)
                wait_mins = wait_secs / 60
                resume_at = (datetime.now() + timedelta(seconds=wait_secs)).strftime("%I:%M %p")
                print(f"\n⏳ Waiting {wait_mins:.0f} min before next session (resumes ~{resume_at})...")
                await asyncio.sleep(wait_secs)
            else:
                break

        await context.close()

    print(f"\n{'='*55}")
    print(f"💬 WHATSAPP SENDER COMPLETE")
    print(f"{'='*55}")
    print(f"Sessions run:   {session_num}")
    print(f"Sent:           {stats['sent']}")
    print(f"Failed:         {stats['failed']}")
    print(f"Skipped:        {stats['skipped']}")
    print(f"Sequence done:  {stats['complete']}")
    print(f"{'='*55}")



# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv
    force = "--force" in sys.argv
    ignore_timing = "--ignore-timing" in sys.argv

    if dry_run:
        print("🔍 DRY RUN MODE — No messages will be sent\n")

    asyncio.run(send_all_whatsapp(dry_run=dry_run, force=force, ignore_timing=ignore_timing))