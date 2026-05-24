import json
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class Symbol:
    """Clean logging symbols that work across all terminals"""
    USE_EMOJI = False # Set to True if your terminal supports UTF-8 emojis
    
    LIST = "📋" if USE_EMOJI else "[LIST]"
    LEAD = "💎" if USE_EMOJI else "[LEAD]"
    SEARCH = "🔍" if USE_EMOJI else "[SEARCH]"
    STOP = "🛑" if USE_EMOJI else "[STOP]"
    CHECK = "✅" if USE_EMOJI else "[OK]"
    WORLD = "🌍" if USE_EMOJI else "[WORLD]"
    WARN = "⚠️" if USE_EMOJI else "[WARN]"
    AI = "🧠" if USE_EMOJI else "[AI]"
    VIBE = "🎨" if USE_EMOJI else "[VIBE]"
    TONE = "🗣️" if USE_EMOJI else "[TONE]"
    PRIDE = "🆕" if USE_EMOJI else "[PRIDE]"
    TARGET = "🎯" if USE_EMOJI else "[TARGET]"
    TIME = "⏰" if USE_EMOJI else "[TIME]"
    NURTURE = "🌱" if USE_EMOJI else "[NURTURE]"
    REFERRAL = "🤝" if USE_EMOJI else "[REFERRAL]"
    EMAIL = "📧" if USE_EMOJI else "[EMAIL]"
    PHONE = "📞" if USE_EMOJI else "[PHONE]"
    WHATSAPP = "💬" if USE_EMOJI else "[WHATSAPP]"
    SOCIAL = "📱" if USE_EMOJI else "[SOCIAL]"
    INSTAGRAM = "📸" if USE_EMOJI else "[INSTAGRAM]"
    FACEBOOK = "📘" if USE_EMOJI else "[FACEBOOK]"
    RETRY = "🔄" if USE_EMOJI else "[RETRY]"
    BOT = "🛡️" if USE_EMOJI else "[BOT-WALL]"
    WAIT = "⏳" if USE_EMOJI else "[WAIT]"
    PITCH = "💡" if USE_EMOJI else "[PITCH]"
    PAGE = "📄" if USE_EMOJI else "[PAGE]"
    MAPS = "📍" if USE_EMOJI else "[MAPS]"
    ERROR = "❌" if USE_EMOJI else "[ERROR]"
    HUMAN = "🧑" if USE_EMOJI else "[USER]"
    BRAIN = "🧠" if USE_EMOJI else "[BRAIN]"
    LEARN = "📖" if USE_EMOJI else "[LEARN]"

sys.stdout.reconfigure(encoding='utf-8')

os.makedirs("results/ceo", exist_ok=True)


def load_config() -> dict:
    with open("ceo_config.json", "r", encoding="utf-8") as f:
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
    - evolve:    Run self-improvement cycle (learn from results)
    - report:    Just print the latest report
    """

    print(f"\n{'═'*60}")
    print(f"  🤖 AI CEO — {mode.upper()} MODE")
    print(f"  {datetime.now().strftime('%A, %d %B %Y — %I:%M %p')}")
    if dry_run:
        print(f"  {Symbol.SEARCH} DRY RUN — No actions will be executed")
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

    # ── STEP 1.5: Run Dynamic Follow-Up Manager
    if mode in ["full", "schedule"]:
        print(f"\n🔄 Running dynamic follow-up manager...")
        try:
            from outreach.followup_manager import run_followup_manager
            followup_result = run_followup_manager(dry_run=dry_run)
            generated = followup_result.get("generated", 0)
            if generated > 0:
                print(f"   {Symbol.CHECK} Generated {generated} new follow-up message(s)")
            else:
                print(f"   {Symbol.CHECK} No follow-ups needed right now")
        except Exception as e:
            print(f"   {Symbol.WARN} Follow-up manager error: {e}")

    # ── STEP 2: Build schedule
    if mode in ["full", "schedule"]:
        print(f"\n{Symbol.TIME} Building daily schedule...")
        schedule = build_daily_schedule()
        print_schedule(schedule)
    else:
        schedule = {}

    # ── STEP 3: Review messages
    if mode in ["full", "review"]:
        print("\n👀 Reviewing all pending messages...")
        review_deadline_hours = config["owner"].get("review_deadline_hours", 12)
        autonomous_fallback = config["owner"].get("autonomous_fallback", True)
        should_act_autonomous = autonomous or (
            autonomous_fallback and _deadline_passed(review_deadline_hours)
        )
        review_results = review_all_pending_messages(autonomous=should_act_autonomous)
        print(f"   {Symbol.CHECK} Reviewed: {review_results['reviewed']}")
        print(f"   {Symbol.CHECK} Approved: {review_results['approved']}")
        print(f"   ✏️  Edited:   {review_results['needs_edit']}")
        print(f"   {Symbol.ERROR} Rejected: {review_results['rejected']}")

    # ── STEP 4: Run audit
    if mode in ["full", "audit"]:
        print(f"\n{Symbol.SEARCH} Running performance audit...")
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

        print(f"\n   {Symbol.LIST} Recommendation: {decisions_result.get('recommendation', '')}")
        print(f"   🏥 Pipeline health: {decisions_result.get('pipeline_health', 'unknown')}")

        if should_act_autonomous and not dry_run:
            print(f"\n   ▶️  Executing autonomous decisions...")
            executed = execute_decisions(decisions_result, dry_run=dry_run)
            print(f"\n   {Symbol.CHECK} Executed {len([e for e in executed if e.get('executed')])} decisions")
        elif dry_run:
            print(f"\n   {Symbol.SEARCH} DRY RUN — Would execute:")
            for d in decisions_result.get("decisions", []):
                print(f"      [{d.get('priority')}] {d.get('reason')} → {d.get('command', '')}")
        else:
            print(f"\n   {Symbol.WAIT} Awaiting human review (deadline: {review_deadline_hours}h)")
            print(f"   Run with --autonomous to execute now")

    # ── STEP 6: Evolution & Self-Improvement
    if mode in ["full", "evolve"]:
        from intelligence.self_optimizer import SelfEvolutionEngine
        print(f"\n{Symbol.BRAIN} Running self-evolution cycle...")
        engine = SelfEvolutionEngine()
        # Autonomous evolution if --autonomous is set
        apply = autonomous or config["owner"].get("autonomous_fallback", True)
        evolution_result = engine.run_evolution_cycle(apply_changes=apply)
        if evolution_result:
            summary = evolution_result.get('learning_summary', 'Cycle complete')
            print(f"   {Symbol.LEARN} {summary}")

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
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(run_log, f, indent=2, ensure_ascii=False)

    print(f"\n{Symbol.CHECK} AI CEO run complete — log: {log_path}")
    print(f"{'═'*60}\n")


def _deadline_passed(hours: int) -> bool:
    """Check if the human review deadline has passed since any pending sequence was last updated"""
    seq_dir = "results/messages/sequences"
    if not os.path.isdir(seq_dir):
        return False
        
    pending_files = []
    for f in os.listdir(seq_dir):
        if f.endswith("_sequence.json") and f != "master_sequence.json":
            path = os.path.join(seq_dir, f)
            try:
                with open(path, "r", encoding="utf-8") as file:
                    seq = json.load(file)
                # If there is any message in status "queued"
                if any(m.get("status") == "queued" for m in seq):
                    pending_files.append(path)
            except:
                pass
                
    if not pending_files:
        return False
        
    # If any of the pending sequences has been waiting for more than 12 hours
    for path in pending_files:
        mtime = os.path.getmtime(path)
        elapsed = (datetime.now() - datetime.fromtimestamp(mtime)).total_seconds()
        if elapsed > (hours * 3600):
            return True
            
    return False


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mode = "full"
    dry_run = "--dry-run" in sys.argv
    autonomous = "--autonomous" in sys.argv

    # Parse mode from args
    for arg in sys.argv[1:]:
        if arg in ["full", "schedule", "audit", "review", "decide", "report", "evolve"]:
            mode = arg
            break

    run_ai_ceo(mode=mode, dry_run=dry_run, autonomous=autonomous)