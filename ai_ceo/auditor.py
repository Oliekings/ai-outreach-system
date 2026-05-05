import json
import os
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from anthropic import Anthropic
from groq import Groq

load_dotenv()


def get_ai_response(prompt: str, max_tokens: int = 2000) -> str:
    try:
        claude = Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
        response = claude.messages.create(
            model="claude-opus-4-5",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        if True: # Fallback on any error
            groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
            response = groq.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        raise e


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


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# PERFORMANCE AUDITOR
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def run_daily_audit(state: dict) -> dict:
    """
    The AI CEO runs a full daily audit of the entire system.
    Produces insights, warnings, and action recommendations.
    """

    prompt = f"""
You are the AI CEO auditing your digital outreach agency's performance.
Be direct, specific, and actionable. Think like a real CEO reviewing KPIs.

SYSTEM DATA:
{json.dumps(state, indent=2)}

Perform a thorough audit across all dimensions:

1. LEAD PIPELINE HEALTH
   - Are we generating enough leads?
   - Is enrichment quality high enough?
   - How many are contactable?

2. OUTREACH EFFECTIVENESS
   - Which channel has best performance?
   - Are we hitting our daily limits?
   - Any channels to pause or increase?

3. REPLY & CONVERSION ANALYSIS
   - What is our reply rate?
   - What is our interest rate?
   - Are we following up on interested leads fast enough?

4. REVENUE PIPELINE
   - How many interested leads?
   - Estimated pipeline value?
   - What actions would close deals fastest?

5. SYSTEM HEALTH
   - Any errors or failures to address?
   - Any optimizations needed?

Return ONLY valid JSON:
{{
  "overall_health": "excellent" or "good" or "fair" or "poor" or "critical",
  "health_score": 0-100,
  "kpis": {{
    "leads_in_pipeline": 0,
    "reply_rate_pct": 0.0,
    "interest_rate_pct": 0.0,
    "estimated_pipeline_value_ngn": 0,
    "days_to_first_client_estimate": 0
  }},
  "winning_channel": "email or whatsapp or instagram or facebook",
  "underperforming_channel": "channel name or null",
  "critical_issues": ["list of urgent problems"],
  "opportunities": ["list of quick wins"],
  "today_priorities": ["top 3 things to do today in order"],
  "weekly_targets": ["3 targets for this week"],
  "ceo_message": "2-3 sentence honest CEO assessment of where things stand and what matters most",
  "hire_signal": "yes, consider hiring delivery help" or "no, too early"
}}
"""

    try:
        response = get_ai_response(prompt, max_tokens=2000)
        result = safe_json(response)
        if result:
            return result
    except Exception as e:
        print(f"   âš ï¸  Audit AI failed: {e}")

    return {
        "overall_health": "unknown",
        "health_score": 50,
        "kpis": {},
        "critical_issues": ["Audit system unavailable â€” check manually"],
        "opportunities": [],
        "today_priorities": ["Run reply_monitor.py", "Check leads pipeline", "Review messages"],
        "ceo_message": "System audit unavailable. Run manually.",
        "hire_signal": "no"
    }


def generate_audit_report(audit_result: dict, state: dict) -> str:
    """Generate a beautiful text audit report"""
    now = datetime.now()
    health = audit_result.get("overall_health", "unknown")
    score = audit_result.get("health_score", 0)
    kpis = audit_result.get("kpis", {})

    health_icon = {
        "excellent": "ðŸŸ¢", "good": "ðŸŸ¢",
        "fair": "ðŸŸ¡", "poor": "ðŸŸ ", "critical": "ðŸ”´"
    }.get(health, "âšª")

    line = "â”" * 56

    report = f"""
â•”{'â•'*56}â•—
â•‘  ðŸ¤– AI CEO DAILY AUDIT REPORT                        â•‘
â•‘  {now.strftime('%A, %d %B %Y â€” %I:%M %p'):<52}  â•‘
â•š{'â•'*56}â•

{line}
  OVERALL HEALTH: {health_icon} {health.upper()} ({score}/100)
{line}

  ðŸ“Š KEY METRICS
  {line}
  Leads in pipeline:       {kpis.get('leads_in_pipeline', state['leads'].get('total', 0))}
  Contactable leads:       {state['leads'].get('with_email', 0)} email / {state['leads'].get('with_whatsapp', 0)} WhatsApp
  Interested leads:        {state['leads'].get('interested', 0)} ðŸ”¥
  Total messages sent:     {state['performance'].get('total_messages_sent', 0)}
  Reply rate:              {state['performance'].get('reply_rate', 0)}%
  Interest rate:           {state['performance'].get('interest_rate', 0)}%
  Est. pipeline value:     â‚¦{kpis.get('estimated_pipeline_value_ngn', 0):,}
  Est. days to 1st client: {kpis.get('days_to_first_client_estimate', 'Unknown')}

  ðŸ“º CHANNEL PERFORMANCE
  {line}
  Email:     {state['outreach'].get('email', {}).get('total_sent', 0)} sent total
  WhatsApp:  {state['outreach'].get('whatsapp', {}).get('total_sent', 0)} sent total
  Instagram: {state['outreach'].get('instagram', {}).get('total_sent', 0)} sent total
  Facebook:  {state['outreach'].get('facebook', {}).get('total_sent', 0)} sent total
  Best channel: {(audit_result.get('winning_channel') or 'Unknown').upper()}
"""

    if audit_result.get("critical_issues"):
        report += f"\n  ðŸ”´ CRITICAL ISSUES\n  {line}\n"
        for issue in audit_result["critical_issues"]:
            report += f"  âœ— {issue}\n"

    if audit_result.get("opportunities"):
        report += f"\n  âœ… OPPORTUNITIES\n  {line}\n"
        for opp in audit_result["opportunities"]:
            report += f"  â†’ {opp}\n"

    if audit_result.get("today_priorities"):
        report += f"\n  ðŸŽ¯ TODAY'S PRIORITIES\n  {line}\n"
        for i, priority in enumerate(audit_result["today_priorities"], 1):
            report += f"  {i}. {priority}\n"

    if audit_result.get("weekly_targets"):
        report += f"\n  ðŸ“… THIS WEEK'S TARGETS\n  {line}\n"
        for target in audit_result["weekly_targets"]:
            report += f"  â€¢ {target}\n"

    ceo_msg = audit_result.get("ceo_message", "")
    if ceo_msg:
        report += f"\n  ðŸ’¼ CEO MESSAGE\n  {line}\n"
        # Word wrap at 54 chars
        words = ceo_msg.split()
        line_text = "  "
        for word in words:
            if len(line_text) + len(word) + 1 > 56:
                report += line_text + "\n"
                line_text = "  " + word + " "
            else:
                line_text += word + " "
        report += line_text + "\n"

    hire_signal = audit_result.get("hire_signal", "no")
    if hire_signal and "yes" in hire_signal.lower():
        report += f"\n  ðŸ‘¥ HIRING SIGNAL: {hire_signal}\n"

    report += f"\n{'â•'*58}\n"
    return report


def save_audit(audit_result: dict, report_text: str):
    """Save audit results and report"""
    os.makedirs("results/ceo", exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")

    # Save JSON
    with open(f"results/ceo/audit_{today}.json", "w") as f:
        json.dump(audit_result, f, indent=2)

    # Save text report
    with open(f"results/ceo/audit_{today}.txt", "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"   ðŸ’¾ Audit saved: results/ceo/audit_{today}.txt")
