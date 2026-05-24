import sys
import asyncio
import json
import os
import re
import random
from datetime import datetime
from playwright.async_api import async_playwright
from dotenv import load_dotenv

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

load_dotenv()
import pathlib
# Ensure project root is on sys.path so 'from outreach.x import ...' always works
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

os.makedirs("results/sent/facebook", exist_ok=True)
os.makedirs("results/logs", exist_ok=True)


def load_config() -> dict:
    with open("ceo_config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def load_fb_log() -> dict:
    path = "results/logs/facebook_log.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"messages": [], "stats": {"sent": 0, "failed": 0}}


def save_fb_log(log: dict):
    with open("results/logs/facebook_log.json", "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def already_sent_fb(log: dict, page_url: str, business: str, msg_key: str) -> bool:
    try:
        curr_idx = int(msg_key.split("_")[1])
    except:
        curr_idx = 0

    for entry in log["messages"]:
        entry_business = entry.get("business") or ""
        entry_msg_key = entry.get("msg_key") or ""
        try:
            entry_idx = int(entry_msg_key.split("_")[1])
        except:
            entry_idx = 0

        if (entry_business.lower().strip() == business.lower().strip() and
                entry_idx >= curr_idx and
                entry.get("success")):
            return True
            
        # Also check page URL if matching specific profile/page target
        if entry.get("page") == page_url and entry.get("success") and entry_idx >= curr_idx:
            return True
    return False



def get_todays_fb_count(log: dict) -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    return sum(
        1 for e in log["messages"]
        if e.get("date", "").startswith(today) and e.get("success")
    )


async def human_pause(min_s=2.0, max_s=5.0):
    await asyncio.sleep(random.uniform(min_s, max_s))


async def human_type(element, text: str):
    for char in text:
        await element.type(char)
        await asyncio.sleep(random.uniform(0.04, 0.15))
    await human_pause(0.5, 1.5)


async def handle_consent(page):
    for sel in [
        'button[data-cookiebanner="accept_button"]',
        'button:has-text("Allow all cookies")',
        'button:has-text("Accept All")',
        '[data-testid="cookie-policy-manage-dialog-accept-button"]',
        'button:has-text("Only allow essential cookies")',
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


async def dismiss_popups(page):
    """Dismiss common Facebook popups"""
    for sel in [
        'div[aria-label="Close"]',
        'button:has-text("Not now")',
        'button:has-text("Cancel")',
        'button:has-text("Close")',
        '[data-testid="dialog-close-button"]',
    ]:
        try:
            btn = await page.query_selector(sel)
            if btn:
                await btn.click()
                await human_pause(1.0, 2.0)
        except:
            continue


async def ensure_fb_session(page) -> bool:
    """Ensure Facebook is logged in"""
    print("   📘 Loading Facebook...")
    await page.goto("https://www.facebook.com", timeout=30000, wait_until="domcontentloaded")
    await human_pause(3.0, 5.0)
    await handle_consent(page)
    await human_pause(2.0, 4.0)

    for attempt in range(30):
        await asyncio.sleep(2)

        # Check if logged in
        logged_in = await page.query_selector('[aria-label="Facebook"]')
        if logged_in:
            print("   ✅ Facebook session active")
            return True

        # Login form
        email_input = await page.query_selector('input[name="email"]')
        if email_input and attempt == 0:
            fb_email = os.getenv("FACEBOOK_EMAIL")
            fb_pass = os.getenv("FACEBOOK_PASSWORD")

            if fb_email and fb_pass:
                print("   🔑 Logging into Facebook...")
                await email_input.click()
                await human_type(email_input, fb_email)
                await human_pause(1.0, 2.0)

                pass_input = await page.query_selector('input[name="pass"]')
                if pass_input:
                    await pass_input.click()
                    await human_type(pass_input, fb_pass)
                    await human_pause(1.5, 3.0)

                    submit = await page.query_selector('button[name="login"]')
                    if submit:
                        await submit.click()
                        await human_pause(5.0, 8.0)
            else:
                print("   ⚠️  No Facebook credentials in .env")
                print("   Add FACEBOOK_EMAIL and FACEBOOK_PASSWORD to .env")
                return False

        if attempt == 29:
            print("   ❌ Facebook login timeout")
            await page.screenshot(path="results/logs/fb_login_timeout.png")
            
            html = await page.content()
            with open("results/logs/fb_login_timeout.html", "w", encoding="utf-8") as f:
                f.write(html)
                
            print("   📸 Saved screenshot to results/logs/fb_login_timeout.png")
            return False

    return False


async def send_facebook_message(
    page,
    page_url: str,
    message: str,
    business_name: str
) -> dict:
    result = {
        "success": False,
        "page": page_url,
        "business": business_name,
        "error": None
    }

    try:
        print(f"   📤 Messaging Facebook page: {page_url[:60]}...")

        # Visit the business page
        await page.goto(page_url, timeout=20000, wait_until="domcontentloaded")
        await handle_consent(page)
        await human_pause(3.0, 6.0)
        await dismiss_popups(page)
        await human_pause(1.0, 2.0)

        # Find Send Message button
        msg_btn_selectors = [
            'div[aria-label="Send Message"]',
            'a[aria-label="Send Message"]',
            'div[role="button"]:has-text("Send Message")',
            'a:has-text("Send Message")',
        ]

        msg_btn = None
        for sel in msg_btn_selectors:
            try:
                btn = await page.query_selector(sel)
                if btn:
                    msg_btn = btn
                    break
            except:
                continue

        if not msg_btn:
            # Try scrolling to find it
            await page.evaluate("window.scrollBy(0, 300)")
            await human_pause(1.0, 2.0)
            for sel in msg_btn_selectors:
                try:
                    btn = await page.query_selector(sel)
                    if btn:
                        msg_btn = btn
                        break
                except:
                    continue

        if not msg_btn:
            result["error"] = "Send Message button not found on this page"
            return result

        await msg_btn.click()
        await human_pause(3.0, 6.0)
        await dismiss_popups(page)
        await human_pause(1.0, 2.0)

        # Find message input in the chat window
        input_selectors = [
            'div[aria-label="Message"]',
            'div[role="textbox"]',
            'div[contenteditable="true"]',
            'textarea[placeholder="Aa"]',
        ]

        msg_input = None
        for sel in input_selectors:
            try:
                await page.wait_for_selector(sel, timeout=8000)
                msg_input = await page.query_selector(sel)
                if msg_input:
                    break
            except:
                continue

        if not msg_input:
            result["error"] = "Message input not found in chat window"
            return result

        await msg_input.click()
        await human_pause(1.0, 2.0)
        await human_type(msg_input, message)
        await human_pause(2.0, 5.0)

        # Send
        send_selectors = [
            'div[aria-label="Press Enter to send"]',
            'button[aria-label="Send"]',
            'div[role="button"]:has-text("Send")',
        ]

        sent = False
        for sel in send_selectors:
            try:
                btn = await page.query_selector(sel)
                if btn:
                    await btn.click()
                    sent = True
                    break
            except:
                continue

        if not sent:
            await msg_input.press("Enter")
            sent = True

        await human_pause(2.0, 4.0)
        result["success"] = True
        print(f"   ✅ Message sent to Facebook page")

    except Exception as e:
        result["error"] = str(e)[:100]
        print(f"   ❌ Failed: {result['error']}")

    return result


def get_next_fb_message(lead_name: str, log: dict) -> tuple:
    safe_name = lead_name.replace(" ", "_").replace("/", "_").replace("&", "and")
    fb_file = f"results/messages/facebook/{safe_name}_facebook.json"

    if not os.path.exists(fb_file):
        return None, None

    with open(fb_file, "r", encoding="utf-8") as f:
        messages = json.load(f)

    min_days = {"fb_1": 0, "fb_2": 5}

    for key in ["fb_1", "fb_2"]:
        if key not in messages:
            continue

        msg_data = messages[key]
        if not msg_data.get("message"):
            continue

        page_url = msg_data.get("to", "")
        if not page_url or "facebook.com" not in page_url:
            continue

        if already_sent_fb(log, page_url, lead_name, key):
            continue

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


async def send_all_facebook(dry_run: bool = False, force: bool = False, ignore_timing: bool = False):
    config = load_config()
    log = load_fb_log()
    daily_limit = config["outreach"]["daily_facebook_limit"]

    enriched_file = "results/leads/enriched_leads.json"
    if not os.path.exists(enriched_file):
        print("❌ No enriched leads found")
        return

    with open(enriched_file, "r", encoding="utf-8") as f:
        leads = json.load(f)

    leads_with_fb = [
        l for l in leads
        if l.get("facebook", {}).get("found") and l.get("facebook", {}).get("url")
    ]

    print(f"\n📘 FACEBOOK MESSAGE SENDER")
    print(f"{'='*55}")
    print(f"Leads with Facebook:  {len(leads_with_fb)}")
    print(f"Daily limit:          {daily_limit}")
    print(f"Dry run:              {dry_run}")
    print(f"{'='*55}\n")

    todays_count = get_todays_fb_count(log)
    print(f"Already sent today:   {todays_count}/{daily_limit}\n")

    if todays_count >= daily_limit and not force and not ignore_timing:
        print("🛑 Daily Facebook limit reached")
        return

    if dry_run:
        print("🔍 DRY RUN PREVIEW:\n")
        for i, lead in enumerate(leads_with_fb, 1):
            name = lead["name"]
            msg_key, msg_data = get_next_fb_message(name, log)
            if msg_key in [None, "complete", "too_soon"]:
                print(f"[{i}] {name} — {msg_key or 'no message'}")
                continue
            print(f"[{i}] {name}")
            print(f"     Page: {msg_data.get('to', '')}")
            print(f"     Key: {msg_key}")
            from outreach.message_writer import clean_message_content
            print(f"     Message: {clean_message_content(msg_data.get('message', ''), default_option=3)[:100]}...")
            print()
        return

    stats = {"sent": 0, "failed": 0, "skipped": 0, "complete": 0}

    user_data_dir = os.path.join(os.getcwd(), ".fb_session")
    os.makedirs(user_data_dir, exist_ok=True)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
            viewport={"width": 1366, "height": 768},
        )

        page = await context.new_page()
        session_ok = await ensure_fb_session(page)

        if not session_ok:
            print("❌ Facebook session failed")
            await context.close()
            return

        await human_pause(3.0, 5.0)

        for i, lead in enumerate(leads_with_fb, 1):
            if todays_count + stats["sent"] >= daily_limit and not force:
                print(f"\n🛑 Daily limit reached — stopping")
                break

            name = lead["name"]
            print(f"\n[{i}/{len(leads_with_fb)}] {name}")

            msg_key, msg_data = get_next_fb_message(name, log)

            if msg_key == "complete":
                print(f"   ✅ Sequence complete")
                stats["complete"] += 1
                continue

            if msg_key in ["too_soon", None]:
                print(f"   ⏭️  Skipping: {msg_data or 'no message'}")
                stats["skipped"] += 1
                continue

            page_url = msg_data.get("to", "")
            from outreach.message_writer import clean_message_content
            message = clean_message_content(msg_data.get("message", ""), default_option=3)

            send_result = await send_facebook_message(
                page=page,
                page_url=page_url,
                message=message,
                business_name=name
            )

            log_entry = {
                "business": name,
                "page": page_url,
                "msg_key": msg_key,
                "message_preview": message[:100],
                "message": message,  # SAVE FULL MESSAGE TEXT
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

            save_fb_log(log)

            if i < len(leads_with_fb):
                wait = random.uniform(60, 180)
                print(f"   ⏳ Waiting {wait:.0f}s...")
                await asyncio.sleep(wait)

        await context.close()

    print(f"\n{'='*55}")
    print(f"📘 FACEBOOK SENDER COMPLETE")
    print(f"{'='*55}")
    print(f"Sent:          {stats['sent']}")
    print(f"Failed:        {stats['failed']}")
    print(f"Skipped:       {stats['skipped']}")
    print(f"Complete:      {stats['complete']}")
    print(f"{'='*55}")


if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv
    force = "--force" in sys.argv
    ignore_timing = "--ignore-timing" in sys.argv
    asyncio.run(send_all_facebook(dry_run=dry_run, force=force, ignore_timing=ignore_timing))