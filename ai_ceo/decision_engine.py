from utils.symbols import Symbol
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from dotenv import load_dotenv
from anthropic import Anthropic
from groq import Groq

load_dotenv()

sys.stdout.reconfigure(encoding='utf-8')


def get_ai_response(prompt: str, max_tokens: int = 1500) -> str:
    from utils.ai_client import ai_response
    return ai_response(prompt, task="decide", max_tokens=max_tokens)


from utils.ai_client import safe_json


def is_safe_command(command: str) -> bool:
    """Validate that the command is in the whitelist and has no malicious characters."""
    if not command:
        return False
    
    # Strip whitespace
    cmd = command.strip()
    
    # Must start with python
    if not (cmd.startswith("python ") or cmd.startswith("python3 ")):
        return False
        
    # Split into parts
    parts = cmd.split()
    if len(parts) < 2:
        return False
        
    script = parts[1]
    
    # Whitelist of allowed scripts
    allowed_scripts = {
        "intelligence/lead_finder.py",
        "intelligence/lead_enricher.py",
        "intelligence/general_auditor.py",
        "intelligence/email_verifier.py",
        "intelligence/website_auditor.py",
        "intelligence/self_optimizer.py",
        "outreach/message_writer.py",
        "outreach/email_sender.py",
        "outreach/whatsapp_sender.py",
        "outreach/sample_site_builder.py",
        "response_management/reply_monitor.py",
        "response_management/reply_handler.py",
        "scale/campaign_manager.py",
        "scale/city_manager.py",
        "scale/niche_manager.py",
        "scale/performance_tracker.py",
        "ai_ceo/auditor.py",
        "ai_ceo/decision_engine.py",
        "ai_ceo/scheduler.py",
        "ai_ceo/reviewer.py",
    }
    
    if script not in allowed_scripts:
        return False
        
    # Verify remaining arguments are safe: only alphanumeric, dashes, underscores, spaces, or simple values
    # Absolutely no shell metacharacters like ;, &, |, $, `, >, <, \, *, ? etc.
    safe_pattern = re.compile(r'^[\w\s\-\=\.\/]*$')
    for arg in parts[2:]:
        if not safe_pattern.match(arg):
            return False
            
    return True



def load_config() -> dict:
    with open("ceo_config.json", "r", encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM STATE READER
# ─────────────────────────────────────────────────────────────────────────────
def read_full_system_state() -> dict:
    state = {
        "timestamp": datetime.now().isoformat(),
        "leads": {},
        "outreach": {},
        "replies": {},
        "performance": {},
        "campaigns": [],
        "expansion": [],
        "knowledge": [],
        "workflow": {}
    }

    # Workflow state
    workflow_file = "results/ceo/workflow_state.json"
    if os.path.exists(workflow_file):
        try:
            with open(workflow_file, "r", encoding="utf-8") as f:
                w_state = json.load(f)
            
            # Check if it needs to refresh daily
            last_updated_str = w_state.get("last_updated")
            needs_reset = False
            if last_updated_str:
                try:
                    clean_str = last_updated_str.split('+')[0].replace('Z', '')
                    last_dt = datetime.fromisoformat(clean_str)
                    if last_dt.date() != datetime.now().date():
                        needs_reset = True
                except:
                    needs_reset = True
            else:
                needs_reset = True

            if needs_reset:
                w_state = {
                    "current_step": "audit",
                    "status": "idle",
                    "last_updated": datetime.now().isoformat()
                }
                os.makedirs(os.path.dirname(workflow_file), exist_ok=True)
                with open(workflow_file, "w", encoding="utf-8") as f:
                    json.dump(w_state, f, indent=4, ensure_ascii=False)
            
            state["workflow"] = w_state
        except:
            state["workflow"] = {
                "current_step": "audit",
                "status": "idle",
                "last_updated": datetime.now().isoformat()
            }

    # Leads state
    enriched_file = "results/leads/enriched_leads.json"
    if os.path.exists(enriched_file):
        with open(enriched_file, "r", encoding="utf-8") as f:
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
            with open(path, "r", encoding="utf-8") as f:
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
        with open(reply_file, "r", encoding="utf-8") as f:
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
    outreach_sent_today = sum(
        state["outreach"].get(ch, {}).get("sent_today", 0)
        for ch in ["email", "whatsapp", "instagram", "facebook"]
    )
    total_replies = state["replies"].get("total", 0)
    total_interested = state["replies"].get("interested", 0)

    state["performance"] = {
        "total_messages_sent": total_sent,
        "sent_today": outreach_sent_today,
        "reply_rate": round(total_replies / max(total_sent, 1) * 100, 1),
        "interest_rate": round(total_interested / max(total_sent, 1) * 100, 1),
        "conversion_rate": round(
            state["leads"].get("interested", 0) / max(state["leads"].get("total", 1), 1) * 100, 1
        )
    }

    # Scale & Campaign state
    campaign_file = "results/campaigns/active_campaigns.json"
    if os.path.exists(campaign_file):
        try:
            with open(campaign_file, "r", encoding="utf-8") as f:
                state["campaigns"] = json.load(f)
        except: pass

    # Expansion roadmap
    try:
        from scale.city_manager import get_expansion_roadmap
        config_data = load_config()
        cities = config_data.get("outreach", {}).get("cities", ["Uromi"])
        current_city = cities[0] if cities else "Uromi"
        state["expansion"] = get_expansion_roadmap(current_city)
    except: pass

    # Deep Revenue Metrics (from scale module)
    try:
        from scale.performance_tracker import calculate_revenue_metrics, load_all_data
        data = load_all_data()
        state["revenue"] = calculate_revenue_metrics(data)
    except: pass

    # Evolution & Knowledge state
    lessons_file = "results/knowledge/lessons_learned.json"
    if os.path.exists(lessons_file):
        try:
            with open(lessons_file, "r", encoding="utf-8") as f:
                state["knowledge"] = json.load(f)
        except: pass

    # Daily Progress resets daily
    def is_modified_today(filepath: str) -> bool:
        if not os.path.exists(filepath):
            return False
        try:
            mtime = os.path.getmtime(filepath)
            mtime_date = datetime.fromtimestamp(mtime).date()
            return mtime_date == datetime.today().date()
        except:
            return False

    today_str = datetime.now().strftime("%Y-%m-%d")
    state["daily_progress"] = {
        "discovered_today": is_modified_today("results/leads/leads.json"),
        "enriched_today": is_modified_today("results/leads/enriched_leads.json"),
        "audited_today": is_modified_today("results/audits/audit_results.json"),
        "crafted_today": is_modified_today("results/messages/sequences/master_sequence.json"),
        "sent_today": outreach_sent_today > 0,
        "replies_checked_today": is_modified_today("results/replies/reply_log.json"),
        "audit_done_today": os.path.exists(f"results/ceo/audit_{today_str}.json")
    }

    return state


def _avg_enrichment_score(leads: list) -> float:
    scores = []
    for l in leads:
        score_str = l.get("enrichment_score", "0/10")
        try:
            num = int(score_str.split("/")[0])
            scores.append(num)
        except:
            pass
    return round(sum(scores) / max(len(scores), 1), 1)


# ─────────────────────────────────────────────────────────────────────────────
# AI DECISION MAKER
# ─────────────────────────────────────────────────────────────────────────────
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
6. SCALING: If performance is stable, should we launch a new campaign in a new city or niche?
7. EXPANSION: Look at the 'expansion' roadmap in the state. Is it time to move to the next city?
8. EVOLUTION: Review the 'knowledge' section (Lessons Learned). How should these insights affect today's strategy?
9. Any risks or issues to flag?

Return ONLY valid JSON:
{{
  "decisions": [
    {{
      "action": "run_command or pause_channel or alert_owner or launch_campaign or skip",
      "command": "python command to run if applicable (e.g. python scale/campaign_manager.py --create ...)",
      "reason": "why this decision was made",
      "priority": 1-10,
      "autonomous": true or false
    }}
  ],
  "alerts": ["any urgent issues to flag to owner"],
  "performance_insight": "one paragraph insight on current performance and scaling potential",
  "recommendation": "single most important thing to focus on today",
  "pipeline_health": "healthy or at_risk or critical",
  "growth_strategy": "stay_put or test_niche or expand_city"
}}
"""

    try:
        response = get_ai_response(prompt, max_tokens=1500)
        result = safe_json(response)
        if result:
            return result
    except Exception as e:
        print(f"   {Symbol.WARN}  Decision engine failed: {e}")

    # Fallback decisions
    decisions = []

    # Check Workflow state for 12-hour timeout
    workflow = state.get("workflow", {})
    current_step = workflow.get("current_step", "audit")
    last_updated_str = workflow.get("last_updated")
    
    if last_updated_str:
        try:
            last_updated = datetime.fromisoformat(last_updated_str)
            hours_passed = (datetime.now() - last_updated).total_seconds() / 3600
            
            if hours_passed >= 12:
                # Need to advance workflow
                if current_step == "audit":
                    decisions.append({
                        "action": "run_command",
                        "command": "python intelligence/general_auditor.py",
                        "reason": f"Workflow timeout ({hours_passed:.1f}h): Running Auditor",
                        "priority": 1,
                        "autonomous": True
                    })
                elif current_step == "craft":
                    decisions.append({
                        "action": "run_command",
                        "command": "python outreach/message_writer.py",
                        "reason": f"Workflow timeout ({hours_passed:.1f}h): Crafting Messages",
                        "priority": 1,
                        "autonomous": True
                    })
                elif current_step == "outreach":
                    decisions.append({
                        "action": "run_command",
                        "command": "python outreach/email_sender.py",
                        "reason": f"Workflow timeout ({hours_passed:.1f}h): Running Outreach",
                        "priority": 1,
                        "autonomous": True
                    })
        except:
            pass

    # Always check replies first
    if state["replies"].get("interested", 0) > 0:
        decisions.append({
            "action": "run_command",
            "command": "python response_management/reply_monitor.py --send",
            "reason": "Interested leads waiting for reply",
            "priority": 2,
            "autonomous": True
        })

    # Check inbox
    decisions.append({
        "action": "run_command",
        "command": "python response_management/reply_monitor.py",
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
            "command": "python outreach/whatsapp_sender.py",
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
            if not is_safe_command(command):
                print(f"      🛑 SECURITY ALERT: Command blocked by whitelist: '{command}'")
                executed.append({
                    "decision": decision,
                    "executed": False,
                    "success": False,
                    "result": "blocked_by_security_whitelist"
                })
                continue

            if dry_run:
                print(f"      {Symbol.SEARCH}  DRY RUN — would run: {command}")
                executed.append({
                    "decision": decision,
                    "executed": False,
                    "result": "dry_run"
                })
            else:
                try:
                    print(f"      â–¶ï¸   Executing: {command}")
                    parts = command.split()
                    if parts and parts[0] in ("python", "python3"):
                        parts[0] = sys.executable
                    env = os.environ.copy()
                    cwd = os.getcwd()
                    if "PYTHONPATH" in env:
                        env["PYTHONPATH"] = cwd + os.pathsep + env["PYTHONPATH"]
                    else:
                        env["PYTHONPATH"] = cwd
                    result = subprocess.run(
                        parts,
                        capture_output=True,
                        text=True,
                        encoding='utf-8',
                        cwd=cwd,
                        env=env,
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
                        print(f"      {Symbol.CHECK} Completed")
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
