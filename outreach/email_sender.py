import json
import os
import re
import time
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import requests

load_dotenv()
import sys
import pathlib
# Ensure project root is on sys.path so 'from outreach.x import ...' always works
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding='utf-8')

os.makedirs("results/sent", exist_ok=True)
os.makedirs("results/sent/emails", exist_ok=True)
os.makedirs("results/logs", exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG LOADER
# ─────────────────────────────────────────────────────────────────────────────
def load_config() -> dict:
    with open("ceo_config.json", "r", encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────────────
# SEND LOG
# ─────────────────────────────────────────────────────────────────────────────
def load_send_log() -> dict:
    log_path = "results/logs/send_log.json"
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"emails": [], "stats": {"sent": 0, "failed": 0, "skipped": 0}}


def save_send_log(log: dict):
    with open("results/logs/send_log.json", "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def already_sent(log: dict, email: str, business_name: str, email_key: str) -> bool:
    for entry in log["emails"]:
        if (entry["to"] == email and
            entry["business"] == business_name and
            entry["email_key"] == email_key):
            return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# EMAIL RENDERER — converts plain text to beautiful HTML
# ─────────────────────────────────────────────────────────────────────────────
def render_html_email(subject: str, body: str, business_name: str,
                      sender_name: str, site_link: str = None) -> str:
    # Convert line breaks to paragraphs
    paragraphs = [p.strip() for p in body.split('\n') if p.strip()]
    body_html = "".join(f"<p>{p}</p>" for p in paragraphs)

    site_section = ""
    if site_link:
        site_section = f"""
        <div style="background:#F0F7FF;border-radius:12px;padding:20px;margin:24px 0;text-align:center;">
            <p style="margin:0 0 12px;font-weight:600;color:#1A3A5C;">
                🌐 We built you a free sample website
            </p>
            <a href="{site_link}"
               style="background:#1A3A5C;color:white;padding:12px 28px;border-radius:50px;
                      text-decoration:none;font-weight:600;font-size:14px;display:inline-block;">
                View Your Sample Website →
            </a>
        </div>
        """

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;background:#F5F5F5;font-family:'Segoe UI',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0">
<tr><td align="center" style="padding:40px 20px;">
<table width="600" cellpadding="0" cellspacing="0"
       style="background:white;border-radius:16px;overflow:hidden;
              box-shadow:0 4px 20px rgba(0,0,0,0.08);max-width:600px;width:100%;">

    <!-- Header -->
    <tr>
        <td style="background:linear-gradient(135deg,#1A3A5C,#2E6B9E);
                   padding:32px 40px;text-align:center;">
            <h1 style="margin:0;color:white;font-size:22px;font-weight:700;
                       letter-spacing:-0.5px;">{sender_name}</h1>
            <p style="margin:6px 0 0;color:rgba(255,255,255,0.7);font-size:13px;">
                Digital Growth Partner
            </p>
        </td>
    </tr>

    <!-- Body -->
    <tr>
        <td style="padding:40px;">
            <div style="color:#2D2D2D;font-size:15px;line-height:1.8;">
                {body_html}
            </div>
            {site_section}
        </td>
    </tr>

    <!-- Footer -->
    <tr>
        <td style="background:#F8F9FA;padding:24px 40px;border-top:1px solid #E5E7EB;">
            <p style="margin:0;color:#9CA3AF;font-size:12px;text-align:center;">
                You received this email because we researched {business_name}
                and genuinely believe we can help.<br>
                <a href="mailto:{os.getenv('BREVO_SMTP_USER', '')}"
                   style="color:#6B7280;text-decoration:none;">Unsubscribe</a>
            </p>
        </td>
    </tr>

</table>
</td></tr>
</table>
</body>
</html>
"""
    return html


# ─────────────────────────────────────────────────────────────────────────────
# BREVO SMTP SENDER
# ─────────────────────────────────────────────────────────────────────────────
def send_via_brevo_smtp(
    to_email: str,
    subject: str,
    body_text: str,
    body_html: str,
    from_name: str,
    from_email: str,
    reply_to: str = None,
    attachment_path: str = None
) -> dict:
    result = {"success": False, "method": "brevo_smtp", "error": None}

    try:
        smtp_user = os.getenv("BREVO_SMTP_USER")
        smtp_pass = os.getenv("BREVO_SMTP_PASS")

        if not smtp_user or not smtp_pass:
            result["error"] = "Brevo SMTP credentials not configured"
            return result

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{from_name} <{from_email}>"
        msg["To"] = to_email
        msg["Reply-To"] = reply_to or from_email

        # Attach plain text and HTML
        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        # Attach file if provided (e.g. audit report or site screenshot)
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, "rb") as f:
                attachment = MIMEBase("application", "octet-stream")
                attachment.set_payload(f.read())
                encoders.encode_base64(attachment)
                filename = os.path.basename(attachment_path)
                attachment.add_header(
                    "Content-Disposition", f"attachment; filename={filename}"
                )
                msg.attach(attachment)

        context = ssl.create_default_context()
        with smtplib.SMTP("smtp-relay.brevo.com", 587) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, to_email, msg.as_string())

        result["success"] = True

    except smtplib.SMTPRecipientsRefused:
        result["error"] = "Recipient refused — email may not exist"
    except smtplib.SMTPAuthenticationError:
        result["error"] = "Brevo authentication failed — check credentials"
    except Exception as e:
        result["error"] = str(e)[:100]

    return result


# ─────────────────────────────────────────────────────────────────────────────
# BREVO API SENDER (fallback)
# ─────────────────────────────────────────────────────────────────────────────
def send_via_brevo_api(
    to_email: str,
    to_name: str,
    subject: str,
    body_html: str,
    from_name: str,
    from_email: str,
) -> dict:
    result = {"success": False, "method": "brevo_api", "error": None}

    try:
        api_key = os.getenv("BREVO_API_KEY")
        if not api_key:
            result["error"] = "Brevo API key not configured"
            return result

        payload = {
            "sender": {"name": from_name, "email": from_email},
            "to": [{"email": to_email, "name": to_name}],
            "subject": subject,
            "htmlContent": body_html,
        }

        response = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "api-key": api_key,
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=15
        )

        if response.status_code in [200, 201]:
            result["success"] = True
        else:
            result["error"] = f"API error {response.status_code}: {response.text[:100]}"

    except Exception as e:
        result["error"] = str(e)[:100]

    return result


# ─────────────────────────────────────────────────────────────────────────────
# TIMING CHECKER
# ─────────────────────────────────────────────────────────────────────────────
def is_good_send_time(config: dict) -> tuple:
    now = datetime.now()
    day = now.strftime("%A")
    hour = now.hour

    send_days = config["outreach"].get("send_days", [
        "Monday", "Tuesday", "Wednesday", "Thursday"
    ])
    send_start = config["outreach"].get("send_hours", {}).get("start", 9)
    send_end = config["outreach"].get("send_hours", {}).get("end", 12)

    is_good_day = day in send_days
    is_good_hour = send_start <= hour <= send_end

    if not is_good_day:
        return False, f"Today is {day} — not in send days {send_days}"
    if not is_good_hour:
        return False, f"Current hour {hour}:00 — outside send window {send_start}:00-{send_end}:00"

    return True, "Good time to send"


# ─────────────────────────────────────────────────────────────────────────────
# DAILY LIMIT CHECKER
# ─────────────────────────────────────────────────────────────────────────────
def get_todays_send_count(log: dict) -> int:
    today = datetime.now().strftime("%Y-%m-%d")
    return sum(
        1 for e in log["emails"]
        if e.get("date", "").startswith(today) and e.get("success")
    )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN SENDER
# ─────────────────────────────────────────────────────────────────────────────
def send_email_sequence(
    lead_name: str,
    force: bool = False,
    dry_run: bool = False,
    ignore_timing: bool = False
) -> dict:
    """
    Send the appropriate email in the sequence for a specific lead.
    Respects timing, daily limits, and never double-sends.
    """
    config = load_config()
    log = load_send_log()

    from_name = config["brevo"]["from_name"]
    from_email = config["brevo"]["from_email"]
    reply_to = config["brevo"].get("reply_to", from_email)
    daily_limit = config["outreach"]["daily_email_limit"]

    result = {
        "lead": lead_name,
        "action": None,
        "success": False,
        "reason": None
    }

    # Check timing
    if not force and not ignore_timing:
        good_time, reason = is_good_send_time(config)
        if not good_time:
            result["reason"] = reason
            result["action"] = "skipped_timing"
            return result

    # Check daily limit — always enforced regardless of --ignore-timing
    todays_count = get_todays_send_count(log)
    if todays_count >= daily_limit and not force:
        result["reason"] = f"Daily limit reached ({todays_count}/{daily_limit})"
        result["action"] = "skipped_limit"
        return result

    # Load the email sequence for this lead
    safe_name = lead_name.replace(" ", "_").replace("/", "_").replace("&", "and")
    email_file = f"results/emails/{safe_name}_emails.json"

    if not os.path.exists(email_file):
        result["reason"] = "No email sequence found for this lead"
        result["action"] = "skipped_no_file"
        return result

    with open(email_file, "r", encoding="utf-8") as f:
        emails = json.load(f)

    # Load enriched lead data
    enriched_file = "results/leads/enriched_leads.json"
    lead_data = {}
    if os.path.exists(enriched_file):
        with open(enriched_file, "r", encoding="utf-8") as f:
            all_leads = json.load(f)
        for l in all_leads:
            if l["name"] == lead_name:
                lead_data = l
                break

    # Gather all emails associated with this organization
    emails_to_try = []
    contact_email = lead_data.get("contact_email")
    if contact_email:
        emails_to_try.append(contact_email)
    
    all_emails = lead_data.get("all_emails", [])
    if isinstance(all_emails, list):
        for e in all_emails:
            if e and isinstance(e, str):
                emails_to_try.append(e)
    elif isinstance(all_emails, str) and all_emails:
        emails_to_try.append(all_emails)

    # Deduplicate while preserving order
    emails_to_try = list(dict.fromkeys(emails_to_try))

    if not emails_to_try:
        result["reason"] = "No email addresses found for this lead"
        result["action"] = "skipped_no_email"
        return result

    # Load sequence for human review check
    seq_path = f"results/messages/sequences/{safe_name}_sequence.json"
    sequence = []
    if os.path.exists(seq_path):
        with open(seq_path, "r", encoding="utf-8") as f:
            sequence = json.load(f)
    email_seq_items = [m for m in sequence if m.get("channel") == "email"]
    require_human = config.get("quality", {}).get("require_human_review", True)

    # Determine which email to send next
    email_order = ["email_1", "email_2", "email_3"]
    email_to_send = None
    email_key = None
    unsent_emails = []

    for key in email_order:
        if key not in emails:
            continue
        
        # Check which of the emails have not been sent yet for this key
        key_unsent = [e for e in emails_to_try if not already_sent(log, e, lead_name, key)]
        
        if key_unsent:
            # Check human approval if required
            if require_human and not force:
                email_idx = int(key.split("_")[1]) - 1
                if email_idx < len(email_seq_items):
                    status = email_seq_items[email_idx].get("status", "queued")
                    if status != "approved":
                        result["reason"] = f"Awaiting human approval (status is '{status}')"
                        result["action"] = "skipped_awaiting_approval"
                        return result

            # Check if enough days have passed since last email
            last_sent = None
            for entry in reversed(log["emails"]):
                if entry["business"] == lead_name and entry["success"]:
                    last_sent = entry.get("date")
                    break

            if last_sent and not force:
                last_sent_dt = datetime.fromisoformat(last_sent)
                days_since = (datetime.now() - last_sent_dt).days
                min_days = {"email_1": 0, "email_2": 4, "email_3": 7}
                if days_since < min_days.get(key, 0):
                    result["reason"] = f"Too soon — {days_since} days since last email (need {min_days[key]})"
                    result["action"] = "skipped_too_soon"
                    return result

            email_to_send = emails[key]
            email_key = key
            unsent_emails = key_unsent
            break

    if not email_to_send:
        result["reason"] = "All emails in sequence already sent to all addresses"
        result["action"] = "sequence_complete"
        return result

    subject = email_to_send.get("subject", "")
    body_text = email_to_send.get("body", "")

    from outreach.message_writer import clean_message_content
    body_text = clean_message_content(body_text, default_option=2)

    if not subject or not body_text:
        result["reason"] = "Email content is empty"
        result["action"] = "skipped_empty"
        return result

    # Check if there's a sample site to include
    site_link = None
    if email_key in ["email_2", "email_3"]:
        site_safe_name = re.sub(r'[^a-z0-9]', '-', lead_name.lower()).strip('-')
        site_path = f"results/sites/{site_safe_name}.html"
        if os.path.exists(site_path):
            site_link = f"[SAMPLE SITE: {site_path}]"

    # Render HTML
    body_html = render_html_email(
        subject=subject,
        body=body_text,
        business_name=lead_name,
        sender_name=from_name,
        site_link=site_link
    )

    any_success = False
    last_error = None
    sends_attempted = 0

    for idx, to_email in enumerate(unsent_emails):
        # Check daily limit BEFORE each email send in case we hit it mid-loop
        todays_count = get_todays_send_count(log)
        if todays_count >= daily_limit and not force:
            print(f"   🛑 Daily limit reached mid-loop ({todays_count}/{daily_limit})")
            if not last_error:
                last_error = f"Daily limit reached ({todays_count}/{daily_limit})"
            break

        # Dry run — just preview
        if dry_run:
            print(f"\n   📧 DRY RUN — Would send {email_key} to {to_email}")
            print(f"   Subject: {subject}")
            print(f"   Body preview: {body_text[:150]}...")
            any_success = True
            sends_attempted += 1
            continue

        # Human-like random delay before sending
        if idx > 0 or sends_attempted > 0:
            delay = random.uniform(20, 60)
            print(f"   ⏳ Waiting {delay:.0f}s before sending to next address {to_email} (human-like)...")
            time.sleep(delay)
        else:
            delay = random.uniform(30, 120)
            print(f"   ⏳ Waiting {delay:.0f}s before sending to {to_email} (human-like)...")
            time.sleep(delay)

        print(f"   📧 Sending {email_key} to {to_email}...")
        send_result = send_via_brevo_smtp(
            to_email=to_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            from_name=from_name,
            from_email=from_email,
            reply_to=reply_to
        )

        if not send_result["success"]:
            print(f"   ⚠️  SMTP failed: {send_result['error']} — trying API...")
            send_result = send_via_brevo_api(
                to_email=to_email,
                to_name=lead_name,
                subject=subject,
                body_html=body_html,
                from_name=from_name,
                from_email=from_email
            )

        # Log the send
        log_entry = {
            "business": lead_name,
            "to": to_email,
            "email_key": email_key,
            "subject": subject,
            "message": body_text,  # SAVE FULL MESSAGE TEXT
            "date": datetime.now().isoformat(),
            "success": send_result["success"],
            "method": send_result["method"],
            "error": send_result.get("error")
        }
        log["emails"].append(log_entry)
        sends_attempted += 1

        if send_result["success"]:
            log["stats"]["sent"] = log["stats"].get("sent", 0) + 1
            print(f"   ✅ Sent successfully to {to_email} via {send_result['method']}")
            any_success = True
        else:
            log["stats"]["failed"] = log["stats"].get("failed", 0) + 1
            print(f"   ❌ Failed to send to {to_email}: {send_result.get('error')}")
            last_error = send_result.get("error")

        # Save send log after each send
        save_send_log(log)

    if sends_attempted == 0:
        result["action"] = "skipped_limit"
        result["success"] = False
        result["reason"] = f"Daily limit reached ({get_todays_send_count(log)}/{daily_limit})"
        return result

    if any_success:
        # Update sequence status to 'sent' in sequence files if successful
        try:
            # 1. Update individual sequence file
            if os.path.exists(seq_path):
                with open(seq_path, "r", encoding="utf-8") as f:
                    seq_data = json.load(f)
                email_idx = int(email_key.split("_")[1]) - 1
                curr_idx = 0
                for msg in seq_data:
                    if msg.get("channel") == "email":
                        if curr_idx == email_idx:
                            msg["status"] = "sent"
                            break
                        curr_idx += 1
                with open(seq_path, "w", encoding="utf-8") as f:
                    json.dump(seq_data, f, indent=2, ensure_ascii=False)
            
            # 2. Update master sequence file
            master_seq_path = "results/messages/sequences/master_sequence.json"
            if os.path.exists(master_seq_path):
                with open(master_seq_path, "r", encoding="utf-8") as f:
                    master_seq = json.load(f)
                for lead_seq in master_seq:
                    if lead_seq.get("lead") == lead_name:
                        email_idx = int(email_key.split("_")[1]) - 1
                        curr_idx = 0
                        for msg in lead_seq.get("sequence", []):
                            if msg.get("channel") == "email":
                                if curr_idx == email_idx:
                                    msg["status"] = "sent"
                                    break
                                curr_idx += 1
                with open(master_seq_path, "w", encoding="utf-8") as f:
                    json.dump(master_seq, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"   ⚠️  Failed to update sequence status: {e}")

    result["action"] = f"sent_{email_key}"
    result["success"] = any_success
    result["reason"] = None if any_success else last_error
    return result


# ─────────────────────────────────────────────────────────────────────────────
# BATCH SENDER — session-based: 2 per session, 30-60 min between sessions
# ─────────────────────────────────────────────────────────────────────────────
def send_all_emails(dry_run: bool = False, force: bool = False, ignore_timing: bool = False):
    config = load_config()
    daily_limit = config["outreach"]["daily_email_limit"]
    session_size = 2          # emails per session
    session_wait_min = 30 * 60   # 30 minutes in seconds
    session_wait_max = 60 * 60   # 60 minutes in seconds

    # Load all leads with emails
    enriched_file = "results/leads/enriched_leads.json"
    if not os.path.exists(enriched_file):
        print("❌ No enriched leads found")
        return

    with open(enriched_file, "r", encoding="utf-8") as f:
        leads = json.load(f)

    leads_with_email = [l for l in leads if l.get("contact_email")]

    print(f"\n📧 EMAIL SENDER")
    print(f"{'='*55}")
    print(f"Leads with emails:  {len(leads_with_email)}")
    print(f"Daily limit:        {daily_limit}")
    print(f"Session size:       {session_size}")
    print(f"Session wait:       30-60 min")
    print(f"Dry run:            {dry_run}")
    print(f"{'='*55}\n")

    # Timing check (bypassed only by --ignore-timing or --force)
    if not force and not ignore_timing and not dry_run:
        good_time, reason = is_good_send_time(config)
        if not good_time:
            print(f"⏰ {reason}")
            print(f"   Run with --force or --ignore-timing to override timing")
            return

    stats = {"sent": 0, "failed": 0, "skipped": 0, "complete": 0}
    lead_index = 0        # tracks position in lead list across sessions
    session_num = 0

    while lead_index < len(leads_with_email):
        # Re-read log + count fresh each session (picks up new sends from this run)
        log = load_send_log()
        todays_count = get_todays_send_count(log)

        # Daily limit always enforced
        if todays_count >= daily_limit and not force:
            print(f"\n🛑 Daily limit reached ({todays_count}/{daily_limit}) — stopping")
            break

        # Timing guard: stop sessions outside send window
        if not force and not ignore_timing and not dry_run:
            good_time, reason = is_good_send_time(config)
            if not good_time:
                print(f"\n⏰ Outside send window — {reason} — stopping")
                break

        session_num += 1
        remaining_today = daily_limit - todays_count
        this_session = min(session_size, remaining_today)
        print(f"\n{'─'*55}")
        print(f"📬 Session {session_num}  |  Sent today: {todays_count}/{daily_limit}  |  Sending up to {this_session} now")
        print(f"{'─'*55}")

        sent_this_session = 0

        while sent_this_session < this_session and lead_index < len(leads_with_email):
            lead = leads_with_email[lead_index]
            lead_index += 1
            name = lead["name"]

            print(f"\n  [{lead_index}/{len(leads_with_email)}] {name}")

            result = send_email_sequence(
                lead_name=name,
                force=force,
                dry_run=dry_run,
                ignore_timing=ignore_timing
            )

            if result["success"]:
                stats["sent"] += 1
                sent_this_session += 1
            elif result["action"] == "sequence_complete":
                stats["complete"] += 1
                print(f"   ✅ Sequence complete")
            elif result["action"] == "skipped_limit":
                # Hit limit mid-session — stop immediately
                print(f"   🛑 Daily limit hit — stopping session")
                lead_index = len(leads_with_email)  # force outer loop exit
                break
            elif result["action"] and "skipped" in result["action"]:
                stats["skipped"] += 1
                print(f"   ⏭️  Skipped: {result['reason']}")
            else:
                stats["failed"] += 1

            # Short gap between individual sends within a session (human-like)
            if sent_this_session < this_session and lead_index < len(leads_with_email):
                gap = random.uniform(20, 60)
                print(f"   ⏳ {gap:.0f}s before next in session...")
                if not dry_run:
                    time.sleep(gap)

        print(f"\n  ✔ Session {session_num} done — sent {sent_this_session} email(s)")

        # Check if we should wait for the next session
        if lead_index < len(leads_with_email) and not dry_run:
            # Recheck daily limit before deciding to wait
            log = load_send_log()
            if get_todays_send_count(log) >= daily_limit and not force:
                print(f"🛑 Daily limit reached — no more sessions today")
                break

            wait_secs = random.uniform(session_wait_min, session_wait_max)
            wait_mins = wait_secs / 60
            resume_at = (datetime.now() + timedelta(seconds=wait_secs)).strftime("%I:%M %p")
            print(f"\n⏳ Waiting {wait_mins:.0f} min before next session (resumes ~{resume_at})...")
            time.sleep(wait_secs)
        elif dry_run and lead_index < len(leads_with_email):
            # In dry-run, just continue without waiting
            pass
        else:
            break

    print(f"\n{'='*55}")
    print(f"📊 EMAIL SENDER COMPLETE")
    print(f"{'='*55}")
    print(f"Sessions run:     {session_num}")
    print(f"Sent:             {stats['sent']}")
    print(f"Failed:           {stats['failed']}")
    print(f"Skipped:          {stats['skipped']}")
    print(f"Sequence done:    {stats['complete']}")
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
        print("🔍 DRY RUN MODE — No emails will actually be sent\n")

    send_all_emails(dry_run=dry_run, force=force, ignore_timing=ignore_timing)