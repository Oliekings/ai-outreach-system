import json
import os
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

os.makedirs("results/campaigns", exist_ok=True)


def load_config() -> dict:
    with open("ceo_config.json", "r", encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────────────
# CAMPAIGN MANAGER
# ─────────────────────────────────────────────────────────────────────────────
def create_campaign(
    name: str,
    city: str,
    niches: list,
    daily_lead_target: int = 10,
    duration_days: int = 30,
    notes: str = ""
) -> dict:
    """Create a new outreach campaign"""
    try:
        from scale.city_manager import get_city_strategy
        from scale.niche_manager import get_niche_revenue_estimate
    except ImportError:
        from city_manager import get_city_strategy
        from niche_manager import get_niche_revenue_estimate

    campaign_id = f"campaign_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    strategy = get_city_strategy(city)

    # Revenue projections
    total_leads = daily_lead_target * duration_days
    revenue_projections = []
    for niche in niches:
        leads_per_niche = total_leads // len(niches)
        rev = get_niche_revenue_estimate(niche, leads_per_niche)
        revenue_projections.append(rev)

    total_projected_revenue = sum(r["one_time_revenue_ngn"] for r in revenue_projections)
    total_projected_retainer = sum(r["monthly_retainer_ngn"] for r in revenue_projections)

    campaign = {
        "id": campaign_id,
        "name": name,
        "city": city,
        "niches": niches,
        "status": "active",
        "created_at": datetime.now().isoformat(),
        "start_date": datetime.now().strftime("%Y-%m-%d"),
        "end_date": (datetime.now() + timedelta(days=duration_days)).strftime("%Y-%m-%d"),
        "duration_days": duration_days,
        "targets": {
            "daily_leads": daily_lead_target,
            "total_leads": total_leads,
            "conversion_rate_target": 5.0,
            "clients_target": max(1, int(total_leads * 0.05))
        },
        "actual": {
            "leads_found": 0,
            "leads_enriched": 0,
            "messages_sent": 0,
            "replies_received": 0,
            "interested_leads": 0,
            "clients_closed": 0,
            "revenue_ngn": 0
        },
        "revenue_projections": {
            "one_time_ngn": total_projected_revenue,
            "monthly_retainer_ngn": total_projected_retainer,
            "annual_ngn": total_projected_revenue + (total_projected_retainer * 12),
            "by_niche": revenue_projections
        },
        "city_strategy": strategy,
        "notes": notes
    }

    # Save campaign
    campaign_path = f"results/campaigns/{campaign_id}.json"
    with open(campaign_path, "w", encoding="utf-8") as f:
        json.dump(campaign, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Campaign created: {name}")
    print(f"   ID: {campaign_id}")
    print(f"   City: {city}")
    print(f"   Niches: {', '.join(niches)}")
    print(f"   Duration: {duration_days} days")
    print(f"   Lead target: {total_leads} total")
    print(f"   Revenue projection: ₦{total_projected_revenue:,} one-time + ₦{total_projected_retainer:,}/mo retainer")

    # Update ceo_config.json
    _update_config_for_campaign(campaign)

    return campaign


def _update_config_for_campaign(campaign: dict):
    """Update ceo_config.json to match campaign settings"""
    config = load_config()
    config["outreach"]["cities"] = [campaign["city"]]
    config["outreach"]["niches"] = campaign["niches"]
    config["active_campaign"] = campaign["id"]

    with open("ceo_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_active_campaign() -> dict:
    """Get the currently active campaign"""
    config = load_config()
    active_id = config.get("active_campaign")

    if not active_id:
        # Find most recent active campaign
        campaigns = list_campaigns()
        active = [c for c in campaigns if c.get("status") == "active"]
        if active:
            return active[0]
        return {}

    path = f"results/campaigns/{active_id}.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    return {}


def list_campaigns() -> list:
    """List all campaigns"""
    campaigns = []
    if not os.path.exists("results/campaigns"):
        return campaigns

    for fname in os.listdir("results/campaigns"):
        if fname.endswith(".json") and not fname.endswith("_report.json"):
            path = os.path.join("results/campaigns", fname)
            with open(path, "r", encoding="utf-8") as f:
                campaigns.append(json.load(f))

    campaigns.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return campaigns


def update_campaign_actuals(campaign_id: str):
    """Update campaign actual metrics from current results"""
    path = f"results/campaigns/{campaign_id}.json"
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as f:
        campaign = json.load(f)

    # Count leads
    leads = []
    enriched_file = "results/leads/enriched_leads.json"
    if os.path.exists(enriched_file):
        with open(enriched_file, "r", encoding="utf-8") as f:
            leads = json.load(f)

    campaign["actual"]["leads_found"] = len(leads)
    campaign["actual"]["leads_enriched"] = len([l for l in leads if l.get("enriched")])
    campaign["actual"]["interested_leads"] = len([l for l in leads if l.get("status") == "interested"])

    # Count messages
    total_sent = 0
    for log_file in [
        "results/logs/send_log.json",
        "results/logs/whatsapp_log.json",
        "results/logs/instagram_log.json",
        "results/logs/facebook_log.json"
    ]:
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8") as f:
                log = json.load(f)
            entries = log.get("emails", log.get("messages", []))
            total_sent += sum(1 for e in entries if e.get("success"))

    campaign["actual"]["messages_sent"] = total_sent

    # Count replies
    reply_file = "results/replies/reply_log.json"
    if os.path.exists(reply_file):
        with open(reply_file, "r", encoding="utf-8") as f:
            reply_log = json.load(f)
        campaign["actual"]["replies_received"] = len(reply_log.get("replies", []))

    campaign["last_updated"] = datetime.now().isoformat()

    with open(path, "w", encoding="utf-8") as f:
        json.dump(campaign, f, indent=2, ensure_ascii=False)

    return campaign


def generate_campaign_report(campaign_id: str) -> str:
    """Generate a detailed campaign performance report"""
    campaign = update_campaign_actuals(campaign_id)
    if not campaign:
        return "Campaign not found"

    actual = campaign.get("actual", {})
    targets = campaign.get("targets", {})
    projections = campaign.get("revenue_projections", {})

    # Calculate performance metrics
    leads_found = actual.get("leads_found", 0)
    leads_target = targets.get("total_leads", 1)
    lead_pct = min(100, int((leads_found / max(leads_target, 1)) * 100))

    messages_sent = actual.get("messages_sent", 0)
    replies = actual.get("replies_received", 0)
    interested = actual.get("interested_leads", 0)
    reply_rate = round((replies / max(messages_sent, 1)) * 100, 1)
    interest_rate = round((interested / max(messages_sent, 1)) * 100, 1)

    # Days remaining
    end_date = datetime.strptime(campaign.get("end_date", ""), "%Y-%m-%d")
    days_remaining = max(0, (end_date - datetime.now()).days)
    days_elapsed = campaign.get("duration_days", 30) - days_remaining

    report = f"""
╔{'═'*58}╗
║  📊 CAMPAIGN REPORT                                      ║
║  {campaign['name'][:54]:<54}  ║
║  ID: {campaign_id[:52]:<52}  ║
╚{'═'*58}╝

  📍 CAMPAIGN OVERVIEW
  {'─'*56}
  City:          {campaign['city']}
  Niches:        {', '.join(campaign['niches'])}
  Status:        {campaign['status'].upper()}
  Duration:      {days_elapsed}/{campaign['duration_days']} days elapsed
  Days Left:     {days_remaining}
  Start Date:    {campaign['start_date']}
  End Date:      {campaign['end_date']}

  🎯 LEAD PIPELINE
  {'─'*56}
  Leads Found:   {leads_found} / {leads_target} target ({lead_pct}%)
  Enriched:      {actual.get('leads_enriched', 0)}
  Interested:    {actual.get('interested_leads', 0)} 🔥
  Clients:       {actual.get('clients_closed', 0)}

  📤 OUTREACH PERFORMANCE
  {'─'*56}
  Messages Sent:   {messages_sent}
  Replies:         {replies} ({reply_rate}% reply rate)
  Interested:      {interested} ({interest_rate}% interest rate)

  💰 REVENUE
  {'─'*56}
  Projected One-Time:  ₦{projections.get('one_time_ngn', 0):,}
  Projected Retainer:  ₦{projections.get('monthly_retainer_ngn', 0):,}/mo
  Projected Annual:    ₦{projections.get('annual_ngn', 0):,}
  Actual Revenue:      ₦{actual.get('revenue_ngn', 0):,}

  📝 NOTES
  {'─'*56}
  {campaign.get('notes', 'No notes')}

{'═'*60}
"""
    # Save report
    report_path = f"results/campaigns/{campaign_id}_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    return report


def pause_campaign(campaign_id: str):
    path = f"results/campaigns/{campaign_id}.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            campaign = json.load(f)
        campaign["status"] = "paused"
        campaign["paused_at"] = datetime.now().isoformat()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(campaign, f, indent=2, ensure_ascii=False)
        print(f"⏸️  Campaign paused: {campaign['name']}")


def resume_campaign(campaign_id: str):
    path = f"results/campaigns/{campaign_id}.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            campaign = json.load(f)
        campaign["status"] = "active"
        campaign["resumed_at"] = datetime.now().isoformat()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(campaign, f, indent=2, ensure_ascii=False)
        _update_config_for_campaign(campaign)
        print(f"▶️  Campaign resumed: {campaign['name']}")


if __name__ == "__main__":
    import sys

    if "--create" in sys.argv:
        campaign = create_campaign(
            name="Uromi Restaurant Test Campaign",
            city="Uromi",
            niches=["restaurants", "salons", "pharmacies"],
            daily_lead_target=10,
            duration_days=30,
            notes="Test campaign for system validation"
        )

    elif "--list" in sys.argv:
        campaigns = list_campaigns()
        print(f"\n📋 {len(campaigns)} campaigns\n")
        for c in campaigns:
            actual = c.get("actual", {})
            print(f"  {'▶' if c['status'] == 'active' else '⏸'} {c['name']}")
            print(f"     {c['city']} | {', '.join(c['niches'])}")
            print(f"     Leads: {actual.get('leads_found', 0)} | Sent: {actual.get('messages_sent', 0)} | Interested: {actual.get('interested_leads', 0)}")
            print()

    elif "--report" in sys.argv:
        campaign_id = sys.argv[sys.argv.index("--report") + 1]
        print(generate_campaign_report(campaign_id))

    else:
        campaigns = list_campaigns()
        if campaigns:
            active = [c for c in campaigns if c["status"] == "active"]
            print(f"\n✅ {len(active)} active campaigns | {len(campaigns)} total")
        else:
            print("\n📋 No campaigns yet. Run with --create to create one.")