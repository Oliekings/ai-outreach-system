import json
import os
import re
from datetime import datetime

from dotenv import load_dotenv
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from response_management.shared import load_reply_log, save_reply_log

from utils.ai_client import ai_response as get_ai_response

load_dotenv()

sys.stdout.reconfigure(encoding='utf-8')



def load_config() -> dict:
    with open("ceo_config.json", "r", encoding="utf-8") as f:
        return json.load(f)



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
    print(f"✅ Approved {count} {intent} replies")
    return count


def auto_approve_pending_replies(deadline_hours: int = 12) -> int:
    """
    Automatically transition pending review replies to ready_to_send if they 
    have been in the queue for longer than the review deadline.
    """
    log = load_reply_log()
    count = 0
    now = datetime.now()
    
    for reply in log.get("replies", []):
        if reply.get("status") == "pending_review":
            processed_str = reply.get("date_processed")
            if not processed_str:
                continue
            try:
                processed_dt = datetime.fromisoformat(processed_str)
                elapsed = now - processed_dt
                if elapsed.total_seconds() > (deadline_hours * 3600):
                    reply["status"] = "ready_to_send"
                    reply["approved_at"] = now.isoformat()
                    reply["action_taken"] = f"Auto-approved by AI CEO (Deadline {deadline_hours}h passed)"
                    print(f"🤖 Auto-approved reply for {reply.get('business')} ({elapsed.total_seconds() / 3600:.1f}h elapsed)")
                    count += 1
            except Exception as e:
                print(f"⚠️ Error parsing date_processed for {reply.get('business')}: {e}")
                
    if count > 0:
        save_reply_log(log)
        
    return count


# ——————————————————————————————————————————————————————————————————————————————————————————————————
# NURTURE MANAGER
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def get_nurture_queue() -> list:
    """Get all leads that need nurture follow-ups today"""
    enriched_file = "results/leads/enriched_leads.json"
    if not os.path.exists(enriched_file):
        return []

    with open(enriched_file, "r", encoding="utf-8") as f:
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
    with open(enriched_file, "r", encoding="utf-8") as f:
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

    with open(enriched_file, "w", encoding="utf-8") as f:
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

    elif "--auto-approve" in sys.argv:
        config = load_config()
        review_deadline_hours = config.get("owner", {}).get("review_deadline_hours", 12)
        auto_approve_pending_replies(review_deadline_hours)

    elif "--nurture" in sys.argv:
        dry_run = "--dry-run" in sys.argv
        send_nurture_messages(dry_run=dry_run)

    elif "--send" in sys.argv:
        from response_management.reply_monitor import send_queued_replies
        dry_run = "--dry-run" in sys.argv
        send_queued_replies(dry_run=dry_run)

    else:
        print(generate_handler_report())
