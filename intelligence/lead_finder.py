import asyncio
import random
import json
import os
import re
from playwright.async_api import async_playwright
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

async def scrape_google_maps(query: str, max_results: int = 20):
    leads = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ]
        )
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

        print(f"\n🔍 Searching Google Maps for: {query}")
        await page.goto(f"https://www.google.com/maps/search/{query.replace(' ', '+')}")
        await page.wait_for_timeout(random.randint(2500, 5000))

        # Auto-handle Google consent popup
        try:
            consent_button = await page.query_selector('button[aria-label="Accept all"]')
            if not consent_button:
                consent_button = await page.query_selector('button[jsname="b3VHJd"]')
            if consent_button:
                await consent_button.click()
                print("✅ Google consent handled automatically")
                await page.wait_for_timeout(2000)
        except:
            pass

        # Human-like scrolling with random pauses
        try:
            results_panel = await page.query_selector('div[role="feed"]')
            if results_panel:
                print("🧑 Scrolling like a human...")
                for _ in range(10):
                    # Random scroll distance like a real person
                    scroll_distance = random.randint(400, 900)
                    await results_panel.evaluate(f"el => el.scrollTop += {scroll_distance}")
                    
                    # Random pause between scrolls (1.5 to 4 seconds)
                    pause = random.uniform(1.5, 4.0)
                    await page.wait_for_timeout(int(pause * 1000))
                print("✅ Scrolled results panel successfully")
        except:
            print("⚠️  Could not scroll panel, continuing with visible results")


        # Grab all business listing elements
        listings = await page.query_selector_all('a[href*="/maps/place/"]')
        print(f"📍 Found {len(listings)} listings, extracting details...\n")

        seen = set()

        for listing in listings[:max_results]:
            try:
                name = await listing.get_attribute("aria-label")
                href = await listing.get_attribute("href")

                if not name or name in seen:
                    continue
                seen.add(name)

                # Click each business to get full details
                await listing.click()
                await page.wait_for_timeout(random.randint(2000, 4000))

                # Extract details
                details = await page.evaluate("""
                    () => {
                        const getText = (selector) => {
                            const el = document.querySelector(selector);
                            return el ? el.innerText.trim() : null;
                        };

                        const getAttr = (selector, attr) => {
                            const el = document.querySelector(selector);
                            return el ? el.getAttribute(attr) : null;
                        };

                        return {
                            phone: getText('button[data-item-id^="phone"] div.fontBodyMedium') ||
                                   getText('[data-tooltip="Copy phone number"]'),
                            website: getAttr('a[data-item-id="authority"]', 'href'),
                            address: getText('button[data-item-id="address"] div.fontBodyMedium'),
                            rating: getText('div.fontDisplayLarge'),
                            reviews: getText('button[jsaction*="reviewChart"] span'),
                            category: getText('button[jsaction*="category"]'),
                        };
                    }
                """)

                lead = {
                    "name": name,
                    "phone": details.get("phone"),
                    "website": details.get("website"),
                    "address": details.get("address"),
                    "rating": details.get("rating"),
                    "reviews": details.get("reviews"),
                    "category": details.get("category"),
                    "has_website": bool(details.get("website")),
                    "maps_url": href,
                }

                # Score the lead
                lead["opportunity_score"] = score_lead(lead)

                leads.append(lead)
                print(f"✅ {name}")
                print(f"   📞 {lead['phone'] or 'No phone found'}")
                print(f"   🌐 {'Has website' if lead['has_website'] else '⚠️  NO WEBSITE - Hot lead!'}")
                print(f"   ⭐ {lead['rating']} ({lead['reviews']} reviews)")
                print(f"   🎯 Opportunity Score: {lead['opportunity_score']}/10\n")

            except Exception as e:
                print(f"⚠️  Skipped one listing: {e}")
                continue

        await browser.close()

    return leads


def score_lead(lead: dict) -> int:
    """Score each lead from 1-10 based on opportunity"""
    score = 5  # base score

    # No website = big opportunity
    if not lead["has_website"]:
        score += 3

    # Has reviews = active business with real customers
    reviews = lead.get("reviews") or ""
    reviews_clean = reviews.replace(",", "").replace("(", "").replace(")", "").strip()
    if reviews_clean.isdigit():
        count = int(reviews_clean)
        if count > 50:
            score += 1
        if count > 200:
            score += 1

    # Cap at 10
    return min(score, 10)


def save_leads(leads: list, filename: str = "results/leads/leads.json"):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w") as f:
        json.dump(leads, f, indent=2)
    print(f"\n💾 {len(leads)} leads saved to {filename}")


def load_config(path: str = "ceo_config.json") -> dict:
    with open(path, "r") as f:
        return json.load(f)


def load_progress() -> dict:
    """Track which niches have been done and which businesses already found"""
    progress_file = "results/leads/progress.json"
    if os.path.exists(progress_file):
        with open(progress_file, "r") as f:
            return json.load(f)
    return {
        "completed_niches": [],
        "current_niche_index": 0,
        "all_business_names": [],
        "total_leads_found": 0,
        "runs": []
    }


def save_progress(progress: dict):
    os.makedirs("results/leads", exist_ok=True)
    with open("results/leads/progress.json", "w") as f:
        json.dump(progress, f, indent=2)


def get_todays_niche(config: dict, progress: dict) -> str:
    """Pick the next niche in rotation — never repeat until all done"""
    niches = config["outreach"]["niches"]

    if niches == ["all"]:
        niches = [
            "restaurants", "salons", "clinics", "schools",
            "hotels", "pharmacies", "churches", "real estate",
            "contractors", "supermarkets", "gyms", "event centers",
            "bakeries", "car dealers", "law firms"
        ]

    completed = progress.get("completed_niches", [])
    remaining = [n for n in niches if n not in completed]

    if not remaining:
        # All niches done — reset and start over
        print("✅ All niches completed — resetting rotation for next cycle")
        progress["completed_niches"] = []
        save_progress(progress)
        return niches[0]

    return remaining[0]


def load_existing_leads() -> list:
    """Load existing leads to avoid duplicates"""
    path = "results/leads/leads.json"
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return []


async def main():
    config = load_config()
    progress = load_progress()

    city = config["outreach"]["cities"][0]
    daily_limit = 10  # Always exactly 10 leads per run

    # Pick today's niche
    niche = get_todays_niche(config, progress)
    print(f"\n{'='*55}")
    print(f"🎯 TODAY'S NICHE: {niche.upper()}")
    print(f"🌍 CITY: {city}")
    print(f"🎯 TARGET: {daily_limit} fresh leads")
    print(f"📅 DATE: {datetime.now().strftime('%A, %d %B %Y')}")
    print(f"{'='*55}\n")

    # Load existing leads to avoid duplicates
    existing_leads = load_existing_leads()
    existing_names = {l["name"].lower() for l in existing_leads}
    all_known_names = set(progress.get("all_business_names", []))

    country = config["outreach"].get("country", "Nigeria")
    query = f"{niche} in {city} {country}"
    print(f"🔍 Searching: {query}")

    # Scrape more than we need so we can filter duplicates
    raw_leads = await scrape_google_maps(query, max_results=30)

    # Filter out duplicates and already-known businesses
    fresh_leads = []
    # Names that are clearly not businesses
    def is_valid_business(name: str) -> bool:
        name = name.strip()
        if len(name) <= 2: return False
        if re.match(r'^[A-Z][a-z]+$', name): return False  # Single word like a city
        junk = ["main market", "road", "street", "junction", "bus stop", "avenue"]
        if any(j in name.lower() for j in junk): return False
        return True

    for lead in raw_leads:
        name_lower = lead["name"].lower()
        if not is_valid_business(lead["name"]):
            continue
        if name_lower not in existing_names and name_lower not in all_known_names:
            lead["niche"] = niche
            lead["city"] = city
            lead["date_found"] = datetime.now().strftime("%Y-%m-%d")
            fresh_leads.append(lead)
            if len(fresh_leads) >= daily_limit:
                break

    if not fresh_leads:
        print(f"\n⚠️  No fresh leads found for {niche} in {city}")
        print(f"   Moving this niche to completed and trying tomorrow")
        progress["completed_niches"].append(niche)
        save_progress(progress)
        return

    # Sort by opportunity score
    fresh_leads.sort(key=lambda x: x["opportunity_score"], reverse=True)
    todays_leads = fresh_leads[:daily_limit]

    print(f"\n✅ Found {len(todays_leads)} fresh leads for today\n")

    # Merge with existing leads
    all_leads = existing_leads + todays_leads
    save_leads(all_leads)

    # Update progress
    for lead in todays_leads:
        all_known_names.add(lead["name"].lower())

    progress["all_business_names"] = list(all_known_names)
    progress["completed_niches"].append(niche)
    progress["total_leads_found"] = progress.get("total_leads_found", 0) + len(todays_leads)
    progress["runs"].append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "niche": niche,
        "city": city,
        "leads_found": len(todays_leads)
    })
    save_progress(progress)

    # Print today's leads
    no_website = [l for l in todays_leads if not l["has_website"]]
    has_website = [l for l in todays_leads if l["has_website"]]

    print("\n" + "="*55)
    print(f"📊 TODAY'S LEAD FINDER SUMMARY")
    print("="*55)
    print(f"Niche:                {niche}")
    print(f"City:                 {city}")
    print(f"Fresh leads today:    {len(todays_leads)}")
    print(f"No website (hot):     {len(no_website)}")
    print(f"Has website (audit):  {len(has_website)}")
    print(f"Total leads overall:  {len(all_leads)}")
    print(f"Next niche tomorrow:  {get_todays_niche(config, progress)}")
    print("="*55)
    print(f"\n📋 TODAY'S LEADS:")
    for i, lead in enumerate(todays_leads, 1):
        website_status = "Has website" if lead["has_website"] else "⚠️  NO WEBSITE"
        print(f"  {i:2}. {lead['name'][:40]:<40} {website_status}")
    print(f"\n💾 Saved to results/leads/leads.json")
    print(f"▶️  Next step: python lead_enricher.py")

if __name__ == "__main__":
    asyncio.run(main())