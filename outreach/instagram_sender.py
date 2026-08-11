import sys
import asyncio
import json
import os
import re
import random
from datetime import datetime
from playwright.async_api import async_playwright
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

load_dotenv()
import pathlib

# Ensure project root is on sys.path so 'from outreach.x import ...' always works
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

os.makedirs("results/sent/instagram", exist_ok=True)
os.makedirs("results/logs", exist_ok=True)


def load_config() -> dict:
    with open("ceo_config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def load_ig_log() -> dict:
    path = "results/logs/instagram_log.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"messages": [], "stats": {"sent": 0, "failed": 0}}


def save_ig_log(log: dict):
    with open("results/logs/instagram_log.json", "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def already_sent_ig(log: dict, profile_url: str, business: str, msg_key: str) -> bool:
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

        if (
            entry_business.lower().strip() == business.lower().strip()
            and entry_idx >= curr_idx
            and entry.get("success")
        ):
            return True

        # Also check profile URL if matching specific profile/page target
        if (
            entry.get("profile") == profile_url
            and entry.get("success")
            and entry_idx >= curr_idx
        ):
            return True
    return False


def get_todays_ig_count(log: dict) -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    return sum(
        1
        for e in log["messages"]
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
        'button:has-text("Allow all cookies")',
        'button:has-text("Accept All")',
        'button:has-text("Allow essential and optional cookies")',
        '[data-testid="cookie-policy-manage-dialog-accept-button"]',
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


async def ensure_ig_session(page) -> bool:
    """Ensure Instagram is logged in"""
    print("   📸 Loading Instagram...")
    await page.goto(
        "https://www.instagram.com", timeout=30000, wait_until="domcontentloaded"
    )
    await human_pause(3.0, 5.0)
    await handle_consent(page)
    await human_pause(2.0, 4.0)

    # Check if logged in
    for attempt in range(30):
        await asyncio.sleep(2)

        # Look for home feed indicators
        logged_in = await page.query_selector('nav[role="navigation"]')
        if logged_in:
            print("   ✅ Instagram session active")
            return True

        # Look for login form
        login_form = await page.query_selector('input[name="username"]')
        if login_form and attempt == 0:
            ig_user = os.getenv("INSTAGRAM_USERNAME")
            ig_pass = os.getenv("INSTAGRAM_PASSWORD")

            if ig_user and ig_pass:
                print("   🔑 Logging into Instagram...")
                await login_form.click()
                await human_type(login_form, ig_user)
                await human_pause(1.0, 2.0)

                pass_input = await page.query_selector('input[name="password"]')
                if pass_input:
                    await pass_input.click()
                    await human_type(pass_input, ig_pass)
                    await human_pause(1.5, 3.0)

                    submit = await page.query_selector('button[type="submit"]')
                    if submit:
                        await submit.click()
                        await human_pause(4.0, 7.0)
            else:
                print("   ⚠️  No Instagram credentials in .env")
                print("   Add INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD to .env")
                return False

        if attempt == 29:
            print("   ❌ Instagram login timeout")
            return False

    return False


async def send_instagram_dm(
    page, profile_url: str, message: str, business_name: str
) -> dict:
    result = {
        "success": False,
        "profile": profile_url,
        "business": business_name,
        "error": None,
    }

    try:
        # Clean profile URL
        ig_match = re.search(r"instagram\.com/([a-zA-Z0-9._]+)", profile_url)
        if not ig_match:
            result["error"] = "Invalid Instagram URL"
            return result

        username = ig_match.group(1)

        # Remove trailing path fragments
        for skip in ["reels", "posts", "tagged", "tv", "reel"]:
            if username == skip:
                result["error"] = "Not a profile URL"
                return result

        print(f"   📤 DMing @{username}...")

        # Visit their profile
        await page.goto(
            f"https://www.instagram.com/{username}/",
            timeout=20000,
            wait_until="domcontentloaded",
        )
        await handle_consent(page)
        await human_pause(3.0, 6.0)

        # Check if profile exists
        not_found = await page.query_selector('h2:has-text("Sorry")')
        if not_found:
            result["error"] = "Profile not found"
            return result

        # Find and click Message button
        msg_btn_selectors = [
            'div[role="button"]:has-text("Message")',
            'button:has-text("Message")',
            'a:has-text("Message")',
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
            result["error"] = "No Message button found — may need to follow first"
            return result

        await msg_btn.click()
        await human_pause(2.0, 4.0)

        # Handle any popups (e.g. "Open in app")
        for popup_sel in [
            'button:has-text("Not now")',
            'button:has-text("Cancel")',
            '[aria-label="Close"]',
        ]:
            try:
                popup = await page.query_selector(popup_sel)
                if popup:
                    await popup.click()
                    await human_pause(1.0, 2.0)
                    break
            except:
                continue

        # Find message input
        await human_pause(2.0, 4.0)

        input_selectors = [
            'div[aria-label="Message"]',
            'div[role="textbox"]',
            'textarea[placeholder="Message..."]',
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
            result["error"] = "Message input not found"
            return result

        await msg_input.click()
        await human_pause(1.0, 2.0)

        # Type the message
        await human_type(msg_input, message)
        await human_pause(2.0, 4.0)

        # Send
        send_selectors = [
            'button:has-text("Send")',
            'div[role="button"]:has-text("Send")',
            'button[type="submit"]',
        ]

        sent = False
        for sel in send_selectors:
            try:
                send_btn = await page.query_selector(sel)
                if send_btn:
                    await send_btn.click()
                    sent = True
                    break
            except:
                continue

        if not sent:
            await msg_input.press("Enter")
            sent = True

        await human_pause(2.0, 4.0)
        result["success"] = True
        print(f"   ✅ DM sent to @{username}")

    except Exception as e:
        result["error"] = str(e)[:100]
        print(f"   ❌ Failed: {result['error']}")

    return result


def get_next_ig_message(lead_name: str, log: dict) -> tuple:
    safe_name = lead_name.replace(" ", "_").replace("/", "_").replace("&", "and")
    ig_file = f"results/messages/instagram/{safe_name}_instagram.json"

    if not os.path.exists(ig_file):
        return None, None

    with open(ig_file, "r", encoding="utf-8") as f:
        messages = json.load(f)

    min_days = {"ig_1": 0, "ig_2": 5}

    for key in ["ig_1", "ig_2"]:
        if key not in messages:
            continue

        msg_data = messages[key]
        if not msg_data.get("message"):
            continue

        profile_url = msg_data.get("to", "")
        if not profile_url or "instagram.com" not in profile_url:
            continue

        if already_sent_ig(log, profile_url, lead_name, key):
            continue

        # Check days gap
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


async def send_all_instagram(
    dry_run: bool = False, force: bool = False, ignore_timing: bool = False
):
    config = load_config()
    log = load_ig_log()
    daily_limit = config["outreach"]["daily_instagram_limit"]

    enriched_file = "results/leads/enriched_leads.json"
    if not os.path.exists(enriched_file):
        print("❌ No enriched leads found")
        return

    with open(enriched_file, "r", encoding="utf-8") as f:
        leads = json.load(f)

    leads_with_ig = [
        l
        for l in leads
        if l.get("instagram", {}).get("found") and l.get("instagram", {}).get("url")
    ]

    print(f"\n📸 INSTAGRAM DM SENDER")
    print(f"{'='*55}")
    print(f"Leads with Instagram:  {len(leads_with_ig)}")
    print(f"Daily limit:           {daily_limit}")
    print(f"Dry run:               {dry_run}")
    print(f"{'='*55}\n")

    todays_count = get_todays_ig_count(log)
    print(f"Already sent today:    {todays_count}/{daily_limit}\n")

    if todays_count >= daily_limit and not force and not ignore_timing:
        print("🛑 Daily Instagram limit reached")
        return

    if dry_run:
        print("🔍 DRY RUN PREVIEW:\n")
        for i, lead in enumerate(leads_with_ig, 1):
            name = lead["name"]
            msg_key, msg_data = get_next_ig_message(name, log)
            if msg_key in [None, "complete", "too_soon"]:
                print(f"[{i}] {name} — {msg_key or 'no message'}")
                continue
            print(f"[{i}] {name}")
            print(f"     Profile: {msg_data.get('to', '')}")
            print(f"     Key: {msg_key}")
            from outreach.message_writer import clean_message_content

            print(
                f"     Message: {clean_message_content(msg_data.get('message', ''), default_option=3)[:100]}..."
            )
            print()
        return

    stats = {"sent": 0, "failed": 0, "skipped": 0, "complete": 0}

    user_data_dir = os.path.join(os.getcwd(), ".ig_session")
    os.makedirs(user_data_dir, exist_ok=True)

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
            viewport={"width": 1366, "height": 768},
        )

        page = await context.new_page()
        session_ok = await ensure_ig_session(page)

        if not session_ok:
            print("❌ Instagram session failed")
            await context.close()
            return

        await human_pause(3.0, 5.0)

        for i, lead in enumerate(leads_with_ig, 1):
            if todays_count + stats["sent"] >= daily_limit and not force:
                print(f"\n🛑 Daily limit reached — stopping")
                break

            name = lead["name"]
            print(f"\n[{i}/{len(leads_with_ig)}] {name}")

            msg_key, msg_data = get_next_ig_message(name, log)

            if msg_key == "complete":
                print(f"   ✅ Sequence complete")
                stats["complete"] += 1
                continue

            if msg_key in ["too_soon", None]:
                print(f"   ⏭️  Skipping: {msg_data or 'no message'}")
                stats["skipped"] += 1
                continue

            profile_url = msg_data.get("to", "")
            from outreach.message_writer import clean_message_content

            message = clean_message_content(
                msg_data.get("message", ""), default_option=3
            )

            send_result = await send_instagram_dm(
                page=page, profile_url=profile_url, message=message, business_name=name
            )

            log_entry = {
                "business": name,
                "profile": profile_url,
                "msg_key": msg_key,
                "message_preview": message[:100],
                "message": message,  # SAVE FULL MESSAGE TEXT
                "date": datetime.now().isoformat(),
                "success": send_result["success"],
                "error": send_result.get("error"),
            }
            log["messages"].append(log_entry)

            if send_result["success"]:
                stats["sent"] += 1
                log["stats"]["sent"] = log["stats"].get("sent", 0) + 1
            else:
                stats["failed"] += 1
                log["stats"]["failed"] = log["stats"].get("failed", 0) + 1

            save_ig_log(log)

            if i < len(leads_with_ig):
                wait = random.uniform(60, 180)
                print(f"   ⏳ Waiting {wait:.0f}s...")
                await asyncio.sleep(wait)

        await context.close()

    print(f"\n{'='*55}")
    print(f"📸 INSTAGRAM SENDER COMPLETE")
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
    asyncio.run(
        send_all_instagram(dry_run=dry_run, force=force, ignore_timing=ignore_timing)
    )
