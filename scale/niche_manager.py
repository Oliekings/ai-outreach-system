import json
import os
import re
from datetime import datetime
from dotenv import load_dotenv
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from utils.ai_client import ai_response as get_ai_response, safe_json

load_dotenv()

os.makedirs("results/campaigns", exist_ok=True)



# ─────────────────────────────────────────────────────────────────────────────
# NICHE DEFINITIONS
# Complete playbook per niche — pitch angles, audit criteria, revenue calc
# ─────────────────────────────────────────────────────────────────────────────
NICHES = {
    "restaurants": {
        "label": "Restaurants & Food",
        "icon": "🍽️",
        "search_terms": [
            "restaurants", "fast food", "eateries", "cafes",
            "bars and grills", "suya spots", "bukka"
        ],
        "pain_points": [
            "No online ordering or delivery system",
            "Customers can't find menu online",
            "No WhatsApp for quick orders",
            "No reservation system",
            "Missing from Google Maps properly"
        ],
        "pitch_hooks": [
            "Your customers are searching for you online but can't find a menu",
            "Competitors like {} already accept online orders — you don't",
            "Your {} Google reviews show customers love you but can't reach you easily"
        ],
        "services_to_offer": [
            "Professional restaurant website with menu",
            "Online ordering system",
            "WhatsApp Business setup with catalog",
            "Google Business Profile optimization",
            "Instagram presence setup"
        ],
        "avg_deal_ngn": 250000,
        "monthly_retainer_ngn": 75000,
        "audit_criteria": [
            "has_online_menu", "has_ordering_system", "has_reservation",
            "has_whatsapp", "google_profile_complete"
        ],
        "lead_score_weight": {
            "no_website": 3,
            "no_ordering": 2,
            "high_reviews": 2,
            "no_whatsapp": 1
        }
    },

    "salons": {
        "label": "Salons & Beauty",
        "icon": "💅",
        "search_terms": [
            "salons", "beauty salons", "hair salons", "barbershops",
            "nail salons", "makeup artists", "spa"
        ],
        "pain_points": [
            "No online booking — customers call or walk in only",
            "No portfolio website showing their work",
            "No Instagram presence with quality photos",
            "Can't send appointment reminders automatically",
            "Losing clients to salons with better online presence"
        ],
        "pitch_hooks": [
            "Salons with online booking fill 40% more appointments on average",
            "Your potential clients are browsing Instagram for their next salon",
            "You're losing walk-ins to salons that show up in Google search"
        ],
        "services_to_offer": [
            "Portfolio website with photo gallery",
            "Online booking system",
            "Instagram profile setup and strategy",
            "WhatsApp Business for appointment reminders",
            "Google Business optimization"
        ],
        "avg_deal_ngn": 180000,
        "monthly_retainer_ngn": 60000,
        "audit_criteria": [
            "has_booking", "has_portfolio", "has_instagram",
            "has_whatsapp", "google_profile_complete"
        ],
        "lead_score_weight": {
            "no_website": 3,
            "no_booking": 3,
            "no_instagram": 2
        }
    },

    "clinics": {
        "label": "Clinics & Healthcare",
        "icon": "🏥",
        "search_terms": [
            "clinics", "hospitals", "specialist hospitals",
            "dental clinics", "eye clinics", "medical centers"
        ],
        "pain_points": [
            "Patients can't book appointments online",
            "No way to share test results or documents securely",
            "No professional website that builds patient trust",
            "Missing from Google when patients search for specialists",
            "No automated appointment reminder system"
        ],
        "pitch_hooks": [
            "Patients increasingly choose clinics based on online presence before visiting",
            "A professional medical website builds trust before patients walk in",
            "Your clinic isn't showing up when patients search for your specialty online"
        ],
        "services_to_offer": [
            "Professional clinic website with doctor profiles",
            "Online appointment booking system",
            "Google Business optimization for medical searches",
            "Patient communication via WhatsApp Business",
            "Social media presence for health education"
        ],
        "avg_deal_ngn": 350000,
        "monthly_retainer_ngn": 100000,
        "audit_criteria": [
            "has_appointment_booking", "has_professional_site",
            "has_doctor_profiles", "has_whatsapp", "google_profile_complete"
        ],
        "lead_score_weight": {
            "no_website": 4,
            "no_booking": 3,
            "no_google_presence": 2
        }
    },

    "schools": {
        "label": "Schools & Education",
        "icon": "🏫",
        "search_terms": [
            "schools", "private schools", "international schools",
            "nursery schools", "secondary schools", "tutorial centers"
        ],
        "pain_points": [
            "Parents can't find school information online",
            "No online fee payment system",
            "No way to communicate with parents digitally",
            "Missing from Google when parents search for schools",
            "No platform to share results or updates with parents"
        ],
        "pitch_hooks": [
            "Parents now research schools online before enrolling their children",
            "Schools with professional websites attract 60% more inquiries",
            "Your competitors have parent portals — you're still using paper"
        ],
        "services_to_offer": [
            "Professional school website with virtual tour",
            "Parent communication portal",
            "Online fee payment integration",
            "Google Business optimization",
            "Social media for school events and achievements"
        ],
        "avg_deal_ngn": 400000,
        "monthly_retainer_ngn": 120000,
        "audit_criteria": [
            "has_parent_portal", "has_fee_system",
            "has_professional_site", "has_social_media"
        ],
        "lead_score_weight": {
            "no_website": 4,
            "no_parent_portal": 3,
            "no_fee_system": 3
        }
    },

    "hotels": {
        "label": "Hotels & Hospitality",
        "icon": "🏨",
        "search_terms": [
            "hotels", "guest houses", "suites", "lodges",
            "short lets", "airbnb", "serviced apartments"
        ],
        "pain_points": [
            "No online booking system — rely on phone calls only",
            "Not listed on booking platforms properly",
            "No virtual tour or photo gallery online",
            "Losing bookings to hotels with better digital presence",
            "No way to collect and showcase reviews"
        ],
        "pitch_hooks": [
            "Over 70% of hotel bookings now start with an online search",
            "Your competitors on Booking.com are filling rooms you're missing",
            "A professional website with booking can reduce your vacancy rate significantly"
        ],
        "services_to_offer": [
            "Professional hotel website with room gallery",
            "Online booking integration",
            "Booking platform listing optimization",
            "Google Business with photos and reviews",
            "WhatsApp Business for direct bookings"
        ],
        "avg_deal_ngn": 450000,
        "monthly_retainer_ngn": 130000,
        "audit_criteria": [
            "has_online_booking", "has_photo_gallery",
            "listed_on_platforms", "has_whatsapp", "google_profile_complete"
        ],
        "lead_score_weight": {
            "no_website": 4,
            "no_booking": 4,
            "no_photos": 2
        }
    },

    "pharmacies": {
        "label": "Pharmacies & Drugstores",
        "icon": "💊",
        "search_terms": [
            "pharmacies", "pharmacy", "chemist", "drugstore",
            "drug stores", "medical stores"
        ],
        "pain_points": [
            "Customers can't check if drugs are available before coming",
            "No WhatsApp ordering for home delivery",
            "Not showing up when people search for drugs online",
            "No way to share drug information and health tips",
            "Missing delivery system for repeat prescriptions"
        ],
        "pitch_hooks": [
            "Pharmacies with WhatsApp ordering see 3x more home delivery orders",
            "Customers are ordering drugs online — are they finding you?",
            "A simple inventory listing online can drive significant foot traffic"
        ],
        "services_to_offer": [
            "Pharmacy website with drug catalog",
            "WhatsApp ordering system",
            "Google Business optimization",
            "Health tips social media presence",
            "Home delivery tracking system"
        ],
        "avg_deal_ngn": 200000,
        "monthly_retainer_ngn": 65000,
        "audit_criteria": [
            "has_catalog", "has_whatsapp_ordering",
            "has_delivery", "google_profile_complete"
        ],
        "lead_score_weight": {
            "no_website": 3,
            "no_whatsapp": 3,
            "no_delivery": 2
        }
    },

    "churches": {
        "label": "Churches & Religious",
        "icon": "⛪",
        "search_terms": [
            "churches", "ministries", "assemblies",
            "cathedral", "chapel", "bible church"
        ],
        "pain_points": [
            "Members miss service times and event updates",
            "No online giving or tithe platform",
            "Visitors can't find church location or service times easily",
            "Sermons and content not reaching members between Sundays",
            "No way to manage member communication efficiently"
        ],
        "pitch_hooks": [
            "Churches with digital platforms grow membership 40% faster",
            "Your members want to tithe online — are you set up for that?",
            "New residents searching for a church home need to find you first"
        ],
        "services_to_offer": [
            "Church website with service times and location",
            "Online giving platform integration",
            "Sermon streaming or podcast setup",
            "Member communication via WhatsApp",
            "Event management system"
        ],
        "avg_deal_ngn": 300000,
        "monthly_retainer_ngn": 80000,
        "audit_criteria": [
            "has_giving_platform", "has_website",
            "has_streaming", "has_member_portal"
        ],
        "lead_score_weight": {
            "no_website": 3,
            "no_giving": 4,
            "no_streaming": 2
        }
    },

    "real_estate": {
        "label": "Real Estate",
        "icon": "🏠",
        "search_terms": [
            "real estate", "property agents", "estate agents",
            "property developers", "land agents", "property management"
        ],
        "pain_points": [
            "No property listing website — rely on WhatsApp and word of mouth",
            "Can't showcase properties professionally online",
            "Missing serious buyers who search online first",
            "No virtual tour capability",
            "Losing clients to agents with professional digital presence"
        ],
        "pitch_hooks": [
            "Property buyers research online for months before calling an agent",
            "Agents with listing websites close deals 2x faster on average",
            "Your competitors are getting leads from Google — you're not"
        ],
        "services_to_offer": [
            "Property listing website with search and filters",
            "Virtual tour integration",
            "Lead capture and CRM setup",
            "Google Business optimization",
            "Social media property showcase"
        ],
        "avg_deal_ngn": 500000,
        "monthly_retainer_ngn": 150000,
        "audit_criteria": [
            "has_listing_site", "has_virtual_tour",
            "has_lead_capture", "has_social_showcase"
        ],
        "lead_score_weight": {
            "no_website": 5,
            "no_listings": 4,
            "no_virtual_tour": 2
        }
    },

    "contractors": {
        "label": "Contractors & Construction",
        "icon": "🔨",
        "search_terms": [
            "contractors", "construction companies", "builders",
            "plumbers", "electricians", "interior designers", "architects"
        ],
        "pain_points": [
            "No portfolio website showing completed projects",
            "Relying entirely on referrals — no inbound leads",
            "Can't compete with larger firms that have professional websites",
            "No way to generate quotes or proposals online",
            "Missing from Google when people search for contractors"
        ],
        "pitch_hooks": [
            "Your best projects are invisible — no one sees them except past clients",
            "Contractors with portfolio websites get 3x more unsolicited quotes",
            "People search for 'best contractor in {}' — are you showing up?"
        ],
        "services_to_offer": [
            "Portfolio website with project gallery",
            "Online quote request system",
            "Google Business with before/after photos",
            "Social media project showcasing",
            "Client testimonial collection system"
        ],
        "avg_deal_ngn": 280000,
        "monthly_retainer_ngn": 80000,
        "audit_criteria": [
            "has_portfolio", "has_quote_system",
            "has_testimonials", "google_profile_complete"
        ],
        "lead_score_weight": {
            "no_website": 4,
            "no_portfolio": 4,
            "no_google_presence": 2
        }
    },

    "supermarkets": {
        "label": "Supermarkets & Retail",
        "icon": "🛒",
        "search_terms": [
            "supermarkets", "stores", "shopping", "retail",
            "grocery stores", "provision stores", "mini marts"
        ],
        "pain_points": [
            "No online ordering or delivery setup",
            "Customers don't know what's in stock before coming",
            "Missing loyalty program to retain customers",
            "Can't reach customers with promotions digitally",
            "Losing sales to stores with WhatsApp ordering"
        ],
        "pitch_hooks": [
            "WhatsApp ordering stores see 50% more repeat purchases",
            "Your customers want to order groceries — are you set up for delivery?",
            "A simple product catalog online can double your reach"
        ],
        "services_to_offer": [
            "Online store with product catalog",
            "WhatsApp ordering system",
            "Delivery tracking setup",
            "Loyalty program",
            "Promotional campaigns via WhatsApp broadcast"
        ],
        "avg_deal_ngn": 320000,
        "monthly_retainer_ngn": 90000,
        "audit_criteria": [
            "has_online_catalog", "has_ordering",
            "has_delivery", "has_loyalty_program"
        ],
        "lead_score_weight": {
            "no_website": 3,
            "no_ordering": 4,
            "no_delivery": 3
        }
    },

    "gyms": {
        "label": "Gyms & Fitness",
        "icon": "💪",
        "search_terms": [
            "gyms", "fitness centers", "health clubs",
            "yoga studios", "crossfit", "personal trainers"
        ],
        "pain_points": [
            "No online membership or class booking system",
            "Relying on word of mouth — no digital marketing",
            "Can't showcase transformation results online",
            "No way to sell online training programs",
            "Missing the growing online fitness market"
        ],
        "pitch_hooks": [
            "Gyms with online booking fill classes 60% more consistently",
            "Fitness content on Instagram drives new memberships every week",
            "People searching for gyms near them need to find yours first"
        ],
        "services_to_offer": [
            "Gym website with class schedule and booking",
            "Online membership management",
            "Instagram transformation showcase",
            "WhatsApp community management",
            "Online training program sales"
        ],
        "avg_deal_ngn": 220000,
        "monthly_retainer_ngn": 70000,
        "audit_criteria": [
            "has_booking", "has_membership_system",
            "has_instagram", "has_transformation_gallery"
        ],
        "lead_score_weight": {
            "no_website": 3,
            "no_booking": 3,
            "no_instagram": 3
        }
    },

    "law_firms": {
        "label": "Law Firms & Legal",
        "icon": "⚖️",
        "search_terms": [
            "law firms", "lawyers", "legal services",
            "solicitors", "barristers", "legal consultants"
        ],
        "pain_points": [
            "No professional website that conveys expertise and trust",
            "Clients can't find or verify credentials online",
            "Missing from searches when people need legal help",
            "No way to generate consultation bookings online",
            "Competitors with websites look more credible"
        ],
        "pitch_hooks": [
            "Clients research lawyers online before making contact",
            "A professional legal website converts 3x more inquiries to consultations",
            "Your expertise is invisible without a professional online presence"
        ],
        "services_to_offer": [
            "Professional law firm website with attorney profiles",
            "Online consultation booking",
            "Legal blog for SEO and authority",
            "Google Business optimization",
            "LinkedIn presence for professional network"
        ],
        "avg_deal_ngn": 450000,
        "monthly_retainer_ngn": 130000,
        "audit_criteria": [
            "has_professional_site", "has_attorney_profiles",
            "has_consultation_booking", "has_legal_blog"
        ],
        "lead_score_weight": {
            "no_website": 5,
            "no_profiles": 3,
            "no_booking": 2
        }
    },

    "bakeries": {
        "label": "Bakeries & Cake Shops",
        "icon": "🍰",
        "search_terms": [
            "bakeries", "bakery", "cake shops", "pastry shops",
            "confectionery", "bread bakeries"
        ],
        "pain_points": [
            "No online ordering for custom birthday/wedding cakes",
            "No dynamic product catalog or pricing list visible online",
            "No WhatsApp ordering setup for automated stock checks",
            "No Instagram portfolio showcasing custom designs beautifully",
            "Losing custom celebration orders to modern online bakeries"
        ],
        "pitch_hooks": [
            "Customers looking for custom cakes in {} want to browse designs and order online easily",
            "Bakeries with WhatsApp ordering and e-commerce catalogs see 60% more cake bookings",
            "Your delicious pastries deserve a stunning digital menu and easy order system"
        ],
        "services_to_offer": [
            "Bakery website with visual custom cake builder/catalog",
            "E-Commerce integration for direct pastry ordering",
            "WhatsApp Business automation with catalog & payment link",
            "Instagram branding and cake photo strategy",
            "Google Maps SEO for local bakery searches"
        ],
        "avg_deal_ngn": 220000,
        "monthly_retainer_ngn": 70000,
        "audit_criteria": [
            "has_online_catalog", "has_cake_builder", "has_whatsapp_ordering",
            "has_instagram_gallery", "google_profile_complete"
        ],
        "lead_score_weight": {
            "no_website": 3,
            "no_ordering": 3,
            "no_whatsapp": 2,
            "no_instagram": 2
        }
    },

    "boutiques": {
        "label": "Boutiques & Fashion",
        "icon": "👗",
        "search_terms": [
            "boutiques", "clothing stores", "fashion boutiques", "wears shop",
            "shoe shops", "accessories shop"
        ],
        "pain_points": [
            "No e-commerce storefront for customers to browse sizes and buy",
            "Highly dependent on manual DMs on Instagram/WhatsApp to close sales",
            "No inventory sync between offline shop and online catalog",
            "No professional website that builds high-end fashion trust",
            "Losing retail customers to competitors with seamless payment gateways"
        ],
        "pitch_hooks": [
            "Retail stores with automated checkout close 3x more sales without answering endless DMs",
            "Your beautiful fashion collection deserves a professional e-commerce storefront",
            "Customers browsing your Instagram want to click, buy, and get delivery instantly"
        ],
        "services_to_offer": [
            "Premium e-commerce website with inventory tracking",
            "Instagram Storefront setup & product tagging",
            "WhatsApp AI customer agent for size & stock availability",
            "Social media growth & styling content strategy",
            "Local delivery integration & payment gateway setup"
        ],
        "avg_deal_ngn": 280000,
        "monthly_retainer_ngn": 80000,
        "audit_criteria": [
            "has_ecom_site", "has_instagram_shop", "has_delivery_integration",
            "has_automated_checkout", "has_whatsapp_bot"
        ],
        "lead_score_weight": {
            "no_website": 4,
            "no_checkout": 3,
            "no_instagram_shop": 2,
            "no_whatsapp": 1
        }
    },

    "laundry": {
        "label": "Laundry & Dry Cleaning",
        "icon": "🧺",
        "search_terms": [
            "laundry services", "dry cleaners", "laundromat", "dry cleaning"
        ],
        "pain_points": [
            "No online pickup & delivery scheduling system",
            "No automated WhatsApp notifications when clothes are ready",
            "No online price list or subscription packages listed",
            "Relying completely on physical receipts and manual tracking",
            "Missing premium clients who demand scheduled home pickup"
        ],
        "pitch_hooks": [
            "Dry cleaners offering scheduled home pickup and digital updates grow revenue by 80%",
            "Your busy clients in {} want to book their laundry pickup online in two clicks",
            "Automated ready-for-collection alerts on WhatsApp increase customer satisfaction immensely"
        ],
        "services_to_offer": [
            "Laundry website with pickup & delivery scheduling",
            "WhatsApp Business automation for tracking and notifications",
            "Digital price list & subscription billing setup",
            "Google Maps local SEO for dry cleaning searches",
            "SMS/WhatsApp automated notification system"
        ],
        "avg_deal_ngn": 200000,
        "monthly_retainer_ngn": 60000,
        "audit_criteria": [
            "has_scheduling", "has_online_pricing", "has_whatsapp_updates",
            "has_subscription", "google_profile_complete"
        ],
        "lead_score_weight": {
            "no_website": 3,
            "no_scheduling": 4,
            "no_whatsapp": 2,
            "no_pricing": 1
        }
    },

    "car_dealers": {
        "label": "Car Dealers & Auto",
        "icon": "🚗",
        "search_terms": [
            "car dealers", "car sales", "auto dealers", "auto mart",
            "tokunbo cars", "car wash", "auto mechanic"
        ],
        "pain_points": [
            "No online vehicle catalog with filterable specs and prices",
            "Buyers can't see virtual car walkarounds or inspect options online",
            "Missing serious buyers who search online before visiting car lots",
            "No WhatsApp automated bot for car inquiry and booking physical test drives",
            "Losing high-ticket dealership sales to digital-first auto portals"
        ],
        "pitch_hooks": [
            "75% of car buyers in Nigeria research vehicle catalogs online before stepping into a dealership",
            "An online showroom with clear virtual walkarounds drives 2x more physical car lot visits",
            "Dealerships with automated WhatsApp inquiry setups capture high-intent buyers 24/7"
        ],
        "services_to_offer": [
            "Auto dealership website with filterable inventory and specs",
            "Virtual walkaround and high-res gallery integration",
            "WhatsApp AI booking bot for test drives & price inquiries",
            "Google Maps local search SEO for car dealerships",
            "Social media branding & Facebook marketplace strategy"
        ],
        "avg_deal_ngn": 400000,
        "monthly_retainer_ngn": 120000,
        "audit_criteria": [
            "has_inventory_site", "has_virtual_walkaround", "has_testdrive_booking",
            "has_whatsapp_bot", "google_profile_complete"
        ],
        "lead_score_weight": {
            "no_website": 5,
            "no_inventory": 4,
            "no_whatsapp": 2,
            "no_photos": 1
        }
    },

    "event_centers": {
        "label": "Event Centers & Halls",
        "icon": "🎪",
        "search_terms": [
            "event centers", "event halls", "wedding venues", "conference centers",
            "party halls", "gardens for events"
        ],
        "pain_points": [
            "No online booking calendar showing hall availability",
            "Clients have to physically travel to inspect the hall layout and capacity",
            "No high-quality virtual 3D tour or photo gallery online",
            "No simple package pricing list or quote generator online",
            "Losing lucrative wedding/corporate bookings to halls with modern websites"
        ],
        "pitch_hooks": [
            "Event planners and couples in {} prefer booking halls that display availability online",
            "Halls with high-quality virtual tours and quote tools secure 50% more weekend bookings",
            "Your event center deserves a professional digital presence to close high-budget events"
        ],
        "services_to_offer": [
            "Event center website with real-time availability calendar",
            "High-resolution photo gallery & virtual 3D tour setup",
            "Online event package quote generator",
            "WhatsApp Business automation for event inquiries",
            "Google Maps local search optimization with review campaigns"
        ],
        "avg_deal_ngn": 350000,
        "monthly_retainer_ngn": 90000,
        "audit_criteria": [
            "has_website", "has_availability_calendar", "has_virtual_tour",
            "has_quote_generator", "google_profile_complete"
        ],
        "lead_score_weight": {
            "no_website": 4,
            "no_calendar": 3,
            "no_tour": 3,
            "no_quotes": 2
        }
    },

    "printing_press": {
        "label": "Printing & Branding",
        "icon": "🖨️",
        "search_terms": [
            "printing press", "printers", "graphic designers", "branding companies",
            "publishing", "signage makers"
        ],
        "pain_points": [
            "No online order upload or file submission system",
            "No online pricing calculator for bulk flyer/card/banner printing",
            "No digital portfolio showing print quality and branding work",
            "Relying completely on manual walk-ins and physical quotes",
            "Losing corporate branding accounts to digital printing companies"
        ],
        "pitch_hooks": [
            "Businesses and event planners want to upload artwork and order prints online instantly",
            "Printing shops with digital pricing calculators and order forms see 3x more bulk print runs",
            "Your beautiful print quality needs a professional digital portfolio to win corporate accounts"
        ],
        "services_to_offer": [
            "E-commerce printing website with file upload and bulk pricing calculator",
            "Digital branding and design portfolio setup",
            "WhatsApp Business custom catalog & quote submission",
            "Google Maps local search SEO for business printers",
            "Client testimonial and print showcase system"
        ],
        "avg_deal_ngn": 250000,
        "monthly_retainer_ngn": 75000,
        "audit_criteria": [
            "has_ordering_site", "has_file_upload", "has_bulk_calculator",
            "has_portfolio", "google_profile_complete"
        ],
        "lead_score_weight": {
            "no_website": 4,
            "no_upload": 4,
            "no_calculator": 3,
            "no_portfolio": 2
        }
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# NICHE MANAGER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────
def get_niche_config(niche_key: str) -> dict:
    """Get full config for a specific niche"""
    # Try exact match first
    if niche_key in NICHES:
        return NICHES[niche_key]

    # Try partial match
    niche_lower = niche_key.lower()
    for key, config in NICHES.items():
        if key in niche_lower or niche_lower in key:
            return config

    # Check search terms
    for key, config in NICHES.items():
        for term in config.get("search_terms", []):
            if term in niche_lower or niche_lower in term:
                return config

    return NICHES.get("restaurants", {})  # Default fallback


def get_all_search_terms() -> list:
    """Get all search terms across all niches"""
    terms = []
    for niche, config in NICHES.items():
        for term in config.get("search_terms", []):
            terms.append({"term": term, "niche": niche, "label": config["label"]})
    return terms


def calculate_opportunity_score(lead: dict, niche_key: str) -> int:
    """Calculate lead opportunity score based on niche-specific criteria"""
    config = get_niche_config(niche_key)
    weights = config.get("lead_score_weight", {})
    score = 5  # Base score

    has_website = bool(lead.get("official_website", {}).get("url"))
    has_whatsapp = bool(lead.get("contact_whatsapp"))
    has_instagram = lead.get("instagram", {}).get("found", False)
    reviews_str = str(lead.get("reviews", "0")).replace(",", "")

    try:
        review_count = int(re.sub(r'[^0-9]', '', reviews_str))
    except:
        review_count = 0

    if not has_website:
        score += weights.get("no_website", 3)

    if not has_whatsapp:
        score += weights.get("no_whatsapp", 1)

    if not has_instagram:
        score += weights.get("no_instagram", 0)

    if review_count >= 100:
        score += weights.get("high_reviews", 2)

    return min(score, 10)


def generate_niche_pitch(lead: dict, niche_key: str) -> str:
    """Generate a niche-specific pitch angle"""
    config = get_niche_config(niche_key)
    name = lead.get("name", "your business")
    city = lead.get("city", "Nigeria")
    reviews = lead.get("reviews", "")
    personality = lead.get("personality") or {}
    tone = personality.get("tone_to_use", "semi-formal")

    pain_points = config.get("pain_points", [])
    services = config.get("services_to_offer", [])
    hooks = config.get("pitch_hooks", [])

    prompt = f"""
Write a hyper-personalized pitch angle for a {niche_key} business in {city}, Nigeria.

Business: {name}
Google Reviews: {reviews}
Tone: {tone}

Industry-specific pain points:
{chr(10).join(f'- {p}' for p in pain_points[:3])}

Services we offer for this industry:
{chr(10).join(f'- {s}' for s in services[:3])}

Write 3 sentences:
1. A specific compliment referencing their {niche_key} business
2. The most relevant pain point for their specific situation
3. A soft curious question that invites a reply

Sound like a real human consultant who knows this industry deeply.
Never use generic words. Be specific to {niche_key} businesses in Nigeria.
"""

    try:
        return get_ai_response(prompt, max_tokens=200)
    except:
        return hooks[0].format(name, city) if hooks else f"We noticed some exciting opportunities for {name}."


def get_niche_revenue_estimate(niche_key: str, lead_count: int) -> dict:
    """Estimate revenue potential from leads in this niche"""
    config = get_niche_config(niche_key)
    avg_deal = config.get("avg_deal_ngn", 200000)
    retainer = config.get("monthly_retainer_ngn", 60000)

    # Assume 5% conversion rate
    expected_clients = max(1, int(lead_count * 0.05))

    return {
        "niche": niche_key,
        "lead_count": lead_count,
        "expected_clients": expected_clients,
        "one_time_revenue_ngn": expected_clients * avg_deal,
        "monthly_retainer_ngn": expected_clients * retainer,
        "annual_revenue_ngn": (expected_clients * avg_deal) + (expected_clients * retainer * 12),
        "avg_deal_ngn": avg_deal
    }


def list_all_niches() -> str:
    """Print all available niches"""
    output = f"\n{'='*60}\n"
    output += "  📊 AVAILABLE NICHES\n"
    output += f"{'='*60}\n\n"

    for key, config in NICHES.items():
        terms = ", ".join(config["search_terms"][:3])
        output += f"  {config['icon']} {config['label']}\n"
        output += f"     Key: {key}\n"
        output += f"     Search terms: {terms}...\n"
        output += f"     Avg deal: ₦{config['avg_deal_ngn']:,}\n"
        output += f"     Retainer: ₦{config['monthly_retainer_ngn']:,}/mo\n\n"

    output += f"  Total niches: {len(NICHES)}\n"
    output += f"  Total search terms: {len(get_all_search_terms())}\n"
    output += f"{'='*60}\n"
    return output


if __name__ == "__main__":
    print(list_all_niches())