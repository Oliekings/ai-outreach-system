from utils.symbols import Symbol
import json
import os
import re
import sys
from datetime import datetime
from dotenv import load_dotenv
from anthropic import Anthropic
from groq import Groq

load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.getcwd())

# Ensure directories exist
os.makedirs("results/knowledge", exist_ok=True)
os.makedirs("results/logs", exist_ok=True)

def get_ai_response(prompt: str, max_tokens: int = 1000) -> str:
    from utils.ai_client import ai_response
    return ai_response(prompt, task="audit", max_tokens=max_tokens)

from utils.ai_client import safe_json

class SelfEvolutionEngine:
    def __init__(self):
        self.lessons_path = "results/knowledge/lessons_learned.json"
        self.optimizations_path = "results/knowledge/optimizations_log.json"
        self.config_path = "ceo_config.json"

    def load_lessons(self) -> list:
        if os.path.exists(self.lessons_path):
            try:
                with open(self.lessons_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: pass
        return []

    def save_lesson(self, lesson: dict):
        lessons = self.load_lessons()
        lesson["id"] = f"lesson_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        lesson["timestamp"] = datetime.now().isoformat()
        lessons.append(lesson)
        
        # Keep only last 50 lessons
        lessons = lessons[-50:]
        
        with open(self.lessons_path, "w", encoding="utf-8") as f:
            json.dump(lessons, f, indent=2, ensure_ascii=False)
        return lesson

    def log_optimization(self, optimization: dict):
        optimizations = []
        if os.path.exists(self.optimizations_path):
            try:
                with open(self.optimizations_path, "r", encoding="utf-8") as f:
                    optimizations = json.load(f)
            except: pass
            
        optimization["timestamp"] = datetime.now().isoformat()
        optimizations.append(optimization)
        
        with open(self.optimizations_path, "w", encoding="utf-8") as f:
            json.dump(optimizations[-100:], f, indent=2, ensure_ascii=False)

    def run_evolution_cycle(self, apply_changes: bool = False):
        print(f"\n{Symbol.BRAIN} Starting Self-Evolution Cycle...")
        
        # 1. Load system state/metrics
        try:
            from scale.performance_tracker import load_all_data, calculate_channel_metrics, calculate_reply_metrics, calculate_lead_metrics
            data = load_all_data()
            metrics = {
                "channels": calculate_channel_metrics(data),
                "replies": calculate_reply_metrics(data),
                "leads": calculate_lead_metrics(data)
            }
        except Exception as e:
            print(f"   {Symbol.WARN} Could not load metrics: {e}")
            return

        # 2. Consult existing knowledge
        history = self.load_lessons()
        
        # 3. AI Analysis
        prompt = f"""
You are the Self-Improvement Engine of an AI Outreach Agency in Nigeria.
Your job is to LEARN from current data and OPTIMIZE the system.

CURRENT PERFORMANCE DATA:
{json.dumps(metrics, indent=2)}

PAST LESSONS:
{json.dumps(history[-5:] if history else "No lessons yet.")}

TASK:
1. Analyze what is working and what is failing.
2. Identify 1-3 'Lessons Learned'. These should be specific insights (e.g. "WhatsApp conversion for Restaurants is 3x higher than Email").
3. Propose configuration optimizations to improve performance.
4. If a channel is failing (high fail rate), suggest a fix or a pause.

Return ONLY valid JSON:
{{
    "lessons": [
        {{
            "category": "channel_performance | niche_targeting | message_conversion",
            "insight": "Description of what was learned",
            "actionable_takeaway": "What we should do differently",
            "impact": "positive | negative | neutral",
            "confidence_score": 0.0-1.0
        }}
    ],
    "proposed_optimizations": [
        {{
            "target": "config.outreach.daily_whatsapp_limit",
            "old_value": "current",
            "new_value": "suggested",
            "reasoning": "why change this"
        }}
    ],
    "system_health_assessment": "healthy | needs_tuning | critical_failure",
    "learning_summary": "One sentence summary of today's learning"
}}
"""
        print(f"   {Symbol.LEARN} AI is analyzing performance patterns...")
        response = get_ai_response(prompt)
        result = safe_json(response)
        
        if not result:
            print(f"   {Symbol.WARN} AI failed to generate evolution insights.")
            return

        # 4. Save Lessons
        for lesson in result.get("lessons", []):
            saved = self.save_lesson(lesson)
            print(f"   {Symbol.CHECK} New Lesson Learned: {saved['insight']}")

        # 5. Apply Optimizations (if requested)
        if apply_changes and result.get("proposed_optimizations"):
            self.apply_config_changes(result["proposed_optimizations"])
        
        # 6. Log results
        self.log_optimization({
            "summary": result.get("learning_summary"),
            "health": result.get("system_health_assessment"),
            "lessons_count": len(result.get("lessons", [])),
            "optimizations_count": len(result.get("proposed_optimizations", []))
        })
        
        print(f"\n{Symbol.BRAIN} Evolution Cycle Complete. {len(result.get('lessons', []))} lessons added.")
        return result

    def apply_config_changes(self, optimizations: list):
        print(f"   {Symbol.FIX} Applying autonomous optimizations...")
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            
            # Check lock_manual_limits (defaulting to True)
            lock_limits = config.get("outreach", {}).get("lock_manual_limits", True)

            changes_made = 0
            for opt in optimizations:
                target = opt.get("target") or ""
                new_val = opt.get("new_value")
                
                # Check lock safety
                if lock_limits and ("daily_whatsapp_limit" in target.lower() or "daily_email_limit" in target.lower()):
                    print(f"      🔒 Skipping target '{target}' because manual limits are locked.")
                    continue

                # Simple path traversal for "config.section.key"
                parts = target.split('.')
                if parts[0] == "config":
                    parts = parts[1:]
                
                curr = config
                success = False
                for i, part in enumerate(parts):
                    if i == len(parts) - 1:
                        if part in curr:
                            curr[part] = new_val
                            changes_made += 1
                            success = True
                    else:
                        if part in curr:
                            curr = curr[part]
                        else:
                            break
                
                if success:
                    print(f"      🔧 Set {target} = {new_val}")
            
            if changes_made > 0:
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                print(f"   {Symbol.CHECK} Saved {changes_made} configuration changes.")
                
        except Exception as e:
            print(f"   {Symbol.WARN} Failed to apply optimizations: {e}")

if __name__ == "__main__":
    engine = SelfEvolutionEngine()
    engine.run_evolution_cycle(apply_changes="--apply" in sys.argv)
