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

os.makedirs("results/sent", exist_ok=True)
os.makedirs("results/sent/emails", exist_ok=True)
os.makedirs("results/logs", exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG LOADER
# ─────────────────────────────────────────────────────────────────────────────
def load_config() -> dict:
    with open("ceo_config.json", "r") as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────────────
# SEND LOG
# ─────────────────────────────────────────────────────────────────────────────
def load_send_log() -> dict:
    log_path = "results/logs/send_log.json"
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            return json.load(f)
    return {"emails": [], "stats": {"sent": 0, "failed": 0, "skipped": 0}}


def save_send_log(log: dict):
    with open("results/logs/send_log.json", "w") as f:
        json.dump(log, f, indent=2)


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
    dry_run: bool = False
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
    if not force:
        good_time, reason = is_good_send_time(config)
        if not good_time:
            result["reason"] = reason
            result["action"] = "skipped_timing"
            return result

    # Check daily limit
    todays_count = get_todays_send_count(log)
    if todays_count >= daily_limit and not force:
        result["reason"] = f"Daily limit reached ({todays_count}/{daily_limit})"
        result["action"] = "skipped_limit"
        return result

    # Load the email sequence for this lead
    safe_name = re.sub(r'[^a-z0-9]', '-', lead_name.lower()).strip('-')
    email_file = f"results/emails/{safe_name}_emails.json"

    if not os.path.exists(email_file):
        result["reason"] = "No email sequence found for this lead"
        result["action"] = "skipped_no_file"
        return result

    with open(email_file, "r") as f:
        emails = json.load(f)

    # Load enriched lead data
    enriched_file = "results/leads/enriched_leads.json"
    lead_data = {}
    if os.path.exists(enriched_file):
        with open(enriched_file, "r") as f:
            all_leads = json.load(f)
        for l in all_leads:
            if l["name"] == lead_name:
                lead_data = l
                break

    to_email = lead_data.get("contact_email")
    if not to_email:
        result["reason"] = "No email address for this lead"
        result["action"] = "skipped_no_email"
        return result

    # Determine which email to send next
    email_order = ["email_1", "email_2", "email_3"]
    email_to_send = None
    email_key = None

    for key in email_order:
        if key not in emails:
            continue
        if not already_sent(log, to_email, lead_name, key):
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
            break

    if not email_to_send:
        result["reason"] = "All emails in sequence already sent"
        result["action"] = "sequence_complete"
        return result

    subject = email_to_send.get("subject", "")
    body_text = email_to_send.get("body", "")

    if not subject or not body_text:
        result["reason"] = "Email content is empty"
        result["action"] = "skipped_empty"
        return result

    # Check if there's a sample site to include
    site_link = None
    if email_key in ["email_2", "email_3"]:
        site_path = f"results/sites/{safe_name}.html"
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

    # Dry run — just preview
    if dry_run:
        print(f"\n   📧 DRY RUN — Would send {email_key} to {to_email}")
        print(f"   Subject: {subject}")
        print(f"   Body preview: {body_text[:150]}...")
        result["action"] = "dry_run"
        result["success"] = True
        return result

    # Human-like random delay before sending
    delay = random.uniform(30, 120)
    print(f"   ⏳ Waiting {delay:.0f}s before sending (human-like)...")
    time.sleep(delay)

    # Try SMTP first, fall back to API
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
        "date": datetime.now().isoformat(),
        "success": send_result["success"],
        "method": send_result["method"],
        "error": send_result.get("error")
    }
    log["emails"].append(log_entry)

    if send_result["success"]:
        log["stats"]["sent"] = log["stats"].get("sent", 0) + 1
        print(f"   ✅ Sent successfully via {send_result['method']}")
    else:
        log["stats"]["failed"] = log["stats"].get("failed", 0) + 1
        print(f"   ❌ Failed: {send_result.get('error')}")

    save_send_log(log)

    result["action"] = f"sent_{email_key}"
    result["success"] = send_result["success"]
    result["reason"] = send_result.get("error")
    return result


# ─────────────────────────────────────────────────────────────────────────────
# BATCH SENDER — send to all leads
# ─────────────────────────────────────────────────────────────────────────────
def send_all_emails(dry_run: bool = False, force: bool = False):
    config = load_config()
    log = load_send_log()
    daily_limit = config["outreach"]["daily_email_limit"]

    # Load all leads with emails
    enriched_file = "results/leads/enriched_leads.json"
    if not os.path.exists(enriched_file):
        print("❌ No enriched leads found")
        return

    with open(enriched_file, "r") as f:
        leads = json.load(f)

    leads_with_email = [l for l in leads if l.get("contact_email")]

    print(f"\n📧 EMAIL SENDER")
    print(f"{'='*55}")
    print(f"Leads with emails:  {len(leads_with_email)}")
    print(f"Daily limit:        {daily_limit}")
    print(f"Dry run:            {dry_run}")
    print(f"{'='*55}\n")

    # Check timing
    if not force and not dry_run:
        good_time, reason = is_good_send_time(config)
        if not good_time:
            print(f"⏰ {reason}")
            print(f"   Run with --force to override timing")
            return

    todays_count = get_todays_send_count(log)
    print(f"Already sent today: {todays_count}/{daily_limit}\n")

    stats = {"sent": 0, "failed": 0, "skipped": 0, "complete": 0}

    for i, lead in enumerate(leads_with_email, 1):
        name = lead["name"]

        if todays_count + stats["sent"] >= daily_limit and not force:
            print(f"   🛑 Daily limit reached — stopping")
            break

        print(f"[{i}/{len(leads_with_email)}] {name}")

        result = send_email_sequence(
            lead_name=name,
            force=force,
            dry_run=dry_run
        )

        if result["success"]:
            stats["sent"] += 1
        elif result["action"] == "sequence_complete":
            stats["complete"] += 1
            print(f"   ✅ Sequence complete")
        elif result["action"] and "skipped" in result["action"]:
            stats["skipped"] += 1
            print(f"   ⏭️  Skipped: {result['reason']}")
        else:
            stats["failed"] += 1

        # Random delay between leads
        if i < len(leads_with_email):
            wait = random.uniform(15, 45)
            print(f"   ⏳ Waiting {wait:.0f}s before next lead...")
            time.sleep(wait)

    print(f"\n{'='*55}")
    print(f"📊 EMAIL SENDER COMPLETE")
    print(f"{'='*55}")
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

    if dry_run:
        print("🔍 DRY RUN MODE — No emails will actually be sent\n")

    send_all_emails(dry_run=dry_run, force=force)