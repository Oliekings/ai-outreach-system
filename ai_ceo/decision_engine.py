import json
import os
import re
import subprocess
from datetime import datetime
from dotenv import load_dotenv
from anthropic import Anthropic
from groq import Groq

load_dotenv()


def get_ai_response(prompt: str, max_tokens: int = 1500) -> str:
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


def load_config() -> dict:
    with open("ceo_config.json", "r") as f:
        return json.load(f)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# SYSTEM STATE READER
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def read_full_system_state() -> dict:
    state = {
        "timestamp": datetime.now().isoformat(),
        "leads": {},
        "outreach": {},
        "replies": {},
        "performance": {}
    }

    # Leads state
    enriched_file = "results/leads/enriched_leads.json"
    if os.path.exists(enriched_file):
        with open(enriched_file, "r") as f:
            leads = json.load(f)

        state["leads"] = {
            "total": len(leads),
            "enriched": len([l for l in leads if l.get("enriched")]),
            "with_email": len([l for l in leads if l.get("contact_email")]),
            "with_whatsapp": len([l for l in leads if l.get("contact_whatsapp")]),
            "interested": len([l for l in leads if l.get("status") == "interested"]),
            "not_interested": len([l for l in leads if l.get("status") == "not_interested"]),
            "site_built": len([l for l in leads if l.get("site_built")]),
            "average_score": _avg_enrichment_score(leads)
        }

    # Outreach state
    log_files = {
        "email": "results/logs/send_log.json",
        "whatsapp": "results/logs/whatsapp_log.json",
        "instagram": "results/logs/instagram_log.json",
        "facebook": "results/logs/facebook_log.json"
    }

    today = datetime.now().strftime("%Y-%m-%d")
    for channel, path in log_files.items():
        if os.path.exists(path):
            with open(path, "r") as f:
                log = json.load(f)

            entries = log.get(
                "emails" if channel == "email" else "messages", []
            )
            state["outreach"][channel] = {
                "total_sent": sum(1 for e in entries if e.get("success")),
                "sent_today": sum(
                    1 for e in entries
                    if e.get("date", "").startswith(today) and e.get("success")
                ),
                "failed": sum(1 for e in entries if not e.get("success")),
                "stats": log.get("stats", {})
            }

    # Reply state
    reply_file = "results/replies/reply_log.json"
    if os.path.exists(reply_file):
        with open(reply_file, "r") as f:
            reply_log = json.load(f)

        replies = reply_log.get("replies", [])
        state["replies"] = {
            "total": len(replies),
            "interested": len([r for r in replies if r.get("classification", {}).get("intent") == "interested"]),
            "not_interested": len([r for r in replies if r.get("classification", {}).get("intent") == "not_interested"]),
            "questions": len([r for r in replies if r.get("classification", {}).get("intent") == "question"]),
            "pending_review": len([r for r in replies if r.get("status") == "pending_review"]),
            "ready_to_send": len([r for r in replies if r.get("status") == "ready_to_send"]),
            "replied": len([r for r in replies if r.get("status") == "replied"])
        }

    # Performance metrics
    total_sent = sum(
        state["outreach"].get(ch, {}).get("total_sent", 0)
        for ch in ["email", "whatsapp", "instagram", "facebook"]
    )
    total_replies = state["replies"].get("total", 0)
    total_interested = state["replies"].get("interested", 0)

    state["performance"] = {
        "total_messages_sent": total_sent,
        "reply_rate": round(total_replies / max(total_sent, 1) * 100, 1),
        "interest_rate": round(total_interested / max(total_sent, 1) * 100, 1),
        "conversion_rate": round(
            state["leads"].get("interested", 0) / max(state["leads"].get("total", 1), 1) * 100, 1
        )
    }

    return state


def _avg_enrichment_score(leads: list) -> float:
    scores = []
    for l in leads:
        score_str = l.get("enrichment_score", "0/8")
        try:
            num = int(score_str.split("/")[0])
            scores.append(num)
        except:
            pass
    return round(sum(scores) / max(len(scores), 1), 1)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# AI DECISION MAKER
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def make_autonomous_decisions(state: dict, schedule: dict, config: dict) -> dict:
    """
    The AI CEO reads the full system state and makes autonomous decisions.
    This runs when human review deadline has passed.
    """

    prompt = f"""
You are the AI CEO of an automated digital outreach agency in Nigeria.
Your job is to make smart business decisions based on current system state.

CURRENT SYSTEM STATE:
{json.dumps(state, indent=2)}

TODAY'S SCHEDULE:
{json.dumps(schedule.get('tasks', []), indent=2)}

BUSINESS CONFIG:
- Daily email limit: {config['outreach']['daily_email_limit']}
- Daily WhatsApp limit: {config['outreach']['daily_whatsapp_limit']}
- Autonomous fallback enabled: {config['owner']['autonomous_fallback']}
- Min score to auto-send: {config['owner']['autonomous_min_score']}

Make decisions for today. Consider:
1. Which tasks are most urgent and should run first?
2. Should we pause any channels that are underperforming?
3. Do we need more leads? (run lead finder?)
4. Are there interested leads that urgently need replies?
5. What is the best use of today's send limits?
6. Any risks or issues to flag?

Return ONLY valid JSON:
{{
  "decisions": [
    {{
      "action": "run_command or pause_channel or alert_owner or skip",
      "command": "python command to run if applicable",
      "reason": "why this decision was made",
      "priority": 1-10,
      "autonomous": true or false
    }}
  ],
  "alerts": ["any urgent issues to flag to owner"],
  "performance_insight": "one paragraph insight on current performance",
  "recommendation": "single most important thing to focus on today",
  "pipeline_health": "healthy or at_risk or critical"
}}
"""

    try:
        response = get_ai_response(prompt, max_tokens=1500)
        result = safe_json(response)
        if result:
            return result
    except Exception as e:
        print(f"   âš ï¸  Decision engine failed: {e}")

    # Fallback decisions
    decisions = []

    # Always check replies first
    if state["replies"].get("interested", 0) > 0:
        decisions.append({
            "action": "run_command",
            "command": "python reply_monitor.py --send",
            "reason": "Interested leads waiting for reply",
            "priority": 1,
            "autonomous": True
        })

    # Check inbox
    decisions.append({
        "action": "run_command",
        "command": "python reply_monitor.py",
        "reason": "Daily inbox check",
        "priority": 2,
        "autonomous": True
    })

    # Send WhatsApp if slots available
    wa_today = state["outreach"].get("whatsapp", {}).get("sent_today", 0)
    wa_limit = config["outreach"]["daily_whatsapp_limit"]
    if wa_today < wa_limit:
        decisions.append({
            "action": "run_command",
            "command": "python whatsapp_sender.py",
            "reason": f"WhatsApp slots available: {wa_limit - wa_today}",
            "priority": 3,
            "autonomous": True
        })

    return {
        "decisions": decisions,
        "alerts": [],
        "performance_insight": "System running on fallback decisions",
        "recommendation": "Check system manually",
        "pipeline_health": "unknown"
    }


def execute_decisions(decisions_result: dict, dry_run: bool = False) -> list:
    """Execute the AI CEO's decisions"""
    executed = []
    decisions = decisions_result.get("decisions", [])

    # Sort by priority
    decisions.sort(key=lambda x: x.get("priority", 99))

    for decision in decisions:
        action = decision.get("action")
        command = decision.get("command", "")
        reason = decision.get("reason", "")
        autonomous = decision.get("autonomous", False)

        print(f"\n   ðŸ¤– Decision [{decision.get('priority')}]: {reason}")
        print(f"      Action: {action}")
        if command:
            print(f"      Command: {command}")

        if action == "alert_owner":
            print(f"      ðŸš¨ ALERT: {reason}")
            executed.append({
                "decision": decision,
                "executed": True,
                "result": "alert_sent"
            })
            continue

        if action == "skip":
            executed.append({
                "decision": decision,
                "executed": False,
                "result": "skipped"
            })
            continue

        if action == "run_command" and command and autonomous:
            if dry_run:
                print(f"      ðŸ” DRY RUN â€” would run: {command}")
                executed.append({
                    "decision": decision,
                    "executed": False,
                    "result": "dry_run"
                })
            else:
                try:
                    print(f"      â–¶ï¸  Executing: {command}")
                    result = subprocess.run(
                        command.split(),
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                    success = result.returncode == 0
                    executed.append({
                        "decision": decision,
                        "executed": True,
                        "success": success,
                        "output": result.stdout[-500:] if result.stdout else "",
                        "result": "completed" if success else "failed"
                    })
                    if success:
                        print(f"      âœ… Completed")
                    else:
                        print(f"      âŒ Failed: {result.stderr[:100]}")
                except subprocess.TimeoutExpired:
                    print(f"      â±ï¸  Timed out")
                    executed.append({
                        "decision": decision,
                        "executed": True,
                        "success": False,
                        "result": "timeout"
                    })
                except Exception as e:
                    print(f"      âŒ Error: {str(e)[:80]}")
                    executed.append({
                        "decision": decision,
                        "executed": True,
                        "success": False,
                        "result": str(e)[:80]
                    })

    return executed
