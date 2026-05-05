from groq import Groq
from anthropic import Anthropic
import time
import random

import os
import json
import re
from dotenv import load_dotenv
load_dotenv()

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
    for attempt in range(retry):
        try:
            claude = Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
            response = claude.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            error = str(e).lower()
            if "credit" in error or "balance" in error:
                try:
                    groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
                    response = groq.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        max_tokens=max_tokens,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    return response.choices[0].message.content
                except Exception as groq_error:
                    groq_err = str(groq_error).lower()
                    if "rate" in groq_err or "limit" in groq_err:
                        wait = (attempt + 1) * 15
                        print(f"      ⏳ Rate limited — waiting {wait}s before retry...")
                        time.sleep(wait)
                        continue
                    raise groq_error
            elif "rate" in error or "limit" in error:
                wait = (attempt + 1) * 15
                print(f"      ⏳ Rate limited — waiting {wait}s before retry...")
                time.sleep(wait)
                continue
            raise e
    return ""


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
        f"the incredible {praises[0]}" if praises else
        f"what you've built at {lead['name']}"
    )

    # Most urgent pain point
    pain = personality.get("pain_hook") or (
        complaints[0] if complaints else
        personality.get("biggest_opportunity") or
        "your digital presence"
    )

    # Revenue hook
    monthly_lost = revenue.get("monthly_lost_naira", 0)
    revenue_hook = (
        f"₦{monthly_lost:,}/month in potential revenue" if monthly_lost > 0
        else None
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
            r'(https?://(?:www\.)?instagram\.com/[a-zA-Z0-9._]{2,}?)(?:/reels|/posts|/tagged|/\?|/#|$)',
            raw_ig_url
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
            r'(https?://(?:www\.)?facebook\.com/(?!p$|pg/|pages/)[a-zA-Z0-9._\-]{3,})',
            raw_fb_url
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
        "city": lead.get("city", "Abuja")
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
You are writing the FIRST ever email from a digital consultant to a business owner in {ctx.get('city', 'Abuja')}, Nigeria.

Business: {business}
Owner first name: {ctx['first_name'] or 'there'}
Business vibe: {vibe}
Tone: {tone}
What customers love: {praises}
What customers complain about: {complaints}
Key pride of this business: {ctx['key_pride']}
Has website: {has_website}
Biggest digital gap: {ctx['biggest_opportunity']}
Season note: {ctx['season_note'] or 'None'}

STRICT RULES:
- This email has ZERO pitch and ZERO selling
- It is purely a warm, genuine human observation
- Reference something REAL and SPECIFIC we found about their business
- Open with a genuine compliment about something real
- Mention ONE specific gap we noticed — naturally, not pushy
- End with ONE soft curious question that invites a reply
- NO company name, NO services mentioned, NO calls to action
- Sound like a real person who genuinely noticed something while browsing
- Max 120 words in the body
- Use {tone} tone throughout
- Subject line must feel personal, not marketing

Return ONLY valid JSON:
{{
  "subject": "subject line here",
  "body": "full email body here",
  "preview_text": "the preview text shown in inbox before opening"
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

    for key, prompt in [
        ("email_1", prompt_email1),
        ("email_2", prompt_email2),
        ("email_3", prompt_email3)
    ]:
        try:
            response = get_ai_response(prompt, max_tokens=800)
            parsed = safe_json(response)
            if parsed:
                emails[key] = {
                    "to": ctx["email"],
                    "subject": parsed.get("subject", ""),
                    "body": parsed.get("body", ""),
                    "preview_text": parsed.get("preview_text", ""),
                    "send_day": {"email_1": 3, "email_2": 7, "email_3": 14}[key],
                    "channel": "email"
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
Write a first WhatsApp message to a business owner in {ctx.get('city', 'Abuja')}, Nigeria.

Business: {business}
Owner first name: {first_name}
Vibe: {vibe}
Use pidgin: {use_pidgin}
What customers love: {praises}
Biggest gap: {biggest_opportunity}
Has website: {has_website}

STRICT RULES:
- This is WhatsApp — it must feel like a text from a real person
- Maximum 3 sentences total
- Ultra conversational, warm, zero formality
- Open with their name if known
- Reference ONE real thing about their business
- End with ONE simple question that invites a reply
- NO links, NO company name, NO pitch
- Must NOT feel like marketing or spam
- If use_pidgin is true, sprinkle natural Nigerian pidgin
- Emojis: maximum 2, only if they feel natural

Return ONLY valid JSON:
{{
  "message": "the whatsapp message here"
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

    for key, prompt in [
        ("wa_1", prompt_wa1),
        ("wa_2", prompt_wa2),
        ("wa_3", prompt_wa3)
    ]:
        try:
            response = get_ai_response(prompt, max_tokens=400)
            parsed = safe_json(response)
            if parsed:
                messages[key] = {
                    "to": ctx["whatsapp"],
                    "message": parsed.get("message", ""),
                    "send_day": {"wa_1": 1, "wa_2": 4, "wa_3": 8}[key],
                    "channel": "whatsapp"
                }
            else:
                messages[key] = {"error": "Failed to parse AI response"}
        except Exception as e:
            messages[key] = {"error": str(e)}

    return messages


# ─────────────────────────────────────────────────────────────────────────────
# INSTAGRAM DM WRITER
# writes 2 instagram dms per lead
# ─────────────────────────────────────────────────────────────────────────────
def write_instagram_dms(ctx: dict) -> dict:
    business = ctx["name"]
    first_name = ctx["first_name"] or ""
    followers = ctx["instagram_followers"]
    praises = ctx["praises"]
    vibe = ctx["vibe"]
    biggest_opportunity = ctx["biggest_opportunity"]
    has_website = ctx["has_website"]

    prompt_ig1 = f"""
Write a first Instagram DM to a business owner in {ctx.get('city', 'Abuja')}, Nigeria.

Business: {business}
Owner first name: {first_name}
Instagram followers: {followers or 'unknown'}
Vibe: {vibe}
What customers love: {praises}
Biggest digital gap: {biggest_opportunity}
Has website: {has_website}

STRICT RULES:
- Instagram DMs are the most casual of all channels
- Maximum 3 sentences — Instagram is not email
- Feel like a genuine follower who noticed something
- Compliment something SPECIFIC from their presence
- Ask ONE natural question — don't pitch anything
- NO links in first DM (Instagram flags them as spam)
- NO company name, NO services
- Emojis welcome but max 3 — must feel natural not corporate
- Must pass the "would a real person send this?" test

Return ONLY valid JSON:
{{
  "message": "the instagram dm here"
}}
"""

    prompt_ig2 = f"""
Write a second Instagram DM follow-up to a business owner who didn't reply.

Business: {business}
Owner first name: {first_name}
Vibe: {vibe}
Biggest opportunity: {biggest_opportunity}
Has website: {has_website}

STRICT RULES:
- Maximum 4 sentences
- Reference what you mentioned before briefly
- Offer something genuinely useful — a free insight or observation
- This time you can mention what you do — ONE line, softly
- End with a simple question or soft offer
- Still casual Instagram tone — not email formal

Return ONLY valid JSON:
{{
  "message": "the instagram dm here"
}}
"""

    messages = {}

    for key, prompt in [
        ("ig_1", prompt_ig1),
        ("ig_2", prompt_ig2),
    ]:
        try:
            response = get_ai_response(prompt, max_tokens=400)
            parsed = safe_json(response)
            if parsed:
                messages[key] = {
                    "to": ctx["instagram_url"],
                    "message": parsed.get("message", ""),
                    "send_day": {"ig_1": 2, "ig_2": 6}[key],
                    "channel": "instagram"
                }
            else:
                messages[key] = {"error": "Failed to parse AI response"}
        except Exception as e:
            messages[key] = {"error": str(e)}

    return messages


# ─────────────────────────────────────────────────────────────────────────────
# FACEBOOK MESSAGE WRITER
# writes 2 facebook messages per lead
# ─────────────────────────────────────────────────────────────────────────────
def write_facebook_messages(ctx: dict) -> dict:
    business = ctx["name"]
    first_name = ctx["first_name"] or ""
    vibe = ctx["vibe"]
    tone = ctx["tone"]
    praises = ctx["praises"]
    biggest_opportunity = ctx["biggest_opportunity"]
    has_website = ctx["has_website"]
    revenue_hook = ctx["revenue_hook"]

    prompt_fb1 = f"""
Write a first Facebook page message to a business owner in {ctx.get('city', 'Abuja')}, Nigeria.

Business: {business}
Owner first name: {first_name}
Vibe: {vibe}
Tone: {tone}
What customers love: {praises}
Biggest gap: {biggest_opportunity}
Has website: {has_website}

STRICT RULES:
- Facebook messages sit between email formality and Instagram casualness
- Maximum 4 sentences
- Warm, genuine, researched-feeling
- Compliment something specific and real
- Mention ONE gap or opportunity naturally
- End with a soft question
- NO pitch, NO company name, NO services mentioned yet
- Must feel like a warm professional who genuinely noticed something

Return ONLY valid JSON:
{{
  "message": "the facebook message here"
}}
"""

    prompt_fb2 = f"""
Write a second Facebook follow-up message to a business owner who didn't reply.

Business: {business}
Owner first name: {first_name}
Vibe: {vibe}
Tone: {tone}
Revenue opportunity: {revenue_hook or 'real revenue opportunity identified'}
Biggest opportunity: {biggest_opportunity}

STRICT RULES:
- Maximum 5 sentences
- Acknowledge the previous message warmly
- Lead with ONE specific valuable insight for their business
- Mention the revenue opportunity naturally — make it feel real
- Introduce what you do in ONE line — softly, helpfully
- End with a clear but pressure-free offer
- Warm professional tone throughout

Return ONLY valid JSON:
{{
  "message": "the facebook message here"
}}
"""

    messages = {}

    for key, prompt in [
        ("fb_1", prompt_fb1),
        ("fb_2", prompt_fb2),
    ]:
        try:
            response = get_ai_response(prompt, max_tokens=400)
            parsed = safe_json(response)
            if parsed:
                messages[key] = {
                    "to": ctx["facebook_url"],
                    "message": parsed.get("message", ""),
                    "send_day": {"fb_1": 5, "fb_2": 10}[key],
                    "channel": "facebook"
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
    instagram: dict,
    facebook: dict
) -> list:
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
            sequence.append({
                "day": msg.get("send_day", 1),
                "channel": "whatsapp",
                "to": ctx["whatsapp"],
                "content": msg.get("message", ""),
                "status": "queued"
            })

    # Instagram
    if ctx.get("on_instagram") and ctx.get("instagram_url"):
        for msg in extract_messages(instagram, "message"):
            sequence.append({
                "day": msg.get("send_day", 2),
                "channel": "instagram",
                "to": ctx["instagram_url"],
                "content": msg.get("message", ""),
                "status": "queued"
            })

    # Email
    if ctx.get("email"):
        for msg in extract_messages(emails, "body"):
            sequence.append({
                "day": msg.get("send_day", 3),
                "channel": "email",
                "to": ctx["email"],
                "subject": msg.get("subject", ""),
                "content": msg.get("body", ""),
                "preview": msg.get("preview_text", ""),
                "status": "queued"
            })

    # Facebook
    if ctx.get("on_facebook") and ctx.get("facebook_url"):
        for msg in extract_messages(facebook, "message"):
            sequence.append({
                "day": msg.get("send_day", 5),
                "channel": "facebook",
                "to": ctx["facebook_url"],
                "content": msg.get("message", ""),
                "status": "queued"
            })

    # Sort by send day
    sequence.sort(key=lambda x: x.get("day", 99))
    return sequence


# ─────────────────────────────────────────────────────────────────────────────
# SAVE MESSAGES — organized per lead
# ─────────────────────────────────────────────────────────────────────────────
def save_messages(lead_name: str, emails: dict, whatsapp: dict,
                  instagram: dict, facebook: dict, sequence: list):
    safe_name = lead_name.replace(" ", "_").replace("/", "_").replace("&", "and")

    # Save emails
    email_path = f"results/emails/{safe_name}_emails.json"
    with open(email_path, "w", encoding="utf-8") as f:
        json.dump(emails, f, indent=2, ensure_ascii=False)

    # Save WhatsApp
    wa_path = f"results/messages/whatsapp/{safe_name}_whatsapp.json"
    with open(wa_path, "w", encoding="utf-8") as f:
        json.dump(whatsapp, f, indent=2, ensure_ascii=False)

    # Save Instagram
    ig_path = f"results/messages/instagram/{safe_name}_instagram.json"
    with open(ig_path, "w", encoding="utf-8") as f:
        json.dump(instagram, f, indent=2, ensure_ascii=False)

    # Save Facebook
    fb_path = f"results/messages/facebook/{safe_name}_facebook.json"
    with open(fb_path, "w", encoding="utf-8") as f:
        json.dump(facebook, f, indent=2, ensure_ascii=False)

    # Save full sequence
    seq_path = f"results/messages/sequences/{safe_name}_sequence.json"
    with open(seq_path, "w", encoding="utf-8") as f:
        json.dump(sequence, f, indent=2, ensure_ascii=False)

    return {
        "email": email_path,
        "whatsapp": wa_path,
        "instagram": ig_path,
        "facebook": fb_path,
        "sequence": seq_path
    }


# ─────────────────────────────────────────────────────────────────────────────
# PRINT PREVIEW — shows messages beautifully in terminal
# ─────────────────────────────────────────────────────────────────────────────
def print_preview(lead_name: str, ctx: dict, emails: dict,
                  whatsapp: dict, instagram: dict, facebook: dict):
    print(f"\n{'═'*65}")
    print(f"  📬 MESSAGE PREVIEW — {lead_name}")
    print(f"{'═'*65}")

    # Email 1
    e1 = emails.get("email_1") or {}
    if e1.get("subject"):
        print(f"\n  📧 EMAIL 1 (Day {e1.get('send_day', 3)}) → {ctx['email'] or 'No email'}")
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
        print(f"\n  💬 WHATSAPP 1 (Day {wa1.get('send_day', 1)}) → {ctx['whatsapp'] or 'No number'}")
        print(f"  ─────────────────────────────────────────────────")
        print(f"  {wa1['message']}")

    # Instagram 1
    ig1 = instagram.get("ig_1") or {}
    if ig1.get("message"):
        print(f"\n  📸 INSTAGRAM DM 1 (Day {ig1.get('send_day', 2)}) → {ctx['instagram_url'] or 'No profile'}")
        print(f"  ─────────────────────────────────────────────────")
        print(f"  {ig1['message']}")

    # Facebook 1
    fb1 = facebook.get("fb_1") or {}
    if fb1.get("message"):
        print(f"\n  📘 FACEBOOK MSG 1 (Day {fb1.get('send_day', 5)}) → {ctx['facebook_url'] or 'No page'}")
        print(f"  ─────────────────────────────────────────────────")
        print(f"  {fb1['message']}")

    print(f"\n{'═'*65}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def write_all_messages(
    enriched_file: str = "results/leads/enriched_leads.json",
    audit_file: str = "results/audits/general_audit_results.json"
):
    # Load enriched leads
    with open(enriched_file, "r") as f:
        enriched_leads = json.load(f)

    # Load audit results and index by name
    audit_map = {}
    if os.path.exists(audit_file):
        with open(audit_file, "r") as f:
            audit_results = json.load(f)
        for result in audit_results:
            audit_map[result["name"]] = result

    print(f"\n✍️  Message Writer — Writing for {len(enriched_leads)} leads")
    print(f"{'='*65}")

    all_sequences = []
    stats = {
        "total": len(enriched_leads),
        "emails_written": 0,
        "whatsapp_written": 0,
        "instagram_written": 0,
        "facebook_written": 0,
        "no_contacts": 0
    }

    for i, lead in enumerate(enriched_leads, 1):
        name = lead["name"]
        print(f"\n[{i}/{len(enriched_leads)}] ✍️  Writing messages for: {name}")

        # Merge audit data into lead
        if name in audit_map:
            lead["audits"] = audit_map[name].get("audits", {})
            lead["revenue_opportunity"] = audit_map[name].get("revenue_opportunity", {})

        # Build rich context
        ctx = build_lead_context(lead)

        # Check if we have any contact channels
        has_any_contact = any([
            ctx["email"],
            ctx["whatsapp"],
            ctx["on_instagram"],
            ctx["on_facebook"]
        ])

        if not has_any_contact:
            print(f"   ⚠️  No contact channels found — skipping")
            stats["no_contacts"] += 1
            continue

        print(f"   📧 Email: {ctx['email'] or '—'}")
        print(f"   💬 WhatsApp: {ctx['whatsapp'] or '—'}")
        print(f"   📸 Instagram: {'✅' if ctx['on_instagram'] else '—'}")
        print(f"   📘 Facebook: {'✅' if ctx['on_facebook'] else '—'}")

        # Write all channel messages
        print(f"   ✍️  Writing emails...")
        emails = write_emails(ctx) if ctx["email"] else {}
        if emails: stats["emails_written"] += 1
        time.sleep(random.uniform(2, 4))

        print(f"   ✍️  Writing WhatsApp messages...")
        whatsapp = write_whatsapp_messages(ctx) if ctx["whatsapp"] else {}
        if whatsapp: stats["whatsapp_written"] += 1
        time.sleep(random.uniform(2, 4))

        print(f"   ✍️  Writing Instagram DMs...")
        instagram = write_instagram_dms(ctx) if ctx["on_instagram"] else {}
        if instagram: stats["instagram_written"] += 1
        time.sleep(random.uniform(2, 4))

        print(f"   ✍️  Writing Facebook messages...")
        facebook = write_facebook_messages(ctx) if ctx["on_facebook"] else {}
        if facebook: stats["facebook_written"] += 1
        time.sleep(random.uniform(3, 6))

        # Build unified send sequence
        sequence = build_send_sequence(ctx, emails, whatsapp, instagram, facebook)

        # Save everything
        paths = save_messages(name, emails, whatsapp, instagram, facebook, sequence)

        # Print preview of first messages
        print_preview(name, ctx, emails, whatsapp, instagram, facebook)

        all_sequences.append({
            "lead": name,
            "channels": {
                "email": ctx["email"],
                "whatsapp": ctx["whatsapp"],
                "instagram": ctx["instagram_url"],
                "facebook": ctx["facebook_url"]
            },
            "sequence": sequence,
            "files": paths
        })

        print(f"   ✅ Done — {len(sequence)} messages in sequence")

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
    print(f"Instagram sequences:      {stats['instagram_written']}")
    print(f"Facebook sequences:       {stats['facebook_written']}")
    print(f"No contacts found:        {stats['no_contacts']}")
    print(f"\nFiles saved:")
    print(f"  results/emails/          — email sequences per lead")
    print(f"  results/messages/        — all channel messages")
    print(f"  results/messages/sequences/master_sequence.json")
    print(f"{'='*65}")


if __name__ == "__main__":
    write_all_messages()