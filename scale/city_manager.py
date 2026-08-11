import json
import os
import re
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
sys.stdout.reconfigure(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# NIGERIAN CITIES DATABASE
# ─────────────────────────────────────────────────────────────────────────────
NIGERIAN_CITIES = {
    # Federal Capital Territory
    "Abuja": {
        "state": "FCT",
        "region": "North Central",
        "population": "3.6M",
        "tier": 1,
        "economic_profile": "Government, diplomacy, corporate HQs, high-income residents",
        "best_niches": [
            "restaurants",
            "clinics",
            "schools",
            "hotels",
            "law_firms",
            "real_estate",
        ],
        "avg_spending_power": "high",
        "digital_adoption": "high",
        "competition": "high",
        "language_notes": "Mostly English, multi-ethnic",
    },
    # Lagos State
    "Lagos": {
        "state": "Lagos",
        "region": "South West",
        "population": "15M+",
        "tier": 1,
        "economic_profile": "Finance, trade, entertainment, tech, fashion",
        "best_niches": [
            "restaurants",
            "salons",
            "gyms",
            "hotels",
            "real_estate",
            "contractors",
        ],
        "avg_spending_power": "very_high",
        "digital_adoption": "very_high",
        "competition": "very_high",
        "language_notes": "Yoruba, English, Pidgin",
    },
    "Ikeja": {
        "state": "Lagos",
        "region": "South West",
        "tier": 1,
        "economic_profile": "Industrial, commercial, aviation hub",
        "best_niches": ["restaurants", "hotels", "contractors", "pharmacies"],
        "avg_spending_power": "high",
        "digital_adoption": "high",
        "competition": "high",
    },
    "Victoria Island": {
        "state": "Lagos",
        "region": "South West",
        "tier": 1,
        "economic_profile": "Finance, luxury, corporate",
        "best_niches": ["restaurants", "law_firms", "hotels", "gyms", "real_estate"],
        "avg_spending_power": "very_high",
        "digital_adoption": "very_high",
        "competition": "very_high",
    },
    # Rivers State
    "Port Harcourt": {
        "state": "Rivers",
        "region": "South South",
        "population": "1.9M",
        "tier": 1,
        "economic_profile": "Oil & gas, maritime, trade",
        "best_niches": ["restaurants", "hotels", "clinics", "contractors", "schools"],
        "avg_spending_power": "high",
        "digital_adoption": "high",
        "competition": "medium",
        "language_notes": "Igbo, Ijaw, English",
    },
    # Kano State
    "Kano": {
        "state": "Kano",
        "region": "North West",
        "population": "4.1M",
        "tier": 1,
        "economic_profile": "Trade, textile, agriculture, leather",
        "best_niches": [
            "pharmacies",
            "schools",
            "hotels",
            "supermarkets",
            "contractors",
        ],
        "avg_spending_power": "medium",
        "digital_adoption": "medium",
        "competition": "medium",
        "language_notes": "Hausa primarily, English",
    },
    # Kaduna State
    "Kaduna": {
        "state": "Kaduna",
        "region": "North West",
        "population": "1.5M",
        "tier": 2,
        "economic_profile": "Manufacturing, trade, agriculture",
        "best_niches": ["restaurants", "schools", "clinics", "hotels", "pharmacies"],
        "avg_spending_power": "medium",
        "digital_adoption": "medium",
        "competition": "low",
        "language_notes": "Hausa, English, mixed ethnic",
    },
    # Edo State
    "Benin City": {
        "state": "Edo",
        "region": "South South",
        "population": "1.5M",
        "tier": 2,
        "economic_profile": "Trade, education, rubber industry",
        "best_niches": ["restaurants", "schools", "clinics", "salons", "supermarkets"],
        "avg_spending_power": "medium",
        "digital_adoption": "medium",
        "competition": "medium",
        "language_notes": "Edo, Yoruba, English",
    },
    "Uromi": {
        "state": "Edo",
        "region": "South South",
        "population": "100K+",
        "tier": 3,
        "economic_profile": "Local trade, agriculture, small businesses",
        "best_niches": ["restaurants", "pharmacies", "salons", "schools", "churches"],
        "avg_spending_power": "low_medium",
        "digital_adoption": "low",
        "competition": "very_low",
        "language_notes": "Esan, English",
    },
    # Oyo State
    "Ibadan": {
        "state": "Oyo",
        "region": "South West",
        "population": "3.6M",
        "tier": 1,
        "economic_profile": "Education, agriculture, trade",
        "best_niches": ["restaurants", "schools", "clinics", "salons", "supermarkets"],
        "avg_spending_power": "medium",
        "digital_adoption": "high",
        "competition": "medium",
        "language_notes": "Yoruba, English",
    },
    # Anambra State
    "Onitsha": {
        "state": "Anambra",
        "region": "South East",
        "population": "1M",
        "tier": 2,
        "economic_profile": "Major trade hub, textiles, electronics",
        "best_niches": [
            "supermarkets",
            "contractors",
            "pharmacies",
            "schools",
            "restaurants",
        ],
        "avg_spending_power": "medium_high",
        "digital_adoption": "medium",
        "competition": "medium",
        "language_notes": "Igbo, English",
    },
    "Awka": {
        "state": "Anambra",
        "region": "South East",
        "population": "300K",
        "tier": 2,
        "economic_profile": "State capital, civil service, education",
        "best_niches": ["restaurants", "schools", "clinics", "salons"],
        "avg_spending_power": "medium",
        "digital_adoption": "medium",
        "competition": "low",
        "language_notes": "Igbo, English",
    },
    # Enugu State
    "Enugu": {
        "state": "Enugu",
        "region": "South East",
        "population": "900K",
        "tier": 2,
        "economic_profile": "Education, coal, trade, civil service",
        "best_niches": ["restaurants", "schools", "clinics", "law_firms", "hotels"],
        "avg_spending_power": "medium",
        "digital_adoption": "medium",
        "competition": "low",
        "language_notes": "Igbo, English",
    },
    # Delta State
    "Warri": {
        "state": "Delta",
        "region": "South South",
        "population": "700K",
        "tier": 2,
        "economic_profile": "Oil & gas services, trade, fishing",
        "best_niches": [
            "restaurants",
            "hotels",
            "contractors",
            "pharmacies",
            "clinics",
        ],
        "avg_spending_power": "medium_high",
        "digital_adoption": "medium",
        "competition": "low",
        "language_notes": "Itsekiri, Urhobo, English, Pidgin",
    },
    # Imo State
    "Owerri": {
        "state": "Imo",
        "region": "South East",
        "population": "450K",
        "tier": 2,
        "economic_profile": "Education, entertainment, civil service, trade",
        "best_niches": ["restaurants", "schools", "salons", "hotels", "gyms"],
        "avg_spending_power": "medium",
        "digital_adoption": "medium",
        "competition": "low",
        "language_notes": "Igbo, English",
    },
    # Cross River State
    "Calabar": {
        "state": "Cross River",
        "region": "South South",
        "population": "400K",
        "tier": 2,
        "economic_profile": "Tourism, education, trade, civil service",
        "best_niches": ["restaurants", "hotels", "schools", "salons", "real_estate"],
        "avg_spending_power": "medium",
        "digital_adoption": "medium",
        "competition": "low",
        "language_notes": "Efik, English",
    },
    # Plateau State
    "Jos": {
        "state": "Plateau",
        "region": "North Central",
        "population": "900K",
        "tier": 2,
        "economic_profile": "Agriculture, mining, trade, tourism",
        "best_niches": ["restaurants", "hotels", "schools", "clinics", "churches"],
        "avg_spending_power": "medium",
        "digital_adoption": "medium",
        "competition": "low",
        "language_notes": "Hausa, English, mixed",
    },
    # Borno State
    "Maiduguri": {
        "state": "Borno",
        "region": "North East",
        "population": "1M",
        "tier": 2,
        "economic_profile": "Trade, civil service, agriculture",
        "best_niches": ["pharmacies", "schools", "restaurants", "contractors"],
        "avg_spending_power": "low_medium",
        "digital_adoption": "low",
        "competition": "very_low",
        "language_notes": "Kanuri, Hausa, English",
    },
    # Kwara State
    "Ilorin": {
        "state": "Kwara",
        "region": "North Central",
        "population": "900K",
        "tier": 2,
        "economic_profile": "Trade, education, civil service, textiles",
        "best_niches": [
            "restaurants",
            "schools",
            "salons",
            "pharmacies",
            "supermarkets",
        ],
        "avg_spending_power": "medium",
        "digital_adoption": "medium",
        "competition": "low",
        "language_notes": "Yoruba, Fulani, English",
    },
    # Osun State
    "Osogbo": {
        "state": "Osun",
        "region": "South West",
        "population": "600K",
        "tier": 3,
        "economic_profile": "State capital, civil service, trade",
        "best_niches": ["restaurants", "schools", "salons", "pharmacies"],
        "avg_spending_power": "low_medium",
        "digital_adoption": "medium",
        "competition": "very_low",
        "language_notes": "Yoruba, English",
    },
    "Ekpoma": {
        "state": "Edo",
        "region": "South South",
        "population": "200K",
        "tier": 3,
        "economic_profile": "Major educational hub, university town, agriculture, retail and local trade",
        "best_niches": [
            "restaurants",
            "salons",
            "pharmacies",
            "schools",
            "hotels",
            "boutiques",
            "laundry",
        ],
        "avg_spending_power": "medium",
        "digital_adoption": "medium",
        "competition": "very_low",
        "language_notes": "Esan, English, Pidgin",
    },
    "Auchi": {
        "state": "Edo",
        "region": "South South",
        "population": "150K",
        "tier": 3,
        "economic_profile": "Educational hub, polytechnic town, limestone and mining, local trade",
        "best_niches": [
            "restaurants",
            "salons",
            "pharmacies",
            "schools",
            "churches",
            "bakeries",
            "laundry",
        ],
        "avg_spending_power": "low_medium",
        "digital_adoption": "low_medium",
        "competition": "very_low",
        "language_notes": "Afenmai, English, Pidgin",
    },
    "Agbor": {
        "state": "Delta",
        "region": "South South",
        "population": "150K",
        "tier": 3,
        "economic_profile": "Agricultural hub, food processing, commercial transit town",
        "best_niches": [
            "supermarkets",
            "pharmacies",
            "schools",
            "churches",
            "restaurants",
            "contractors",
            "bakeries",
        ],
        "avg_spending_power": "medium",
        "digital_adoption": "low_medium",
        "competition": "very_low",
        "language_notes": "Ika, English, Pidgin",
    },
    "Sapele": {
        "state": "Delta",
        "region": "South South",
        "population": "200K",
        "tier": 3,
        "economic_profile": "Port town, wood and rubber processing, agricultural trade, local market",
        "best_niches": [
            "restaurants",
            "hotels",
            "salons",
            "pharmacies",
            "contractors",
            "boutiques",
            "printing_press",
        ],
        "avg_spending_power": "medium",
        "digital_adoption": "medium",
        "competition": "low",
        "language_notes": "Urhobo, English, Pidgin",
    },
    "Nsukka": {
        "state": "Enugu",
        "region": "South East",
        "population": "300K",
        "tier": 3,
        "economic_profile": "Academic hub, major university town, agricultural trade",
        "best_niches": [
            "restaurants",
            "salons",
            "schools",
            "hotels",
            "pharmacies",
            "churches",
            "boutiques",
        ],
        "avg_spending_power": "medium",
        "digital_adoption": "medium",
        "competition": "very_low",
        "language_notes": "Igbo, English",
    },
    "Ogbomoso": {
        "state": "Oyo",
        "region": "South West",
        "population": "350K",
        "tier": 3,
        "economic_profile": "Agricultural hub, education center, university town, local commerce",
        "best_niches": [
            "restaurants",
            "schools",
            "pharmacies",
            "clinics",
            "salons",
            "bakeries",
            "event_centers",
        ],
        "avg_spending_power": "low_medium",
        "digital_adoption": "low_medium",
        "competition": "very_low",
        "language_notes": "Yoruba, English",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# CITY MANAGER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────
def get_city_config(city_name: str) -> dict:
    """Get full config for a city"""
    if city_name in NIGERIAN_CITIES:
        return NIGERIAN_CITIES[city_name]

    # Fuzzy match
    city_lower = city_name.lower()
    for city, config in NIGERIAN_CITIES.items():
        if city.lower() in city_lower or city_lower in city.lower():
            return config

    # Return a generic config for unknown cities
    return {
        "state": "Unknown",
        "region": "Nigeria",
        "population": "Unknown",
        "tier": 3,
        "economic_profile": "Local economy",
        "best_niches": ["restaurants", "salons", "pharmacies", "schools"],
        "avg_spending_power": "medium",
        "digital_adoption": "low",
        "competition": "low",
        "language_notes": "English, local language",
    }


def get_recommended_niches(city_name: str, limit: int = 5) -> list:
    """Get the top recommended niches for a city"""
    config = get_city_config(city_name)
    return config.get("best_niches", [])[:limit]


def get_city_strategy(city_name: str) -> dict:
    """Get full outreach strategy for a city"""
    config = get_city_config(city_name)
    from niche_manager import NICHES

    best_niches = config.get("best_niches", [])
    spending = config.get("avg_spending_power", "medium")
    adoption = config.get("digital_adoption", "medium")
    competition = config.get("competition", "medium")

    # Adjust pricing based on spending power
    price_multiplier = {
        "very_high": 1.5,
        "high": 1.2,
        "medium_high": 1.1,
        "medium": 1.0,
        "low_medium": 0.85,
        "low": 0.7,
    }.get(spending, 1.0)

    # Adjust daily limits based on competition
    volume_multiplier = {
        "very_high": 0.6,
        "high": 0.8,
        "medium": 1.0,
        "low": 1.2,
        "very_low": 1.5,
    }.get(competition, 1.0)

    niche_revenue = []
    for niche in best_niches:
        niche_cfg = NICHES.get(niche, {})
        niche_revenue.append(
            {
                "niche": niche,
                "label": niche_cfg.get("label", niche),
                "avg_deal_ngn": int(
                    niche_cfg.get("avg_deal_ngn", 200000) * price_multiplier
                ),
                "retainer_ngn": int(
                    niche_cfg.get("monthly_retainer_ngn", 60000) * price_multiplier
                ),
            }
        )

    return {
        "city": city_name,
        "state": config.get("state"),
        "tier": config.get("tier", 3),
        "recommended_niches": best_niches,
        "niche_revenue": niche_revenue,
        "price_multiplier": price_multiplier,
        "volume_multiplier": volume_multiplier,
        "suggested_daily_emails": int(50 * volume_multiplier),
        "suggested_daily_wa": int(30 * volume_multiplier),
        "key_channels": _get_key_channels(adoption),
        "language_approach": config.get("language_notes", "English"),
        "competition_level": competition,
        "digital_readiness": adoption,
    }


def _get_key_channels(adoption_level: str) -> list:
    """Get recommended channels based on digital adoption level"""
    if adoption_level in ["very_high", "high"]:
        return ["whatsapp", "instagram", "email", "facebook"]
    elif adoption_level == "medium":
        return ["whatsapp", "facebook", "email", "instagram"]
    else:
        return ["whatsapp", "phone_call", "facebook", "email"]


def get_expansion_roadmap(current_city: str) -> list:
    """Get recommended city expansion order"""
    current_config = get_city_config(current_city)
    current_tier = current_config.get("tier", 3)

    # Sort by tier and region proximity
    expansion = []
    for city, config in NIGERIAN_CITIES.items():
        if city == current_city:
            continue

        score = 0
        # Prefer same tier cities
        tier_diff = abs(config.get("tier", 3) - current_tier)
        score -= tier_diff * 2

        # Prefer higher spending power
        spending_scores = {
            "very_high": 5,
            "high": 4,
            "medium_high": 3,
            "medium": 2,
            "low_medium": 1,
            "low": 0,
        }
        score += spending_scores.get(config.get("avg_spending_power", "medium"), 2)

        # Prefer lower competition
        comp_scores = {"very_low": 4, "low": 3, "medium": 2, "high": 1, "very_high": 0}
        score += comp_scores.get(config.get("competition", "medium"), 2)

        expansion.append(
            {
                "city": city,
                "state": config.get("state"),
                "tier": config.get("tier"),
                "score": score,
                "why": f"Tier {config['tier']} city with {config['competition']} competition and {config['avg_spending_power']} spending power",
            }
        )

    expansion.sort(key=lambda x: x["score"], reverse=True)
    return expansion[:8]


def list_cities_by_tier() -> str:
    """Display all cities organized by tier"""
    output = f"\n{'='*60}\n"
    output += "  🌍 NIGERIAN CITY DATABASE\n"
    output += f"{'='*60}\n\n"

    for tier in [1, 2, 3]:
        tier_cities = {
            k: v for k, v in NIGERIAN_CITIES.items() if v.get("tier") == tier
        }
        tier_labels = {
            1: "Tier 1 — Major Cities",
            2: "Tier 2 — State Capitals",
            3: "Tier 3 — Growing Towns",
        }
        output += f"  {tier_labels[tier]}\n"
        output += f"  {'─'*56}\n"
        for city, cfg in tier_cities.items():
            output += f"  📍 {city} ({cfg['state']}) — {cfg['avg_spending_power']} spending, {cfg['competition']} competition\n"
        output += "\n"

    output += f"  Total cities: {len(NIGERIAN_CITIES)}\n"
    output += f"{'='*60}\n"
    return output


def update_config_for_city(city_name: str):
    """Update ceo_config.json with recommended settings for a city"""
    strategy = get_city_strategy(city_name)

    if os.path.exists("ceo_config.json"):
        with open("ceo_config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
    else:
        config = {}

    # Update city
    if "outreach" not in config:
        config["outreach"] = {}

    config["outreach"]["cities"] = [city_name]
    config["outreach"]["niches"] = strategy["recommended_niches"]

    # Respect lock_manual_limits (defaulting to True)
    lock_limits = config["outreach"].get("lock_manual_limits", True)

    if not lock_limits or "daily_email_limit" not in config["outreach"]:
        config["outreach"]["daily_email_limit"] = strategy["suggested_daily_emails"]
        print(f"   Daily email limit set to: {strategy['suggested_daily_emails']}")
    else:
        print(
            f"   🔒 Daily email limit preserved at: {config['outreach']['daily_email_limit']} (locked)"
        )

    if not lock_limits or "daily_whatsapp_limit" not in config["outreach"]:
        config["outreach"]["daily_whatsapp_limit"] = strategy["suggested_daily_wa"]
        print(f"   Daily WA limit set to: {strategy['suggested_daily_wa']}")
    else:
        print(
            f"   🔒 Daily WA limit preserved at: {config['outreach']['daily_whatsapp_limit']} (locked)"
        )

    with open("ceo_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"✅ Config updated for {city_name}")
    print(f"   Best niches: {', '.join(strategy['recommended_niches'])}")


if __name__ == "__main__":
    import sys

    if "--list" in sys.argv:
        print(list_cities_by_tier())
    elif "--strategy" in sys.argv:
        city = sys.argv[sys.argv.index("--strategy") + 1]
        strategy = get_city_strategy(city)
        print(json.dumps(strategy, indent=2))
    elif "--expand" in sys.argv:
        city = sys.argv[sys.argv.index("--expand") + 1]
        roadmap = get_expansion_roadmap(city)
        print(f"\n🗺️  Expansion roadmap from {city}:\n")
        for i, city_data in enumerate(roadmap, 1):
            print(
                f"  {i}. {city_data['city']} ({city_data['state']}) — {city_data['why']}"
            )
    else:
        print(list_cities_by_tier())
