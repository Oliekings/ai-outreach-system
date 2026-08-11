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

    logs.append(
        {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "message": message,
            "details": details,
        }
    )

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
        "last_full_loop_date": None,
        "last_quick_cycle_time": None,
        "next_scheduled_run": None,
        "status": "idle",
        "current_task": None,
        "completed_runs": 0,
        "failed_runs": 0,
        "completed_periods": [],
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

        # Copy environment and inject/prepend current working directory into PYTHONPATH
        env = os.environ.copy()
        cwd = os.getcwd()
        if "PYTHONPATH" in env:
            env["PYTHONPATH"] = cwd + os.pathsep + env["PYTHONPATH"]
        else:
            env["PYTHONPATH"] = cwd

        result = subprocess.run(
            parts, capture_output=True, text=True, encoding="utf-8", cwd=cwd, env=env
        )
        success = result.returncode == 0
        if success:
            log_event("SUBPROCESS_SUCCESS", f"Completed: {command}")
        else:
            log_event(
                "SUBPROCESS_FAILED",
                f"Failed with code {result.returncode}: {command}",
                {"error": result.stderr},
            )
        return success
    except Exception as e:
        log_event("SUBPROCESS_ERROR", f"Exception running {command}: {e}")
        return False


def execute_full_daily_loop():
    state = get_state()
    state["status"] = "running"
    state["current_task"] = "Full Daily Loop - Lead Discovery"
    save_state(state)

    log_event("LIFESTYLE", "Starting Full Daily AI CEO Lifestyle Loop Sequence...")

    # Step 1: Find Leads
    state["current_task"] = "Full Daily Loop - Lead Discovery"
    save_state(state)
    run_command("python intelligence/lead_finder.py")

    # Step 2: Enrich Leads
    state["current_task"] = "Full Daily Loop - Deep Enrichment"
    save_state(state)
    run_command("python intelligence/lead_enricher.py")

    # Step 3: Audit Website
    state["current_task"] = "Full Daily Loop - Website Auditing"
    save_state(state)
    run_command("python intelligence/general_auditor.py")

    # Step 4: Craft Messages
    state["current_task"] = "Full Daily Loop - AI Message Crafting"
    save_state(state)
    run_command("python outreach/message_writer.py")

    # Step 5: AI CEO Review & Decisions
    state["current_task"] = "Full Daily Loop - AI CEO Review & Decisions"
    save_state(state)
    run_command("python ai_ceo.py review --autonomous")
    run_command("python ai_ceo.py decide --autonomous")

    # Step 6: Senders
    state["current_task"] = "Full Daily Loop - Outreach Senders"
    save_state(state)
    run_command("python outreach/email_sender.py")
    run_command("python outreach/whatsapp_sender.py")
    run_command("python outreach/instagram_sender.py")
    run_command("python outreach/facebook_sender.py")

    # Step 7: Reply Monitor & Auto-Approve & Senders & Nurture
    state["current_task"] = "Full Daily Loop - Reply Management"
    save_state(state)
    run_command("python response_management/reply_monitor.py")
    run_command("python response_management/reply_handler.py --auto-approve")
    run_command("python response_management/reply_handler.py --send")
    run_command("python response_management/reply_handler.py --nurture")

    # Finished
    log_event(
        "LIFESTYLE", "Full Daily AI CEO Lifestyle Loop Sequence Completed Successfully!"
    )
    state["status"] = "idle"
    state["current_task"] = None
    state["last_run"] = datetime.now().isoformat()
    state["last_full_loop_date"] = datetime.now().strftime("%Y-%m-%d")
    state["completed_runs"] += 1
    save_state(state)


def execute_quick_check_cycle():
    state = get_state()
    state["status"] = "running"
    state["current_task"] = "Quick Check Cycle"
    save_state(state)

    log_event("LIFESTYLE", "Starting Quick Check Cycle (15-min Active Monitor)...")

    # Step 1: Monitor new replies
    state["current_task"] = "Quick Check Cycle - Fetching Replies"
    save_state(state)
    run_command("python response_management/reply_monitor.py")

    # Step 2: Auto-approve stalled replies
    state["current_task"] = "Quick Check Cycle - Auto-approving Replies"
    save_state(state)
    run_command("python response_management/reply_handler.py --auto-approve")

    # Step 3: Run AI CEO Review and Decide (in case deadline passed for outreach)
    state["current_task"] = "Quick Check Cycle - AI CEO Review & Decisions"
    save_state(state)
    run_command("python ai_ceo.py review --autonomous")
    run_command("python ai_ceo.py decide --autonomous")

    # Step 4: Run senders to dispatch any newly approved outreach
    state["current_task"] = "Quick Check Cycle - Sending Outreach"
    save_state(state)
    run_command("python outreach/email_sender.py")
    run_command("python outreach/whatsapp_sender.py")
    run_command("python outreach/instagram_sender.py")
    run_command("python outreach/facebook_sender.py")

    # Step 5: Send approved/ready replies
    state["current_task"] = "Quick Check Cycle - Sending Replies"
    save_state(state)
    run_command("python response_management/reply_handler.py --send")

    # Step 6: Nurture
    state["current_task"] = "Quick Check Cycle - Nurture Follow-ups"
    save_state(state)
    run_command("python response_management/reply_handler.py --nurture")

    # Finished
    log_event("LIFESTYLE", "Quick Check Cycle Completed Successfully!")
    state["status"] = "idle"
    state["current_task"] = None
    state["last_quick_cycle_time"] = datetime.now().isoformat()
    save_state(state)


_lock_socket = None


def acquire_port_lock(port=5056):
    import socket
    import sys

    global _lock_socket
    try:
        _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _lock_socket.bind(("127.0.0.1", port))
        _lock_socket.listen(1)
        log_event("LOCK", f"Acquired single-instance socket lock on 127.0.0.1:{port}")
        return True
    except OSError:
        log_event(
            "LOCK",
            f"Failed to acquire socket lock on 127.0.0.1:{port}. Another daemon instance is already running. Exiting.",
        )
        sys.exit(0)


def main():
    acquire_port_lock(5056)
    log_event("DAEMON", "Daily AI CEO Lifestyle Daemon Started.")

    while True:
        config = load_config()
        state = get_state()

        if not state.get("is_running", True):
            log_event("DAEMON", "Daemon is paused. Standby...")
            time.sleep(60)
            continue

        now = datetime.now()
        current_day = now.strftime("%A")

        # Determine configured days and hours
        send_days = config.get("outreach", {}).get(
            "send_days", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        )
        send_hours = config.get("outreach", {}).get(
            "send_hours", {"start": 9, "end": 18}
        )
        start_hour = send_hours.get("start", 9)
        end_hour = send_hours.get("end", 18)

        is_sending_day = current_day in send_days
        is_sending_hour = start_hour <= now.hour < end_hour

        if is_sending_day and is_sending_hour:
            today_str = now.strftime("%Y-%m-%d")

            # Reset daily periods if a new day starts
            if state.get("last_full_loop_date") != today_str:
                state["completed_periods"] = []
                state["last_full_loop_date"] = today_str
                save_state(state)

            # Determine which period we are currently in
            current_period = None
            if 9 <= now.hour < 12:
                current_period = "morning"
            elif 13 <= now.hour < 17:
                current_period = "afternoon"
            elif 17 <= now.hour < 22:
                current_period = "evening"

            if current_period and current_period not in state.get(
                "completed_periods", []
            ):
                log_event("DAEMON", f"Starting scheduled {current_period} loop...")
                try:
                    execute_full_daily_loop()
                    state = get_state()
                    if "completed_periods" not in state:
                        state["completed_periods"] = []
                    state["completed_periods"].append(current_period)
                    state["last_full_loop_date"] = today_str
                    save_state(state)
                except Exception as e:
                    log_event("ERROR", f"Scheduled {current_period} loop failed: {e}")
                    state = get_state()
                    state["status"] = "error"
                    state["current_task"] = None
                    state["failed_runs"] += 1
                    save_state(state)
            else:
                # We are either between periods, or have already completed the current period's loop today.
                # Run the Quick Check Cycle every 15 minutes.
                last_quick_str = state.get("last_quick_cycle_time")
                should_run_quick = False

                if not last_quick_str:
                    should_run_quick = True
                else:
                    try:
                        last_quick = datetime.fromisoformat(last_quick_str)
                        elapsed_seconds = (now - last_quick).total_seconds()
                        if elapsed_seconds >= 900:  # 15 minutes
                            should_run_quick = True
                    except:
                        should_run_quick = True

                if should_run_quick:
                    try:
                        execute_quick_check_cycle()
                    except Exception as e:
                        log_event("ERROR", f"Quick check cycle failed: {e}")
                        state = get_state()
                        state["status"] = "error"
                        state["current_task"] = None
                        save_state(state)
        else:
            # Standby/Outside sending hours or on weekends
            status_msg = f"Outside active window (Sending: {', '.join(send_days)} from {start_hour}:00 to {end_hour}:00). "
            status_msg += (
                f"Current: {current_day} at {now.strftime('%I:%M %p')}. Standby."
            )
            print(f"[{now.isoformat()}] [STANDBY] {status_msg}")

            # Update daemon status in state
            if state.get("status") != "standby":
                state["status"] = "standby"
                state["current_task"] = None
                save_state(state)

        # Wake up and check state/time every 30 seconds
        time.sleep(30)


if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
