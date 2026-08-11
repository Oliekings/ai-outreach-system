import json
import os
import re
import smtplib
import socket
import sys
import dns.resolver
from datetime import datetime
from dotenv import load_dotenv
from groq import Groq
from anthropic import Anthropic

load_dotenv()


class Symbol:
    """Clean logging symbols that work across all terminals"""

    USE_EMOJI = False  # Set to True if your terminal supports UTF-8 emojis

    LIST = "📋" if USE_EMOJI else "[LIST]"
    LEAD = "💎" if USE_EMOJI else "[LEAD]"
    SEARCH = "🔍" if USE_EMOJI else "[SEARCH]"
    STOP = "🛑" if USE_EMOJI else "[STOP]"
    CHECK = "✅" if USE_EMOJI else "[OK]"
    WORLD = "🌍" if USE_EMOJI else "[WORLD]"
    WARN = "⚠️" if USE_EMOJI else "[WARN]"
    AI = "🧠" if USE_EMOJI else "[AI]"
    VIBE = "🎨" if USE_EMOJI else "[VIBE]"
    TONE = "🗣️" if USE_EMOJI else "[TONE]"
    PRIDE = "🆕" if USE_EMOJI else "[PRIDE]"
    TARGET = "🎯" if USE_EMOJI else "[TARGET]"
    TIME = "⏰" if USE_EMOJI else "[TIME]"
    NURTURE = "🌱" if USE_EMOJI else "[NURTURE]"
    REFERRAL = "🤝" if USE_EMOJI else "[REFERRAL]"
    EMAIL = "📧" if USE_EMOJI else "[EMAIL]"
    PHONE = "📞" if USE_EMOJI else "[PHONE]"
    WHATSAPP = "💬" if USE_EMOJI else "[WHATSAPP]"
    SOCIAL = "📱" if USE_EMOJI else "[SOCIAL]"
    INSTAGRAM = "📸" if USE_EMOJI else "[INSTAGRAM]"
    FACEBOOK = "📘" if USE_EMOJI else "[FACEBOOK]"
    RETRY = "🔄" if USE_EMOJI else "[RETRY]"
    BOT = "🛡️" if USE_EMOJI else "[BOT-WALL]"
    WAIT = "⏳" if USE_EMOJI else "[WAIT]"
    PITCH = "💡" if USE_EMOJI else "[PITCH]"
    PAGE = "📄" if USE_EMOJI else "[PAGE]"
    MAPS = "📍" if USE_EMOJI else "[MAPS]"
    ERROR = "❌" if USE_EMOJI else "[ERROR]"
    HUMAN = "🧑" if USE_EMOJI else "[USER]"


sys.stdout.reconfigure(encoding="utf-8")

os.makedirs("results/leads", exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# DNS MX RECORD CHECK
# ─────────────────────────────────────────────────────────────────────────────
def check_mx_record(domain: str) -> bool:
    try:
        records = dns.resolver.resolve(domain, "MX")
        return len(records) > 0
    except:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# SMTP VERIFICATION
# ─────────────────────────────────────────────────────────────────────────────
def verify_smtp(email: str) -> dict:
    result = {
        "email": email,
        "format_valid": False,
        "domain_exists": False,
        "mx_record_found": False,
        "smtp_handshake": False,
        "status": "invalid",
        "confidence": 0,
        "reason": "",
    }

    # Format check
    email_re = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_re, email):
        result["reason"] = "Invalid email format"
        return result

    result["format_valid"] = True
    domain = email.split("@")[1]

    # Domain existence check
    try:
        socket.gethostbyname(domain)
        result["domain_exists"] = True
    except:
        result["reason"] = f"Domain {domain} does not exist"
        result["status"] = "invalid"
        return result

    # MX record check
    result["mx_record_found"] = check_mx_record(domain)
    if not result["mx_record_found"]:
        result["reason"] = f"No mail server found for {domain}"
        result["status"] = "risky"
        result["confidence"] = 30
        return result

    # SMTP handshake
    try:
        mx_records = dns.resolver.resolve(domain, "MX")
        mx_host = str(sorted(mx_records, key=lambda r: r.preference)[0].exchange)

        with smtplib.SMTP(timeout=10) as smtp:
            smtp.connect(mx_host, 25)
            smtp.helo("verify.outreach.com")
            smtp.mail("verify@outreach.com")
            code, message = smtp.rcpt(email)

            if code == 250:
                result["smtp_handshake"] = True
                result["status"] = "valid"
                result["confidence"] = 95
                result["reason"] = "Mailbox confirmed via SMTP"
            elif code == 550:
                result["status"] = "invalid"
                result["confidence"] = 0
                result["reason"] = "Mailbox does not exist (550)"
            else:
                result["status"] = "risky"
                result["confidence"] = 50
                result["reason"] = f"Uncertain SMTP response: {code}"

    except smtplib.SMTPConnectError:
        # Server blocked check but domain and MX are valid — likely real
        result["status"] = "likely_valid"
        result["confidence"] = 70
        result["reason"] = (
            "Domain and MX verified — server blocks external SMTP checks (normal)"
        )
    except Exception as e:
        error = str(e).lower()
        if "timed out" in error or "timeout" in error:
            # Timeout usually means server is real but blocking checks
            result["status"] = "likely_valid"
            result["confidence"] = 65
            result["reason"] = (
                "Domain verified — timeout suggests real server blocking checks"
            )
        else:
            result["status"] = "risky"
            result["confidence"] = 45
            result["reason"] = f"SMTP inconclusive: {str(e)[:60]}"

    return result


# ─────────────────────────────────────────────────────────────────────────────
# AI HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def get_ai_response(prompt: str, max_tokens: int = 500) -> str:
    from utils.ai_client import ai_response

    return ai_response(prompt, task="verify", max_tokens=max_tokens)


def filter_relevant_emails(emails: list, business_name: str) -> list:
    """Use AI to filter out emails that don't belong to the business"""
    if not emails:
        return []

    prompt = f"""
You are checking which email addresses actually belong to "{business_name}".

Emails found:
{json.dumps(emails, indent=2)}

Rules for keeping an email:
- Domain matches or relates to the business name specifically
- Looks like a direct business contact (info@, contact@, bookings@, hello@, admin@)
- Gmail/Yahoo is acceptable ONLY if the username clearly relates to the business name
- REJECT any email from a directory, platform, or unrelated company

- placejoys.com@gmail.com (directory site email)
- anything@placejoys.com (directory)
- anything@b2bhint.com (directory)
- anything@dinesurf.com (directory)
- anything@vconnect.com (directory)
- unclaimed@anything.com (placeholder)

When in doubt — REJECT. It's better to have no email than a wrong one.

Return ONLY valid JSON:
{{
  "relevant_emails": ["only emails that actually belong to this business"],
  "rejected": ["emails that don't belong"],
  "reasoning": "one line explanation"
}}
"""
    try:
        import re

        response = get_ai_response(prompt, max_tokens=300)
        clean = re.sub(r"```json|```", "", response).strip()
        start = clean.find("{")
        end = clean.rfind("}")
        if start != -1 and end != -1:
            parsed = json.loads(clean[start : end + 1])
            return parsed.get("relevant_emails", [])
    except:
        pass
    return emails


# ─────────────────────────────────────────────────────────────────────────────
# BATCH EMAIL VERIFIER
# ─────────────────────────────────────────────────────────────────────────────
def verify_all_emails(leads_file: str = "results/leads/enriched_leads.json"):
    with open(leads_file, "r") as f:
        leads = json.load(f)

    print(f"\n{Symbol.EMAIL} Email Verifier — Checking {len(leads)} leads\n")
    print(f"=" * 60)

    verified_leads = []
    stats = {"valid": 0, "likely_valid": 0, "risky": 0, "invalid": 0, "no_email": 0}

    for i, lead in enumerate(leads, 1):
        name = lead["name"]
        print(f"\n[{i}/{len(leads)}] {Symbol.EMAIL} {name}")

        enriched = lead.copy()
        all_emails = lead.get("all_emails") or []
        primary_email = lead.get("contact_email")

        if primary_email and primary_email not in all_emails:
            all_emails.insert(0, primary_email)

        # Filter out irrelevant emails first
        if all_emails:
            print(
                f"   {Symbol.AI}  Filtering {len(all_emails)} emails for relevance..."
            )
            all_emails = filter_relevant_emails(all_emails, name)
            print(
                f"   {Symbol.CHECK} {len(all_emails)} relevant emails remaining after filter"
            )

        if not all_emails:
            print(f"   {Symbol.WARN}  No email found for this lead")
            enriched["email_verification"] = {
                "status": "no_email",
                "verified_emails": [],
                "best_email": None,
                "confidence": 0,
            }
            stats["no_email"] += 1
            verified_leads.append(enriched)
            continue

        verified_emails = []
        best_email = None
        best_confidence = 0

        for email in all_emails[:3]:  # Check top 3 emails per lead
            print(f"   {Symbol.SEARCH} Checking: {email}")
            result = verify_smtp(email)

            status_icon = {
                "valid": "{Symbol.CHECK}",
                "likely_valid": "ðŸŸ¢",
                "risky": "{Symbol.WARN} ",
                "invalid": "âŒ",
            }.get(result["status"], "â“")

            print(
                f"   {status_icon} {result['status'].upper()} ({result['confidence']}%) — {result['reason']}"
            )
            verified_emails.append(result)

            if result["confidence"] > best_confidence:
                best_confidence = result["confidence"]
                best_email = email
                stats[result["status"]] = stats.get(result["status"], 0) + 1

        # Update lead with verification results
        enriched["email_verification"] = {
            "status": verified_emails[0]["status"] if verified_emails else "invalid",
            "verified_emails": verified_emails,
            "best_email": best_email,
            "confidence": best_confidence,
        }
        enriched["contact_email"] = best_email

        # Final status
        if best_confidence >= 80:
            print(f"   💚 Best email: {best_email} ({best_confidence}% confidence)")
        elif best_confidence >= 50:
            print(
                f"   ðŸŸ¡ Best email: {best_email} ({best_confidence}% confidence — risky)"
            )
        else:
            print(f"   {Symbol.SEARCH}´ No reliable email found for {name}")

        verified_leads.append(enriched)

    # Save results
    with open("results/leads/enriched_leads.json", "w") as f:
        json.dump(verified_leads, f, indent=2)

    # Summary
    print("\n" + "=" * 60)
    print("📊 EMAIL VERIFICATION COMPLETE")
    print("=" * 60)
    print(f"Total leads processed:  {len(leads)}")
    print(f"{Symbol.CHECK} Valid emails:           {stats.get('valid', 0)}")
    print(f"ðŸŸ¢ Likely valid emails:    {stats.get('likely_valid', 0)}")
    print(f"{Symbol.WARN}  Risky emails:           {stats.get('risky', 0)}")
    print(f"âŒ Invalid emails:          {stats.get('invalid', 0)}")
    print(f"ðŸš« No email found:          {stats.get('no_email', 0)}")
    usable = stats.get("valid", 0) + stats.get("likely_valid", 0)
    print(f"\n💚 Total usable emails:    {usable}/{len(leads)}")
    print(f"\nUpdated: results/leads/enriched_leads.json")
    print("=" * 60)


if __name__ == "__main__":
    # Install dnspython if needed
    try:
        import dns.resolver
    except ImportError:
        print("Installing dnspython...")
        os.system("pip install dnspython")
        import dns.resolver

    verify_all_emails()
