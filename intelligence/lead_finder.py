import asyncio
import random
import json
import os
import re
import sys
from playwright.async_api import async_playwright
from dotenv import load_dotenv
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv()

class Symbol:
    """Clean logging symbols that work across all terminals"""
    USE_EMOJI = False # Set to True if your terminal supports UTF-8 emojis
    
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
    HUMAN = "🧑" if USE_EMOJI else "[USER]" if USE_EMOJI else "[PAGE]"
    MAPS = "{Symbol.MAPS}" if USE_EMOJI else "[MAPS]"
    ERROR = "{Symbol.ERROR}" if USE_EMOJI else "[ERROR]"
    HUMAN = "{Symbol.HUMAN}" if USE_EMOJI else "[USER]"

async def scrape_google_maps(query: str, max_results: int = 20):
    leads = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print(f"\n{Symbol.SEARCH} Searching Google Maps for: {query}")
        await page.goto(f"https://www.google.com/maps/search/{query.replace(' ', '+')}", wait_until="domcontentloaded")
        
        # Wait for the main UI to settle
        await page.wait_for_timeout(5000)

        # Auto-handle Google consent popup
        try:
            consent_selectors = [
                'button[aria-label="Accept all"]',
                'button[jsname="b3VHJd"]',
                '#L2AGLb', '.QS5gu',
                'button:has-text("Accept all")',
                'button:has-text("I agree")',
                'button:has-text("Accept")',
                'button:has-text("Allow all")',
            ]
            for sel in consent_selectors:
                btn = await page.query_selector(sel)
                if btn:
                    await btn.click()
                    print(f"{Symbol.CHECK} Google consent handled automatically")
                    await page.wait_for_timeout(5000)
                    break
        except:
            pass

        # Give it a good 10 seconds to load results
        print(f"{Symbol.WAIT} Waiting for listings to populate...")
        await page.wait_for_timeout(10000)

        # Human-like scrolling with random pauses
        try:
            results_panel = await page.query_selector('div[role="feed"]')
            if results_panel:
                print(f"{Symbol.HUMAN} Scrolling like a human...")
                for _ in range(10):
                    # Random scroll distance like a real person
                    scroll_distance = random.randint(400, 900)
                    await results_panel.evaluate(f"el => el.scrollTop += {scroll_distance}")
                    
                    # Random pause between scrolls (1.5 to 4 seconds)
                    pause = random.uniform(1.5, 4.0)
                    await page.wait_for_timeout(int(pause * 1000))
                print(f"{Symbol.CHECK} Scrolled results panel successfully")
        except:
            print(f"{Symbol.WARN} Could not scroll panel, continuing with visible results")


        # Grab all business listing elements
        # 1. Try multiple selectors for listings
        selectors = [
            'a[href*="/maps/place/"]',
            'div[role="article"] a',
            'div.m67q60-V67S5c-haAclf a', # Common maps listing class
            '[aria-label*="Results for"] a'
        ]
        
        listings = []
        for selector in selectors:
            listings = await page.query_selector_all(selector)
            if listings:
                print(f"{Symbol.CHECK} Found {len(listings)} listings using selector: {selector}")
                break
        
        if not listings:
            print(f"{Symbol.ERROR} No listings found with any selector. Saving debug screenshot...")
            os.makedirs("results/logs", exist_ok=True)
            await page.screenshot(path="results/logs/maps_fail.png")
            # Also dump HTML for deep debugging
            with open("results/logs/maps_fail.html", "w", encoding="utf-8") as f:
                f.write(await page.content())
        
        print(f"{Symbol.MAPS} Found {len(listings)} listings, extracting details...\n")

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
                print(f"{Symbol.CHECK} {name}")
                print(f"   {Symbol.PHONE} {lead['phone'] or 'No phone found'}")
                print(f"   {Symbol.CHECK} {'Has website' if lead['has_website'] else '[NO WEBSITE] - Hot lead!'}")
                print(f"   ⭐ {lead['rating']} ({lead['reviews']} reviews)")
                print(f"   {Symbol.SEARCH} Opportunity Score: {lead['opportunity_score']}/10\n")

            except Exception as e:
                print(f"{Symbol.WARN}  Skipped one listing: {e}")
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
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(leads, f, indent=2, ensure_ascii=False)
    print(f"\n💾 {len(leads)} leads saved to {filename}")


def load_config(path: str = "ceo_config.json") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_progress() -> dict:
    """Track which niches and cities have been done and which businesses already found"""
    progress_file = "results/leads/progress.json"
    if os.path.exists(progress_file):
        with open(progress_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "completed_cities" not in data:
                data["completed_cities"] = []
            return data
    return {
        "completed_niches": [],
        "completed_cities": [],
        "current_niche_index": 0,
        "all_business_names": [],
        "total_leads_found": 0,
        "runs": []
    }


def save_progress(progress: dict):
    os.makedirs("results/leads", exist_ok=True)
    with open("results/leads/progress.json", "w", encoding="utf-8") as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


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
        print(f"{Symbol.CHECK} All niches completed — resetting rotation for next cycle")
        progress["completed_niches"] = []
        save_progress(progress)
        return niches[0]

    return remaining[0]


def get_todays_city(config: dict, progress: dict) -> str:
    """Pick the next city in rotation — never repeat until all done"""
    cities = config["outreach"]["cities"]
    completed = progress.get("completed_cities", [])
    remaining = [c for c in cities if c not in completed]

    if not remaining:
        # All cities done — reset and start over
        print(f"{Symbol.CHECK} All cities completed — resetting city rotation for next cycle")
        progress["completed_cities"] = []
        save_progress(progress)
        return cities[0]

    return remaining[0]


def load_existing_leads() -> list:
    """Load existing leads to avoid duplicates"""
    path = "results/leads/leads.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


async def main():
    # Check if there are already 10 or more leads with pending/active outreach messages
    master_seq_path = "results/messages/sequences/master_sequence.json"
    if os.path.exists(master_seq_path):
        try:
            with open(master_seq_path, "r", encoding="utf-8") as f:
                master_seq = json.load(f)
            pending_leads_count = sum(
                1 for lead_seq in master_seq
                if any(step.get("status") in ["approved", "queued"] for step in lead_seq.get("sequence", []))
            )
            if pending_leads_count >= 10:
                print(f"\n{Symbol.WARN} Outreach backlog has {pending_leads_count} pending leads (limit is 10).")
                print("⚠️  Skipping lead discovery today to prevent accumulation of extra leads when outreach is not yet fully functional.\n")
                return
        except Exception as e:
            print(f"⚠️  Could not check outreach backlog: {e}")

    config = load_config()
    progress = load_progress()

    city = get_todays_city(config, progress)
    daily_limit = 10  # Always exactly 10 leads per run

    # Pick today's niche
    niche = get_todays_niche(config, progress)
    print(f"\n{'='*55}")
    print(f"{Symbol.SEARCH} TODAY'S NICHE: {niche.upper()}")
    print(f"{Symbol.MAPS} CITY: {city}")
    print(f"{Symbol.SEARCH} TARGET: {daily_limit} fresh leads")
    print(f"{Symbol.WAIT} DATE: {datetime.now().strftime('%A, %d %B %Y')}")
    print(f"{'='*55}\n")

    # Load existing leads to avoid duplicates
    existing_leads = load_existing_leads()
    existing_names = {l["name"].lower() for l in existing_leads}
    all_known_names = set(progress.get("all_business_names", []))

    country = config["outreach"].get("country", "Nigeria")
    query = f"{niche} in {city} {country}"
    print(f"{Symbol.SEARCH} Searching: {query}")

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
        print(f"\n{Symbol.WARN} No fresh leads found for {niche} in {city}")
        print(f"   Moving this niche/city to completed and trying tomorrow")
        progress["completed_niches"].append(niche)
        progress["completed_cities"].append(city)
        save_progress(progress)
        return

    # Sort by opportunity score
    fresh_leads.sort(key=lambda x: x["opportunity_score"], reverse=True)
    todays_leads = fresh_leads[:daily_limit]

    print(f"\n{Symbol.CHECK} Found {len(todays_leads)} fresh leads for today\n")

    # Merge with existing leads
    all_leads = existing_leads + todays_leads
    save_leads(all_leads)

    # Update progress
    for lead in todays_leads:
        all_known_names.add(lead["name"].lower())

    progress["all_business_names"] = list(all_known_names)
    progress["completed_niches"].append(niche)
    progress["completed_cities"].append(city)
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
    print(f"Next city tomorrow:   {get_todays_city(config, progress)}")
    print(f"="*55)
    print(f"\n{Symbol.LIST} TODAY'S LEADS:")
    for i, lead in enumerate(todays_leads, 1):
        website_status = "Has website" if lead["has_website"] else "[NO WEBSITE]"
        print(f"   {i:2}. {lead['name'][:40]:<40} {website_status}")
    print(f"\n💾 Saved to results/leads/leads.json")
    print(f"▶️  Next step: python lead_enricher.py")

if __name__ == "__main__":
    asyncio.run(main())