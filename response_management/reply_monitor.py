import asyncio
import json
import os
import re
import random
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
from dotenv import load_dotenv
import sys
import pathlib

sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from utils.ai_client import ai_response as get_ai_response, safe_json

load_dotenv()

os.makedirs("results/replies", exist_ok=True)
os.makedirs("results/logs", exist_ok=True)



# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM EMAIL FILTER — skip emails that are NOT from leads
# ─────────────────────────────────────────────────────────────────────────────
IGNORE_SENDERS = {
    "noreply", "no-reply", "mailer-daemon", "postmaster",
    "notifications", "notify", "alert", "donotreply",
    "newsletter", "marketing", "billing", "feedback",
    "support", "info", "security", "accounts", "team",
    "updates", "digest", "automated", "system",
}
IGNORE_DOMAINS = {
    "google.com", "youtube.com", "facebook.com", "instagram.com",
    "snapchat.com", "telegram.org", "twitter.com", "x.com",
    "linkedin.com", "amazon.com", "apple.com", "microsoft.com",
    "brevo.com", "github.com", "paypal.com", "netflix.com",
    "whatsapp.com", "tiktok.com", "pinterest.com", "reddit.com",
    "zoom.us", "dropbox.com", "spotify.com", "uber.com",
}

def is_system_email(from_email: str) -> bool:
    """Check if an email is from a system/notification sender (not a lead)."""
    if not from_email:
        return True
    email_lower = from_email.lower().strip()
    local_part = email_lower.split("@")[0] if "@" in email_lower else ""
    if any(prefix in local_part for prefix in IGNORE_SENDERS):
        return True
    domain = email_lower.split("@")[1] if "@" in email_lower else ""
    if domain in IGNORE_DOMAINS:
        return True
    return False


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# CONFIG
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def load_config() -> dict:
    with open("ceo_config.json", "r", encoding="utf-8") as f:
        return json.load(f)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# REPLY LOG
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def load_reply_log() -> dict:
    path = "results/replies/reply_log.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "replies": [],
        "stats": {
            "interested": 0,
            "not_interested": 0,
            "question": 0,
            "out_of_office": 0,
            "total": 0
        }
    }


def save_reply_log(log: dict):
    with open("results/replies/reply_log.json", "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def already_processed(log: dict, message_id: str) -> bool:
    return any(r.get("message_id") == message_id for r in log["replies"])


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# LEAD FINDER â€” match reply to a lead
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def find_lead_by_email(email_address: str) -> dict:
    """Find which lead sent this reply"""
    enriched_file = "results/leads/enriched_leads.json"
    if not os.path.exists(enriched_file):
        return {}

    with open(enriched_file, "r", encoding="utf-8") as f:
        leads = json.load(f)

    email_lower = email_address.lower().strip()
    for lead in leads:
        lead_email = (lead.get("contact_email") or "").lower().strip()
        all_emails = [e.lower() for e in (lead.get("all_emails") or [])]
        if lead_email == email_lower or email_lower in all_emails:
            return lead

    return {}


def find_lead_by_name_in_subject(subject: str, leads: list) -> dict:
    """Try to match lead by business name mentioned in subject"""
    subject_lower = subject.lower()
    for lead in leads:
        name_words = lead["name"].lower().split()
        if any(word in subject_lower for word in name_words if len(word) > 3):
            return lead
    return {}


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# REPLY CLASSIFIER
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def classify_reply(reply_text: str, business_name: str) -> dict:
    """
    Classify reply intent and extract key information.
    Categories: interested, not_interested, question, out_of_office, other
    """
    prompt = f"""
Classify this email reply from "{business_name}" in response to a digital services outreach.

Reply text:
{reply_text[:2000]}

Analyse carefully and return ONLY valid JSON:
{{
  "intent": "interested" or "not_interested" or "question" or "out_of_office" or "other",
  "confidence": "high" or "medium" or "low",
  "sentiment": "positive" or "neutral" or "negative",
  "key_points": ["list of key things they said"],
  "questions_asked": ["any specific questions they asked"],
  "objections": ["any objections or concerns raised"],
  "best_reply_tone": "formal" or "semi-formal" or "casual-warm",
  "urgency": "high" or "medium" or "low",
  "summary": "one sentence summary of their reply"
}}

Intent definitions:
- interested: They want to know more, want to meet, asking about pricing, or showing clear interest
- not_interested: They explicitly said no, not interested, or already have someone
- question: They asked specific questions without committing either way
- out_of_office: Auto-reply, vacation, or out of office message
- other: Anything else — wrong person, bounce, unclear
"""
    try:
        response = get_ai_response(prompt, max_tokens=500)
        result = safe_json(response)
        if result:
            return result
    except Exception as e:
        print(f"   ⚠️   Classification failed: {e}")

    # Fallback classification using keywords
    text_lower = reply_text.lower()
    if any(w in text_lower for w in [
        "interested", "tell me more", "how much", "price",
        "cost", "when can", "let's talk", "please send",
        "yes", "sounds good", "would like"
    ]):
        return {"intent": "interested", "confidence": "medium",
                "sentiment": "positive", "summary": "Shows interest"}

    if any(w in text_lower for w in [
        "not interested", "no thank", "already have",
        "don't need", "remove", "unsubscribe", "stop"
    ]):
        return {"intent": "not_interested", "confidence": "medium",
                "sentiment": "negative", "summary": "Not interested"}

    if any(w in text_lower for w in [
        "out of office", "away", "vacation", "holiday",
        "will be back", "auto", "automatic"
    ]):
        return {"intent": "out_of_office", "confidence": "high",
                "sentiment": "neutral", "summary": "Out of office"}

    if "?" in reply_text:
        return {"intent": "question", "confidence": "medium",
                "sentiment": "neutral", "summary": "Asked a question"}

    return {"intent": "other", "confidence": "low",
            "sentiment": "neutral", "summary": "Unclear intent"}


# —————————————————————————————————————————————————————————————————————————————
# REPLY DRAFTER
# —————————————————————————————————————————————————————————————————————————————
def draft_reply(
    classification: dict,
    lead: dict,
    original_reply: str,
    config: dict
) -> dict:
    """Draft the perfect response based on classification"""

    intent = classification.get("intent", "other")
    business_name = lead.get("name", "the business")
    owner_name = lead.get("owner_name")
    first_name = owner_name.split()[0] if owner_name else None
    greeting = f"Hi {first_name}," if first_name else "Hi,"
    from_name = config["brevo"]["from_name"]
    calendly_link = config.get("calendly_link", "")
    personality = lead.get("personality") or {}
    tone = personality.get("tone_to_use", "semi-formal")
    vibe = personality.get("vibe", "professional")
    city = lead.get("city", "Nigeria")

    # Site link if built
    safe_name = re.sub(r'[^a-z0-9]', '-', business_name.lower()).strip('-')
    site_path = f"results/sites/{safe_name}.html"
    has_site = os.path.exists(site_path)

    # Questions they asked
    questions = classification.get("questions_asked", [])
    objections = classification.get("objections", [])

    if intent == "interested":
        prompt = f"""
Write a warm, professional reply to an interested business owner.

Context:
- Business: {business_name}, {city}
- Owner name: {first_name or 'the owner'}
- They replied: {original_reply[:500]}
- Their questions: {questions}
- Tone: {tone}
- Vibe: {vibe}
- We have built them a sample website: {has_site}
- Our name: {from_name}

Write a reply that:
1. Opens with "{greeting}" and genuine warmth
2. Acknowledges their specific reply naturally
3. Answers any questions they asked directly
4. If we built a sample site — mention it naturally and offer to send them the custom link/preview right here in this thread
5. DO NOT suggest a phone call, voice call, zoom call, or meeting anywhere. Suggest continuing the discussion right here via text/email.
6. Ends warmly and personally
7. Maximum 150 words
8. Sounds like a real human expert, not a salesperson
9. Never use words like "leverage", "synergy", "optimize", "call", "schedule", "zoom", "calendly", "phone"

Return ONLY valid JSON:
{{
  "subject": "Re: [their subject or relevant subject]",
  "body": "full reply body",
  "priority": "high",
  "follow_up_in_days": 2
}}
"""

    elif intent == "question":
        prompt = f"""
Write a helpful, knowledgeable reply to a business owner who asked questions.

Context:
- Business: {business_name}, {city}
- Owner: {first_name or 'the owner'}
- Their reply: {original_reply[:500]}
- Questions they asked: {questions}
- Tone: {tone}
- We have a sample site for them: {has_site}
- Our name: {from_name}

Write a reply that:
1. Opens with "{greeting}"
2. Answers each question clearly and specifically
3. Makes them feel genuinely helped — not sold to
4. If they asked about pricing — give a range naturally
   (basic website ₦{config['services']['basic_website_ngn']:,},
    full package ₦{config['services']['full_package_ngn']:,},
    monthly retainer ₦{config['services']['monthly_retainer_ngn']:,})
5. Ends with a soft invitation to continue chatting and discussing right here via text/email. Never suggest a phone call, scheduling, or voice call anywhere.
6. Maximum 180 words

Return ONLY valid JSON:
{{
  "subject": "Re: [relevant subject]",
  "body": "full reply body",
  "priority": "medium",
  "follow_up_in_days": 3
}}
"""

    elif intent == "not_interested":
        prompt = f"""
Write a gracious, warm reply to a business owner who said they're not interested.

Context:
- Business: {business_name}
- Their reply: {original_reply[:300]}
- Objections: {objections}
- Our name: {from_name}

Write a reply that:
1. Opens with "{greeting}"
2. Completely respects their decision â€” zero pressure
3. Genuinely wishes them well and compliments something real about their business
4. Leaves the door open warmly for the future
5. Asks softly if they know anyone who might benefit (referral seed)
6. Maximum 80 words â€” short and genuine
7. Feels like it came from a real person who genuinely cares

Return ONLY valid JSON:
{{
  "subject": "Re: [relevant subject]",
  "body": "full reply body",
  "priority": "low",
  "follow_up_in_days": 90
}}
"""

    elif intent == "out_of_office":
        # No reply needed â€” just log it
        return {
            "subject": None,
            "body": None,
            "priority": "low",
            "follow_up_in_days": 7,
            "action": "wait_for_return"
        }

    else:
        prompt = f"""
Write a warm, curious reply to an unclear or ambiguous email from a business owner.

Context:
- Business: {business_name}
- Their reply: {original_reply[:300]}
- Our name: {from_name}

Write a reply that:
1. Opens with "{greeting}"
2. Acknowledges their message warmly
3. Gently clarifies what we were reaching out about
4. Asks one simple question to understand their situation better
5. Maximum 60 words
6. Sound like a friendly human

Return ONLY valid JSON:
{{
  "subject": "Re: [relevant subject]",
  "body": "full reply body",
  "priority": "low",
  "follow_up_in_days": 5
}}
"""

    try:
        response = get_ai_response(prompt, max_tokens=600)
        result = safe_json(response)
        if result:
            result["action"] = "send_reply"
            return result
    except Exception as e:
        print(f"   âš ï¸  Draft failed: {e}")

    return {
        "subject": f"Re: Your message",
        "body": f"{greeting}\n\nThank you for getting back to me. I'll follow up shortly.\n\nBest,\n{from_name}",
        "priority": "medium",
        "follow_up_in_days": 3,
        "action": "send_reply"
    }


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# EMAIL MONITOR â€” checks Gmail/IMAP for replies
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def fetch_email_replies(since_days: int = 3) -> list:
    """Fetch recent emails from inbox via IMAP"""
    replies = []

    imap_host = os.getenv("IMAP_HOST", "imap.gmail.com")
    imap_user = os.getenv("IMAP_USER") or os.getenv("BREVO_SMTP_USER")
    imap_pass = os.getenv("IMAP_PASS") or os.getenv("IMAP_PASSWORD")

    if not imap_user or not imap_pass:
        print("   âš ï¸  IMAP credentials not configured")
        print("   Add IMAP_USER and IMAP_PASS to .env")
        return replies

    try:
        print(f"   ðŸ“¬ Connecting to {imap_host}...")
        mail = imaplib.IMAP4_SSL(imap_host)
        mail.login(imap_user, imap_pass)
        mail.select("INBOX")

        # Search for emails since N days ago
        since_date = (datetime.now() - timedelta(days=since_days)).strftime("%d-%b-%Y")
        status, messages = mail.search(None, f'SINCE {since_date}')

        if status != "OK":
            print("   âš ï¸  Could not search inbox")
            return replies

        email_ids = messages[0].split()
        print(f"   ðŸ“¬ Found {len(email_ids)} emails to check")

        for email_id in email_ids:
            try:
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                if status != "OK":
                    continue

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Decode subject
                subject_raw = msg.get("Subject", "")
                subject_parts = decode_header(subject_raw)
                subject = ""
                for part, encoding in subject_parts:
                    if isinstance(part, bytes):
                        subject += part.decode(encoding or "utf-8", errors="ignore")
                    else:
                        subject += str(part)

                # Get sender
                from_raw = msg.get("From", "")
                from_match = re.search(r'[\w.+-]+@[\w.+-]+', from_raw)
                from_email = from_match.group(0) if from_match else from_raw

                # Skip our own emails
                if imap_user.lower() in from_email.lower():
                    continue

                # Skip system/notification emails (Google, Snapchat, etc.)
                if is_system_email(from_email):
                    continue

                # Get message body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            try:
                                body = part.get_payload(decode=True).decode(
                                    part.get_content_charset() or "utf-8",
                                    errors="ignore"
                                )
                                break
                            except:
                                continue
                else:
                    try:
                        body = msg.get_payload(decode=True).decode(
                            msg.get_content_charset() or "utf-8",
                            errors="ignore"
                        )
                    except:
                        body = str(msg.get_payload())

                # Message ID for deduplication
                message_id = msg.get("Message-ID", str(email_id))
                date_str = msg.get("Date", datetime.now().isoformat())

                replies.append({
                    "message_id": message_id,
                    "from_email": from_email,
                    "from_name": from_raw.split("<")[0].strip().strip('"'),
                    "subject": subject,
                    "body": body[:3000],
                    "date": date_str,
                    "channel": "email"
                })

            except Exception as e:
                print(f"   âš ï¸  Error reading email: {str(e)[:60]}")
                continue

        mail.logout()
        print(f"   âœ… Fetched {len(replies)} replies from inbox")

    except imaplib.IMAP4.error as e:
        print(f"   âŒ IMAP connection failed: {str(e)[:100]}")
        print("   Check IMAP_HOST, IMAP_USER, IMAP_PASS in .env")
    except Exception as e:
        print(f"   âŒ Email fetch failed: {str(e)[:100]}")

    return replies


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# PROCESS AND HANDLE REPLIES
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def process_replies(replies: list, dry_run: bool = False) -> dict:
    """Process all fetched replies â€” classify, draft responses, update leads"""
    config = load_config()
    log = load_reply_log()

    # Load all leads for matching
    enriched_file = "results/leads/enriched_leads.json"
    all_leads = []
    if os.path.exists(enriched_file):
        with open(enriched_file, "r", encoding="utf-8") as f:
            all_leads = json.load(f)

    stats = {
        "processed": 0, "interested": 0,
        "not_interested": 0, "questions": 0,
        "out_of_office": 0, "other": 0
    }

    processed_replies = []

    for reply in replies:
        message_id = reply["message_id"]

        # Skip already processed
        if already_processed(log, message_id):
            continue

        from_email = reply["from_email"]
        subject = reply["subject"]
        body = reply["body"]
        channel = reply["channel"]

        print(f"\n   ðŸ“¨ Processing reply from: {from_email}")
        print(f"   Subject: {subject[:60]}")

        # Find matching lead
        lead = find_lead_by_email(from_email)
        if not lead:
            lead = find_lead_by_phone(from_email, all_leads)
        if not lead:
            lead = find_lead_by_name_in_subject(subject, all_leads)

        if not lead:
            print(f"   ⏭️  No matching lead for {from_email} — skipping (not outreach-related)")
            continue

        business_name = lead.get("name", from_email)
        print(f"   🏢 Matched to: {business_name}")

        # Classify the reply
        print(f"   ðŸ§  Classifying intent...")
        classification = classify_reply(body, business_name)
        intent = classification.get("intent", "other")
        confidence = classification.get("confidence", "low")
        print(f"   ðŸ“Š Intent: {intent} ({confidence} confidence)")
        print(f"   ðŸ’¬ Summary: {classification.get('summary', '')}")

        # Draft response
        print(f"   âœï¸  Drafting response...")
        drafted = draft_reply(classification, lead, body, config)

        # Build full reply record
        reply_record = {
            "message_id": message_id,
            "business": business_name,
            "from_email": from_email,
            "subject": subject,
            "body_preview": body[:300],
            "channel": channel,
            "date_received": reply["date"],
            "date_processed": datetime.now().isoformat(),
            "classification": classification,
            "drafted_reply": drafted,
            "status": "pending_review" if config.get("quality", {}).get("require_human_review") else "ready_to_send",
            "action_taken": None
        }

        # Update stats
        stats["processed"] += 1
        stats[intent] = stats.get(intent, 0) + 1
        log["stats"][intent] = log["stats"].get(intent, 0) + 1
        log["stats"]["total"] = log["stats"].get("total", 0) + 1

        log["replies"].append(reply_record)
        processed_replies.append(reply_record)

        # Update lead status in enriched leads
        for i, l in enumerate(all_leads):
            if l.get("name") == business_name or l.get("contact_email") == from_email:
                all_leads[i]["reply_status"] = intent
                all_leads[i]["last_reply_date"] = datetime.now().isoformat()
                all_leads[i]["reply_classification"] = classification

                # Mark interested leads specially
                if intent == "interested":
                    all_leads[i]["status"] = "interested"
                    all_leads[i]["priority"] = "high"
                elif intent == "not_interested":
                    all_leads[i]["status"] = "not_interested"
                    all_leads[i]["priority"] = "nurture"
                break

        # Print draft preview
        if drafted.get("body"):
            print(f"   ðŸ“ Draft: {drafted['body'][:120]}...")

        if not dry_run:
            print(f"   âœ… Reply queued â€” status: {reply_record['status']}")
        else:
            print(f"   ðŸ” DRY RUN â€” would queue reply")

    # Save everything
    save_reply_log(log)

    if not dry_run and all_leads:
        with open(enriched_file, "w", encoding="utf-8") as f:
            json.dump(all_leads, f, indent=2, ensure_ascii=False)

    # Save processed replies for review
    if processed_replies:
        review_file = f"results/replies/pending_review_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(review_file, "w", encoding="utf-8") as f:
            json.dump(processed_replies, f, indent=2, ensure_ascii=False)
        print(f"\n   ðŸ’¾ Replies saved for review: {review_file}")

    return stats


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# SEND QUEUED REPLIES
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def send_queued_replies(dry_run: bool = False):
    """Send all replies that have been reviewed and approved"""
    import smtplib
    import ssl
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    config = load_config()
    log = load_reply_log()

    from_name = config["brevo"]["from_name"]
    from_email = config["brevo"]["from_email"]
    smtp_user = os.getenv("BREVO_SMTP_USER")
    smtp_pass = os.getenv("BREVO_SMTP_PASS")

    ready_replies = [
        r for r in log["replies"]
        if r.get("status") == "ready_to_send"
        and r.get("drafted_reply", {}).get("body")
        and not r.get("action_taken")
    ]

    print(f"\nðŸ“¤ Sending {len(ready_replies)} queued replies...")

    for reply in ready_replies:
        drafted = reply["drafted_reply"]
        to_email = reply["from_email"]
        subject = drafted.get("subject", "Re: Your message")
        body = drafted.get("body", "")

        if not body or not to_email:
            continue

        print(f"\n   ðŸ“§ Replying to: {reply['business']} ({to_email})")

        if dry_run:
            print(f"   ðŸ” DRY RUN â€” Subject: {subject}")
            print(f"   Body: {body[:100]}...")
            continue

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{from_name} <{from_email}>"
            msg["To"] = to_email
            msg.attach(MIMEText(body, "plain", "utf-8"))

            context = ssl.create_default_context()
            with smtplib.SMTP("smtp-relay.brevo.com", 587) as server:
                server.ehlo()
                server.starttls(context=context)
                server.login(smtp_user, smtp_pass)
                server.sendmail(from_email, to_email, msg.as_string())

            reply["action_taken"] = "replied"
            reply["reply_sent_at"] = datetime.now().isoformat()
            reply["status"] = "replied"
            print(f"   âœ… Reply sent")

        except Exception as e:
            print(f"   âŒ Failed: {str(e)[:80]}")
            reply["action_taken"] = "failed"
            reply["error"] = str(e)[:100]

    save_reply_log(log)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# MAIN MONITOR
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def run_reply_monitor(dry_run: bool = False, send_replies: bool = False):
    print(f"\nðŸ“¬ REPLY MONITOR")
    print(f"{'='*55}")
    print(f"Time:         {datetime.now().strftime('%A %d %B %Y, %I:%M %p')}")
    print(f"Dry run:      {dry_run}")
    print(f"{'='*55}\n")

    # Fetch email replies
    print("📧 Checking email inbox...")
    email_replies = fetch_email_replies(since_days=7)

    # Fetch WhatsApp replies
    whatsapp_replies = fetch_whatsapp_replies()

    all_replies = email_replies + whatsapp_replies

    if not all_replies:
        print("\nâœ… No new replies found")
    else:
        print(f"\nðŸ“¨ Processing {len(all_replies)} replies...\n")
        stats = process_replies(all_replies, dry_run=dry_run)

        print(f"\n{'='*55}")
        print(f"ðŸ“Š REPLY MONITOR SUMMARY")
        print(f"{'='*55}")
        print(f"Total processed:    {stats['processed']}")
        print(f"Interested:         {stats.get('interested', 0)} ðŸ”¥")
        print(f"Questions:          {stats.get('question', 0)} â“")
        print(f"Not interested:     {stats.get('not_interested', 0)} âŒ")
        print(f"Out of office:      {stats.get('out_of_office', 0)} ðŸ“…")
        print(f"Other:              {stats.get('other', 0)}")
        print(f"{'='*55}")

    # Send queued replies
    if send_replies:
        print(f"\nðŸ“¤ Sending queued replies...")
        send_queued_replies(dry_run=dry_run)

    # Show interested leads summary
    log = load_reply_log()
    interested = [
        r for r in log["replies"]
        if r.get("classification", {}).get("intent") == "interested"
        and not r.get("action_taken")
    ]

    if interested:
        print(f"\nðŸ”¥ HOT LEADS NEEDING ATTENTION:")
        print(f"{'='*55}")
        for r in interested:
            print(f"  â€¢ {r['business']}")
            print(f"    Email: {r['from_email']}")
            print(f"    Reply: {r['body_preview'][:80]}...")
            print(f"    Status: {r['status']}")
            print()


def find_lead_by_phone(phone: str, leads: list) -> dict:
    """Find which lead matches this phone number"""
    from outreach.whatsapp_sender import format_wa_number
    if not phone:
        return {}
    target_fmt = format_wa_number(phone)
    if not target_fmt:
        return {}
    for lead in leads:
        lead_phones = []
        if lead.get("phone"):
            lead_phones.append(lead.get("phone"))
        if lead.get("contact_whatsapp"):
            lead_phones.append(lead.get("contact_whatsapp"))
        if lead.get("whatsapp_phone"):
            lead_phones.append(lead.get("whatsapp_phone"))
        if lead.get("all_phones"):
            if isinstance(lead.get("all_phones"), list):
                lead_phones.extend(lead.get("all_phones"))
            else:
                lead_phones.append(lead.get("all_phones"))
        
        fb = lead.get("facebook")
        if isinstance(fb, dict) and fb.get("phone"):
            lead_phones.append(fb.get("phone"))
        ig = lead.get("instagram")
        if isinstance(ig, dict) and ig.get("phone"):
            lead_phones.append(ig.get("phone"))
            
        for lp in lead_phones:
            if format_wa_number(str(lp)) == target_fmt:
                return lead
    return {}


def find_phone_by_lead_name(name: str) -> str:
    """Find WhatsApp/phone number for a lead by business name"""
    enriched_file = "results/leads/enriched_leads.json"
    if not os.path.exists(enriched_file):
        return None
    try:
        with open(enriched_file, "r", encoding="utf-8") as f:
            leads = json.load(f)
        for l in leads:
            if l.get("name", "").lower().strip() == name.lower().strip():
                return l.get("contact_whatsapp") or l.get("phone")
    except Exception:
        pass
    return None


def get_recent_outreach_numbers() -> list:
    """Get unique phone numbers recently contacted via WhatsApp from log file"""
    path = "results/logs/whatsapp_log.json"
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        messages = data.get("messages", [])
        seen = set()
        recent = []
        for m in reversed(messages):
            business = m.get("business")
            number = m.get("number")
            if business and number and number not in seen:
                seen.add(number)
                recent.append((business, number))
                if len(recent) >= 100:
                    break
        return recent
    except Exception as e:
        print(f"   ⚠️ Error loading WhatsApp logs: {e}")
        return []


async def extract_messages_from_chat(page, contact_name: str, phone_num: str = None) -> list:
    """Extract consecutive incoming messages from the end of the chat window"""
    import hashlib
    import asyncio
    from outreach.whatsapp_sender import format_wa_number

    # Wait up to 5 seconds for message bubbles to render
    bubbles = []
    for _ in range(10):
        bubbles = await page.query_selector_all('div.message-in, div.message-out')
        if bubbles:
            break
        await asyncio.sleep(0.5)

    if not bubbles:
        return []

    consecutive_incoming = []
    for bubble in reversed(bubbles):
        class_attr = await bubble.get_attribute("class") or ""
        if "message-in" in class_attr:
            consecutive_incoming.append(bubble)
        else:
            # We reached an outgoing message, stop collecting
            break

    if not consecutive_incoming:
        return []

    consecutive_incoming.reverse()

    # Extract text from the consecutive incoming bubbles
    text_parts = []
    for bubble in consecutive_incoming:
        text_el = await bubble.query_selector('span.selectable-text, div.copyable-text')
        if text_el:
            txt = await text_el.inner_text()
            if txt:
                text_parts.append(txt.strip())

    if not text_parts:
        return []

    reply_text = "\n".join(text_parts)
    print(f"   📩 Found WhatsApp reply from {contact_name}: \"{reply_text[:100]}...\"")

    # Determine unique message ID using a hash of the text
    text_hash = hashlib.md5(reply_text.encode('utf-8')).hexdigest()[:12]
    message_id = f"wa_{contact_name.replace(' ', '_')}_{text_hash}"

    # Determine from_email representation (store the phone number or fallback to contact name)
    if not phone_num:
        raw_phone = find_phone_by_lead_name(contact_name)
        if raw_phone:
            phone_num = format_wa_number(raw_phone)
            
    from_email = phone_num if phone_num else contact_name

    return [{
        "message_id": message_id,
        "from_email": from_email,
        "from_name": contact_name,
        "subject": "WhatsApp Message",
        "body": reply_text,
        "date": datetime.now().isoformat(),
        "channel": "whatsapp"
    }]


async def async_fetch_whatsapp_replies() -> list:
    """Fetch unread WhatsApp replies using Playwright"""
    from playwright.async_api import async_playwright
    from outreach.whatsapp_sender import ensure_wa_session, human_pause, format_wa_number

    replies = []
    user_data_dir = os.path.join(os.getcwd(), ".wa_session")
    os.makedirs(user_data_dir, exist_ok=True)

    print("   📱 Launching browser to scan WhatsApp replies...")
    async with async_playwright() as p:
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
            print(f"   ⚠️ Could not launch Chrome channel: {e}. Falling back to default Chromium.")
            context = await p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--start-maximized",
                ],
                viewport={"width": 1366, "height": 768},
            )

        page = context.pages[0] if context.pages else await context.new_page()

        session_ok = await ensure_wa_session(page)
        if not session_ok:
            print("   ❌ WhatsApp Web session failed")
            await context.close()
            return []

        await human_pause(3.0, 5.0)

        # 1. Scan sidebar for unread chats
        print("   🔍 Scanning chat list for unread messages...")
        chat_items = await page.query_selector_all('div[data-testid="chat-list-item"]')
        chats_to_check = []
        for item in chat_items:
            unread_badge = await item.query_selector('span[aria-label*="unread"], span[aria-label*="Unread"], [data-testid="icon-unread-count"]')
            title_el = await item.query_selector('span[title], div[dir="auto"]')
            title = await title_el.get_attribute("title") if title_el else None
            if not title and title_el:
                title = await title_el.text_content()
            if title:
                title = title.strip()
            
            if unread_badge and title:
                chats_to_check.append((item, title))

        print(f"   🔥 Found {len(chats_to_check)} unread chats in sidebar")

        # Click each unread chat and extract messages
        for item, title in chats_to_check:
            try:
                print(f"   👉 Opening unread chat: {title}")
                await item.click()
                await human_pause(2.5, 4.0)

                chat_replies = await extract_messages_from_chat(page, title)
                if chat_replies:
                    replies.extend(chat_replies)
            except Exception as e:
                print(f"   ⚠️ Error checking unread chat '{title}': {e}")

        # 2. Safety check: Check the last 15 active outreach chats from logs
        recent_contacts = get_recent_outreach_numbers()
        print(f"   🔄 Safety Check: Checking {len(recent_contacts)} recent outreach chats...")
        for business, number in recent_contacts:
            # Skip if we already got a reply for this business in this run
            if any(r["from_name"] == business for r in replies):
                continue

            formatted_num = format_wa_number(number)
            if not formatted_num:
                continue

            try:
                clean_num = formatted_num.replace('+', '')
                chat_url = f"https://web.whatsapp.com/send?phone={clean_num}"
                print(f"   🔍 Inspecting chat for {business} ({formatted_num})...")
                await page.goto(chat_url, timeout=20000, wait_until="domcontentloaded")
                await human_pause(4.0, 6.0)

                chat_replies = await extract_messages_from_chat(page, business, phone_num=formatted_num)
                if chat_replies:
                    replies.extend(chat_replies)
            except Exception as e:
                print(f"   ⚠️ Safety check failed for {business}: {e}")

        await context.close()

    return replies


def fetch_whatsapp_replies() -> list:
    """Synchronous wrapper to run async Playwright fetcher"""
    print("\n💬 Checking WhatsApp for replies...")
    try:
        return asyncio.run(async_fetch_whatsapp_replies())
    except Exception as e:
        print(f"   ❌ WhatsApp fetch failed: {e}")
        return []


async def async_send_whatsapp_replies(ready_replies: list) -> list:
    """Send approved WhatsApp replies using Playwright"""
    from playwright.async_api import async_playwright
    from outreach.whatsapp_sender import ensure_wa_session, send_whatsapp_message, format_wa_number, human_pause

    user_data_dir = os.path.join(os.getcwd(), ".wa_session")
    os.makedirs(user_data_dir, exist_ok=True)

    print(f"   🚀 Launching browser to send {len(ready_replies)} WhatsApp replies...")
    async with async_playwright() as p:
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
            print(f"   ⚠️ Could not launch Chrome channel: {e}. Falling back to default Chromium.")
            context = await p.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--start-maximized",
                ],
                viewport={"width": 1366, "height": 768},
            )

        page = context.pages[0] if context.pages else await context.new_page()

        session_ok = await ensure_wa_session(page)
        if not session_ok:
            print("   ❌ WhatsApp Web session failed")
            await context.close()
            return ready_replies

        await human_pause(3.0, 5.0)

        for reply in ready_replies:
            drafted = reply["drafted_reply"]
            to_phone = reply["from_email"]
            business = reply["business"]
            body = drafted.get("body", "")

            if not body or not to_phone:
                continue

            print(f"\n   📤 Replying via WhatsApp to: {business} ({to_phone})")

            send_result = await send_whatsapp_message(
                page=page,
                number=to_phone,
                message=body,
                business_name=business
            )

            if send_result["success"]:
                reply["action_taken"] = "replied"
                reply["reply_sent_at"] = datetime.now().isoformat()
                reply["status"] = "replied"
                print(f"   ✅ Reply sent via WhatsApp")

                log_wa_reply_sent(business, to_phone, body)
            else:
                reply["action_taken"] = "failed"
                reply["error"] = send_result.get("error", "unknown error")
                print(f"   ❌ WhatsApp send failed: {reply['error']}")

        await context.close()

    return ready_replies


def log_wa_reply_sent(business: str, number: str, message: str):
    """Log a sent WhatsApp reply to whatsapp_log.json"""
    from outreach.whatsapp_sender import format_wa_number
    log_path = "results/logs/whatsapp_log.json"
    log = {"messages": [], "stats": {"sent": 0, "failed": 0, "skipped": 0}}
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                log = json.load(f)
        except Exception:
            pass

    formatted = format_wa_number(number) or number
    log_entry = {
        "business": business,
        "number": formatted,
        "msg_key": "wa_reply",
        "message_preview": message[:100],
        "message": message,
        "date": datetime.now().isoformat(),
        "success": True,
        "error": None
    }
    log["messages"].append(log_entry)
    log["stats"]["sent"] = log["stats"].get("sent", 0) + 1

    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv
    send = "--send" in sys.argv
    run_reply_monitor(dry_run=dry_run, send_replies=send)
