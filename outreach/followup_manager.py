"""
Follow-Up Manager — Dynamic Follow-Up Generation
==================================================
Runs daily (called by ai_ceo.py) BEFORE senders.

Logic:
  1. Scan send_log.json and whatsapp_log.json for successfully sent messages.
  2. For each lead, check if enough days have passed since the last message.
  3. Check reply_log.json — if the lead replied, skip them.
  4. If no reply and enough time elapsed, generate the NEXT follow-up via AI.
  5. Save it to the lead's message JSON so the sender picks it up.

Follow-up delays (configurable):
  - email_2: 4 days after email_1
  - email_3: 7 days after email_2
  - wa_2:    3 days after wa_1
  - wa_3:    7 days after wa_2
"""

import json
import os
import sys
import time
import random
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

sys.stdout.reconfigure(encoding="utf-8")

# Ensure project root is on path for imports
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Re-use AI client and helpers from message_writer
from outreach.message_writer import (
    get_ai_response,
    safe_json,
    build_lead_context,
)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURABLE DELAYS (days)
# ─────────────────────────────────────────────────────────────────────────────
FOLLOWUP_DELAYS = {
    "email_2": 4,  # days after email_1
    "email_3": 7,  # days after email_2
    "wa_2": 3,  # days after wa_1
    "wa_3": 7,  # days after wa_2
}

# Which message triggers which follow-up
FOLLOWUP_CHAIN = {
    "email_1": "email_2",
    "email_2": "email_3",
    "wa_1": "wa_2",
    "wa_2": "wa_3",
}


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADERS
# ─────────────────────────────────────────────────────────────────────────────
def load_json(path: str, default=None):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default if default is not None else {}


def save_json(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_enriched_leads() -> list:
    return load_json("results/leads/enriched_leads.json", [])


def load_audit_map() -> dict:
    audit_file = "results/audits/general_audit_results.json"
    audits = load_json(audit_file, [])
    return {a["name"]: a for a in audits}


# ─────────────────────────────────────────────────────────────────────────────
# REPLY CHECKER
# ─────────────────────────────────────────────────────────────────────────────
def get_replied_businesses(channel: str = None) -> set:
    """Return set of business names that have replied (interested/question)."""
    reply_log = load_json("results/replies/reply_log.json", {})
    replied = set()
    for r in reply_log.get("replies", []):
        intent = r.get("classification", {}).get("intent", "")
        if intent in ("interested", "question"):
            replied.add(r.get("business", ""))
    return replied


# ─────────────────────────────────────────────────────────────────────────────
# FIND LEADS NEEDING FOLLOW-UPS
# ─────────────────────────────────────────────────────────────────────────────
def find_pending_followups() -> list:
    """
    Scan logs and return a list of dicts:
      { "business": str, "channel": "email"|"whatsapp",
        "last_key": "email_1", "next_key": "email_2",
        "days_since": int, "delay_needed": int }
    """
    email_log = load_json("results/logs/send_log.json", {})
    wa_log = load_json("results/logs/whatsapp_log.json", {})
    replied = get_replied_businesses()
    now = datetime.now()

    pending = []

    # --- Email follow-ups ---
    # Group successful sends by business
    email_sends = {}
    for e in email_log.get("emails", []):
        if not e.get("success"):
            continue
        biz = e["business"]
        key = e["email_key"]
        if biz not in email_sends:
            email_sends[biz] = {}
        # Keep the latest date for each key
        email_sends[biz][key] = e["date"]

    for biz, keys in email_sends.items():
        if biz in replied:
            continue
        # Check each step in the chain
        for last_key, next_key in [("email_1", "email_2"), ("email_2", "email_3")]:
            if last_key in keys and next_key not in keys:
                sent_date = datetime.fromisoformat(keys[last_key])
                days_since = (now - sent_date).days
                delay = FOLLOWUP_DELAYS[next_key]
                if days_since >= delay:
                    # Check the message file doesn't already have this follow-up
                    safe_name = (
                        biz.replace(" ", "_").replace("/", "_").replace("&", "and")
                    )
                    email_file = f"results/emails/{safe_name}_emails.json"
                    existing = load_json(email_file, {})
                    if next_key in existing and existing[next_key].get("subject"):
                        continue  # Already generated, sender will pick it up
                    pending.append(
                        {
                            "business": biz,
                            "channel": "email",
                            "last_key": last_key,
                            "next_key": next_key,
                            "days_since": days_since,
                            "delay_needed": delay,
                        }
                    )

    # --- WhatsApp follow-ups ---
    wa_sends = {}
    for m in wa_log.get("messages", []):
        if not m.get("success"):
            continue
        biz = m["business"]
        key = m["msg_key"]
        if biz not in wa_sends:
            wa_sends[biz] = {}
        wa_sends[biz][key] = m["date"]

    for biz, keys in wa_sends.items():
        if biz in replied:
            continue
        for last_key, next_key in [("wa_1", "wa_2"), ("wa_2", "wa_3")]:
            if last_key in keys and next_key not in keys:
                sent_date = datetime.fromisoformat(keys[last_key])
                days_since = (now - sent_date).days
                delay = FOLLOWUP_DELAYS[next_key]
                if days_since >= delay:
                    safe_name = (
                        biz.replace(" ", "_").replace("/", "_").replace("&", "and")
                    )
                    wa_file = f"results/messages/whatsapp/{safe_name}_whatsapp.json"
                    existing = load_json(wa_file, {})
                    if next_key in existing and existing[next_key].get("message"):
                        continue
                    pending.append(
                        {
                            "business": biz,
                            "channel": "whatsapp",
                            "last_key": last_key,
                            "next_key": next_key,
                            "days_since": days_since,
                            "delay_needed": delay,
                        }
                    )

    return pending


# ─────────────────────────────────────────────────────────────────────────────
# AI FOLLOW-UP GENERATORS
# ─────────────────────────────────────────────────────────────────────────────
def generate_email_followup(ctx: dict, next_key: str) -> dict:
    """Generate email_2 or email_3 dynamically via AI."""
    business = ctx["name"]
    first_name = ctx["first_name"] or "there"
    vibe = ctx["vibe"]
    tone = ctx["tone"]
    has_website = ctx["has_website"]

    if next_key == "email_2":
        issues_text = ""
        if ctx["site_issues"]:
            issues_text = "\n".join(f"* {i}" for i in ctx["site_issues"][:4])
        elif not has_website:
            issues_text = (
                "* No website found\n* No online booking\n"
                "* No WhatsApp button\n* Missing from directories"
            )

        prompt = f"""
You are writing the SECOND email to a business owner who didn't reply to the first email.
This email delivers a FREE audit report as a gift — no strings attached.

Business: {business}
Owner first name: {first_name}
Business vibe: {vibe}
Tone: {tone}
Has website: {has_website}
Issues found:
{issues_text}
Revenue opportunity: {ctx['revenue_hook'] or 'significant monthly revenue being lost'}
Competitor threat: {ctx['competitor_threat'] or 'competitors are pulling ahead digitally'}

STRICT RULES:
- Reference that you sent a message before (briefly, warmly)
- Lead with the free audit as a genuine gift
- Mention 2-3 specific issues found in plain language
- Include the revenue hook if available
- End with offer to send the full report
- Tone: warm expert friend
- Max 160 words
- Subject must create genuine curiosity

Return ONLY valid JSON:
{{
  "subject": "subject line here",
  "body": "full email body here",
  "preview_text": "preview text here"
}}
"""
    else:  # email_3
        prompt = f"""
You are writing the THIRD and final email in a sequence to a business owner.
This is the last touch — after this we move to nurture mode.

Business: {business}
Owner first name: {first_name}
Business vibe: {vibe}
Tone: {tone}
Has website: {has_website}
Website grade: {ctx['website_grade']}
Biggest opportunity: {ctx['biggest_opportunity']}

STRICT RULES:
- Acknowledge this is the last message
- Make ONE soft offer: a free sample site
- No pressure, no guilt, no urgency tactics
- Mention referral warmly
- End warmly, leave the door open
- Max 130 words

Return ONLY valid JSON:
{{
  "subject": "subject line here",
  "body": "full email body here",
  "preview_text": "preview text here"
}}
"""

    try:
        response = get_ai_response(prompt, max_tokens=800)
        parsed = safe_json(response)
        if parsed:
            return {
                "to": ctx["email"],
                "subject": parsed.get("subject", ""),
                "body": parsed.get("body", ""),
                "preview_text": parsed.get("preview_text", ""),
                "send_day": 0,
                "channel": "email",
                "generated_by": "followup_manager",
                "generated_at": datetime.now().isoformat(),
            }
    except Exception as e:
        print(f"      [ERROR] AI generation failed: {e}")
    return {"error": "Failed to generate follow-up"}


def generate_whatsapp_followup(ctx: dict, next_key: str) -> dict:
    """Generate wa_2 or wa_3 dynamically via AI."""
    business = ctx["name"]
    first_name = ctx["first_name"] or ""
    vibe = ctx["vibe"]
    use_pidgin = ctx["use_pidgin"]

    if next_key == "wa_2":
        prompt = f"""
Write a second WhatsApp follow-up message to a business owner who didn't reply.

Business: {business}
Owner first name: {first_name}
Vibe: {vibe}
Use pidgin: {use_pidgin}
Revenue opportunity: {ctx['revenue_hook'] or 'significant opportunity identified'}
Competitor threat: {ctx['competitor_threat'] or 'competitors are getting ahead'}

STRICT RULES:
- Maximum 4 sentences
- Acknowledge you reached out before — briefly, warmly
- Drop ONE specific insight that's genuinely useful
- Reference the revenue or competitor hook naturally
- End with a soft question or offer
- Still zero pitch — just value
- Feels like a friend who noticed something important

Return ONLY valid JSON:
{{
  "message": "the whatsapp message here"
}}
"""
    else:  # wa_3
        prompt = f"""
Write the third and final WhatsApp message to a business owner.

Business: {business}
Owner first name: {first_name}
Vibe: {vibe}
Use pidgin: {use_pidgin}
Has website: {ctx['has_website']}
Biggest opportunity: {ctx['biggest_opportunity']}

STRICT RULES:
- Maximum 3 sentences
- Warm, genuine, zero pressure
- Make ONE soft offer — a free sample of what their digital presence could look like
- If not ready, genuinely wish them well and mention referrals warmly
- Leave the door open forever
- Must feel like a real human being

Return ONLY valid JSON:
{{
  "message": "the whatsapp message here"
}}
"""

    try:
        response = get_ai_response(prompt, max_tokens=400)
        parsed = safe_json(response)
        if parsed:
            return {
                "to": ctx.get("all_phones") or [],
                "message": parsed.get("message", ""),
                "send_day": 0,
                "channel": "whatsapp",
                "generated_by": "followup_manager",
                "generated_at": datetime.now().isoformat(),
            }
    except Exception as e:
        print(f"      [ERROR] AI generation failed: {e}")
    return {"error": "Failed to generate follow-up"}


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RUNNER
# ─────────────────────────────────────────────────────────────────────────────
def run_followup_manager(dry_run: bool = False) -> dict:
    print(f"\n{'='*60}")
    print(f"  [FOLLOWUP] Dynamic Follow-Up Manager")
    print(f"  {datetime.now().strftime('%A, %d %B %Y — %I:%M %p')}")
    if dry_run:
        print(f"  [DRY RUN] — No messages will be generated")
    print(f"{'='*60}\n")

    pending = find_pending_followups()
    print(f"  Found {len(pending)} lead(s) needing follow-ups\n")

    if not pending:
        print("  [OK] No follow-ups needed right now.")
        return {"generated": 0, "skipped": 0, "errors": 0}

    # Load enriched leads and audit data for context building
    leads = load_enriched_leads()
    lead_map = {l["name"]: l for l in leads}
    audit_map = load_audit_map()

    stats = {"generated": 0, "skipped": 0, "errors": 0}

    for i, item in enumerate(pending, 1):
        biz = item["business"]
        channel = item["channel"]
        next_key = item["next_key"]
        days = item["days_since"]

        print(f"  [{i}/{len(pending)}] {biz}")
        print(f"    Channel: {channel} | Next: {next_key} | {days} days since last")

        # Get lead data
        lead = lead_map.get(biz)
        if not lead:
            print(f"    [WARN] Lead not found in enriched data — skipping")
            stats["skipped"] += 1
            continue

        # Merge audit data
        if biz in audit_map:
            lead["audits"] = audit_map[biz].get("audits", {})
            lead["revenue_opportunity"] = audit_map[biz].get("revenue_opportunity", {})

        # Build context
        ctx = build_lead_context(lead)

        if dry_run:
            print(f"    [DRY RUN] Would generate {next_key} for {biz}")
            stats["skipped"] += 1
            continue

        # Generate the follow-up
        print(f"    Generating {next_key}...")
        time.sleep(random.uniform(1, 3))

        if channel == "email":
            result = generate_email_followup(ctx, next_key)
            if "error" in result:
                print(f"    [ERROR] {result['error']}")
                stats["errors"] += 1
                continue

            # Save to the lead's email JSON
            safe_name = biz.replace(" ", "_").replace("/", "_").replace("&", "and")
            email_file = f"results/emails/{safe_name}_emails.json"
            emails = load_json(email_file, {})
            emails[next_key] = result
            save_json(email_file, emails)
            print(
                f"    [OK] Saved {next_key} — Subject: {result.get('subject', '')[:50]}"
            )

        elif channel == "whatsapp":
            result = generate_whatsapp_followup(ctx, next_key)
            if "error" in result:
                print(f"    [ERROR] {result['error']}")
                stats["errors"] += 1
                continue

            # Save to the lead's WhatsApp JSON
            safe_name = biz.replace(" ", "_").replace("/", "_").replace("&", "and")
            wa_file = f"results/messages/whatsapp/{safe_name}_whatsapp.json"
            wa_msgs = load_json(wa_file, {})
            wa_msgs[next_key] = result
            save_json(wa_file, wa_msgs)
            print(
                f"    [OK] Saved {next_key} — Message: {result.get('message', '')[:60]}"
            )

        stats["generated"] += 1
        time.sleep(random.uniform(2, 4))

    # Summary
    print(f"\n{'='*60}")
    print(f"  [FOLLOWUP] COMPLETE")
    print(f"{'='*60}")
    print(f"  Generated: {stats['generated']}")
    print(f"  Skipped:   {stats['skipped']}")
    print(f"  Errors:    {stats['errors']}")
    print(f"{'='*60}\n")

    return stats


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    run_followup_manager(dry_run=dry_run)
