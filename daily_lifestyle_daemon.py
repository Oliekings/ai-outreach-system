import time
import json
import os
import subprocess
from datetime import datetime

# Initialize directories
os.makedirs("results/ceo", exist_ok=True)

DAEMON_STATE_FILE = "results/ceo/lifestyle_state.json"
DAEMON_LOG_FILE = "results/ceo/lifestyle_log.json"

def log_event(event_type, message, details=None):
    print(f"[{datetime.now().isoformat()}] [{event_type}] {message}")
    
    # Load logs
    logs = []
    if os.path.exists(DAEMON_LOG_FILE):
        try:
            with open(DAEMON_LOG_FILE, "r", encoding="utf-8") as f:
                logs = json.load(f)
        except:
            pass
            
    logs.append({
        "timestamp": datetime.now().isoformat(),
        "type": event_type,
        "message": message,
        "details": details
    })
    
    # Keep last 200 logs
    logs = logs[-200:]
    with open(DAEMON_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=4, ensure_ascii=False)

def load_config() -> dict:
    try:
        with open("ceo_config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log_event("ERROR", f"Failed to load config: {e}")
        return {}

def save_state(state):
    with open(DAEMON_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4, ensure_ascii=False)

def get_state():
    default_state = {
        "is_running": True,
        "last_run": None,
        "next_scheduled_run": None,
        "status": "idle",
        "current_task": None,
        "completed_runs": 0,
        "failed_runs": 0
    }
    if os.path.exists(DAEMON_STATE_FILE):
        try:
            with open(DAEMON_STATE_FILE, "r", encoding="utf-8") as f:
                return {**default_state, **json.load(f)}
        except:
            pass
    return default_state

def run_command(command):
    import sys
    log_event("SUBPROCESS", f"Starting command: {command}")
    try:
        parts = command.split()
        if parts and parts[0] == "python":
            parts[0] = sys.executable
            
        result = subprocess.run(
            parts,
            capture_output=True,
            text=True,
            encoding='utf-8',
            cwd=os.getcwd()
        )
        success = result.returncode == 0
        if success:
            log_event("SUBPROCESS_SUCCESS", f"Completed: {command}")
        else:
            log_event("SUBPROCESS_FAILED", f"Failed with code {result.returncode}: {command}", {"error": result.stderr})
        return success
    except Exception as e:
        log_event("SUBPROCESS_ERROR", f"Exception running {command}: {e}")
        return False

def execute_daily_lifestyle():
    state = get_state()
    state["status"] = "running"
    state["current_task"] = "Lead Discovery"
    save_state(state)
    
    log_event("LIFESTYLE", "Starting Daily AI CEO Lifestyle Loop Sequence...")
    
    # Step 1: Find Leads
    state["current_task"] = "Lead Discovery"
    save_state(state)
    run_command("python intelligence/lead_finder.py")
    
    # Step 2: Enrich Leads
    state["current_task"] = "Deep Enrichment"
    save_state(state)
    run_command("python intelligence/lead_enricher.py")
    
    # Step 3: Audit Website
    state["current_task"] = "Website Auditing"
    save_state(state)
    run_command("python intelligence/general_auditor.py")
    
    # Step 4: Craft Messages
    state["current_task"] = "AI Message Crafting"
    save_state(state)
    run_command("python outreach/message_writer.py")
    
    # Step 5: Senders
    state["current_task"] = "Autonomous Outreach"
    save_state(state)
    run_command("python outreach/email_sender.py")
    run_command("python outreach/whatsapp_sender.py")
    run_command("python outreach/instagram_sender.py")
    run_command("python outreach/facebook_sender.py")
    
    # Step 6: Reply Monitor & Forward & Nurture
    state["current_task"] = "Reply Management"
    save_state(state)
    run_command("python response_management/reply_monitor.py --send")
    run_command("python response_management/reply_handler.py --nurture")
    
    # Finished
    log_event("LIFESTYLE", "Daily AI CEO Lifestyle Loop Sequence Completed Successfully!")
    state["status"] = "idle"
    state["current_task"] = None
    state["last_run"] = datetime.now().isoformat()
    state["completed_runs"] += 1
    
    # Schedule next run in 24 hours
    next_run = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    if next_run <= datetime.now():
        next_run = next_run.replace(day=next_run.day + 1)
    state["next_scheduled_run"] = next_run.isoformat()
    save_state(state)

def main():
    log_event("DAEMON", "Daily AI CEO Lifestyle Daemon Started.")
    
    # Set initial schedule if none exists
    state = get_state()
    if not state.get("next_scheduled_run"):
        next_run = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        if next_run <= datetime.now():
            # If past 9 AM today, schedule for next run in 10 seconds to get it started or for tomorrow
            # Since the user requested " lifestyle of the program and it shouldn't stay a day without doing this"
            # Let's run it immediately on start if we haven't run today!
            next_run = datetime.now()
        state["next_scheduled_run"] = next_run.isoformat()
        save_state(state)

    while True:
        state = get_state()
        if not state.get("is_running"):
            log_event("DAEMON", "Daemon is paused. Waiting...")
            time.sleep(60)
            continue
            
        next_run_str = state.get("next_scheduled_run")
        if next_run_str:
            next_run = datetime.fromisoformat(next_run_str)
            now = datetime.now()
            
            if now >= next_run:
                try:
                    execute_daily_lifestyle()
                except Exception as e:
                    log_event("ERROR", f"Lifestyle sequence failed: {e}")
                    state = get_state()
                    state["status"] = "error"
                    state["current_task"] = None
                    state["failed_runs"] += 1
                    # Try again in 2 hours
                    state["next_scheduled_run"] = (datetime.now().replace(hour=now.hour + 2)).isoformat()
                    save_state(state)
        
        # Sleep for 30 seconds
        time.sleep(30)

if __name__ == "__main__":
    main()
