import asyncio
import json
import os
import random
from playwright.async_api import async_playwright
from anthropic import Anthropic
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

# Smart client — uses Claude if funded, falls back to Groq automatically
def get_ai_response(prompt: str) -> str:
    try:
        claude = Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
        response = claude.messages.create(
            model="claude-opus-4-5",
            max_tokens=400,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        if "credit" in str(e).lower() or "balance" in str(e).lower():
            print("   💡 Claude credits low — switching to Groq automatically...")
            groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
            response = groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        raise e


async def audit_website(url: str, business_name: str) -> dict:
    """Visit a website and collect all audit data"""
    audit_data = {
        "url": url,
        "business_name": business_name,
        "load_time_seconds": None,
        "is_mobile_friendly": False,
        "has_ssl": False,
        "has_contact_form": False,
        "has_whatsapp_button": False,
        "has_booking_system": False,
        "has_google_analytics": False,
        "has_social_links": False,
        "broken_links": [],
        "missing_meta_tags": [],
        "page_title": None,
        "meta_description": None,
        "images_without_alt": 0,
        "errors": []
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )

        # --- Desktop audit ---
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            print(f"  🌐 Visiting {url}...")
            import time
            start = time.time()
            await page.goto(url, timeout=15000, wait_until="domcontentloaded")
            await page.wait_for_timeout(random.randint(2000, 3000))
            load_time = round(time.time() - start, 2)
            audit_data["load_time_seconds"] = load_time

            # SSL check
            audit_data["has_ssl"] = url.startswith("https://")

            # Page title
            audit_data["page_title"] = await page.title()

            # Run all checks via JS
            checks = await page.evaluate("""
                () => {
                    // Meta description
                    const metaDesc = document.querySelector('meta[name="description"]');
                    const metaKeywords = document.querySelector('meta[name="keywords"]');
                    const ogTitle = document.querySelector('meta[property="og:title"]');

                    const missing = [];
                    if (!metaDesc) missing.push("Meta Description");
                    if (!metaKeywords) missing.push("Meta Keywords");
                    if (!ogTitle) missing.push("OG Title (Social Share)");

                    // Contact form
                    const hasForm = !!document.querySelector('form') ||
                                   !!document.querySelector('input[type="email"]') ||
                                   !!document.querySelector('textarea');

                    // WhatsApp
                    const bodyText = document.body.innerHTML.toLowerCase();
                    const hasWhatsApp = bodyText.includes('whatsapp') ||
                                       bodyText.includes('wa.me') ||
                                       bodyText.includes('api.whatsapp');

                    // Booking
                    const hasBooking = bodyText.includes('book') ||
                                      bodyText.includes('reservation') ||
                                      bodyText.includes('schedule') ||
                                      bodyText.includes('appointment');

                    // Google Analytics
                    const hasGA = bodyText.includes('google-analytics') ||
                                 bodyText.includes('gtag(') ||
                                 bodyText.includes('ga(') ||
                                 bodyText.includes('G-') ||
                                 bodyText.includes('UA-');

                    // Social links
                    const hasSocial = bodyText.includes('facebook.com') ||
                                     bodyText.includes('instagram.com') ||
                                     bodyText.includes('twitter.com') ||
                                     bodyText.includes('tiktok.com');

                    // Images without alt
                    const images = document.querySelectorAll('img');
                    let missingAlt = 0;
                    images.forEach(img => {
                        if (!img.alt || img.alt.trim() === '') missingAlt++;
                    });

                    // Meta description content
                    const metaDescContent = metaDesc ? metaDesc.getAttribute('content') : null;

                    return {
                        missing_meta: missing,
                        has_contact_form: hasForm,
                        has_whatsapp: hasWhatsApp,
                        has_booking: hasBooking,
                        has_analytics: hasGA,
                        has_social: hasSocial,
                        images_without_alt: missingAlt,
                        meta_description: metaDescContent
                    };
                }
            """)

            audit_data["missing_meta_tags"] = checks["missing_meta"]
            audit_data["has_contact_form"] = checks["has_contact_form"]
            audit_data["has_whatsapp_button"] = checks["has_whatsapp"]
            audit_data["has_booking_system"] = checks["has_booking"]
            audit_data["has_google_analytics"] = checks["has_analytics"]
            audit_data["has_social_links"] = checks["has_social"]
            audit_data["images_without_alt"] = checks["images_without_alt"]
            audit_data["meta_description"] = checks["meta_description"]

        except Exception as e:
            audit_data["errors"].append(f"Desktop audit error: {str(e)}")
            print(f"  ⚠️  Error auditing {url}: {e}")

        await context.close()

        # --- Mobile audit ---
        try:
            mobile_context = await browser.new_context(
                viewport={"width": 390, "height": 844},
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
            )
            mobile_page = await mobile_context.new_page()
            await mobile_page.goto(url, timeout=15000, wait_until="domcontentloaded")
            await mobile_page.wait_for_timeout(random.randint(1500, 2500))

            mobile_check = await mobile_page.evaluate("""
                () => {
                    const viewport = document.querySelector('meta[name="viewport"]');
                    const hasViewport = !!viewport;
                    const bodyWidth = document.body.scrollWidth;
                    const windowWidth = window.innerWidth;
                    return {
                        has_viewport: hasViewport,
                        is_responsive: bodyWidth <= windowWidth + 20
                    };
                }
            """)

            audit_data["is_mobile_friendly"] = (
                mobile_check["has_viewport"] and mobile_check["is_responsive"]
            )

            await mobile_context.close()

        except Exception as e:
            audit_data["errors"].append(f"Mobile audit error: {str(e)}")

        await browser.close()

    return audit_data


def generate_ai_audit_report(audit_data: dict) -> str:
    """Send audit data to Claude and get a personalized report"""

    issues = []

    if audit_data["load_time_seconds"] and audit_data["load_time_seconds"] > 3:
        issues.append(f"Slow load time ({audit_data['load_time_seconds']}s) — visitors leave after 3 seconds")

    if not audit_data["is_mobile_friendly"]:
        issues.append("Not mobile friendly — over 70% of customers browse on their phones")

    if not audit_data["has_ssl"]:
        issues.append("No SSL certificate — browser shows 'Not Secure' warning, scaring customers away")

    if not audit_data["has_contact_form"]:
        issues.append("No contact form — visitors have no easy way to reach them")

    if not audit_data["has_whatsapp_button"]:
        issues.append("No WhatsApp button — missing the #1 communication tool in Nigeria")

    if not audit_data["has_booking_system"]:
        issues.append("No booking or reservation system — customers can't book online")

    if not audit_data["has_google_analytics"]:
        issues.append("No Google Analytics — they have no idea how many people visit their site")

    if not audit_data["has_social_links"]:
        issues.append("No social media links — disconnected from their own audience")

    if audit_data["missing_meta_tags"]:
        issues.append(f"Missing SEO tags: {', '.join(audit_data['missing_meta_tags'])} — hurting Google ranking")

    if audit_data["images_without_alt"] > 3:
        issues.append(f"{audit_data['images_without_alt']} images missing descriptions — bad for SEO and accessibility")

    if not issues:
        issues.append("Website appears technically sound but could benefit from modern UI/UX improvements and AI-powered features")

    prompt = f"""
You are an expert web consultant writing a friendly but urgent audit report for a business owner.

Business: {audit_data['business_name']}
Website: {audit_data['url']}

Issues found:
{chr(10).join(f"- {issue}" for issue in issues)}

Write a short, punchy audit report (max 150 words) that:
1. Opens with their business name personally
2. Mentions the exact number of issues found
3. Lists the 3 most critical issues in simple plain language (no jargon)
4. Ends with a single clear call to action to reply for a free fix consultation
5. Sounds human, warm and helpful — NOT salesy or robotic
6. Does NOT mention your own name or company

Write it as the body of a follow-up email.
"""

    return get_ai_response(prompt)


async def audit_all_leads(leads_file: str = "results/leads/leads.json"):
    """Audit all leads that have websites"""

    with open(leads_file, "r") as f:
        leads = json.load(f)

    # Only audit businesses with websites
    leads_with_sites = [l for l in leads if l.get("has_website") and l.get("website")]

    if not leads_with_sites:
        print("⚠️  No leads with websites found in leads.json")
        return

    print(f"\n🔍 Auditing {len(leads_with_sites)} websites...\n")
    print("=" * 50)

    audit_results = []

    for lead in leads_with_sites:
        name = lead["name"]
        url = lead["website"]

        print(f"\n📋 Auditing: {name}")
        print(f"   URL: {url}")

        audit_data = await audit_website(url, name)

        if audit_data["errors"] and not audit_data["page_title"]:
            print(f"   ⏭️  Skipping AI report — website unreachable")
            continue

        ai_report = generate_ai_audit_report(audit_data)

        result = {
            "business_name": name,
            "website": url,
            "audit": audit_data,
            "ai_report": ai_report
        }

        audit_results.append(result)

        # Print summary
        issues_count = sum([
            audit_data["load_time_seconds"] > 3 if audit_data["load_time_seconds"] else False,
            not audit_data["is_mobile_friendly"],
            not audit_data["has_ssl"],
            not audit_data["has_contact_form"],
            not audit_data["has_whatsapp_button"],
            not audit_data["has_booking_system"],
            not audit_data["has_google_analytics"],
            not audit_data["has_social_links"],
            bool(audit_data["missing_meta_tags"]),
        ])

        print(f"   ⚠️  Issues found: {issues_count}")
        print(f"   📱 Mobile friendly: {'✅' if audit_data['is_mobile_friendly'] else '❌'}")
        print(f"   🔒 SSL: {'✅' if audit_data['has_ssl'] else '❌'}")
        print(f"   💬 WhatsApp button: {'✅' if audit_data['has_whatsapp_button'] else '❌'}")
        print(f"   📅 Booking system: {'✅' if audit_data['has_booking_system'] else '❌'}")
        print(f"   📊 Analytics: {'✅' if audit_data['has_google_analytics'] else '❌'}")
        print(f"\n   📝 AI Report Preview:")
        print(f"   {ai_report[:200]}...")

        # Random delay between audits — be human
        await asyncio.sleep(random.uniform(2, 4))

    # Save results
    os.makedirs("results/audits", exist_ok=True)
    with open("results/audits/audit_results.json", "w") as f:
        json.dump(audit_results, f, indent=2)

    print("\n" + "=" * 50)
    print("📊 AUDIT COMPLETE")
    print("=" * 50)
    print(f"Total websites audited: {len(audit_results)}")
    print(f"Results saved to: results/audits/audit_results.json")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(audit_all_leads())