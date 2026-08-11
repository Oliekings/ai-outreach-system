import asyncio
import json
import os
import random
import re
from datetime import datetime
from playwright.async_api import async_playwright
from dotenv import load_dotenv
from groq import Groq
from anthropic import Anthropic

load_dotenv()
import sys

sys.stdout.reconfigure(encoding="utf-8")


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


def load_config(path: str = "ceo_config.json") -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


config = load_config()

# ── Output directories ────────────────────────────────────────────────────────
os.makedirs("results/audits", exist_ok=True)
os.makedirs("results/reports", exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# AI CLIENT
# ─────────────────────────────────────────────────────────────────────────────
def get_ai_response(prompt: str, max_tokens: int = 1000) -> str:
    from utils.ai_client import ai_response

    return ai_response(prompt, task="audit", max_tokens=max_tokens)


from utils.browser_utils import human_pause, human_scroll, handle_consent



# ─────────────────────────────────────────────────────────────────────────────
# GRADE CALCULATOR
# ─────────────────────────────────────────────────────────────────────────────
def calculate_grade(score: int, max_score: int) -> str:
    if max_score == 0:
        return "N/A"
    pct = (score / max_score) * 100
    if pct >= 90:
        return "A+"
    if pct >= 85:
        return "A"
    if pct >= 80:
        return "A-"
    if pct >= 75:
        return "B+"
    if pct >= 70:
        return "B"
    if pct >= 65:
        return "B-"
    if pct >= 60:
        return "C+"
    if pct >= 55:
        return "C"
    if pct >= 50:
        return "C-"
    if pct >= 45:
        return "D+"
    if pct >= 40:
        return "D"
    return "F"


# ─────────────────────────────────────────────────────────────────────────────
# 1. WEBSITE AUDIT
# ─────────────────────────────────────────────────────────────────────────────
async def audit_website(page, url: str, business_name: str) -> dict:
    result = {
        "url": url,
        "accessible": False,
        "load_time": None,
        "has_ssl": False,
        "is_mobile_friendly": False,
        "has_contact_form": False,
        "has_whatsapp_button": False,
        "has_booking_system": False,
        "has_google_analytics": False,
        "has_social_links": False,
        "has_clear_cta": False,
        "missing_meta_tags": [],
        "images_without_alt": 0,
        "content_freshness": None,
        "professional_email": False,
        "last_updated": None,
        "score": 0,
        "max_score": 10,
        "grade": "F",
        "issues": [],
        "wins": [],
    }

    if not url:
        result["issues"].append("No website found")
        return result

    try:
        import time

        print(f"      {Symbol.WORLD} Loading website...")
        start = time.time()
        await page.goto(url, timeout=20000, wait_until="domcontentloaded")
        await handle_consent(page)
        await human_pause(2.0, 4.0)
        await human_scroll(page, scrolls=4)
        load_time = round(time.time() - start, 2)

        result["accessible"] = True
        result["load_time"] = load_time
        result["has_ssl"] = url.startswith("https://")

        checks = await page.evaluate("""
            () => {
                const text = document.body.innerText.toLowerCase();
                const html = document.body.innerHTML.toLowerCase();

                const metaDesc = document.querySelector('meta[name="description"]');
                const metaKw = document.querySelector('meta[name="keywords"]');
                const ogTitle = document.querySelector('meta[property="og:title"]');
                const missing = [];
                if (!metaDesc) missing.push("Meta Description");
                if (!metaKw) missing.push("Meta Keywords");
                if (!ogTitle) missing.push("OG Social Share Tag");

                const imgs = document.querySelectorAll('img');
                let missingAlt = 0;
                imgs.forEach(img => { if (!img.alt || !img.alt.trim()) missingAlt++; });

                const hasForm = !!document.querySelector('form') ||
                    html.includes('contact') && html.includes('input');
                const hasWA = html.includes('whatsapp') || html.includes('wa.me');
                const hasBook = text.includes('book') || text.includes('reserv') ||
                    text.includes('appointment') || text.includes('schedule');
                const hasGA = html.includes('gtag') || html.includes('google-analytics') ||
                    html.includes('ua-') || html.includes('g-');
                const hasSocial = html.includes('facebook.com') ||
                    html.includes('instagram.com') || html.includes('twitter.com');
                const hasCTA = html.includes('btn') || html.includes('button') ||
                    text.includes('order now') || text.includes('call us') ||
                    text.includes('get started') || text.includes('book now') ||
                    text.includes('contact us') || text.includes('reserve');

                const lastMod = document.lastModified;

                return {
                    missing_meta: missing,
                    images_without_alt: missingAlt,
                    has_form: hasForm,
                    has_whatsapp: hasWA,
                    has_booking: hasBook,
                    has_analytics: hasGA,
                    has_social: hasSocial,
                    has_cta: hasCTA,
                    last_modified: lastMod
                };
            }
        """)

        result["has_contact_form"] = checks["has_form"]
        result["has_whatsapp_button"] = checks["has_whatsapp"]
        result["has_booking_system"] = checks["has_booking"]
        result["has_google_analytics"] = checks["has_analytics"]
        result["has_social_links"] = checks["has_social"]
        result["has_clear_cta"] = checks["has_cta"]
        result["missing_meta_tags"] = checks["missing_meta"]
        result["images_without_alt"] = checks["images_without_alt"]
        result["last_updated"] = checks["last_modified"]

        # Mobile check
        mobile_ctx = await page.context.browser.new_context(
            viewport={"width": 390, "height": 844},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
        )
        mobile_page = await mobile_ctx.new_page()
        try:
            await mobile_page.goto(url, timeout=15000, wait_until="domcontentloaded")
            mobile_check = await mobile_page.evaluate("""
                () => ({
                    has_viewport: !!document.querySelector('meta[name="viewport"]'),
                    is_responsive: document.body.scrollWidth <= window.innerWidth + 20
                })
            """)
            result["is_mobile_friendly"] = (
                mobile_check["has_viewport"] and mobile_check["is_responsive"]
            )
        except:
            result["is_mobile_friendly"] = False
        finally:
            await mobile_ctx.close()

        # Professional email check
        page_text = await page.evaluate("() => document.body.innerText")
        email_match = re.search(
            r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", page_text
        )
        if email_match:
            email = email_match.group(0).lower()
            result["professional_email"] = not any(
                g in email for g in ["gmail.com", "yahoo.com", "hotmail.com"]
            )

        # Score calculation
        score = 0
        if result["has_ssl"]:
            score += 1
            result["wins"].append("SSL certificate active")
        else:
            result["issues"].append("No SSL — browser shows 'Not Secure' to visitors")

        if result["load_time"] and result["load_time"] < 3:
            score += 1
            result["wins"].append(f"Fast load time ({result['load_time']}s)")
        else:
            result["issues"].append(
                f"Slow load time ({result['load_time']}s) — visitors leave after 3s"
            )

        if result["is_mobile_friendly"]:
            score += 1
            result["wins"].append("Mobile friendly")
        else:
            result["issues"].append(
                "Not mobile friendly — 70%+ of customers use phones"
            )

        if result["has_contact_form"]:
            score += 1
            result["wins"].append("Contact form present")
        else:
            result["issues"].append(
                "No contact form — visitors can't easily reach them"
            )

        if result["has_whatsapp_button"]:
            score += 1
            result["wins"].append("WhatsApp button present")
        else:
            result["issues"].append(
                "No WhatsApp button — missing Nigeria's #1 comm tool"
            )

        if result["has_booking_system"]:
            score += 1
            result["wins"].append("Booking system present")
        else:
            result["issues"].append(
                "No online booking — losing customers who can't reserve"
            )

        if result["has_google_analytics"]:
            score += 1
            result["wins"].append("Analytics tracking active")
        else:
            result["issues"].append("No analytics — flying blind with no visitor data")

        if result["has_social_links"]:
            score += 1
            result["wins"].append("Social media linked")
        else:
            result["issues"].append(
                "No social media links — disconnected from audience"
            )

        if result["has_clear_cta"]:
            score += 1
            result["wins"].append("Clear call-to-action present")
        else:
            result["issues"].append(
                "No clear call-to-action — visitors don't know what to do next"
            )

        if result["professional_email"]:
            score += 1
            result["wins"].append("Professional email domain")
        else:
            result["issues"].append(
                "Using Gmail/Yahoo — looks unprofessional to customers"
            )

        result["score"] = score
        result["grade"] = calculate_grade(score, result["max_score"])

    except Exception as e:
        result["issues"].append(f"Website could not be loaded: {str(e)[:100]}")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# 2. GOOGLE BUSINESS PROFILE AUDIT
# ─────────────────────────────────────────────────────────────────────────────
async def audit_google_business(page, business_name: str, city: str) -> dict:
    result = {
        "found": False,
        "is_claimed": False,
        "has_hours": False,
        "has_photos": False,
        "photo_count": 0,
        "has_description": False,
        "has_booking_link": False,
        "responds_to_reviews": False,
        "uses_google_posts": False,
        "category_set": False,
        "rating": None,
        "review_count": None,
        "profile_completeness": 0,
        "score": 0,
        "max_score": 8,
        "grade": "F",
        "issues": [],
        "wins": [],
    }

    try:
        print(f"      {Symbol.MAPS} Checking Google Business Profile...")
        query = f"{business_name} {city} Nigeria"
        await page.goto(
            f"https://www.google.com/search?q={query.replace(' ', '+')}",
            timeout=15000,
            wait_until="domcontentloaded",
        )
        await handle_consent(page)
        await human_pause(2.0, 4.0)
        await human_scroll(page, scrolls=3)

        text = await page.evaluate("() => document.body.innerText")
        html = await page.evaluate("() => document.body.innerHTML")

        # Check if business panel appears
        result["found"] = any(
            kw in text.lower()
            for kw in [business_name.lower()[:8], "directions", "website", "call"]
        )

        if result["found"]:
            result["is_claimed"] = (
                "claimed" in text.lower() or "website" in text.lower()
            )

            # Rating
            rating_match = re.search(r"(\d\.\d)\s*\(", text)
            if rating_match:
                result["rating"] = float(rating_match.group(1))
                result["wins"].append(f"Rating: {result['rating']} stars")

            # Review count
            review_match = re.search(r"\(([\d,]+)\s*review", text, re.I)
            if review_match:
                result["review_count"] = review_match.group(1)

            # Hours
            result["has_hours"] = any(
                h in text.lower() for h in ["open", "closed", "hours", "am", "pm"]
            )

            # Photos
            photo_match = re.search(r"(\d+)\s*photo", text, re.I)
            if photo_match:
                result["photo_count"] = int(photo_match.group(1))
                result["has_photos"] = result["photo_count"] > 0

            # Description
            result["has_description"] = len(text) > 500

            # Booking link
            result["has_booking_link"] = (
                "book" in text.lower() or "reserv" in text.lower()
            )

            # Responds to reviews
            result["responds_to_reviews"] = "response from the owner" in text.lower()

            # Score
            score = 0
            if result["is_claimed"]:
                score += 1
                result["wins"].append("Profile claimed")
            else:
                result["issues"].append(
                    "Profile may not be claimed — losing local visibility"
                )

            if result["has_hours"]:
                score += 1
                result["wins"].append("Business hours listed")
            else:
                result["issues"].append(
                    "No hours listed — customers don't know when to visit"
                )

            if result["has_photos"]:
                score += 1
                result["wins"].append(f"{result['photo_count']} photos uploaded")
            else:
                result["issues"].append(
                    "No photos — businesses with photos get 42% more direction requests"
                )

            if result["has_description"]:
                score += 1
                result["wins"].append("Business description present")
            else:
                result["issues"].append(
                    "No business description — missing SEO opportunity"
                )

            if result["has_booking_link"]:
                score += 1
                result["wins"].append("Booking link on profile")
            else:
                result["issues"].append("No booking link on Google profile")

            if result["responds_to_reviews"]:
                score += 1
                result["wins"].append("Responds to customer reviews")
            else:
                result["issues"].append(
                    "Not responding to reviews — hurting trust and ranking"
                )

            if result["rating"] and result["rating"] >= 4.0:
                score += 1
                result["wins"].append(f"Strong rating: {result['rating']}")
            elif result["rating"]:
                result["issues"].append(
                    f"Rating below 4.0 ({result['rating']}) — needs improvement"
                )

            if result["review_count"]:
                count = int(result["review_count"].replace(",", ""))
                if count >= 100:
                    score += 1
                    result["wins"].append(
                        f"Strong review volume: {result['review_count']}"
                    )
                else:
                    result["issues"].append(
                        f"Low review count ({result['review_count']}) — needs more reviews"
                    )

            result["score"] = score
            result["grade"] = calculate_grade(score, result["max_score"])
        else:
            result["issues"].append(
                "Business not appearing prominently in Google search"
            )

    except Exception as e:
        result["issues"].append(f"Google Business audit failed: {str(e)[:80]}")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# 3. SOCIAL MEDIA AUDIT
# ─────────────────────────────────────────────────────────────────────────────
async def audit_social_media(lead: dict) -> dict:
    result = {
        "instagram": {
            "found": False,
            "followers": None,
            "last_post_days": None,
            "has_contact_in_bio": False,
            "uses_reels": False,
            "engagement_rating": None,
        },
        "facebook": {
            "found": False,
            "likes": None,
            "last_post_days": None,
            "responds_to_comments": False,
            "has_complete_about": False,
        },
        "tiktok": {"found": False},
        "twitter": {"found": False},
        "score": 0,
        "max_score": 8,
        "grade": "F",
        "issues": [],
        "wins": [],
    }

    ig = lead.get("instagram") or {}
    fb = lead.get("facebook") or {}

    score = 0

    # Instagram
    if ig.get("found"):
        result["instagram"]["found"] = True
        result["instagram"]["followers"] = ig.get("followers")
        score += 1
        result["wins"].append(
            f"Active on Instagram ({ig.get('followers', '?')} followers)"
        )

        if ig.get("email") or ig.get("phone"):
            result["instagram"]["has_contact_in_bio"] = True
            score += 1
            result["wins"].append("Contact info in Instagram bio")
        else:
            result["issues"].append("No contact info in Instagram bio — missing leads")
    else:
        result["issues"].append("Not on Instagram — missing huge Nigerian audience")

    # Facebook
    if fb.get("found"):
        result["facebook"]["found"] = True
        result["facebook"]["likes"] = fb.get("likes")
        score += 1
        result["wins"].append(f"Active Facebook page ({fb.get('likes', '?')} likes)")

        if fb.get("email") or fb.get("phone"):
            result["facebook"]["has_complete_about"] = True
            score += 1
            result["wins"].append("Contact info on Facebook page")
        else:
            result["issues"].append(
                "Facebook About section incomplete — missing contact info"
            )
    else:
        result["issues"].append("No Facebook page found — missing older demographic")

    # Cross platform consistency
    if ig.get("found") and fb.get("found"):
        score += 1
        result["wins"].append("Present on multiple platforms")
    else:
        result["issues"].append(
            "Not consistent across platforms — patchy online presence"
        )

    # Overall social presence
    if score == 0:
        result["issues"].append("No meaningful social media presence found")
    elif score >= 4:
        result["wins"].append("Good overall social media foundation")

    # Bonus scores
    if ig.get("followers"):
        followers_str = (
            str(ig.get("followers", "0"))
            .replace(",", "")
            .replace("K", "000")
            .replace("k", "000")
        )
        try:
            followers_num = float(re.sub(r"[^0-9.]", "", followers_str))
            if followers_num >= 5000:
                score += 1
                result["wins"].append(
                    f"Strong Instagram following ({ig.get('followers')})"
                )
            elif followers_num >= 1000:
                score += 1
                result["wins"].append(
                    f"Growing Instagram following ({ig.get('followers')})"
                )
            else:
                result["issues"].append(
                    f"Low Instagram followers ({ig.get('followers')}) — needs growth strategy"
                )
        except:
            pass

    result["score"] = min(score, result["max_score"])
    result["grade"] = calculate_grade(result["score"], result["max_score"])
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 4. ONLINE REPUTATION AUDIT
# ─────────────────────────────────────────────────────────────────────────────
async def audit_reputation(lead: dict) -> dict:
    reviews = lead.get("reviews_analysis") or {}
    result = {
        "overall_rating": lead.get("rating"),
        "review_count": lead.get("reviews"),
        "has_recent_reviews": False,
        "responds_to_negative": False,
        "press_mentions": False,
        "top_praises": reviews.get("praises", []),
        "top_complaints": reviews.get("complaints", []),
        "sentiment_summary": reviews.get("sentiment_summary"),
        "score": 0,
        "max_score": 6,
        "grade": "F",
        "issues": [],
        "wins": [],
    }

    score = 0

    # Rating
    rating_str = str(lead.get("rating") or "0")
    try:
        rating = float(re.sub(r"[^0-9.]", "", rating_str))
        if rating >= 4.5:
            score += 2
            result["wins"].append(f"Excellent rating: {rating}")
        elif rating >= 4.0:
            score += 1
            result["wins"].append(f"Good rating: {rating}")
        else:
            result["issues"].append(
                f"Below average rating: {rating} — actively harming business"
            )
    except:
        result["issues"].append("Rating not found — Google listing may be incomplete")

    # Review volume
    reviews_str = str(lead.get("reviews") or "0").replace(",", "")
    try:
        count = int(re.sub(r"[^0-9]", "", reviews_str))
        if count >= 500:
            score += 2
            result["wins"].append(f"Very high review volume: {count}")
        elif count >= 100:
            score += 1
            result["wins"].append(f"Good review volume: {count}")
        else:
            result["issues"].append(
                f"Low review count ({count}) — needs review generation strategy"
            )
    except:
        pass

    # Responds to reviews
    if reviews.get("responds_to_reviews"):
        score += 1
        result["wins"].append("Actively responds to customer reviews")
    else:
        result["issues"].append("Not responding to reviews — losing customer trust")

    # Complaints as opportunities
    if reviews.get("complaints"):
        result["issues"].append(
            f"Recurring complaint: '{reviews['complaints'][0]}' — we can help fix this"
        )

    result["score"] = min(score, result["max_score"])
    result["grade"] = calculate_grade(result["score"], result["max_score"])
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 5. SEO & DISCOVERABILITY AUDIT
# ─────────────────────────────────────────────────────────────────────────────
async def audit_seo(page, business_name: str, city: str, website_url: str) -> dict:
    result = {
        "ranks_for_own_name": False,
        "ranks_in_local_pack": False,
        "ranks_for_category": False,
        "website_indexed": False,
        "has_backlinks": False,
        "appears_on_directories": [],
        "score": 0,
        "max_score": 6,
        "grade": "F",
        "issues": [],
        "wins": [],
    }

    try:
        print(f"      {Symbol.SEARCH} Checking SEO visibility...")

        # Check if ranks for own name
        await page.goto(
            f"https://www.google.com/search?q={business_name.replace(' ', '+')}+{city}",
            timeout=15000,
            wait_until="domcontentloaded",
        )
        await handle_consent(page)
        await human_pause(2.0, 3.5)
        text = await page.evaluate("() => document.body.innerText")

        if business_name.lower()[:8] in text.lower():
            result["ranks_for_own_name"] = True
            result["score"] += 1
            result["wins"].append("Appears in search for own business name")
        else:
            result["issues"].append(
                "Doesn't appear when searching for own name — serious SEO problem"
            )

        # Local pack check
        result["ranks_in_local_pack"] = (
            "directions" in text.lower() or "open" in text.lower()
        )
        if result["ranks_in_local_pack"]:
            result["score"] += 1
            result["wins"].append("Appearing in Google local results")
        else:
            result["issues"].append(
                "Not in Google local pack — invisible to nearby customers"
            )

        await human_pause(2.0, 3.5)

        # Category search
        category_query = f"best restaurant in {city} Nigeria"
        await page.goto(
            f"https://www.google.com/search?q={category_query.replace(' ', '+')}",
            timeout=15000,
            wait_until="domcontentloaded",
        )
        await human_pause(2.0, 3.5)
        category_text = await page.evaluate("() => document.body.innerText")

        if business_name.lower()[:6] in category_text.lower():
            result["ranks_for_category"] = True
            result["score"] += 2
            result["wins"].append(f"Ranking for category searches in {city}")
        else:
            result["issues"].append(
                f"Not ranking for category searches — missing discovery traffic"
            )

        # Website indexed
        if website_url:
            result["website_indexed"] = result["ranks_for_own_name"]
            if result["website_indexed"]:
                result["score"] += 1
                result["wins"].append("Website indexed by Google")
            else:
                result["issues"].append("Website may not be indexed by Google")

        result["grade"] = calculate_grade(result["score"], result["max_score"])
        await human_pause(2.0, 3.5)

    except Exception as e:
        result["issues"].append(f"SEO audit failed: {str(e)[:80]}")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# 6. WHATSAPP BUSINESS AUDIT
# ─────────────────────────────────────────────────────────────────────────────
def audit_whatsapp(lead: dict) -> dict:
    result = {
        "has_whatsapp": False,
        "whatsapp_number": None,
        "on_website": False,
        "on_google_listing": False,
        "on_instagram": False,
        "on_facebook": False,
        "likely_business_account": False,
        "score": 0,
        "max_score": 5,
        "grade": "F",
        "issues": [],
        "wins": [],
    }

    whatsapp = lead.get("contact_whatsapp")
    ig = lead.get("instagram") or {}
    fb = lead.get("facebook") or {}
    site = lead.get("website_details") or {}

    if whatsapp:
        result["has_whatsapp"] = True
        result["whatsapp_number"] = whatsapp
        result["score"] += 1
        result["wins"].append(f"WhatsApp number found: {whatsapp}")
    else:
        result["issues"].append(
            "No WhatsApp number found — critical gap for Nigerian market"
        )

    # Check presence across surfaces
    if site.get("whatsapp_links"):
        result["on_website"] = True
        result["score"] += 1
        result["wins"].append("WhatsApp linked on website")
    else:
        result["issues"].append(
            "WhatsApp not linked on website — missing easy contact option"
        )

    if ig.get("whatsapp"):
        result["on_instagram"] = True
        result["score"] += 1
        result["wins"].append("WhatsApp linked on Instagram")
    else:
        result["issues"].append("WhatsApp not in Instagram bio")

    if fb.get("whatsapp"):
        result["on_facebook"] = True
        result["score"] += 1
        result["wins"].append("WhatsApp linked on Facebook")

    # Business account likelihood
    if result["on_website"] or result["on_instagram"]:
        result["likely_business_account"] = True
        result["score"] += 1
        result["wins"].append("Likely using WhatsApp Business")
    else:
        result["issues"].append(
            "Likely on regular WhatsApp — missing catalog, auto-reply, and broadcast features"
        )

    result["grade"] = calculate_grade(result["score"], result["max_score"])
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 7. COMPETITOR GAP AUDIT
# ─────────────────────────────────────────────────────────────────────────────
def audit_competitor_gap(lead: dict, website_audit: dict, social_audit: dict) -> dict:
    competitors = lead.get("competitors") or []
    result = {
        "competitors_analysed": len(competitors),
        "gaps": [],
        "advantages": [],
        "urgent_threats": [],
        "score": 0,
        "max_score": 5,
        "grade": "B",
        "issues": [],
        "wins": [],
    }

    if not competitors:
        result["issues"].append("No competitor data available")
        result["grade"] = "N/A"
        return result

    # Count how many competitors have key features
    comp_with_website = sum(1 for c in competitors if c.get("has_website"))
    comp_with_booking = sum(1 for c in competitors if c.get("has_online_booking"))

    score = 0

    # Website gap
    has_website = bool(lead.get("official_website", {}).get("url"))
    if not has_website and comp_with_website > 0:
        result["urgent_threats"].append(
            f"{comp_with_website} of your competitors have websites — you don't"
        )
        result["issues"].append("Competitors have websites but this business doesn't")
    elif has_website:
        score += 1
        result["wins"].append("Has website (matches or beats competitors)")

    # Booking gap
    if comp_with_booking > 0 and not website_audit.get("has_booking_system"):
        result["urgent_threats"].append(
            f"{comp_with_booking} competitors now accept online bookings — this business doesn't"
        )
        result["issues"].append("Falling behind on online booking")
    elif website_audit.get("has_booking_system"):
        score += 1
        result["wins"].append("Online booking matches competitors")

    # Social gap
    if social_audit["instagram"]["found"] and social_audit["facebook"]["found"]:
        score += 2
        result["advantages"].append("Strong social media presence vs competitors")
    elif social_audit["instagram"]["found"] or social_audit["facebook"]["found"]:
        score += 1
        result["gaps"].append(
            "Only on one social platform while competitors may be on more"
        )
    else:
        result["issues"].append("No social media — likely behind all competitors")

    # Overall competitive position
    if score >= 4:
        result["wins"].append("Competitive digital position overall")
    elif score >= 2:
        result["issues"].append(
            "Slightly behind competitors digitally — gap is closeable"
        )
    else:
        result["urgent_threats"].append(
            "Significantly behind competitors — urgent action needed"
        )

    result["score"] = min(score, result["max_score"])
    result["grade"] = calculate_grade(result["score"], result["max_score"])
    return result


# ─────────────────────────────────────────────────────────────────────────────
# 8. REVENUE OPPORTUNITY CALCULATOR
# ─────────────────────────────────────────────────────────────────────────────
def calculate_revenue_opportunity(lead: dict, audits: dict) -> dict:
    result = {
        "monthly_lost_naira": 0,
        "breakdown": [],
        "quick_wins": [],
        "biggest_opportunity": None,
    }

    # Base estimate from review volume
    reviews_str = str(lead.get("reviews") or "0").replace(",", "")
    try:
        review_count = int(re.sub(r"[^0-9]", "", reviews_str))
    except:
        review_count = 50

    # Estimate monthly customers from reviews
    estimated_monthly_customers = max(review_count * 2, 100)

    # Average spend per customer (Nigerian restaurant average)
    avg_spend_naira = 8000

    website_audit = audits.get("website") or {}
    social_audit = audits.get("social") or {}
    wa_audit = audits.get("whatsapp") or {}

    total_lost = 0

    # No website loss
    if not lead.get("official_website", {}).get("url"):
        lost = int(estimated_monthly_customers * 0.20 * avg_spend_naira)
        total_lost += lost
        result["breakdown"].append(
            {
                "issue": "No website",
                "lost_customers_monthly": int(estimated_monthly_customers * 0.20),
                "lost_revenue_naira": lost,
                "explanation": "Estimated 20% of potential customers can't find you online",
            }
        )
        result["quick_wins"].append(
            "Build a professional website — recover â‚¦{:,}/month".format(lost)
        )

    # No online booking loss
    if not website_audit.get("has_booking_system"):
        lost = int(estimated_monthly_customers * 0.15 * avg_spend_naira)
        total_lost += lost
        result["breakdown"].append(
            {
                "issue": "No online booking",
                "lost_customers_monthly": int(estimated_monthly_customers * 0.15),
                "lost_revenue_naira": lost,
                "explanation": "15% of customers leave if they can't book online",
            }
        )
        result["quick_wins"].append(
            "Add online booking — recover â‚¦{:,}/month".format(lost)
        )

    # Slow website loss
    load_time = website_audit.get("load_time") or 0
    if load_time > 3:
        lost = int(estimated_monthly_customers * 0.10 * avg_spend_naira)
        total_lost += lost
        result["breakdown"].append(
            {
                "issue": f"Slow website ({load_time}s load time)",
                "lost_customers_monthly": int(estimated_monthly_customers * 0.10),
                "lost_revenue_naira": lost,
                "explanation": "53% of mobile visitors leave after 3 seconds",
            }
        )
        result["quick_wins"].append(
            "Speed up website — recover â‚¦{:,}/month".format(lost)
        )

    # No WhatsApp loss
    if not wa_audit.get("has_whatsapp"):
        lost = int(estimated_monthly_customers * 0.12 * avg_spend_naira)
        total_lost += lost
        result["breakdown"].append(
            {
                "issue": "No WhatsApp presence",
                "lost_customers_monthly": int(estimated_monthly_customers * 0.12),
                "lost_revenue_naira": lost,
                "explanation": "Nigerian customers prefer WhatsApp contact — missing this loses leads",
            }
        )
        result["quick_wins"].append(
            "Set up WhatsApp Business — recover â‚¦{:,}/month".format(lost)
        )

    # No social media loss
    if not social_audit.get("instagram", {}).get("found") and not social_audit.get(
        "facebook", {}
    ).get("found"):
        lost = int(estimated_monthly_customers * 0.10 * avg_spend_naira)
        total_lost += lost
        result["breakdown"].append(
            {
                "issue": "No social media presence",
                "lost_customers_monthly": int(estimated_monthly_customers * 0.10),
                "lost_revenue_naira": lost,
                "explanation": "No social discovery means no word-of-mouth amplification",
            }
        )

    result["monthly_lost_naira"] = total_lost
    result["biggest_opportunity"] = (
        result["quick_wins"][0] if result["quick_wins"] else None
    )

    return result


# ─────────────────────────────────────────────────────────────────────────────
# 9. FULL REPORT CARD GENERATOR
# ─────────────────────────────────────────────────────────────────────────────
def generate_report_card(lead: dict, audits: dict, revenue: dict) -> str:
    name = lead.get("name", "Business")
    website_audit = audits.get("website") or {}
    gbp_audit = audits.get("google_business") or {}
    social_audit = audits.get("social") or {}
    rep_audit = audits.get("reputation") or {}
    seo_audit = audits.get("seo") or {}
    wa_audit = audits.get("whatsapp") or {}
    comp_audit = audits.get("competitor_gap") or {}

    # Overall score
    all_scores = [
        website_audit.get("score", 0) / max(website_audit.get("max_score", 1), 1),
        gbp_audit.get("score", 0) / max(gbp_audit.get("max_score", 1), 1),
        social_audit.get("score", 0) / max(social_audit.get("max_score", 1), 1),
        rep_audit.get("score", 0) / max(rep_audit.get("max_score", 1), 1),
        seo_audit.get("score", 0) / max(seo_audit.get("max_score", 1), 1),
        wa_audit.get("score", 0) / max(wa_audit.get("max_score", 1), 1),
    ]
    overall_pct = sum(all_scores) / len(all_scores) * 100
    overall_grade = calculate_grade(int(overall_pct), 100)

    line = "â”" * 52
    report = f"""
â•”{'â•' * 52}â•—
â•‘  DIGITAL HEALTH REPORT                           â•‘
â•‘  {name[:48]:<48}  â•‘
â•‘  Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p'):<38}  â•‘
â•š{'â•' * 52}â•

{line}
  SECTION SCORES
{line}
  Website Quality        {website_audit.get('grade', 'N/A'):<6} {website_audit.get('score', 0)}/{website_audit.get('max_score', 10)} pts
  Google Business        {gbp_audit.get('grade', 'N/A'):<6} {gbp_audit.get('score', 0)}/{gbp_audit.get('max_score', 8)} pts
  Social Media           {social_audit.get('grade', 'N/A'):<6} {social_audit.get('score', 0)}/{social_audit.get('max_score', 8)} pts
  Online Reputation      {rep_audit.get('grade', 'N/A'):<6} {rep_audit.get('score', 0)}/{rep_audit.get('max_score', 6)} pts
  SEO & Discovery        {seo_audit.get('grade', 'N/A'):<6} {seo_audit.get('score', 0)}/{seo_audit.get('max_score', 6)} pts
  WhatsApp Setup         {wa_audit.get('grade', 'N/A'):<6} {wa_audit.get('score', 0)}/{wa_audit.get('max_score', 5)} pts
  Competitor Position    {comp_audit.get('grade', 'N/A'):<6} {comp_audit.get('score', 0)}/{comp_audit.get('max_score', 5)} pts
{line}
  OVERALL GRADE          {overall_grade:<6} ({overall_pct:.0f}%)
{line}

{line}
  REVENUE OPPORTUNITY
{line}
  Estimated monthly revenue being lost:
  â‚¦{revenue.get('monthly_lost_naira', 0):,}
"""

    if revenue.get("breakdown"):
        for item in revenue["breakdown"]:
            report += (
                f"\n  â€¢ {item['issue']}: â‚¦{item['lost_revenue_naira']:,}/month"
            )

    report += f"\n\n{line}\n  CRITICAL ISSUES\n{line}"

    all_issues = []
    for audit_key in [
        "website",
        "google_business",
        "social",
        "reputation",
        "seo",
        "whatsapp",
    ]:
        audit = audits.get(audit_key) or {}
        all_issues.extend(audit.get("issues", [])[:2])

    for issue in all_issues[:8]:
        report += f"\n  âœ— {issue[:60]}"

    report += f"\n\n{line}\n  WHAT'S WORKING\n{line}"

    all_wins = []
    for audit_key in ["website", "google_business", "social", "reputation"]:
        audit = audits.get(audit_key) or {}
        all_wins.extend(audit.get("wins", [])[:2])

    for win in all_wins[:6]:
        report += f"\n  âœ“ {win[:60]}"

    report += f"\n\n{line}\n  QUICK WINS (Highest ROI)\n{line}"
    for qw in (revenue.get("quick_wins") or [])[:3]:
        report += f"\n  â†’ {qw[:70]}"

    report += f"\n\n{'â•' * 52}\n"
    return report


# ─────────────────────────────────────────────────────────────────────────────
# MAIN AUDITOR
# ─────────────────────────────────────────────────────────────────────────────
async def audit_all_leads(leads_file: str = "results/leads/enriched_leads.json"):
    if not os.path.exists(leads_file):
        print(f"{Symbol.ERROR} No enriched leads found. Run lead_enricher.py first.")
        return

    with open(leads_file, "r", encoding="utf-8") as f:
        leads = json.load(f)

    print(f"\n{Symbol.SEARCH}¬ General Auditor — Processing {len(leads)} leads\n")
    print("=" * 60)

    existing_audits = {}
    audit_results_file = "results/audits/general_audit_results.json"
    if os.path.exists(audit_results_file):
        try:
            with open(audit_results_file, "r", encoding="utf-8") as f:
                old_results = json.load(f)
                existing_audits = {r["name"]: r for r in old_results if "name" in r}
                print(f"ℹ️  Loaded {len(existing_audits)} existing audit reports.")
        except Exception as e:
            print(f"⚠️ Could not load existing audit results: {e}")

    to_audit = []
    already_audited = []

    for lead in leads:
        name = lead["name"]
        report_path = (
            f"results/reports/{name.replace(' ', '_').replace('/', '_')}_audit.txt"
        )
        if name in existing_audits and os.path.exists(report_path):
            already_audited.append(existing_audits[name])
        else:
            to_audit.append(lead)

    print(
        f"ℹ️  Leads to audit: {len(to_audit)} | Already audited (skipped): {len(already_audited)}"
    )
    print("=" * 60)

    all_audit_results = list(already_audited)

    if not to_audit:
        print("✅ All leads have already been audited. Saving aggregated file.")
        with open(audit_results_file, "w", encoding="utf-8") as f:
            json.dump(all_audit_results, f, indent=2, ensure_ascii=False)
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
        )
        context = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="en-GB",
            timezone_id="Africa/Lagos",
        )

        # Mask automation signals with advanced stealth script
        await context.add_init_script("""
            // 1. Hide webdriver
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            
            // 2. Add full chrome object
            window.chrome = {
                app: {
                    isInstalled: false,
                    InstallState: { DISABLED: 'DISABLED', INSTALLED: 'INSTALLED', NOT_INSTALLED: 'NOT_INSTALLED' },
                    RunningState: { CANNOT_RUN: 'CANNOT_RUN', RUNNING: 'RUNNING', CAN_RUN: 'CAN_RUN' }
                },
                csi: () => {},
                loadTimes: () => {},
                runtime: {
                    OnInstalledReason: { CHROME_UPDATE: 'chrome_update', INSTALL: 'install', SHARED_MODULE_UPDATE: 'shared_module_update', UPDATE: 'update' },
                    OnRestartRequiredReason: { APP_UPDATE: 'app_update', OS_UPDATE: 'os_update', PERIODIC: 'periodic' },
                    PlatformArch: { ARM: 'arm', ARM64: 'arm64', MIPS: 'mips', MIPS64: 'mips64', X86_32: 'x86-32', X86_64: 'x86-64' },
                    PlatformNaclArch: { ARM: 'arm', MIPS: 'mips', MIPS64: 'mips64', X86_32: 'x86-32', X86_64: 'x86-64' },
                    PlatformOs: { ANDROID: 'android', CROS: 'cros', LINUX: 'linux', MAC: 'mac', OPENBSD: 'openbsd', WIN: 'win' },
                    RequestUpdateCheckStatus: { NO_UPDATE: 'no_update', THROTTLED: 'throttled', UPDATE_AVAILABLE: 'update_available' }
                }
            };

            // 3. Spoof plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    { description: "Portable Document Format", filename: "internal-pdf-viewer", name: "Chrome PDF Viewer" },
                    { description: "", filename: "mhjfbmdgcfjbbpaeojofohoefgieoano", name: "Chromium PDF Viewer" },
                    { description: "", filename: "internal-pdf-viewer", name: "Microsoft Edge PDF Viewer" },
                    { description: "", filename: "internal-pdf-viewer", name: "PDF Viewer" },
                    { description: "", filename: "internal-pdf-viewer", name: "WebKit built-in PDF" }
                ]
            });

            // 4. Spoof permissions
            if (window.navigator.permissions) {
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            }

            // 5. Hardware concurrency and memory
            Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
            Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });
        """)
        page = await context.new_page()

        for i, lead in enumerate(to_audit, 1):
            name = lead["name"]
            website_url = lead.get("official_website", {}).get("url")

            print(f"\n{'='*60}")
            print(f"{Symbol.SEARCH}¬ [{i}/{len(to_audit)}] Auditing: {name}")
            print(f"{'='*60}")

            audits = {}

            # 1. Website
            print(f"\n   {Symbol.WORLD} Website Audit...")
            audits["website"] = await audit_website(page, website_url, name)
            print(
                f"      Grade: {audits['website']['grade']} | Issues: {len(audits['website']['issues'])}"
            )
            await human_pause(3.0, 5.0)

            # 2. Google Business
            print(f"\n   {Symbol.MAPS} Google Business Profile Audit...")
            audits["google_business"] = await audit_google_business(
                page, name, lead.get("city", "Abuja")
            )
            print(
                f"      Grade: {audits['google_business']['grade']} | Rating: {audits['google_business'].get('rating')}"
            )
            await human_pause(3.0, 5.0)

            # 3. Social Media
            print(f"\n   {Symbol.SOCIAL} Social Media Audit...")
            audits["social"] = await audit_social_media(lead)
            print(
                f"      Grade: {audits['social']['grade']} | IG: {audits['social']['instagram']['found']} | FB: {audits['social']['facebook']['found']}"
            )
            await human_pause(2.0, 3.0)

            # 4. Reputation Audit
            print(f"\n   {Symbol.TARGET} Reputation Audit...")
            audits["reputation"] = await audit_reputation(lead)
            print(
                f"      Grade: {audits['reputation']['grade']} | Rating: {audits['reputation'].get('overall_rating')}"
            )
            await human_pause(2.0, 3.0)

            # 5. SEO
            print(f"\n   {Symbol.SEARCH}  SEO Audit...")
            audits["seo"] = await audit_seo(
                page, name, lead.get("city", "Abuja"), website_url
            )
            print(
                f"      Grade: {audits['seo']['grade']} | Local pack: {audits['seo']['ranks_in_local_pack']}"
            )
            await human_pause(3.0, 5.0)

            # 6. WhatsApp
            print(f"\n   {Symbol.WHATSAPP} WhatsApp Audit...")
            audits["whatsapp"] = audit_whatsapp(lead)
            print(
                f"      Grade: {audits['whatsapp']['grade']} | Has WA: {audits['whatsapp']['has_whatsapp']}"
            )

            # 7. Competitor Gap
            print(f"\n   ðŸ† Competitor Gap Audit...")
            audits["competitor_gap"] = audit_competitor_gap(
                lead, audits["website"], audits["social"]
            )
            print(
                f"      Grade: {audits['competitor_gap']['grade']} | Threats: {len(audits['competitor_gap']['urgent_threats'])}"
            )

            # 8. Revenue Opportunity
            print(f"\n   ðŸ’° Revenue Opportunity...")
            revenue = calculate_revenue_opportunity(lead, audits)
            print(f"      Monthly opportunity: â‚¦{revenue['monthly_lost_naira']:,}")

            # 9. Report Card
            print(f"\n   {Symbol.LIST} Generating Report Card...")
            report_card = generate_report_card(lead, audits, revenue)
            print(report_card)

            # Save individual report
            report_path = (
                f"results/reports/{name.replace(' ', '_').replace('/', '_')}_audit.txt"
            )
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_card)

            audit_result = {
                "name": name,
                "website": website_url,
                "audits": audits,
                "revenue_opportunity": revenue,
                "report_card_path": report_path,
                "audited_at": datetime.now().isoformat(),
            }
            all_audit_results.append(audit_result)

            rest = random.uniform(8.0, 12.0)
            print(f"\n   â³ Resting {rest:.0f}s before next lead...")
            await asyncio.sleep(rest)

        await browser.close()

    # Save all results
    with open("results/audits/general_audit_results.json", "w", encoding="utf-8") as f:
        json.dump(all_audit_results, f, indent=2, ensure_ascii=False)

    # Summary
    print("\n" + "=" * 60)
    print("📊 GENERAL AUDIT COMPLETE")
    print("=" * 60)
    print(f"Total leads audited:     {len(all_audit_results)}")
    print(f"Reports saved to:        results/reports/")
    print(f"Full data saved to:      results/audits/general_audit_results.json")

    total_opportunity = sum(
        r["revenue_opportunity"]["monthly_lost_naira"] for r in all_audit_results
    )
    print(f"\nTotal revenue opportunity across all leads:")
    print(f"â‚¦{total_opportunity:,}/month")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(audit_all_leads())
