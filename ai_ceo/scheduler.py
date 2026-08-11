import json
import os
import re
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
from utils.symbols import Symbol

load_dotenv()

sys.stdout.reconfigure(encoding="utf-8")


def load_config() -> dict:
    with open("ceo_config.json", "r", encoding="utf-8") as f:
        return json.load(f)


def load_all_logs() -> dict:
    logs = {}
    log_files = {
        "emails": "results/logs/send_log.json",
        "whatsapp": "results/logs/whatsapp_log.json",
        "instagram": "results/logs/instagram_log.json",
        "facebook": "results/logs/facebook_log.json",
        "replies": "results/replies/reply_log.json",
    }
    for key, path in log_files.items():
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                logs[key] = json.load(f)
        else:
            logs[key] = {}
    return logs


def load_enriched_leads() -> list:
    path = "results/leads/enriched_leads.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


# ─────────────────────────────────────────────────────────────────────────────
# SCHEDULE BUILDER
# builds the complete day plan for what needs to go out
# ─────────────────────────────────────────────────────────────────────────────
def build_daily_schedule() -> dict:
    config = load_config()
    logs = load_all_logs()
    leads = load_enriched_leads()
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")

    schedule = {
        "date": today,
        "generated_at": now.isoformat(),
        "send_window": {
            "start": config["outreach"]["send_hours"]["start"],
            "end": config["outreach"]["send_hours"]["end"],
            "days": config["outreach"]["send_days"],
        },
        "tasks": [],
        "summary": {},
    }

    # ── Email tasks
    email_log = logs.get("emails", {})
    email_entries = email_log.get("emails", [])
    daily_email_limit = config["outreach"]["daily_email_limit"]
    emails_sent_today = sum(
        1
        for e in email_entries
        if e.get("date", "").startswith(today) and e.get("success")
    )
    emails_remaining = max(0, daily_email_limit - emails_sent_today)

    # ── WhatsApp tasks
    wa_log = logs.get("whatsapp", {})
    wa_entries = wa_log.get("messages", [])
    daily_wa_limit = config["outreach"]["daily_whatsapp_limit"]
    wa_sent_today = sum(
        1
        for e in wa_entries
        if e.get("date", "").startswith(today) and e.get("success")
    )
    wa_remaining = max(0, daily_wa_limit - wa_sent_today)

    # ── Instagram tasks
    ig_log = logs.get("instagram", {})
    ig_entries = ig_log.get("messages", [])
    daily_ig_limit = config["outreach"]["daily_instagram_limit"]
    ig_sent_today = sum(
        1
        for e in ig_entries
        if e.get("date", "").startswith(today) and e.get("success")
    )
    ig_remaining = max(0, daily_ig_limit - ig_sent_today)

    # ── Facebook tasks
    fb_log = logs.get("facebook", {})
    fb_entries = fb_log.get("messages", [])
    daily_fb_limit = config["outreach"]["daily_facebook_limit"]
    fb_sent_today = sum(
        1
        for e in fb_entries
        if e.get("date", "").startswith(today) and e.get("success")
    )
    fb_remaining = max(0, daily_fb_limit - fb_sent_today)

    # ── Reply tasks
    reply_log = logs.get("replies", {})
    pending_replies = [
        r
        for r in reply_log.get("replies", [])
        if r.get("status") in ["pending_review", "ready_to_send"]
    ]
    interested_replies = [
        r
        for r in pending_replies
        if r.get("classification", {}).get("intent") == "interested"
    ]

    # ── Leads needing action
    leads_needing_email = [
        l
        for l in leads
        if l.get("contact_email")
        and l.get("status") not in ["not_interested", "replied", "closed"]
        and not _all_emails_sent(l["name"], email_entries)
    ]

    leads_needing_wa = [
        l
        for l in leads
        if l.get("contact_whatsapp")
        and l.get("status") not in ["not_interested", "replied", "closed"]
        and not _all_wa_sent(l["name"], wa_entries)
    ]

    leads_needing_ig = [
        l
        for l in leads
        if l.get("instagram", {}).get("found")
        and l.get("status") not in ["not_interested", "replied", "closed"]
        and not _all_ig_sent(l["name"], ig_entries)
    ]

    leads_needing_fb = [
        l
        for l in leads
        if l.get("facebook", {}).get("found")
        and l.get("status") not in ["not_interested", "replied", "closed"]
        and not _all_fb_sent(l["name"], fb_entries)
    ]

    # ── Build task list with priorities
    # Priority 1 — Reply to interested leads
    if interested_replies:
        schedule["tasks"].append(
            {
                "priority": 1,
                "type": "send_replies",
                "label": "Reply to interested leads",
                "count": len(interested_replies),
                "leads": [r["business"] for r in interested_replies],
                "command": "python response_management/reply_monitor.py --send",
                "urgency": "critical",
                "reason": f"{len(interested_replies)} hot lead(s) waiting for a reply",
            }
        )

    # Priority 2 — Process inbox
    schedule["tasks"].append(
        {
            "priority": 2,
            "type": "check_replies",
            "label": "Check inbox for new replies",
            "command": "python response_management/reply_monitor.py",
            "urgency": "high",
            "reason": "Daily inbox check to catch any new responses",
        }
    )

    # Priority 3 — WhatsApp (highest response rate in Nigeria)
    if wa_remaining > 0 and leads_needing_wa:
        to_send = min(wa_remaining, len(leads_needing_wa))
        schedule["tasks"].append(
            {
                "priority": 3,
                "type": "whatsapp",
                "label": f"Send WhatsApp messages ({to_send} leads)",
                "count": to_send,
                "leads": [l["name"] for l in leads_needing_wa[:to_send]],
                "command": "python outreach/whatsapp_sender.py",
                "urgency": "high",
                "reason": f"{wa_remaining} slots remaining of {daily_wa_limit} daily limit",
            }
        )

    # Priority 4 — Email outreach
    if emails_remaining > 0 and leads_needing_email:
        to_send = min(emails_remaining, len(leads_needing_email))
        schedule["tasks"].append(
            {
                "priority": 4,
                "type": "email",
                "label": f"Send emails ({to_send} leads)",
                "count": to_send,
                "leads": [l["name"] for l in leads_needing_email[:to_send]],
                "command": "python outreach/email_sender.py",
                "urgency": "medium",
                "reason": f"{emails_remaining} slots remaining of {daily_email_limit} daily limit",
            }
        )

    # Priority 5 — Instagram DMs
    if ig_remaining > 0 and leads_needing_ig:
        to_send = min(ig_remaining, len(leads_needing_ig))
        schedule["tasks"].append(
            {
                "priority": 5,
                "type": "instagram",
                "label": f"Send Instagram DMs ({to_send} leads)",
                "count": to_send,
                "leads": [l["name"] for l in leads_needing_ig[:to_send]],
                "command": "python outreach/instagram_sender.py",
                "urgency": "medium",
                "reason": f"{ig_remaining} slots remaining of {daily_ig_limit} daily limit",
            }
        )

    # Priority 6 — Facebook messages
    if fb_remaining > 0 and leads_needing_fb:
        to_send = min(fb_remaining, len(leads_needing_fb))
        schedule["tasks"].append(
            {
                "priority": 6,
                "type": "facebook",
                "label": f"Send Facebook messages ({to_send} leads)",
                "count": to_send,
                "leads": [l["name"] for l in leads_needing_fb[:to_send]],
                "command": "python outreach/facebook_sender.py",
                "urgency": "low",
                "reason": f"{fb_remaining} slots remaining of {daily_fb_limit} daily limit",
            }
        )

    # Priority 7 — Find new leads if running low
    total_active = len(
        [l for l in leads if l.get("status") not in ["not_interested", "closed"]]
    )
    if total_active < 15:
        schedule["tasks"].append(
            {
                "priority": 7,
                "type": "find_leads",
                "label": "Find new leads — pipeline running low",
                "command": "python intelligence/lead_finder.py",
                "urgency": "medium",
                "reason": f"Only {total_active} active leads in pipeline",
            }
        )

    # ── Summary
    schedule["summary"] = {
        "total_tasks": len(schedule["tasks"]),
        "critical_tasks": len(
            [t for t in schedule["tasks"] if t.get("urgency") == "critical"]
        ),
        "emails_sent_today": emails_sent_today,
        "emails_remaining": emails_remaining,
        "wa_sent_today": wa_sent_today,
        "wa_remaining": wa_remaining,
        "ig_sent_today": ig_sent_today,
        "ig_remaining": ig_remaining,
        "fb_sent_today": fb_sent_today,
        "fb_remaining": fb_remaining,
        "pending_replies": len(pending_replies),
        "interested_leads": len(interested_replies),
        "total_active_leads": total_active,
        "total_leads": len(leads),
    }

    # Save schedule
    os.makedirs("results/ceo", exist_ok=True)
    schedule_path = f"results/ceo/schedule_{today}.json"
    with open(schedule_path, "w", encoding="utf-8") as f:
        json.dump(schedule, f, indent=2, ensure_ascii=False)

    return schedule


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _all_emails_sent(business_name: str, email_entries: list) -> bool:
    sent_keys = {
        e["email_key"]
        for e in email_entries
        if e.get("business") == business_name and e.get("success")
    }
    return {"email_1", "email_2", "email_3"}.issubset(sent_keys)


def _all_wa_sent(business_name: str, wa_entries: list) -> bool:
    sent_keys = {
        e["msg_key"]
        for e in wa_entries
        if e.get("business") == business_name and e.get("success")
    }
    return {"wa_1", "wa_2", "wa_3"}.issubset(sent_keys)


def _all_ig_sent(business_name: str, ig_entries: list) -> bool:
    sent_keys = {
        e["msg_key"]
        for e in ig_entries
        if e.get("business") == business_name and e.get("success")
    }
    return {"ig_1", "ig_2"}.issubset(sent_keys)


def _all_fb_sent(business_name: str, fb_entries: list) -> bool:
    sent_keys = {
        e["msg_key"]
        for e in fb_entries
        if e.get("business") == business_name and e.get("success")
    }
    return {"fb_1", "fb_2"}.issubset(sent_keys)


def print_schedule(schedule: dict):
    print(f"\n{'═'*60}")
    print(f"  {Symbol.TIME} DAILY SCHEDULE — {schedule['date']}")
    print(
        f"  Send window: {schedule['send_window']['start']}:00 — {schedule['send_window']['end']}:00"
    )
    print(f"{'═'*60}")

    summary = schedule["summary"]
    print(f"\n  📊 PIPELINE STATUS")
    print(f"  {'─'*56}")
    print(
        f"  Active leads:        {summary['total_active_leads']}/{summary['total_leads']}"
    )
    print(f"  Interested replies:  {summary['interested_leads']} 🔥")
    print(f"  Pending reviews:     {summary['pending_replies']}")
    print(f"\n  TODAY'S SEND STATUS")
    print(f"  {'─'*56}")
    print(
        f"  Emails:    {summary['emails_sent_today']} sent / {summary['emails_remaining']} remaining"
    )
    print(
        f"  WhatsApp:  {summary['wa_sent_today']} sent / {summary['wa_remaining']} remaining"
    )
    print(
        f"  Instagram: {summary['ig_sent_today']} sent / {summary['ig_remaining']} remaining"
    )
    print(
        f"  Facebook:  {summary['fb_sent_today']} sent / {summary['fb_remaining']} remaining"
    )

    print(f"\n  {Symbol.LIST} TASKS FOR TODAY ({summary['total_tasks']} total)")
    print(f"  {'─'*56}")
    for task in schedule["tasks"]:
        urgency_icon = {
            "critical": "🔴",
            "high": "🟡",
            "medium": "🔵",
            "low": "⚪",
        }.get(task.get("urgency", "low"), "⚪")
        print(f"\n  {urgency_icon} [{task['priority']}] {task['label']}")
        print(f"     Reason: {task['reason']}")
        print(f"     Run:    {task['command']}")

    print(f"\n{'═'*60}\n")
