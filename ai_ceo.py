import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

os.makedirs("results/ceo", exist_ok=True)


def load_config() -> dict:
    with open("ceo_config.json", "r") as f:
        return json.load(f)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN AI CEO ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
def run_ai_ceo(
    mode: str = "full",
    dry_run: bool = False,
    autonomous: bool = False
):
    """
    Modes:
    - full:      Complete daily run (schedule + review + audit + decisions)
    - schedule:  Just build today's schedule
    - audit:     Just run the performance audit
    - review:    Just review pending messages
    - decide:    Just make and execute decisions
    - report:    Just print the latest report
    """

    print(f"\n{'═'*60}")
    print(f"  🤖 AI CEO — {mode.upper()} MODE")
    print(f"  {datetime.now().strftime('%A, %d %B %Y — %I:%M %p')}")
    if dry_run:
        print(f"  🔍 DRY RUN — No actions will be executed")
    if autonomous:
        print(f"  🤖 AUTONOMOUS MODE — Will execute decisions without human input")
    print(f"{'═'*60}\n")

    config = load_config()

    # Import CEO modules
    from ai_ceo.scheduler import build_daily_schedule, print_schedule
    from ai_ceo.reviewer import review_all_pending_messages
    from ai_ceo.decision_engine import (
        read_full_system_state,
        make_autonomous_decisions,
        execute_decisions
    )
    from ai_ceo.auditor import run_daily_audit, generate_audit_report, save_audit

    # ── STEP 1: Read system state
    print("📊 Reading system state...")
    state = read_full_system_state()

    # ── STEP 2: Build schedule
    if mode in ["full", "schedule"]:
        print("\n📅 Building daily schedule...")
        schedule = build_daily_schedule()
        print_schedule(schedule)
    else:
        schedule = {}

    # ── STEP 3: Review messages
    if mode in ["full", "review"]:
        print("\n👀 Reviewing all pending messages...")
        review_results = review_all_pending_messages()
        print(f"   ✅ Reviewed: {review_results['reviewed']}")
        print(f"   ✅ Approved: {review_results['approved']}")
        print(f"   ✏️  Edited:   {review_results['needs_edit']}")
        print(f"   ❌ Rejected: {review_results['rejected']}")

    # ── STEP 4: Run audit
    if mode in ["full", "audit"]:
        print("\n🔍 Running performance audit...")
        audit_result = run_daily_audit(state)
        report_text = generate_audit_report(audit_result, state)
        print(report_text)
        save_audit(audit_result, report_text)

    # ── STEP 5: Make decisions
    if mode in ["full", "decide"]:
        review_deadline_hours = config["owner"].get("review_deadline_hours", 12)
        autonomous_fallback = config["owner"].get("autonomous_fallback", True)
        autonomous_min_score = config["owner"].get("autonomous_min_score", 7)

        should_act_autonomous = autonomous or (
            autonomous_fallback and _deadline_passed(review_deadline_hours)
        )

        print(f"\n🤖 Making decisions...")
        print(f"   Autonomous mode: {should_act_autonomous}")

        decisions_result = make_autonomous_decisions(state, schedule, config)

        # Print alerts
        for alert in decisions_result.get("alerts", []):
            print(f"   🚨 ALERT: {alert}")

        # Print insight
        insight = decisions_result.get("performance_insight", "")
        if insight:
            print(f"\n   💡 Insight: {insight}")

        print(f"\n   📋 Recommendation: {decisions_result.get('recommendation', '')}")
        print(f"   🏥 Pipeline health: {decisions_result.get('pipeline_health', 'unknown')}")

        if should_act_autonomous and not dry_run:
            print(f"\n   ▶️  Executing autonomous decisions...")
            executed = execute_decisions(decisions_result, dry_run=dry_run)
            print(f"\n   ✅ Executed {len([e for e in executed if e.get('executed')])} decisions")
        elif dry_run:
            print(f"\n   🔍 DRY RUN — Would execute:")
            for d in decisions_result.get("decisions", []):
                print(f"      [{d.get('priority')}] {d.get('reason')} → {d.get('command', '')}")
        else:
            print(f"\n   ⏳ Awaiting human review (deadline: {review_deadline_hours}h)")
            print(f"   Run with --autonomous to execute now")

    # Save full run log
    run_log = {
        "timestamp": datetime.now().isoformat(),
        "mode": mode,
        "dry_run": dry_run,
        "autonomous": autonomous,
        "state_summary": state.get("performance", {}),
        "leads_summary": state.get("leads", {})
    }

    log_path = f"results/ceo/run_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    with open(log_path, "w") as f:
        json.dump(run_log, f, indent=2)

    print(f"\n✅ AI CEO run complete — log: {log_path}")
    print(f"{'═'*60}\n")


def _deadline_passed(hours: int) -> bool:
    """Check if the human review deadline has passed today"""
    now = datetime.now()
    deadline_hour = now.replace(
        hour=min(now.hour, 23),
        minute=0, second=0, microsecond=0
    )
    # If it's past the configured send start time plus deadline hours
    config = load_config()
    send_start = config["outreach"]["send_hours"]["start"]
    deadline_time = now.replace(hour=send_start) + __import__('datetime').timedelta(hours=hours)
    return now > deadline_time


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mode = "full"
    dry_run = "--dry-run" in sys.argv
    autonomous = "--autonomous" in sys.argv

    # Parse mode from args
    for arg in sys.argv[1:]:
        if arg in ["full", "schedule", "audit", "review", "decide", "report"]:
            mode = arg
            break

    run_ai_ceo(mode=mode, dry_run=dry_run, autonomous=autonomous)