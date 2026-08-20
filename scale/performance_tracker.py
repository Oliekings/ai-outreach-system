import json
import os
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
import sys
sys.stdout.reconfigure(encoding='utf-8')

os.makedirs("results/analytics", exist_ok=True)


def load_all_data() -> dict:
    """Load all system data for analysis"""
    data = {}

    files = {
        "leads": "results/leads/enriched_leads.json",
        "email_log": "results/logs/send_log.json",
        "wa_log": "results/logs/whatsapp_log.json",
        "ig_log": "results/logs/instagram_log.json",
        "fb_log": "results/logs/facebook_log.json",
        "reply_log": "results/replies/reply_log.json",
        "config": "ceo_config.json"
    }

    for key, path in files.items():
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data[key] = json.load(f)
        else:
            data[key] = {} if key != "leads" else []

    return data


# ─────────────────────────────────────────────────────────────────────────────
# METRIC CALCULATORS
# ─────────────────────────────────────────────────────────────────────────────
def calculate_channel_metrics(data: dict) -> dict:
    """Calculate performance metrics per channel"""
    metrics = {}

    channel_map = {
        "email": ("email_log", "emails"),
        "whatsapp": ("wa_log", "messages"),
        "instagram": ("ig_log", "messages"),
        "facebook": ("fb_log", "messages")
    }

    for channel, (log_key, entries_key) in channel_map.items():
        log = data.get(log_key, {})
        entries = log.get(entries_key, [])

        total = len(entries)
        successful = sum(1 for e in entries if e.get("success"))
        failed = sum(1 for e in entries if not e.get("success"))

        # Today's metrics
        today = datetime.now().strftime("%Y-%m-%d")
        today_entries = [e for e in entries if e.get("date", "").startswith(today)]
        today_sent = sum(1 for e in today_entries if e.get("success"))

        # This week
        week_start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        week_entries = [e for e in entries if e.get("date", "") >= week_start]
        week_sent = sum(1 for e in week_entries if e.get("success"))

        metrics[channel] = {
            "total_sent": successful,
            "total_failed": failed,
            "total_attempts": total,
            "success_rate": round((successful / max(total, 1)) * 100, 1),
            "today_sent": today_sent,
            "week_sent": week_sent,
            "last_sent": entries[-1].get("date") if entries else None
        }

    return metrics


def calculate_reply_metrics(data: dict) -> dict:
    """Calculate reply and conversion metrics"""
    reply_log = data.get("reply_log", {})
    replies = reply_log.get("replies", [])

    total = len(replies)
    by_intent = {}
    for reply in replies:
        intent = reply.get("classification", {}).get("intent", "unknown")
        by_intent[intent] = by_intent.get(intent, 0) + 1

    by_status = {}
    for reply in replies:
        status = reply.get("status", "unknown")
        by_status[status] = by_status.get(status, 0) + 1

    # Calculate total messages sent for reply rate
    total_sent = 0
    for log_key, entries_key in [
        ("email_log", "emails"), ("wa_log", "messages"),
        ("ig_log", "messages"), ("fb_log", "messages")
    ]:
        log = data.get(log_key, {})
        entries = log.get(entries_key, [])
        total_sent += sum(1 for e in entries if e.get("success"))

    return {
        "total_replies": total,
        "reply_rate_pct": round((total / max(total_sent, 1)) * 100, 2),
        "by_intent": by_intent,
        "by_status": by_status,
        "interested_count": by_intent.get("interested", 0),
        "interest_rate_pct": round((by_intent.get("interested", 0) / max(total_sent, 1)) * 100, 2),
        "pending_review": by_status.get("pending_review", 0),
        "replied": by_status.get("replied", 0)
    }


def calculate_lead_metrics(data: dict) -> dict:
    """Calculate lead pipeline metrics"""
    leads = data.get("leads", [])
    if not isinstance(leads, list):
        leads = []

    total = len(leads)
    enriched = 0
    with_email = 0
    with_wa = 0
    with_ig = 0
    with_fb = 0
    site_built = 0

    by_status = {}
    by_niche = {}
    by_city = {}
    scores = []

    # O(N) Single pass to calculate metrics (Performance optimization)
    for lead in leads:
        if lead.get("enriched"): enriched += 1
        if lead.get("contact_email"): with_email += 1
        if lead.get("contact_whatsapp"): with_wa += 1
        if lead.get("instagram", {}).get("found"): with_ig += 1
        if lead.get("facebook", {}).get("found"): with_fb += 1
        if lead.get("site_built"): site_built += 1

        status = lead.get("status", "active")
        by_status[status] = by_status.get(status, 0) + 1

        niche = lead.get("niche", "unknown")
        by_niche[niche] = by_niche.get(niche, 0) + 1

        city = lead.get("city", "unknown")
        by_city[city] = by_city.get(city, 0) + 1

        score_str = lead.get("enrichment_score", "0/8")
        try:
            scores.append(int(score_str.split("/")[0]))
        except:
            scores.append(0)

    avg_score = round(sum(scores) / max(len(scores), 1), 1)

    return {
        "total": total,
        "enriched": enriched,
        "enrichment_rate": round((enriched / max(total, 1)) * 100, 1),
        "with_email": with_email,
        "with_whatsapp": with_wa,
        "with_instagram": with_ig,
        "with_facebook": with_fb,
        "site_built": site_built,
        "avg_enrichment_score": avg_score,
        "by_status": by_status,
        "by_niche": by_niche,
        "by_city": by_city,
        "contactable": min(with_email, with_wa)
    }


def calculate_revenue_metrics(data: dict) -> dict:
    """Calculate revenue pipeline metrics"""
    try:
        from scale.niche_manager import NICHES
    except ImportError:
        from niche_manager import NICHES

    leads = data.get("leads", [])
    config = data.get("config", {})
    services = config.get("services", {})

    basic_price = services.get("basic_website_ngn", 150000)
    full_price = services.get("full_package_ngn", 450000)
    retainer_price = services.get("monthly_retainer_ngn", 75000)

    interested = [l for l in leads if l.get("status") == "interested"]
    closed = [l for l in leads if l.get("status") == "closed"]

    # Pipeline value calculation
    pipeline_value = 0
    for lead in interested:
        niche = lead.get("niche", "")
        niche_cfg = NICHES.get(niche, {})
        pipeline_value += niche_cfg.get("avg_deal_ngn", full_price)

    # Actual revenue
    actual_revenue = sum(l.get("deal_value_ngn", 0) for l in closed)

    # Projected monthly retainer
    projected_retainer = len(closed) * retainer_price

    return {
        "pipeline_value_ngn": pipeline_value,
        "actual_revenue_ngn": actual_revenue,
        "monthly_retainer_ngn": projected_retainer,
        "annual_projected_ngn": actual_revenue + (projected_retainer * 12),
        "interested_leads": len(interested),
        "closed_deals": len(closed),
        "avg_deal_size_ngn": int(pipeline_value / max(len(interested), 1)),
        "close_rate_pct": round((len(closed) / max(len(leads), 1)) * 100, 2)
    }


def calculate_daily_trend(data: dict, days: int = 7) -> list:
    """Calculate daily send/reply trends"""
    trend = []
    today = datetime.now()

    for i in range(days - 1, -1, -1):
        day = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        day_label = (today - timedelta(days=i)).strftime("%a %d")

        day_data = {"date": day, "label": day_label}

        # Messages sent per channel
        for channel, log_key, entries_key in [
            ("email", "email_log", "emails"),
            ("whatsapp", "wa_log", "messages"),
            ("instagram", "ig_log", "messages"),
            ("facebook", "fb_log", "messages")
        ]:
            log = data.get(log_key, {})
            entries = log.get(entries_key, [])
            day_sent = sum(
                1 for e in entries
                if e.get("date", "").startswith(day) and e.get("success")
            )
            day_data[channel] = day_sent

        # Replies
        reply_log = data.get("reply_log", {})
        day_replies = sum(
            1 for r in reply_log.get("replies", [])
            if r.get("date_received", "").startswith(day)
        )
        day_data["replies"] = day_replies

        day_data["total"] = sum(
            day_data.get(ch, 0) for ch in ["email", "whatsapp", "instagram", "facebook"]
        )

        trend.append(day_data)

    return trend


# ─────────────────────────────────────────────────────────────────────────────
# FULL PERFORMANCE REPORT
# ─────────────────────────────────────────────────────────────────────────────
def generate_performance_report(save: bool = True) -> str:
    data = load_all_data()

    channel_metrics = calculate_channel_metrics(data)
    reply_metrics = calculate_reply_metrics(data)
    lead_metrics = calculate_lead_metrics(data)
    revenue_metrics = calculate_revenue_metrics(data)
    daily_trend = calculate_daily_trend(data, days=7)

    now = datetime.now()
    line = "━" * 58

    report = f"""
╔{'═'*58}╗
║  📈 PERFORMANCE TRACKER REPORT                           ║
║  {now.strftime('%A, %d %B %Y — %I:%M %p'):<54}  ║
╚{'═'*58}╝

  🎯 LEAD PIPELINE
  {line}
  Total Leads:          {lead_metrics['total']}
  Enriched:             {lead_metrics['enriched']} ({lead_metrics['enrichment_rate']}%)
  With Email:           {lead_metrics['with_email']}
  With WhatsApp:        {lead_metrics['with_whatsapp']}
  With Instagram:       {lead_metrics['with_instagram']}
  With Facebook:        {lead_metrics['with_facebook']}
  Site Built:           {lead_metrics['site_built']}
  Avg Enrichment Score: {lead_metrics['avg_enrichment_score']}/8

  📤 OUTREACH PERFORMANCE
  {line}
  {'Channel':<14} {'Sent':>8} {'Today':>8} {'Week':>8} {'Rate':>8}
  {'─'*56}"""

    for channel, metrics in channel_metrics.items():
        report += f"\n  {channel.title():<14} {metrics['total_sent']:>8} {metrics['today_sent']:>8} {metrics['week_sent']:>8} {metrics['success_rate']:>7}%"

    total_all = sum(m["total_sent"] for m in channel_metrics.values())
    today_all = sum(m["today_sent"] for m in channel_metrics.values())
    week_all = sum(m["week_sent"] for m in channel_metrics.values())
    report += f"\n  {'TOTAL':<14} {total_all:>8} {today_all:>8} {week_all:>8}"

    report += f"""

  💬 REPLY ANALYSIS
  {line}
  Total Replies:      {reply_metrics['total_replies']}
  Reply Rate:         {reply_metrics['reply_rate_pct']}%
  Interested:         {reply_metrics.get('interested_count', 0)} 🔥 ({reply_metrics['interest_rate_pct']}%)
  Pending Review:     {reply_metrics.get('pending_review', 0)}
  Already Replied:    {reply_metrics.get('replied', 0)}

  By Intent:"""

    for intent, count in reply_metrics.get("by_intent", {}).items():
        icon = {"interested": "🔥", "not_interested": "❌", "question": "❓", "out_of_office": "📅"}.get(intent, "•")
        report += f"\n    {icon} {intent}: {count}"

    report += f"""

  💰 REVENUE PIPELINE
  {line}
  Pipeline Value:     ₦{revenue_metrics['pipeline_value_ngn']:,}
  Actual Revenue:     ₦{revenue_metrics['actual_revenue_ngn']:,}
  Monthly Retainer:   ₦{revenue_metrics['monthly_retainer_ngn']:,}
  Annual Projected:   ₦{revenue_metrics['annual_projected_ngn']:,}
  Interested Leads:   {revenue_metrics['interested_leads']}
  Closed Deals:       {revenue_metrics['closed_deals']}
  Avg Deal Size:      ₦{revenue_metrics['avg_deal_size_ngn']:,}
  Close Rate:         {revenue_metrics['close_rate_pct']}%

  📅 7-DAY TREND
  {line}
  {'Date':<12} {'Email':>7} {'WA':>7} {'IG':>7} {'FB':>7} {'Reply':>7} {'Total':>7}
  {'─'*56}"""

    for day in daily_trend:
        report += f"\n  {day['label']:<12} {day.get('email', 0):>7} {day.get('whatsapp', 0):>7} {day.get('instagram', 0):>7} {day.get('facebook', 0):>7} {day.get('replies', 0):>7} {day.get('total', 0):>7}"

    report += f"""

  🏆 TOP NICHES
  {line}"""

    for niche, count in sorted(lead_metrics["by_niche"].items(), key=lambda x: x[1], reverse=True)[:5]:
        report += f"\n  • {niche}: {count} leads"

    report += f"""

  🌍 TOP CITIES
  {line}"""

    for city, count in sorted(lead_metrics["by_city"].items(), key=lambda x: x[1], reverse=True)[:5]:
        report += f"\n  • {city}: {count} leads"

    report += f"\n\n{'═'*60}\n"

    if save:
        timestamp = now.strftime("%Y%m%d_%H%M")
        report_path = f"results/analytics/performance_{timestamp}.txt"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        # Save JSON snapshot
        snapshot = {
            "timestamp": now.isoformat(),
            "channel_metrics": channel_metrics,
            "reply_metrics": reply_metrics,
            "lead_metrics": lead_metrics,
            "revenue_metrics": revenue_metrics,
            "daily_trend": daily_trend
        }
        json_path = f"results/analytics/snapshot_{timestamp}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)

        print(f"   💾 Report saved: {report_path}")

    return report


if __name__ == "__main__":
    import sys

    if "--campaign" in sys.argv:
        try:
            from scale.campaign_manager import get_active_campaign, generate_campaign_report
        except ImportError:
            from campaign_manager import get_active_campaign, generate_campaign_report
        campaign = get_active_campaign()
        if campaign:
            print(generate_campaign_report(campaign["id"]))
        else:
            print("No active campaign")
    else:
        print(generate_performance_report(save=True))