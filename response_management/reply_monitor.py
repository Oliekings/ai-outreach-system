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
from anthropic import Anthropic
from groq import Groq

load_dotenv()

os.makedirs("results/replies", exist_ok=True)
os.makedirs("results/logs", exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# AI CLIENT
# ─────────────────────────────────────────────────────────────────────────────
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
        if "credit" in str(e).lower() or "balance" in str(e).lower():
            groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
            response = groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        raise e


def safe_json(text: str) -> dict:
    try:
        clean = re.sub(r'```json|```', '', text).strip()
        start = clean.find('{')
        end = clean.rfind('}')
        if start != -1 and end != -1:
            return json.loads(clean[start:end+1])
    except:
        pass
    return {}


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
def load_config() -> dict:
    with open("ceo_config.json", "r") as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────────────
# REPLY LOG
# ─────────────────────────────────────────────────────────────────────────────
def load_reply_log() -> dict:
    path = "results/replies/reply_log.json"
    if os.path.exists(path):
        with open(path, "r") as f:
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
    with open("results/replies/reply_log.json", "w") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def already_processed(log: dict, message_id: str) -> bool:
    return any(r.get("message_id") == message_id for r in log["replies"])


# ─────────────────────────────────────────────────────────────────────────────
# LEAD FINDER — match reply to a lead
# ─────────────────────────────────────────────────────────────────────────────
def find_lead_by_email(email_address: str) -> dict:
    """Find which lead sent this reply"""
    enriched_file = "results/leads/enriched_leads.json"
    if not os.path.exists(enriched_file):
        return {}

    with open(enriched_file, "r") as f:
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


# ─────────────────────────────────────────────────────────────────────────────
# REPLY CLASSIFIER
# ─────────────────────────────────────────────────────────────────────────────
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
        print(f"   ⚠️  Classification failed: {e}")

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


# ─────────────────────────────────────────────────────────────────────────────
# REPLY DRAFTER
# ─────────────────────────────────────────────────────────────────────────────
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
- Calendly booking link: {calendly_link}
- Our name: {from_name}

Write a reply that:
1. Opens with "{greeting}" and genuine warmth
2. Acknowledges their specific reply naturally
3. Answers any questions they asked directly
4. If we built a sample site — mention it naturally and offer to share it
5. Suggests a quick 15-minute call — include Calendly link if available
6. Ends warmly and personally
7. Maximum 150 words
8. Sounds like a real human expert, not a salesperson
9. Never use words like "leverage", "synergy", "optimize"

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
5. Ends with a soft invitation to chat more
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
2. Completely respects their decision — zero pressure
3. Genuinely wishes them well and compliments something real about their business
4. Leaves the door open warmly for the future
5. Asks softly if they know anyone who might benefit (referral seed)
6. Maximum 80 words — short and genuine
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
        # No reply needed — just log it
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
        print(f"   ⚠️  Draft failed: {e}")

    return {
        "subject": f"Re: Your message",
        "body": f"{greeting}\n\nThank you for getting back to me. I'll follow up shortly.\n\nBest,\n{from_name}",
        "priority": "medium",
        "follow_up_in_days": 3,
        "action": "send_reply"
    }


# ─────────────────────────────────────────────────────────────────────────────
# EMAIL MONITOR — checks Gmail/IMAP for replies
# ─────────────────────────────────────────────────────────────────────────────
def fetch_email_replies(since_days: int = 3) -> list:
    """Fetch recent emails from inbox via IMAP"""
    replies = []

    imap_host = os.getenv("IMAP_HOST", "imap.gmail.com")
    imap_user = os.getenv("IMAP_USER") or os.getenv("BREVO_SMTP_USER")
    imap_pass = os.getenv("IMAP_PASS") or os.getenv("IMAP_PASSWORD")

    if not imap_user or not imap_pass:
        print("   ⚠️  IMAP credentials not configured")
        print("   Add IMAP_USER and IMAP_PASS to .env")
        return replies

    try:
        print(f"   📬 Connecting to {imap_host}...")
        mail = imaplib.IMAP4_SSL(imap_host)
        mail.login(imap_user, imap_pass)
        mail.select("INBOX")

        # Search for emails since N days ago
        since_date = (datetime.now() - timedelta(days=since_days)).strftime("%d-%b-%Y")
        status, messages = mail.search(None, f'SINCE {since_date}')

        if status != "OK":
            print("   ⚠️  Could not search inbox")
            return replies

        email_ids = messages[0].split()
        print(f"   📬 Found {len(email_ids)} emails to check")

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
                print(f"   ⚠️  Error reading email: {str(e)[:60]}")
                continue

        mail.logout()
        print(f"   ✅ Fetched {len(replies)} replies from inbox")

    except imaplib.IMAP4.error as e:
        print(f"   ❌ IMAP connection failed: {str(e)[:100]}")
        print("   Check IMAP_HOST, IMAP_USER, IMAP_PASS in .env")
    except Exception as e:
        print(f"   ❌ Email fetch failed: {str(e)[:100]}")

    return replies


# ─────────────────────────────────────────────────────────────────────────────
# PROCESS AND HANDLE REPLIES
# ─────────────────────────────────────────────────────────────────────────────
def process_replies(replies: list, dry_run: bool = False) -> dict:
    """Process all fetched replies — classify, draft responses, update leads"""
    config = load_config()
    log = load_reply_log()

    # Load all leads for matching
    enriched_file = "results/leads/enriched_leads.json"
    all_leads = []
    if os.path.exists(enriched_file):
        with open(enriched_file, "r") as f:
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

        print(f"\n   📨 Processing reply from: {from_email}")
        print(f"   Subject: {subject[:60]}")

        # Find matching lead
        lead = find_lead_by_email(from_email)
        if not lead:
            lead = find_lead_by_name_in_subject(subject, all_leads)

        if not lead:
            print(f"   ⚠️  No matching lead found — logging as unknown")
            lead = {
                "name": reply.get("from_name") or from_email,
                "contact_email": from_email
            }

        business_name = lead.get("name", from_email)
        print(f"   🏢 Matched to: {business_name}")

        # Classify the reply
        print(f"   🧠 Classifying intent...")
        classification = classify_reply(body, business_name)
        intent = classification.get("intent", "other")
        confidence = classification.get("confidence", "low")
        print(f"   📊 Intent: {intent} ({confidence} confidence)")
        print(f"   💬 Summary: {classification.get('summary', '')}")

        # Draft response
        print(f"   ✍️  Drafting response...")
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
            print(f"   📝 Draft: {drafted['body'][:120]}...")

        if not dry_run:
            print(f"   ✅ Reply queued — status: {reply_record['status']}")
        else:
            print(f"   🔍 DRY RUN — would queue reply")

    # Save everything
    save_reply_log(log)

    if not dry_run and all_leads:
        with open(enriched_file, "w") as f:
            json.dump(all_leads, f, indent=2, ensure_ascii=False)

    # Save processed replies for review
    if processed_replies:
        review_file = f"results/replies/pending_review_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(review_file, "w", encoding="utf-8") as f:
            json.dump(processed_replies, f, indent=2, ensure_ascii=False)
        print(f"\n   💾 Replies saved for review: {review_file}")

    return stats


# ─────────────────────────────────────────────────────────────────────────────
# SEND QUEUED REPLIES
# ─────────────────────────────────────────────────────────────────────────────
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

    print(f"\n📤 Sending {len(ready_replies)} queued replies...")

    for reply in ready_replies:
        drafted = reply["drafted_reply"]
        to_email = reply["from_email"]
        subject = drafted.get("subject", "Re: Your message")
        body = drafted.get("body", "")

        if not body or not to_email:
            continue

        print(f"\n   📧 Replying to: {reply['business']} ({to_email})")

        if dry_run:
            print(f"   🔍 DRY RUN — Subject: {subject}")
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
            print(f"   ✅ Reply sent")

        except Exception as e:
            print(f"   ❌ Failed: {str(e)[:80]}")
            reply["action_taken"] = "failed"
            reply["error"] = str(e)[:100]

    save_reply_log(log)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN MONITOR
# ─────────────────────────────────────────────────────────────────────────────
def run_reply_monitor(dry_run: bool = False, send_replies: bool = False):
    print(f"\n📬 REPLY MONITOR")
    print(f"{'='*55}")
    print(f"Time:         {datetime.now().strftime('%A %d %B %Y, %I:%M %p')}")
    print(f"Dry run:      {dry_run}")
    print(f"{'='*55}\n")

    # Fetch email replies
    print("📧 Checking email inbox...")
    email_replies = fetch_email_replies(since_days=7)

    all_replies = email_replies

    if not all_replies:
        print("\n✅ No new replies found")
    else:
        print(f"\n📨 Processing {len(all_replies)} replies...\n")
        stats = process_replies(all_replies, dry_run=dry_run)

        print(f"\n{'='*55}")
        print(f"📊 REPLY MONITOR SUMMARY")
        print(f"{'='*55}")
        print(f"Total processed:    {stats['processed']}")
        print(f"Interested:         {stats.get('interested', 0)} 🔥")
        print(f"Questions:          {stats.get('question', 0)} ❓")
        print(f"Not interested:     {stats.get('not_interested', 0)} ❌")
        print(f"Out of office:      {stats.get('out_of_office', 0)} 📅")
        print(f"Other:              {stats.get('other', 0)}")
        print(f"{'='*55}")

    # Send queued replies
    if send_replies:
        print(f"\n📤 Sending queued replies...")
        send_queued_replies(dry_run=dry_run)

    # Show interested leads summary
    log = load_reply_log()
    interested = [
        r for r in log["replies"]
        if r.get("classification", {}).get("intent") == "interested"
        and not r.get("action_taken")
    ]

    if interested:
        print(f"\n🔥 HOT LEADS NEEDING ATTENTION:")
        print(f"{'='*55}")
        for r in interested:
            print(f"  • {r['business']}")
            print(f"    Email: {r['from_email']}")
            print(f"    Reply: {r['body_preview'][:80]}...")
            print(f"    Status: {r['status']}")
            print()


if __name__ == "__main__":
    import sys
    dry_run = "--dry-run" in sys.argv
    send = "--send" in sys.argv
    run_reply_monitor(dry_run=dry_run, send_replies=send)