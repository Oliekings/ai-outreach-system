import asyncio
import json
import os
import re
import random
import time
from datetime import datetime
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

os.makedirs("results/sent/whatsapp", exist_ok=True)
os.makedirs("results/logs", exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
def load_config() -> dict:
    with open("ceo_config.json", "r") as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────────────
# SEND LOG
# ─────────────────────────────────────────────────────────────────────────────
def load_wa_log() -> dict:
    log_path = "results/logs/whatsapp_log.json"
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            return json.load(f)
    return {"messages": [], "stats": {"sent": 0, "failed": 0, "skipped": 0}}


def save_wa_log(log: dict):
    with open("results/logs/whatsapp_log.json", "w") as f:
        json.dump(log, f, indent=2)


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

    # Wait up to 60 seconds for either QR code or chat list
    for attempt in range(60):
        await asyncio.sleep(1)

        # Check if logged in
        chat_list = await page.query_selector('div[aria-label="Chat list"]')
        if chat_list:
            print("   ✅ WhatsApp Web session active")
            return True

        # Check for QR code
        qr_code = await page.query_selector('canvas[aria-label="Scan me!"]')
        if qr_code and attempt == 0:
            print("   📷 QR Code detected — please scan with your phone")
            print("   ⏳ Waiting up to 60 seconds for scan...")

        if attempt == 59:
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
            invalid = await page.query_selector('div[data-animate-modal-popup="true"]')
            if invalid:
                result["error"] = "Phone number not on WhatsApp"
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

            # Verify message was sent by checking for double tick or sent indicator
            await asyncio.sleep(2)
            result["success"] = True
            print(f"   ✅ Message sent to {formatted}")
        else:
            result["error"] = "Could not find send button"

    except Exception as e:
        result["error"] = str(e)[:100]
        print(f"   ❌ Failed: {result['error']}")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# DETERMINE NEXT MESSAGE IN SEQUENCE
# ─────────────────────────────────────────────────────────────────────────────
def get_next_wa_message(lead_name: str, log: dict) -> tuple:
    """Returns (msg_key, message_text) or (None, None)"""
    safe_name = re.sub(r'[^a-z0-9]', '-', lead_name.lower()).strip('-')
    wa_file = f"results/messages/whatsapp/{safe_name}_whatsapp.json"

    if not os.path.exists(wa_file):
        return None, None

    with open(wa_file, "r") as f:
        messages = json.load(f)

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
# BATCH WHATSAPP SENDER
# ─────────────────────────────────────────────────────────────────────────────
async def send_all_whatsapp(dry_run: bool = False, force: bool = False):
    config = load_config()
    log = load_wa_log()
    daily_limit = config["outreach"]["daily_whatsapp_limit"]

    # Load leads
    enriched_file = "results/leads/enriched_leads.json"
    if not os.path.exists(enriched_file):
        print("❌ No enriched leads found")
        return

    with open(enriched_file, "r") as f:
        leads = json.load(f)

    leads_with_wa = [
        l for l in leads
        if l.get("contact_whatsapp") or l.get("all_phones")
    ]

    print(f"\n💬 WHATSAPP SENDER")
    print(f"{'='*55}")
    print(f"Leads with WhatsApp:  {len(leads_with_wa)}")
    print(f"Daily limit:          {daily_limit}")
    print(f"Dry run:              {dry_run}")
    print(f"{'='*55}\n")

    # Check timing
    if not force and not dry_run:
        now = datetime.now()
        day = now.strftime("%A")
        hour = now.hour
        send_days = config["outreach"].get("send_days", ["Monday","Tuesday","Wednesday","Thursday"])
        send_start = config["outreach"].get("send_hours", {}).get("start", 9)
        send_end = config["outreach"].get("send_hours", {}).get("end", 17)

        if day not in send_days:
            print(f"⏰ Today is {day} — not a send day")
            return
        if not (send_start <= hour <= send_end):
            print(f"⏰ Hour {hour}:00 outside send window")
            return

    todays_count = get_todays_wa_count(log)
    print(f"Already sent today:   {todays_count}/{daily_limit}\n")

    if todays_count >= daily_limit and not force:
        print(f"🛑 Daily WhatsApp limit reached")
        return

    stats = {"sent": 0, "failed": 0, "skipped": 0, "complete": 0}

    if dry_run:
        # Dry run — just preview what would be sent
        print("🔍 DRY RUN PREVIEW:\n")
        for i, lead in enumerate(leads_with_wa, 1):
            name = lead["name"]
            number = lead.get("contact_whatsapp") or (lead.get("all_phones") or [None])[0]
            if not number:
                continue

            msg_key, msg_data = get_next_wa_message(name, log)
            if msg_key in [None, "complete", "too_soon"]:
                print(f"[{i}] {name} — {msg_key or 'no message'}")
                continue

            formatted = format_wa_number(number)
            message = msg_data.get("message", "")
            print(f"[{i}] {name}")
            print(f"     To: {formatted}")
            print(f"     Key: {msg_key}")
            print(f"     Message: {message[:100]}...")
            print()
        return

    # Real sending — launch WhatsApp Web
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # Must be visible for WhatsApp Web QR scan
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
            ]
        )

        # Use persistent context to save WhatsApp login session
        user_data_dir = os.path.join(os.getcwd(), ".wa_session")
        os.makedirs(user_data_dir, exist_ok=True)

        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
            ],
            viewport={"width": 1366, "height": 768},
        )

        await browser.close()
        page = await context.new_page()

        # Ensure WhatsApp Web session
        session_ok = await ensure_wa_session(page)
        if not session_ok:
            print("❌ WhatsApp Web session failed")
            await context.close()
            return

        await human_pause(3.0, 5.0)

        # Send to each lead
        for i, lead in enumerate(leads_with_wa, 1):
            if todays_count + stats["sent"] >= daily_limit and not force:
                print(f"\n🛑 Daily limit reached — stopping")
                break

            name = lead["name"]
            number = lead.get("contact_whatsapp") or (lead.get("all_phones") or [None])[0]

            if not number:
                stats["skipped"] += 1
                continue

            print(f"\n[{i}/{len(leads_with_wa)}] {name}")

            # Get next message in sequence
            msg_key, msg_data = get_next_wa_message(name, log)

            if msg_key == "complete":
                print(f"   ✅ Sequence complete for {name}")
                stats["complete"] += 1
                continue

            if msg_key == "too_soon" or msg_key is None:
                print(f"   ⏭️  Skipping: {msg_data or 'no message available'}")
                stats["skipped"] += 1
                continue

            message = msg_data.get("message", "")
            send_number = msg_data.get("to") or number

            if not message:
                stats["skipped"] += 1
                continue

            # Send message
            send_result = await send_whatsapp_message(
                page=page,
                number=send_number,
                message=message,
                business_name=name
            )

            # Log result
            formatted = format_wa_number(send_number)
            log_entry = {
                "business": name,
                "number": formatted,
                "msg_key": msg_key,
                "message_preview": message[:100],
                "date": datetime.now().isoformat(),
                "success": send_result["success"],
                "error": send_result.get("error")
            }
            log["messages"].append(log_entry)

            if send_result["success"]:
                stats["sent"] += 1
                log["stats"]["sent"] = log["stats"].get("sent", 0) + 1
            else:
                stats["failed"] += 1
                log["stats"]["failed"] = log["stats"].get("failed", 0) + 1

            save_wa_log(log)

            # Human pause between messages — critical
            if i < len(leads_with_wa):
                wait = random.uniform(45, 120)
                print(f"   ⏳ Waiting {wait:.0f}s before next message...")
                await asyncio.sleep(wait)

        await context.close()

    # Summary
    print(f"\n{'='*55}")
    print(f"💬 WHATSAPP SENDER COMPLETE")
    print(f"{'='*55}")
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

    if dry_run:
        print("🔍 DRY RUN MODE — No messages will be sent\n")

    asyncio.run(send_all_whatsapp(dry_run=dry_run, force=force))