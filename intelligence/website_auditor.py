import asyncio
import json
import os
import random
from playwright.async_api import async_playwright
from anthropic import Anthropic
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

def get_ai_response(prompt: str, max_tokens: int = 1000) -> str:
    from utils.ai_client import ai_response
    return ai_response(prompt, task="audit", max_tokens=max_tokens)


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
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
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

        try:
            print(f"  ðŸŒ Visiting {url}...")
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
            print(f"  âš ï¸  Error auditing {url}: {e}")

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
        issues.append(f"Slow load time ({audit_data['load_time_seconds']}s) â€” visitors leave after 3 seconds")

    if not audit_data["is_mobile_friendly"]:
        issues.append("Not mobile friendly â€” over 70% of customers browse on their phones")

    if not audit_data["has_ssl"]:
        issues.append("No SSL certificate â€” browser shows 'Not Secure' warning, scaring customers away")

    if not audit_data["has_contact_form"]:
        issues.append("No contact form â€” visitors have no easy way to reach them")

    if not audit_data["has_whatsapp_button"]:
        issues.append("No WhatsApp button â€” missing the #1 communication tool in Nigeria")

    if not audit_data["has_booking_system"]:
        issues.append("No booking or reservation system â€” customers can't book online")

    if not audit_data["has_google_analytics"]:
        issues.append("No Google Analytics â€” they have no idea how many people visit their site")

    if not audit_data["has_social_links"]:
        issues.append("No social media links â€” disconnected from their own audience")

    if audit_data["missing_meta_tags"]:
        issues.append(f"Missing SEO tags: {', '.join(audit_data['missing_meta_tags'])} â€” hurting Google ranking")

    if audit_data["images_without_alt"] > 3:
        issues.append(f"{audit_data['images_without_alt']} images missing descriptions â€” bad for SEO and accessibility")

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
5. Sounds human, warm and helpful â€” NOT salesy or robotic
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

    existing_audits = {}
    audit_results_file = "results/audits/audit_results.json"
    if os.path.exists(audit_results_file):
        try:
            with open(audit_results_file, "r", encoding="utf-8") as f:
                old_results = json.load(f)
                existing_audits = {r["business_name"]: r for r in old_results if "business_name" in r}
        except:
            pass

    to_audit = []
    already_audited = []
    for lead in leads_with_sites:
        name = lead["name"]
        if name in existing_audits:
            already_audited.append(existing_audits[name])
        else:
            to_audit.append(lead)

    print(f"ℹ️  Websites to audit: {len(to_audit)} | Already audited (skipped): {len(already_audited)}")
    print("=" * 50)

    audit_results = list(already_audited)

    if not to_audit:
        print("✅ All websites have already been audited. Saving aggregated file.")
        with open(audit_results_file, "w", encoding="utf-8") as f:
            json.dump(audit_results, f, indent=2, ensure_ascii=False)
        return

    for lead in to_audit:
        name = lead["name"]
        url = lead["website"]

        print(f"\nðŸ“‹ Auditing: {name}")
        print(f"   URL: {url}")

        audit_data = await audit_website(url, name)

        if audit_data["errors"] and not audit_data["page_title"]:
            print(f"   â­ï¸  Skipping AI report â€” website unreachable")
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

        print(f"   âš ï¸  Issues found: {issues_count}")
        print(f"   ðŸ“± Mobile friendly: {'âœ…' if audit_data['is_mobile_friendly'] else 'âŒ'}")
        print(f"   ðŸ”’ SSL: {'âœ…' if audit_data['has_ssl'] else 'âŒ'}")
        print(f"   ðŸ’¬ WhatsApp button: {'âœ…' if audit_data['has_whatsapp_button'] else 'âŒ'}")
        print(f"   ðŸ“… Booking system: {'âœ…' if audit_data['has_booking_system'] else 'âŒ'}")
        print(f"   ðŸ“Š Analytics: {'âœ…' if audit_data['has_google_analytics'] else 'âŒ'}")
        print(f"\n   ðŸ“ AI Report Preview:")
        print(f"   {ai_report[:200]}...")

        # Random delay between audits â€” be human
        await asyncio.sleep(random.uniform(2, 4))

    # Save results
    os.makedirs("results/audits", exist_ok=True)
    with open("results/audits/audit_results.json", "w") as f:
        json.dump(audit_results, f, indent=2)

    print("\n" + "=" * 50)
    print("ðŸ“Š AUDIT COMPLETE")
    print("=" * 50)
    print(f"Total websites audited: {len(audit_results)}")
    print(f"Results saved to: results/audits/audit_results.json")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(audit_all_leads())
