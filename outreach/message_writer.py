from groq import Groq
from anthropic import Anthropic
import time
import random

import os
import json
import re
import sys
from dotenv import load_dotenv

load_dotenv()

sys.stdout.reconfigure(encoding="utf-8")

os.makedirs("results/emails", exist_ok=True)
os.makedirs("results/messages", exist_ok=True)
os.makedirs("results/messages/whatsapp", exist_ok=True)
os.makedirs("results/messages/instagram", exist_ok=True)
os.makedirs("results/messages/facebook", exist_ok=True)
os.makedirs("results/messages/sequences", exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# AI CLIENT
# ─────────────────────────────────────────────────────────────────────────────
def get_ai_response(prompt: str, max_tokens: int = 1500, retry: int = 3) -> str:
    from utils.ai_client import ai_response

    return ai_response(prompt, task="generate", max_tokens=max_tokens, retry=retry)


from utils.ai_client import safe_json
from utils.symbols import Symbol


def clean_message_content(content: str, default_option: int = 2) -> str:
    """
    If the content contains multiple options/variations (formatted with headers),
    extract a single clean option to avoid sending headers and all options.
    If the user has edited the message and removed the headers, returns the content as-is.

    default_option = 1: Professional & Formal (index 0)
    default_option = 2: Warm & Conversational (index 1)
    default_option = 3: Short DM (index 2)
    """
    if not content:
        return ""

    lines = content.splitlines()
    options = {}  # key: int (1, 2, or 3) -> list of lines
    current_option = None

    import re

    header_pat = re.compile(
        r"^\s*(?:Option\s*(\d+)\s*[:\-]|Variation\s*(\d+)\s*[:\-]|===\s*VARIATION\s*(\d+)\s*===|Option\s*(\d+)\s*$|Variation\s*(\d+)\s*$)",
        re.IGNORECASE,
    )

    has_headers = False
    for line in lines:
        match = header_pat.match(line)
        if match:
            has_headers = True
            opt_num = next(int(g) for g in match.groups() if g is not None)
            current_option = opt_num
            options[current_option] = []
        else:
            if current_option is not None:
                options[current_option].append(line)

    if not has_headers:
        return content

    # Pick preferred option
    if default_option == 3:
        pref_order = [3, 2, 1]
    elif default_option == 1:
        pref_order = [1, 2, 3]
    else:
        pref_order = [2, 1, 3]

    for opt in pref_order:
        if opt in options:
            opt_content = "\n".join(options[opt]).strip()
            if opt_content:
                return opt_content

    return content


# ─────────────────────────────────────────────────────────────────────────────
# LEAD CONTEXT BUILDER
# builds a rich human-readable summary of everything we know about the lead
# this feeds every message writer so nothing feels generic
# ─────────────────────────────────────────────────────────────────────────────
def build_lead_context(lead: dict) -> dict:
    personality = lead.get("personality") or {}
    reviews = lead.get("reviews_analysis") or {}
    ig = lead.get("instagram") or {}
    fb = lead.get("facebook") or {}
    audits = lead.get("audits") or {}
    website_audit = audits.get("website") or {}
    gbp_audit = audits.get("google_business") or {}
    wa_audit = audits.get("whatsapp") or {}
    seo_audit = audits.get("seo") or {}
    comp_audit = audits.get("competitor_gap") or {}
    revenue = lead.get("revenue_opportunity") or {}
    official_site = lead.get("official_website") or {}
    timing = lead.get("contact_timing") or {}

    # Owner greeting
    owner = lead.get("owner_name")
    owner_source = lead.get("owner_source") or ""

    # Reject titles without real names
    fake_names = ["mrs", "mr", "dr", "chief", "happy", "sir", "madam"]
    if owner:
        first = owner.strip().split()[0].lower()
        if first in fake_names or len(owner.strip()) < 3:
            owner = None

    # Only use owner if source is confirmed
    if owner and any(
        conf in owner_source.lower()
        for conf in ["high", "linkedin", "website", "medium"]
    ):
        first_name = owner.strip().split()[0].title()
    else:
        first_name = None
        owner = None

    # Best compliment to open with
    praises = reviews.get("praises") or []
    complaints = reviews.get("complaints") or []
    compliment = personality.get("compliment_hook") or (
        f"the incredible {praises[0]}"
        if praises
        else f"what you've built at {lead['name']}"
    )

    # Most urgent pain point
    pain = personality.get("pain_hook") or (
        complaints[0]
        if complaints
        else personality.get("biggest_opportunity") or "your digital presence"
    )

    # Revenue hook
    monthly_lost = revenue.get("monthly_lost_naira", 0)
    revenue_hook = (
        f"₦{monthly_lost:,}/month in potential revenue" if monthly_lost > 0 else None
    )

    # Competitor threat
    threats = comp_audit.get("urgent_threats") or []
    competitor_threat = threats[0] if threats else None

    # Critical website issues
    site_issues = website_audit.get("issues") or []
    site_wins = website_audit.get("wins") or []

    # WhatsApp status
    has_whatsapp = wa_audit.get("has_whatsapp", False)
    whatsapp_number = lead.get("contact_whatsapp")

    # Social presence
    on_instagram = ig.get("found", False)
    raw_ig_url = ig.get("url") or ""
    if raw_ig_url and "instagram.com" in raw_ig_url:
        ig_match = re.search(
            r"(https?://(?:www\.)?instagram\.com/[a-zA-Z0-9._]{2,}?)(?:/reels|/posts|/tagged|/\?|/#|$)",
            raw_ig_url,
        )
        instagram_url = ig_match.group(1).rstrip("/") if ig_match else None
    else:
        instagram_url = None
    instagram_followers = ig.get("followers")
    on_facebook = fb.get("found", False)
    # Clean Facebook URL — strip to page level only
    raw_fb_url = fb.get("url") or ""
    if raw_fb_url and "facebook.com" in raw_fb_url:
        # Extract clean page URL — must be at least 5 chars after facebook.com/
        fb_match = re.search(
            r"(https?://(?:www\.)?facebook\.com/(?!p$|pg/|pages/)[a-zA-Z0-9._\-]{3,})",
            raw_fb_url,
        )
        facebook_url = fb_match.group(1) if fb_match else None
        # Reject numeric-only IDs that are too short
        if facebook_url:
            slug = facebook_url.split("facebook.com/")[-1]
            if len(slug) < 4:
                facebook_url = None
    else:
        facebook_url = None

    # SEO visibility
    in_local_pack = seo_audit.get("ranks_in_local_pack", False)

    # Website status
    has_website = bool(official_site.get("url"))
    website_url = official_site.get("url")
    website_grade = website_audit.get("grade", "N/A")

    # Business character
    vibe = personality.get("vibe", "professional")
    tone = personality.get("tone_to_use", "semi-formal")
    use_pidgin = personality.get("use_pidgin", False)
    key_pride = personality.get("key_pride", "")
    target_audience = personality.get("target_audience", "customers")
    biggest_opportunity = personality.get("biggest_opportunity", "")

    # Season/timing note
    season_note = timing.get("season_note")
    best_time = timing.get("best_send_time", "Tuesday–Thursday, 9am–12pm")

    return {
        "name": lead["name"],
        "owner": owner,
        "first_name": first_name,
        "email": lead.get("contact_email"),
        "whatsapp": whatsapp_number,
        "all_phones": lead.get("all_phones", []),
        "instagram_url": instagram_url,
        "instagram_followers": instagram_followers,
        "facebook_url": facebook_url,
        "on_instagram": on_instagram,
        "on_facebook": on_facebook,
        "has_whatsapp": has_whatsapp,
        "has_website": has_website,
        "website_url": website_url,
        "website_grade": website_grade,
        "site_issues": site_issues[:4],
        "site_wins": site_wins[:3],
        "vibe": vibe,
        "tone": tone,
        "use_pidgin": use_pidgin,
        "key_pride": key_pride,
        "target_audience": target_audience,
        "biggest_opportunity": biggest_opportunity,
        "compliment": compliment,
        "pain": pain,
        "praises": praises[:3],
        "complaints": complaints[:3],
        "revenue_hook": revenue_hook,
        "competitor_threat": competitor_threat,
        "in_local_pack": in_local_pack,
        "season_note": season_note,
        "best_send_time": best_time,
        "rating": lead.get("rating"),
        "reviews": lead.get("reviews"),
        "city": lead.get("city", "Abuja"),
        "sample_site_url": lead.get("site_url"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# EMAIL WRITER
# writes 3 emails per lead:
# email_1 — first contact, zero pitch, makes them feel seen
# email_2 — follow up after no reply, delivers the audit report
# email_3 — final follow up, soft close with sample site offer
# ─────────────────────────────────────────────────────────────────────────────
def write_emails(ctx: dict) -> dict:
    greeting = f"Hi {ctx['first_name']}," if ctx["first_name"] else f"Hi,"
    business = ctx["name"]
    has_website = ctx["has_website"]
    site_issues = ctx["site_issues"]
    revenue_hook = ctx["revenue_hook"]
    competitor_threat = ctx["competitor_threat"]
    praises = ctx["praises"]
    complaints = ctx["complaints"]
    vibe = ctx["vibe"]
    tone = ctx["tone"]

    # Build issue summary for email 2
    issues_text = ""
    if site_issues:
        issues_text = "\n".join(f"• {issue}" for issue in site_issues[:4])
    elif not has_website:
        issues_text = "• No website found — customers searching online can't find you\n• No online booking system\n• No WhatsApp button for easy contact\n• Missing from key digital directories"

    prompt_email1 = f"""
Write a highly persuasive but natural-sounding outreach email for a {ctx.get('niche', 'business/school/company')} in {ctx.get('city', 'Abuja')}, Nigeria.

The message should:
* Start with a genuine compliment based on their brand, mission, website, or online presence: {ctx.get('compliment', 'what you have built')}
* Sound human, warm, confident, and professional
* Subtly identify a missed opportunity in their digital presence, marketing, branding, website, or social media: {ctx['biggest_opportunity']}
* Position my service as a valuable solution without sounding desperate or overly salesy.
  - My service/business is: A digital consulting and development service that builds premium websites, custom portals, sets up Google Maps SEO and WhatsApp business automation, and deploys custom AI customer service agents to help businesses automate operations, increase visibility, and convert more leads.
* Create curiosity and emotional buy-in.
* Make the recipient feel understood, respected, and important.
* Include psychologically engaging questions that naturally encourage a response.
* End with a soft but compelling call-to-action that is difficult to ignore.

Tone:
* Conversational, Intelligent, Premium, Friendly but strategic, Persuasive without pressure.
* Avoid generic marketing language.
* Avoid sounding robotic.
* Default Tone Guideline: {tone} (sprinkle naturally, use {vibe} vibe)

Additional details to mention (integrate naturally where appropriate):
- Business name: {business}
- Owner first name: {ctx['first_name'] or 'there'}
- Key pride of this business: {ctx['key_pride']}
- Has website: {has_website}
- Website grade: {ctx['website_grade']}
- What customers love: {praises}
- What customers complain about: {complaints}
- Revenue opportunity: {revenue_hook or 'significant monthly revenue being lost'}
- Competitor threat: {competitor_threat or 'competitors are pulling ahead digitally'}
- Season note: {ctx['season_note'] or 'None'}
- Sample site built for them: {ctx.get('sample_site_url') or 'None'} (If a sample site URL is provided, you MUST include it warmly in the email and invite them to check it out on their own custom page! Let them know we made this custom demo for them.)

Generate 3 variations:
1. Professional and formal
2. Warm and conversational
3. Short high-conversion DM version

Return ONLY valid JSON:
{{
  "subject": "subject line here",
  "preview_text": "preview text here",
  "variation_1": "Professional and formal version here",
  "variation_2": "Warm and conversational version here",
  "variation_3": "Short high-conversion DM version here"
}}
"""

    prompt_email2 = f"""
You are writing the SECOND email to a business owner who didn't reply to the first email.
This email delivers a FREE audit report as a gift — no strings attached.

Business: {business}
Owner first name: {ctx['first_name'] or 'there'}
Business vibe: {vibe}
Tone: {tone}
Has website: {has_website}
Issues found:
{issues_text}
Revenue opportunity: {revenue_hook or 'significant monthly revenue being lost'}
Competitor threat: {competitor_threat or 'competitors are pulling ahead digitally'}

STRICT RULES:
- Reference that you sent a message before (briefly, warmly — not guilting)
- Lead with the free audit as a genuine gift
- Mention 2-3 specific issues found — in plain language, not technical
- Include the revenue hook if available — make it feel real not salesy
- End with offer to send the full report — ask if they want it
- Tone: warm expert friend, not cold salesperson
- Max 160 words
- Subject must create genuine curiosity

Return ONLY valid JSON:
{{
  "subject": "subject line here",
  "body": "full email body here",
  "preview_text": "preview text here"
}}
"""

    prompt_email3 = f"""
You are writing the THIRD and final email in a sequence to a business owner.
This is the last touch — after this we move to nurture mode.
This email makes a soft, no-pressure offer to show them a sample website built specifically for their business.

Business: {business}
Owner first name: {ctx['first_name'] or 'there'}
Business vibe: {vibe}
Tone: {tone}
Has website: {has_website}
Website grade: {ctx['website_grade']}
Biggest opportunity: {ctx['biggest_opportunity']}

STRICT RULES:
- Acknowledge this is the last message — respect their time
- Make ONE clear, soft offer: a free sample site built for their business
- No pressure, no guilt, no urgency tactics
- If they're not ready now, wish them genuinely well
- Mention the referral — if they know someone who could use this, you'd appreciate the mention
- End warmly, leave the door open forever
- Max 130 words
- Subject must feel like a warm goodbye, not a last chance sales pitch

Return ONLY valid JSON:
{{
  "subject": "subject line here",
  "body": "full email body here",
  "preview_text": "preview text here"
}}
"""

    emails = {}

    for key, prompt in [("email_1", prompt_email1)]:
        try:
            response = get_ai_response(prompt, max_tokens=800)
            parsed = safe_json(response)
            if parsed:
                body_content = f"""Option 1: Professional & Formal
{parsed.get('variation_1', parsed.get('body', '')).strip()}

Option 2: Warm & Conversational
{parsed.get('variation_2', '').strip()}

Option 3: Short High-Conversion DM
{parsed.get('variation_3', '').strip()}"""

                emails[key] = {
                    "to": ctx["email"],
                    "subject": parsed.get("subject", ""),
                    "body": body_content.strip(),
                    "preview_text": parsed.get("preview_text", ""),
                    "send_day": 0,
                    "channel": "email",
                }
            else:
                emails[key] = {"error": "Failed to parse AI response"}
        except Exception as e:
            emails[key] = {"error": str(e)}

    return emails


# ─────────────────────────────────────────────────────────────────────────────
# WHATSAPP MESSAGE WRITER
# writes 3 whatsapp messages per lead:
# wa_1 — first contact, ultra short, warm, feels like a friend
# wa_2 — follow up after no reply, delivers one insight
# wa_3 — final touch, soft offer + referral ask
# ─────────────────────────────────────────────────────────────────────────────
def write_whatsapp_messages(ctx: dict) -> dict:
    business = ctx["name"]
    first_name = ctx["first_name"] or ""
    praises = ctx["praises"]
    complaints = ctx["complaints"]
    vibe = ctx["vibe"]
    use_pidgin = ctx["use_pidgin"]
    revenue_hook = ctx["revenue_hook"]
    has_website = ctx["has_website"]
    biggest_opportunity = ctx["biggest_opportunity"]

    prompt_wa1 = f"""
Write a highly persuasive but natural-sounding outreach WhatsApp message for a {ctx.get('niche', 'business/school/company')} in {ctx.get('city', 'Abuja')}, Nigeria.

The message should:
* Start with a genuine compliment based on their brand, mission, website, or online presence: {ctx.get('compliment', 'what you have built')}
* Sound human, warm, confident, and professional
* Subtly identify a missed opportunity in their digital presence, marketing, branding, website, or social media: {biggest_opportunity}
* Position my service as a valuable solution without sounding desperate or overly salesy.
  - My service/business is: A digital consulting and development service that builds premium websites, custom portals, sets up Google Maps SEO and WhatsApp business automation, and deploys custom AI customer service agents to help businesses automate operations, increase visibility, and convert more leads.
* Create curiosity and emotional buy-in.
* Make the recipient feel understood, respected, and important.
* Include psychologically engaging questions that naturally encourage a response.
* End with a soft but compelling call-to-action that is difficult to ignore.

Tone:
* Conversational, Intelligent, Premium, Friendly but strategic, Persuasive without pressure.
* Avoid generic marketing language.
* Avoid sounding robotic.
* Sprinkle natural Nigerian pidgin if use_pidgin is true (use_pidgin = {use_pidgin}).
* Emojis: maximum 2, only if they feel natural.

Additional details to mention (integrate naturally where appropriate):
- Business name: {business}
- Owner first name: {first_name or 'there'}
- Has website: {has_website}
- What customers love: {praises}
- Sample site built for them: {ctx.get('sample_site_url') or 'None'} (If a sample site URL is provided, you MUST include it warmly in the message and invite them to check it out on their own custom page! Let them know we made this custom demo for them.)

Generate 3 variations:
1. Professional and formal
2. Warm and conversational
3. Short high-conversion DM version

Return ONLY valid JSON:
{{
  "variation_1": "Professional and formal version here",
  "variation_2": "Warm and conversational version here",
  "variation_3": "Short high-conversion DM version here"
}}
"""

    prompt_wa2 = f"""
Write a second WhatsApp follow-up message to a business owner who didn't reply.

Business: {business}
Owner first name: {first_name}
Vibe: {vibe}
Use pidgin: {use_pidgin}
Revenue opportunity: {revenue_hook or 'significant opportunity identified'}
Competitor threat: {ctx['competitor_threat'] or 'competitors are getting ahead'}

STRICT RULES:
- Maximum 4 sentences
- Acknowledge you reached out before — briefly, warmly
- Drop ONE specific insight that's genuinely useful to them
- Reference the revenue or competitor hook naturally
- End with a soft question or offer
- Still zero pitch — just value
- Feels like a friend who noticed something important

Return ONLY valid JSON:
{{
  "message": "the whatsapp message here"
}}
"""

    prompt_wa3 = f"""
Write the third and final WhatsApp message to a business owner.

Business: {business}
Owner first name: {first_name}
Vibe: {vibe}
Use pidgin: {use_pidgin}
Has website: {has_website}
Biggest opportunity: {biggest_opportunity}

STRICT RULES:
- Maximum 3 sentences
- Warm, genuine, zero pressure
- Make ONE soft offer — a free sample of what their digital presence could look like
- If not ready, genuinely wish them well and mention referrals warmly
- Leave the door open forever — no guilt, no urgency
- Must feel like a real human being, not a campaign

Return ONLY valid JSON:
{{
  "message": "the whatsapp message here"
}}
"""

    messages = {}

    for key, prompt in [("wa_1", prompt_wa1)]:
        try:
            response = get_ai_response(prompt, max_tokens=800)
            parsed = safe_json(response)
            if parsed:
                msg_content = f"""Option 1: Professional & Formal
{parsed.get('variation_1', parsed.get('message', '')).strip()}

Option 2: Warm & Conversational
{parsed.get('variation_2', '').strip()}

Option 3: Short High-Conversion DM
{parsed.get('variation_3', '').strip()}"""

                messages[key] = {
                    "to": ctx["all_phones"],
                    "message": msg_content.strip(),
                    "send_day": 1,
                    "channel": "whatsapp",
                }
            else:
                messages[key] = {"error": "Failed to parse AI response"}
        except Exception as e:
            messages[key] = {"error": str(e)}

    return messages


# ─────────────────────────────────────────────────────────────────────────────
# FULL SEQUENCE BUILDER
# assembles all messages into a day-by-day send sequence per lead
# ─────────────────────────────────────────────────────────────────────────────
def build_send_sequence(
    ctx: dict,
    emails: dict,
    whatsapp: dict,
    instagram: dict = None,
    facebook: dict = None,
) -> list:
    instagram = instagram or {}
    facebook = facebook or {}
    sequence = []

    # Helper to safely extract messages from any channel dict
    def extract_messages(channel_dict: dict, content_key: str) -> list:
        messages = []
        for key, msg in channel_dict.items():
            if not isinstance(msg, dict):
                continue
            if "error" in msg:
                continue
            content = msg.get(content_key) or msg.get("message") or msg.get("body")
            if not content or not content.strip():
                continue
            messages.append(msg)
        return messages

    # WhatsApp
    if ctx.get("whatsapp"):
        for msg in extract_messages(whatsapp, "message"):
            sequence.append(
                {
                    "day": msg.get("send_day", 1),
                    "channel": "whatsapp",
                    "to": ctx["whatsapp"],
                    "content": msg.get("message", ""),
                    "status": "queued",
                }
            )

    # Instagram
    if ctx.get("on_instagram") and ctx.get("instagram_url"):
        for msg in extract_messages(instagram, "message"):
            sequence.append(
                {
                    "day": msg.get("send_day", 2),
                    "channel": "instagram",
                    "to": ctx["instagram_url"],
                    "content": msg.get("message", ""),
                    "status": "queued",
                }
            )

    # Email
    if ctx.get("email"):
        for msg in extract_messages(emails, "body"):
            sequence.append(
                {
                    "day": msg.get("send_day", 3),
                    "channel": "email",
                    "to": ctx["email"],
                    "subject": msg.get("subject", ""),
                    "content": msg.get("body", ""),
                    "preview": msg.get("preview_text", ""),
                    "status": "queued",
                }
            )

    # Facebook
    if ctx.get("on_facebook") and ctx.get("facebook_url"):
        for msg in extract_messages(facebook, "message"):
            sequence.append(
                {
                    "day": msg.get("send_day", 5),
                    "channel": "facebook",
                    "to": ctx["facebook_url"],
                    "content": msg.get("message", ""),
                    "status": "queued",
                }
            )

    # Sort by send day
    sequence.sort(key=lambda x: x.get("day", 99))
    return sequence


# ─────────────────────────────────────────────────────────────────────────────
# SAVE MESSAGES — organized per lead
# ─────────────────────────────────────────────────────────────────────────────
def save_messages(lead_name: str, emails: dict, whatsapp: dict, sequence: list):
    safe_name = lead_name.replace(" ", "_").replace("/", "_").replace("&", "and")

    # Save emails
    email_path = f"results/emails/{safe_name}_emails.json"
    with open(email_path, "w", encoding="utf-8") as f:
        json.dump(emails, f, indent=2, ensure_ascii=False)

    # Save WhatsApp
    wa_path = f"results/messages/whatsapp/{safe_name}_whatsapp.json"
    with open(wa_path, "w", encoding="utf-8") as f:
        json.dump(whatsapp, f, indent=2, ensure_ascii=False)

    # Save full sequence
    seq_path = f"results/messages/sequences/{safe_name}_sequence.json"
    with open(seq_path, "w", encoding="utf-8") as f:
        json.dump(sequence, f, indent=2, ensure_ascii=False)

    return {"email": email_path, "whatsapp": wa_path, "sequence": seq_path}


# ─────────────────────────────────────────────────────────────────────────────
# PRINT PREVIEW — shows messages beautifully in terminal
# ─────────────────────────────────────────────────────────────────────────────
def print_preview(
    lead_name: str,
    ctx: dict,
    emails: dict,
    whatsapp: dict,
    instagram: dict,
    facebook: dict,
):
    print(f"\n{'═'*65}")
    print(f"  📬 MESSAGE PREVIEW — {lead_name}")
    print(f"{'═'*65}")

    # Email 1
    e1 = emails.get("email_1") or {}
    if e1.get("subject"):
        print(
            f"\n  {Symbol.EMAIL} EMAIL 1 (Day {e1.get('send_day', 3)}) → {ctx['email'] or 'No email'}"
        )
        print(f"  Subject: {e1['subject']}")
        print(f"  Preview: {e1.get('preview_text', '')}")
        print(f"  ─────────────────────────────────────────────────")
        body_lines = e1.get("body", "").split("\n")
        for line in body_lines[:8]:
            print(f"  {line}")
        if len(body_lines) > 8:
            print(f"  ... [{len(body_lines)-8} more lines]")

    # WhatsApp 1
    wa1 = whatsapp.get("wa_1") or {}
    if wa1.get("message"):
        print(
            f"\n  {Symbol.WHATSAPP} WHATSAPP 1 (Day {wa1.get('send_day', 1)}) → {ctx['whatsapp'] or 'No number'}"
        )
        print(f"  ─────────────────────────────────────────────────")
        print(f"  {wa1['message']}")

    # Instagram 1
    ig1 = instagram.get("ig_1") or {}
    if ig1.get("message"):
        print(
            f"\n  {Symbol.INSTAGRAM} INSTAGRAM DM 1 (Day {ig1.get('send_day', 2)}) → {ctx['instagram_url'] or 'No profile'}"
        )
        print(f"  ─────────────────────────────────────────────────")
        print(f"  {ig1['message']}")

    # Facebook 1
    fb1 = facebook.get("fb_1") or {}
    if fb1.get("message"):
        print(
            f"\n  {Symbol.FACEBOOK} FACEBOOK MSG 1 (Day {fb1.get('send_day', 5)}) → {ctx['facebook_url'] or 'No page'}"
        )
        print(f"  ─────────────────────────────────────────────────")
        print(f"  {fb1['message']}")

    print(f"\n{'═'*65}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def write_all_messages(
    enriched_file: str = "results/leads/enriched_leads.json",
    audit_file: str = "results/audits/general_audit_results.json",
):
    # Load enriched leads
    with open(enriched_file, "r", encoding="utf-8") as f:
        enriched_leads = json.load(f)

    # Load audit results and index by name
    audit_map = {}
    if os.path.exists(audit_file):
        with open(audit_file, "r", encoding="utf-8") as f:
            audit_results = json.load(f)
        for result in audit_results:
            audit_map[result["name"]] = result

    # Load existing approved/sent messages to preserve them
    master_path = "results/messages/sequences/master_sequence.json"
    approved_messages = {}  # key: (lead_name, channel, day) -> msg_dict
    if os.path.exists(master_path):
        try:
            with open(master_path, "r", encoding="utf-8") as f:
                old_data = json.load(f)
            for item in old_data:
                lead_name = item.get("lead")
                for msg in item.get("sequence", []):
                    if msg.get("status") in ["approved", "sent"]:
                        approved_messages[
                            (lead_name, msg.get("channel"), msg.get("day"))
                        ] = msg
        except Exception as e:
            print(f"⚠️  Could not load existing master sequence: {e}")

    print(f"\n✍️  Message Writer — Writing for {len(enriched_leads)} leads")
    print(f"{'='*65}")

    all_sequences = []
    stats = {
        "total": len(enriched_leads),
        "emails_written": 0,
        "whatsapp_written": 0,
        "no_contacts": 0,
    }

    for i, lead in enumerate(enriched_leads, 1):
        name = lead["name"]
        print(
            f"\n[{i}/{len(enriched_leads)}] ✍️  Writing/Updating messages for: {name}"
        )

        # Merge audit data into lead
        if name in audit_map:
            lead["audits"] = audit_map[name].get("audits", {})
            lead["revenue_opportunity"] = audit_map[name].get("revenue_opportunity", {})

        # Build rich context
        ctx = build_lead_context(lead)

        # Check if we have any contact channels
        has_any_contact = any([ctx["email"], ctx["whatsapp"], ctx.get("all_phones")])

        if not has_any_contact:
            print(f"   {Symbol.WARN}  No contact channels found — skipping")
            stats["no_contacts"] += 1
            continue

        print(f"   {Symbol.EMAIL} Email: {ctx['email'] or '—'}")
        print(f"   {Symbol.WHATSAPP} WhatsApp: {ctx['whatsapp'] or '—'}")

        # Check for approved/sent messages
        emails = {}
        whatsapp = {}

        approved_email = approved_messages.get((name, "email", 0))
        approved_wa = approved_messages.get((name, "whatsapp", 1))

        # Write/preserve emails
        if approved_email:
            print(f"   ℹ️  Preserving approved/sent email_1")
            emails["email_1"] = {
                "to": approved_email.get("to"),
                "subject": approved_email.get("subject"),
                "body": approved_email.get("content"),
                "preview_text": approved_email.get("preview"),
                "send_day": 0,
                "channel": "email",
            }
        elif ctx["email"]:
            print(f"   ✍️  Writing emails...")
            emails = write_emails(ctx)
            if emails:
                stats["emails_written"] += 1
            time.sleep(random.uniform(2, 4))

        # Write/preserve WhatsApp
        if approved_wa:
            print(f"   ℹ️  Preserving approved/sent WhatsApp message")
            whatsapp["wa_1"] = {
                "to": approved_wa.get("to"),
                "message": approved_wa.get("content"),
                "send_day": 1,
                "channel": "whatsapp",
            }
        elif ctx["whatsapp"] or ctx.get("all_phones"):
            print(f"   ✍️  Writing WhatsApp messages...")
            whatsapp = write_whatsapp_messages(ctx)
            if whatsapp:
                stats["whatsapp_written"] += 1
            time.sleep(random.uniform(2, 4))

        # Build unified send sequence
        sequence = build_send_sequence(ctx, emails, whatsapp)

        # Apply approved/sent overrides
        for item in sequence:
            key = (name, item["channel"], item["day"])
            if key in approved_messages:
                item["status"] = approved_messages[key]["status"]
                item["content"] = approved_messages[key]["content"]
                if "subject" in approved_messages[key]:
                    item["subject"] = approved_messages[key]["subject"]
                if "preview" in approved_messages[key]:
                    item["preview"] = approved_messages[key]["preview"]
                if "to" in approved_messages[key]:
                    item["to"] = approved_messages[key]["to"]

        # Save everything
        paths = save_messages(name, emails, whatsapp, sequence)

        all_sequences.append(
            {
                "lead": name,
                "channels": {
                    "email": ctx["email"],
                    "whatsapp": ctx.get("all_phones") or ctx["whatsapp"],
                },
                "sequence": sequence,
                "files": paths,
            }
        )

        print(f"   {Symbol.CHECK} Done — {len(sequence)} messages in sequence")

    # Save master sequence file
    master_path = "results/messages/sequences/master_sequence.json"
    with open(master_path, "w", encoding="utf-8") as f:
        json.dump(all_sequences, f, indent=2, ensure_ascii=False)

    # Final summary
    print(f"\n{'='*65}")
    print(f"✍️  MESSAGE WRITING COMPLETE")
    print(f"{'='*65}")
    print(f"Total leads:              {stats['total']}")
    print(f"Email sequences written:  {stats['emails_written']}")
    print(f"WhatsApp sequences:       {stats['whatsapp_written']}")
    print(f"No contacts found:        {stats['no_contacts']}")
    print(f"\nFiles saved:")
    print(f"  results/emails/          — email sequences per lead")
    print(f"  results/messages/whatsapp/ — whatsapp sequences per lead")
    print(f"  results/messages/sequences/master_sequence.json")
    print(f"{'='*65}")


if __name__ == "__main__":
    write_all_messages()
