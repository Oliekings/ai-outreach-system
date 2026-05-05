import json
import os
import re
from datetime import datetime
from dotenv import load_dotenv
from anthropic import Anthropic
from groq import Groq

load_dotenv()


def get_ai_response(prompt: str, max_tokens: int = 1000) -> str:
    try:
        claude = Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
        response = claude.messages.create(
            model="claude-opus-4-5",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        if True: # Fallback on any error
            groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
            response = groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        raise e


def load_config() -> dict:
    with open("ceo_config.json", "r") as f:
        return json.load(f)


def load_reply_log() -> dict:
    path = "results/replies/reply_log.json"
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {"replies": [], "stats": {}}


def save_reply_log(log: dict):
    with open("results/replies/reply_log.json", "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# APPROVE AND SEND REPLY
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def approve_reply(message_id: str, edit_body: str = None):
    """
    Approve a pending reply and queue it for sending.
    Optionally provide edited body text.
    """
    log = load_reply_log()

    for reply in log["replies"]:
        if reply.get("message_id") == message_id:
            if edit_body:
                reply["drafted_reply"]["body"] = edit_body
            reply["status"] = "ready_to_send"
            reply["approved_at"] = datetime.now().isoformat()
            save_reply_log(log)
            print(f"âœ… Reply approved for {reply['business']}")
            return True

    print(f"âŒ Reply not found: {message_id}")
    return False


def reject_reply(message_id: str, reason: str = ""):
    """Mark a reply as rejected â€” will not be sent"""
    log = load_reply_log()
    for reply in log["replies"]:
        if reply.get("message_id") == message_id:
            reply["status"] = "rejected"
            reply["rejection_reason"] = reason
            reply["rejected_at"] = datetime.now().isoformat()
            save_reply_log(log)
            print(f"âŒ Reply rejected for {reply['business']}")
            return True
    return False


def approve_all_by_intent(intent: str):
    """Approve all pending replies of a specific intent"""
    log = load_reply_log()
    count = 0
    for reply in log["replies"]:
        if (reply.get("classification", {}).get("intent") == intent and
                reply.get("status") == "pending_review"):
            reply["status"] = "ready_to_send"
            reply["approved_at"] = datetime.now().isoformat()
            count += 1
    save_reply_log(log)
    print(f"âœ… Approved {count} {intent} replies")
    return count


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# NURTURE MANAGER
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def get_nurture_queue() -> list:
    """Get all leads that need nurture follow-ups today"""
    enriched_file = "results/leads/enriched_leads.json"
    if not os.path.exists(enriched_file):
        return []

    with open(enriched_file, "r") as f:
        leads = json.load(f)

    nurture_leads = []
    today = datetime.now()

    for lead in leads:
        if lead.get("status") != "not_interested":
            continue

        nurture_plan = lead.get("nurture_plan") or {}
        touchpoints = nurture_plan.get("touchpoints") or []

        last_reply = lead.get("last_reply_date")
        if not last_reply:
            continue

        last_reply_dt = datetime.fromisoformat(last_reply)

        for tp in touchpoints:
            day_target = tp.get("day", 999)
            days_since = (today - last_reply_dt).days

            if days_since >= day_target:
                # Check if this touchpoint was already sent
                tp_key = f"nurture_day_{day_target}"
                sent_nurtures = lead.get("sent_nurtures") or []
                if tp_key not in sent_nurtures:
                    nurture_leads.append({
                        "lead": lead,
                        "touchpoint": tp,
                        "tp_key": tp_key,
                        "days_since_reply": days_since
                    })

    return nurture_leads


def send_nurture_messages(dry_run: bool = False):
    """Send nurture messages to not-interested leads"""
    import smtplib
    import ssl
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    config = load_config()
    nurture_queue = get_nurture_queue()

    if not nurture_queue:
        print("âœ… No nurture messages due today")
        return

    print(f"\nðŸŒ± NURTURE MANAGER")
    print(f"{'='*55}")
    print(f"Nurture messages due: {len(nurture_queue)}")
    print(f"{'='*55}\n")

    from_name = config["brevo"]["from_name"]
    from_email = config["brevo"]["from_email"]
    smtp_user = os.getenv("BREVO_SMTP_USER")
    smtp_pass = os.getenv("BREVO_SMTP_PASS")

    enriched_file = "results/leads/enriched_leads.json"
    with open(enriched_file, "r") as f:
        all_leads = json.load(f)

    for item in nurture_queue:
        lead = item["lead"]
        tp = item["touchpoint"]
        tp_key = item["tp_key"]

        name = lead["name"]
        to_email = lead.get("contact_email")
        to_wa = lead.get("contact_whatsapp")

        tp_type = tp.get("type", "email")
        subject = tp.get("subject", "Checking in")
        message_preview = tp.get("message_preview", "")
        value_offered = tp.get("value_offered", "")

        print(f"ðŸŒ± {name} â€” Day {tp.get('day')} nurture ({tp_type})")
        print(f"   Value: {value_offered}")

        if dry_run:
            print(f"   ðŸ” DRY RUN â€” Would send: {subject}")
            print(f"   Preview: {message_preview[:100]}...")
            continue

        sent = False

        if tp_type == "email" and to_email:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = f"{from_name} <{from_email}>"
                msg["To"] = to_email
                msg.attach(MIMEText(message_preview, "plain", "utf-8"))

                context = ssl.create_default_context()
                with smtplib.SMTP("smtp-relay.brevo.com", 587) as server:
                    server.ehlo()
                    server.starttls(context=context)
                    server.login(smtp_user, smtp_pass)
                    server.sendmail(from_email, to_email, msg.as_string())
                sent = True
                print(f"   âœ… Nurture email sent to {to_email}")
            except Exception as e:
                print(f"   âŒ Email failed: {str(e)[:60]}")

        # Mark as sent in lead record
        if sent:
            for i, l in enumerate(all_leads):
                if l["name"] == name:
                    if "sent_nurtures" not in all_leads[i]:
                        all_leads[i]["sent_nurtures"] = []
                    all_leads[i]["sent_nurtures"].append(tp_key)
                    break

    with open(enriched_file, "w") as f:
        json.dump(all_leads, f, indent=2, ensure_ascii=False)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# DAILY HANDLER REPORT
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def generate_handler_report() -> str:
    log = load_reply_log()
    all_replies = log.get("replies", [])

    interested = [r for r in all_replies if r.get("classification", {}).get("intent") == "interested"]
    pending = [r for r in all_replies if r.get("status") == "pending_review"]
    ready = [r for r in all_replies if r.get("status") == "ready_to_send"]
    replied = [r for r in all_replies if r.get("status") == "replied"]

    report = f"""
â•”{'â•'*52}â•—
â•‘  REPLY HANDLER REPORT                            â•‘
â•‘  {datetime.now().strftime('%d %b %Y, %I:%M %p'):<48}  â•‘
â•š{'â•'*52}â•

REPLY STATISTICS
â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”
Total replies received:    {len(all_replies)}
ðŸ”¥ Interested leads:       {len(interested)}
â³ Pending review:         {len(pending)}
ðŸ“¤ Ready to send:          {len(ready)}
âœ… Already replied:        {len(replied)}
"""

    if interested:
        report += "\nðŸ”¥ HOT LEADS â€” NEEDS YOUR ATTENTION:\n"
        report += "â”" * 52 + "\n"
        for r in interested:
            report += f"  â€¢ {r['business']}\n"
            report += f"    From: {r['from_email']}\n"
            report += f"    Received: {r['date_received'][:10]}\n"
            if r.get("drafted_reply", {}).get("body"):
                report += f"    Draft ready: âœ…\n"
            report += f"    Status: {r['status']}\n\n"

    if pending:
        report += "\nâ³ PENDING REVIEW:\n"
        report += "â”" * 52 + "\n"
        for r in pending[:5]:
            report += f"  â€¢ {r['business']} â€” {r.get('classification',{}).get('intent','?')}\n"

    report += "\n" + "â•" * 52 + "\n"
    return report


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# ENTRY POINT
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if __name__ == "__main__":
    import sys

    if "--report" in sys.argv:
        print(generate_handler_report())

    elif "--approve-all-interested" in sys.argv:
        approve_all_by_intent("interested")

    elif "--approve-all-questions" in sys.argv:
        approve_all_by_intent("question")

    elif "--nurture" in sys.argv:
        dry_run = "--dry-run" in sys.argv
        send_nurture_messages(dry_run=dry_run)

    elif "--send" in sys.argv:
        from .reply_monitor import send_queued_replies
        dry_run = "--dry-run" in sys.argv
        send_queued_replies(dry_run=dry_run)

    else:
        print(generate_handler_report())
