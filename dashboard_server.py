import json
import os
import subprocess
import sys
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory, Response
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

app = Flask(__name__, static_folder=os.path.join(os.getcwd(), 'dashboard'), static_url_path='')
CORS(app, supports_credentials=True)

import secrets

DASHBOARD_AUTH_KEY = os.getenv("DASHBOARD_AUTH_KEY", "")
app.secret_key = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))


@app.before_request
def check_auth():
    # Exempt paths: health check and login
    exempt = ['/api/health', '/api/login']
    
    # We only enforce auth on API endpoints
    if not request.path.startswith('/api/'):
        return  # Let static assets through (the JS/HTML will handle redirects on 401)
        
    if request.path in exempt:
        return
        
    if not DASHBOARD_AUTH_KEY:
        return  # Allow if auth key is not configured in .env
        
    # Check Authorization header (Bearer token)
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer ') and auth_header[7:] == DASHBOARD_AUTH_KEY:
        return
        
    # Check query param
    if request.args.get('auth_key') == DASHBOARD_AUTH_KEY:
        return
        
    # Check session cookie
    if request.cookies.get('dashboard_auth') == DASHBOARD_AUTH_KEY:
        return
        
    return jsonify({'error': 'Unauthorized', 'message': 'Please provide auth key'}), 401


@app.route('/api/login', methods=['POST'])
def login():
    data = request.json or {}
    key = data.get('key', '')
    if key == DASHBOARD_AUTH_KEY:
        response = jsonify({'success': True, 'message': 'Authenticated'})
        # Set cookie to keep login persistent, Lax samesite
        response.set_cookie('dashboard_auth', key, max_age=86400*30, httponly=True, samesite='Lax')
        return response
    return jsonify({'success': False, 'error': 'Invalid key'}), 401


@app.route('/api/logout', methods=['POST'])
def logout():
    response = jsonify({'success': True})
    response.delete_cookie('dashboard_auth')
    return response


@app.route('/')
def index():
    return send_from_directory('dashboard', 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('dashboard', path)


def load_json(path: str, default=None):
    if default is None:
        default = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def latest_file(directory: str, prefix: str) -> dict:
    if not os.path.exists(directory):
        return {}
    files = [f for f in os.listdir(directory) if f.startswith(prefix) and f.endswith('.json')]
    if not files:
        return {}
    files.sort(reverse=True)
    return load_json(os.path.join(directory, files[0]))


# ─────────────────────────────────────────────────────────────────────────────
# DATA ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/state')
def get_state():
    try:
        sys.path.insert(0, os.getcwd())
        from ai_ceo.decision_engine import read_full_system_state
        state = read_full_system_state()
        return jsonify(state)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/leads')
def get_leads():
    enriched = load_json("results/leads/enriched_leads.json", [])
    raw = load_json("results/leads/leads.json", [])
    audits = load_json("results/audits/audit_results.json", [])
    
    if not isinstance(enriched, list): enriched = []
    if not isinstance(raw, list): raw = []
    if not isinstance(audits, list): audits = []
    
    # Map audits by website for quick lookup
    audits_map = {a['website']: a for a in audits if 'website' in a}
    
    # Merge: raw leads first, then overwrite with richer enriched data
    enriched_names = {l['name'] for l in enriched if 'name' in l}
    
    leads_dict = {}
    for l in raw:
        if 'name' in l:
            # Force enriched flag to reflect actual existence in enriched_leads.json
            l['enriched'] = l['name'] in enriched_names
            # Attach audit if available
            if l.get('website') in audits_map:
                l['website_audit'] = audits_map[l['website']]
            leads_dict[l['name']] = l
            
    for l in enriched:
        if 'name' in l:
            l['enriched'] = True
            # Attach audit if available
            if l.get('website') in audits_map:
                l['website_audit'] = audits_map[l['website']]
            leads_dict[l['name']] = l
    
    final_leads = list(leads_dict.values())
    
    response = jsonify(final_leads)
    # Prevent browser/Flask from caching stale lead data
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    return response


@app.route('/api/replies')
def get_replies():
    log = load_json("results/replies/reply_log.json", {})
    return jsonify(log.get("replies", []))


@app.route('/api/schedule')
def get_schedule():
    today = datetime.now().strftime("%Y-%m-%d")
    schedule = load_json(f"results/ceo/schedule_{today}.json", {})
    if not schedule:
        try:
            from ai_ceo.scheduler import build_daily_schedule
            schedule = build_daily_schedule()
        except Exception as e:
            schedule = {"tasks": [], "error": str(e)}
    return jsonify(schedule)


@app.route('/api/audit')
def get_audit():
    today = datetime.now().strftime("%Y-%m-%d")
    audit = load_json(f"results/ceo/audit_{today}.json", {})
    if not audit:
        audit = latest_file("results/ceo", "audit_")
    return jsonify(audit)


@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    if request.method == 'POST':
        try:
            new_config = request.json
            with open("ceo_config.json", "w", encoding="utf-8") as f:
                json.dump(new_config, f, indent=4, ensure_ascii=False)
            return jsonify({"success": True, "message": "Configuration updated successfully"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    return jsonify(load_json("ceo_config.json", {}))


@app.route('/api/env', methods=['GET', 'POST'])
def handle_env():
    env_path = ".env"
    
    # Load current env vars from file to resolve masked values during POST
    existing_vars = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    parts = line.strip().split("=", 1)
                    if len(parts) == 2:
                        k, v = parts
                        existing_vars[k.strip()] = v.strip()

    if request.method == 'POST':
        try:
            new_env = request.json or {}
            lines = []
            for k, v in new_env.items():
                k = k.strip()
                v = v.strip()
                
                # Check if this looks like a masked value matching our masking pattern
                is_masked = False
                if k in existing_vars:
                    orig_val = existing_vars[k]
                    if v == '****':
                        is_masked = True
                    elif '*' in v:
                        # Re-mask the original value and see if it matches the received value
                        if len(orig_val) > 8:
                            expected_mask = orig_val[:4] + '*' * (len(orig_val) - 8) + orig_val[-4:]
                            if v == expected_mask:
                                is_masked = True
                
                # Use original value if it was not modified (i.e. remains masked)
                final_val = existing_vars[k] if is_masked else v
                lines.append(f"{k}={final_val}")
                
            with open(env_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
            return jsonify({"success": True, "message": "Environment variables updated"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    parts = line.strip().split("=", 1)
                    if len(parts) == 2:
                        k, v = parts
                        env_vars[k.strip()] = v.strip()
                        
    # Mask sensitive values (keys containing KEY, SECRET, PASS, TOKEN, AUTH)
    SENSITIVE_PREFIXES = ('KEY', 'SECRET', 'PASS', 'TOKEN', 'AUTH')
    for k in env_vars:
        if any(p in k.upper() for p in SENSITIVE_PREFIXES):
            val = env_vars[k]
            if len(val) > 8:
                env_vars[k] = val[:4] + '*' * (len(val) - 8) + val[-4:]
            else:
                env_vars[k] = '****'
                
    return jsonify(env_vars)


@app.route('/api/logs')
def get_logs():
    logs = {}
    for name, path in [
        ("email", "results/logs/send_log.json"),
        ("whatsapp", "results/logs/whatsapp_log.json"),
        ("instagram", "results/logs/instagram_log.json"),
        ("facebook", "results/logs/facebook_log.json"),
    ]:
        data = load_json(path, {})
        logs[name] = data.get("stats", {})
    return jsonify(logs)


@app.route('/api/logs/detailed')
def get_detailed_logs():
    from datetime import datetime, timedelta
    now = datetime.now()
    cutoff = now - timedelta(days=12)
    
    detailed_logs = []
    
    def parse_date(date_str):
        if not date_str:
            return None
        try:
            clean_str = date_str
            if date_str.endswith('Z'):
                clean_str = date_str[:-1]
            if '+' in clean_str:
                clean_str = clean_str.split('+')[0]
            return datetime.fromisoformat(clean_str)
        except Exception:
            for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            return None

    # 1. Emails
    email_log = load_json("results/logs/send_log.json", {})
    for entry in email_log.get("emails", []):
        dt = parse_date(entry.get("date"))
        if dt and dt >= cutoff:
            detailed_logs.append({
                "timestamp": entry.get("date"),
                "channel": "email",
                "recipient": entry.get("to"),
                "business": entry.get("business"),
                "subject": entry.get("subject"),
                "message": entry.get("message") or entry.get("message_preview") or f"Subject: {entry.get('subject')}",
                "success": entry.get("success", False),
                "error": entry.get("error"),
                "parsed_dt": dt
            })

    # 2. WhatsApp
    wa_log = load_json("results/logs/whatsapp_log.json", {})
    for entry in wa_log.get("messages", []):
        dt = parse_date(entry.get("date"))
        if dt and dt >= cutoff:
            detailed_logs.append({
                "timestamp": entry.get("date"),
                "channel": "whatsapp",
                "recipient": entry.get("number"),
                "business": entry.get("business"),
                "subject": None,
                "message": entry.get("message") or entry.get("message_preview") or "No message content",
                "success": entry.get("success", False),
                "error": entry.get("error"),
                "parsed_dt": dt
            })

    # 3. Facebook
    fb_log = load_json("results/logs/facebook_log.json", {})
    for entry in fb_log.get("messages", []):
        dt = parse_date(entry.get("date"))
        if dt and dt >= cutoff:
            detailed_logs.append({
                "timestamp": entry.get("date"),
                "channel": "facebook",
                "recipient": entry.get("page"),
                "business": entry.get("business"),
                "subject": None,
                "message": entry.get("message") or entry.get("message_preview") or "No message content",
                "success": entry.get("success", False),
                "error": entry.get("error"),
                "parsed_dt": dt
            })

    # 4. Instagram
    ig_log = load_json("results/logs/instagram_log.json", {})
    for entry in ig_log.get("messages", []):
        dt = parse_date(entry.get("date"))
        if dt and dt >= cutoff:
            detailed_logs.append({
                "timestamp": entry.get("date"),
                "channel": "instagram",
                "recipient": entry.get("profile"),
                "business": entry.get("business"),
                "subject": None,
                "message": entry.get("message") or entry.get("message_preview") or "No message content",
                "success": entry.get("success", False),
                "error": entry.get("error"),
                "parsed_dt": dt
            })

    # Sort descending chronologically
    detailed_logs.sort(key=lambda x: x["parsed_dt"], reverse=True)
    
    # Remove helper datetime objects before returning JSON
    for log_item in detailed_logs:
        del log_item["parsed_dt"]
        
    return jsonify(detailed_logs)


@app.route('/api/scale/campaigns', methods=['GET', 'POST'])
def handle_campaigns():
    try:
        sys.path.insert(0, os.getcwd())
        from scale.campaign_manager import list_campaigns, create_campaign
        if request.method == 'POST':
            data = request.json
            campaign = create_campaign(
                name=data.get("name"),
                city=data.get("city"),
                niches=data.get("niches"),
                daily_lead_target=int(data.get("daily_lead_target", 10)),
                duration_days=int(data.get("duration_days", 30)),
                notes=data.get("notes", "")
            )
            return jsonify(campaign)
        return jsonify(list_campaigns())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/scale/analytics')
def get_scale_analytics():
    try:
        sys.path.insert(0, os.getcwd())
        from scale.performance_tracker import (
            calculate_channel_metrics, 
            calculate_reply_metrics, 
            calculate_lead_metrics, 
            calculate_revenue_metrics, 
            load_all_data
        )
        data = load_all_data()
        return jsonify({
            "channels": calculate_channel_metrics(data),
            "replies": calculate_reply_metrics(data),
            "leads": calculate_lead_metrics(data),
            "revenue": calculate_revenue_metrics(data)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/scale/expansion')
def get_expansion():
    try:
        sys.path.insert(0, os.getcwd())
        from scale.city_manager import get_expansion_roadmap
        config = load_json("ceo_config.json", {})
        cities = config.get("outreach", {}).get("cities", ["Uromi"])
        current_city = cities[0] if cities else "Uromi"
        return jsonify(get_expansion_roadmap(current_city))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/evolution/lessons')
def get_lessons():
    return jsonify(load_json("results/knowledge/lessons_learned.json", []))


@app.route('/api/evolution/optimizations')
def get_optimizations():
    return jsonify(load_json("results/knowledge/optimizations_log.json", []))


@app.route('/api/workflow/state', methods=['GET', 'POST'])
def handle_workflow_state():
    state_path = "results/ceo/workflow_state.json"
    if request.method == 'POST':
        try:
            new_state = request.json
            # Add timestamp if advancing
            new_state["last_updated"] = datetime.now().isoformat()
            os.makedirs("results/ceo", exist_ok=True)
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(new_state, f, indent=4, ensure_ascii=False)
            return jsonify({"success": True, "state": new_state})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    # GET method
    default_state = {
        "current_step": "audit",  # audit, craft, outreach
        "last_updated": datetime.now().isoformat(),
        "status": "idle" # idle, running, waiting
    }
    w_state = load_json(state_path, default_state)
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
        try:
            os.makedirs(os.path.dirname(state_path), exist_ok=True)
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(w_state, f, indent=4, ensure_ascii=False)
        except:
            pass
            
    return jsonify(w_state)


# ─────────────────────────────────────────────────────────────────────────────
# ACTION ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/api/run-command', methods=['POST'])
def run_command():
    data = request.json or {}
    command = data.get("command", "")

    if not command:
        return jsonify({"success": False, "error": "No command provided"})

    # Security — only allow whitelisted commands
    allowed_prefixes = [
        "python intelligence/lead_finder.py",
        "python intelligence/lead_enricher.py",
        "python intelligence/general_auditor.py",
        "python intelligence/email_verifier.py",
        "python outreach/message_writer.py",
        "python scale/sample_site_builder.py",
        "python outreach/email_sender.py",
        "python outreach/whatsapp_sender.py",
        "python outreach/instagram_sender.py",
        "python outreach/facebook_sender.py",
        "python response_management/reply_monitor.py",
        "python response_management/reply_handler.py",
        "python scale/campaign_manager.py",
        "python scale/performance_tracker.py",
        "python intelligence/self_optimizer.py",
        "python ai_ceo.py",
    ]

    if not any(command.startswith(p) for p in allowed_prefixes):
        return jsonify({"success": False, "error": "Command not allowed"})

    cmd_parts = command.split()
    if cmd_parts and cmd_parts[0] == "python":
        venv_python = os.path.join(os.getcwd(), "venv", "Scripts", "python.exe")
        if os.path.exists(venv_python):
            cmd_parts[0] = venv_python

    # Copy environment and inject/prepend current working directory into PYTHONPATH
    env = os.environ.copy()
    cwd = os.getcwd()
    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = cwd + os.pathsep + env["PYTHONPATH"]
    else:
        env["PYTHONPATH"] = cwd

    try:
        result = subprocess.run(
            cmd_parts,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=300,
            cwd=cwd,
            env=env
        )
        return jsonify({
            "success": result.returncode == 0,
            "output": result.stdout[-2000:] if result.stdout else "",
            "error": result.stderr[-500:] if result.stderr else "",
            "command": command
        })
    except subprocess.TimeoutExpired:
        return jsonify({"success": False, "error": "Command timed out", "command": command})
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "command": command})


@app.route('/api/stream-command')
def stream_command():
    command = request.args.get("command", "")
    if not command:
        return "No command provided", 400

    # Security — same whitelist as run-command
    allowed_prefixes = [
        "python intelligence/lead_finder.py",
        "python intelligence/lead_enricher.py",
        "python intelligence/general_auditor.py",
        "python intelligence/email_verifier.py",
        "python outreach/message_writer.py",
        "python scale/sample_site_builder.py",
        "python outreach/email_sender.py",
        "python outreach/whatsapp_sender.py",
        "python outreach/instagram_sender.py",
        "python outreach/facebook_sender.py",
        "python response_management/reply_monitor.py",
        "python response_management/reply_handler.py",
        "python scale/campaign_manager.py",
        "python scale/performance_tracker.py",
        "python intelligence/self_optimizer.py",
        "python ai_ceo.py",
    ]

    if not any(command.startswith(p) for p in allowed_prefixes):
        return "Command not allowed", 403

    def generate():
        process = None
        try:
            cmd_parts = command.split()
            if cmd_parts and cmd_parts[0] == "python":
                venv_python = os.path.join(os.getcwd(), "venv", "Scripts", "python.exe")
                if os.path.exists(venv_python):
                    cmd_parts[0] = venv_python

            # Copy environment and inject/prepend current working directory into PYTHONPATH
            env = os.environ.copy()
            cwd = os.getcwd()
            if "PYTHONPATH" in env:
                env["PYTHONPATH"] = cwd + os.pathsep + env["PYTHONPATH"]
            else:
                env["PYTHONPATH"] = cwd

            process = subprocess.Popen(
                cmd_parts,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                cwd=cwd,
                env=env,
                bufsize=1
            )
            
            yield f"data: {json.dumps({'type': 'start', 'command': command})}\n\n"

            for line in iter(process.stdout.readline, ''):
                if line:
                    yield f"data: {json.dumps({'type': 'output', 'line': line.strip()})}\n\n"
            
            process.stdout.close()
            return_code = process.wait()
            process = None
            
            yield f"data: {json.dumps({'type': 'end', 'success': return_code == 0, 'code': return_code})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            if process and process.poll() is None:
                try:
                    process.terminate()
                    # Wait up to 3 seconds for termination
                    for _ in range(30):
                        if process.poll() is not None:
                            break
                        import time
                        time.sleep(0.1)
                    if process.poll() is None:
                        process.kill()
                except Exception:
                    pass

    return Response(generate(), mimetype='text/event-stream')


@app.route('/api/approve-reply', methods=['POST'])
def approve_reply():
    data = request.json or {}
    message_id = data.get("message_id")
    edit_body = data.get("edit_body")

    try:
        from response_management.reply_handler import approve_reply as _approve
        success = _approve(message_id, edit_body)
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/reject-reply', methods=['POST'])
def reject_reply():
    data = request.json or {}
    message_id = data.get("message_id")
    reason = data.get("reason", "")

    try:
        from response_management.reply_handler import reject_reply as _reject
        success = _reject(message_id, reason)
        return jsonify({"success": success})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/approve-all', methods=['POST'])
def approve_all():
    data = request.json or {}
    intent = data.get("intent", "interested")

    try:
        from response_management.reply_handler import approve_all_by_intent
        count = approve_all_by_intent(intent)
        return jsonify({"success": True, "count": count})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/send-queued-replies', methods=['POST'])
def send_queued():
    try:
        from response_management.reply_monitor import send_queued_replies
        send_queued_replies()
        return jsonify({"success": True, "message": "Queued replies sent"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/update-lead', methods=['POST'])
def update_lead():
    data = request.json or {}
    name = data.get("name")
    updates = data.get("updates", {})
    
    if not name:
        return jsonify({"success": False, "error": "No lead name provided"})
        
    updated_any = False
    
    # 1. Update enriched_leads.json
    enriched_path = "results/leads/enriched_leads.json"
    if os.path.exists(enriched_path):
        enriched = load_json(enriched_path, [])
        for l in enriched:
            if l.get("name") == name:
                for k, v in updates.items():
                    l[k] = v
                updated_any = True
                break
        with open(enriched_path, "w", encoding="utf-8") as f:
            json.dump(enriched, f, indent=2, ensure_ascii=False)
            
    # 2. Update leads.json
    leads_path = "results/leads/leads.json"
    if os.path.exists(leads_path):
        leads = load_json(leads_path, [])
        for l in leads:
            if l.get("name") == name:
                for k, v in updates.items():
                    # Only update fields that exist in leads.json or are important
                    l[k] = v
                updated_any = True
                break
        with open(leads_path, "w", encoding="utf-8") as f:
            json.dump(leads, f, indent=2, ensure_ascii=False)
            
    return jsonify({"success": updated_any})


def sync_master_sequence_to_files(sequences):
    """
    Split and synchronize master sequence list into individual lead files.
    Uses the exact same naming scheme (safe_name with underscores) as the Python sender scripts.
    """
    if not isinstance(sequences, list):
        return
        
    for lead_seq in sequences:
        lead_name = lead_seq.get("lead")
        if not lead_name:
            continue
            
        # Use same safe name format as the Python sender scripts
        safe_name = lead_name.replace(" ", "_").replace("/", "_").replace("&", "and")
        
        # 1. Update {safe_name}_sequence.json
        os.makedirs("results/messages/sequences", exist_ok=True)
        ind_seq_path = f"results/messages/sequences/{safe_name}_sequence.json"
        with open(ind_seq_path, "w", encoding="utf-8") as f:
            json.dump(lead_seq.get("sequence", []), f, indent=2, ensure_ascii=False)
            
        # 2. Update {safe_name}_emails.json (for email sender)
        email_sequence = [m for m in lead_seq.get("sequence", []) if m.get("channel") == "email"]
        if email_sequence:
            os.makedirs("results/emails", exist_ok=True)
            email_path = f"results/emails/{safe_name}_emails.json"
            email_data = {}
            for i, email_msg in enumerate(email_sequence, 1):
                email_data[f"email_{i}"] = {
                    "subject": email_msg.get("subject", ""),
                    "body": email_msg.get("content", ""),
                    "send_day": email_msg.get("day", 1)
                }
            with open(email_path, "w", encoding="utf-8") as f:
                json.dump(email_data, f, indent=2, ensure_ascii=False)
                
        # 3. Update channel-specific JSON files for other channels
        wa_data = {}
        ig_data = {}
        fb_data = {}
        wa_count, ig_count, fb_count = 1, 1, 1
        
        for msg in lead_seq.get("sequence", []):
            ch = msg.get("channel")
            if ch == "whatsapp":
                wa_data[f"wa_{wa_count}"] = {
                    "to": msg.get("to", ""),
                    "message": msg.get("content", ""),
                    "send_day": msg.get("day", 1),
                    "channel": "whatsapp"
                }
                wa_count += 1
            elif ch == "instagram":
                ig_data[f"ig_{ig_count}"] = {
                    "to": msg.get("to", ""),
                    "message": msg.get("content", ""),
                    "send_day": msg.get("day", 1),
                    "channel": "instagram"
                }
                ig_count += 1
            elif ch == "facebook":
                fb_data[f"fb_{fb_count}"] = {
                    "to": msg.get("to", ""),
                    "message": msg.get("content", ""),
                    "send_day": msg.get("day", 1),
                    "channel": "facebook"
                }
                fb_count += 1
        
        # Write individual channel files
        if wa_data:
            os.makedirs("results/messages/whatsapp", exist_ok=True)
            with open(f"results/messages/whatsapp/{safe_name}_whatsapp.json", "w", encoding="utf-8") as f:
                json.dump(wa_data, f, indent=2, ensure_ascii=False)
        if ig_data:
            os.makedirs("results/messages/instagram", exist_ok=True)
            with open(f"results/messages/instagram/{safe_name}_instagram.json", "w", encoding="utf-8") as f:
                json.dump(ig_data, f, indent=2, ensure_ascii=False)
        if fb_data:
            os.makedirs("results/messages/facebook", exist_ok=True)
            with open(f"results/messages/facebook/{safe_name}_facebook.json", "w", encoding="utf-8") as f:
                json.dump(fb_data, f, indent=2, ensure_ascii=False)


@app.route('/api/outreach/sequences', methods=['GET', 'POST'])
def handle_outreach_sequences():
    seq_path = "results/messages/sequences/master_sequence.json"
    if request.method == 'POST':
        try:
            new_sequences = request.json
            
            # Save master sequence
            os.makedirs("results/messages/sequences", exist_ok=True)
            with open(seq_path, "w", encoding="utf-8") as f:
                json.dump(new_sequences, f, indent=2, ensure_ascii=False)
            
            # Synchronize to individual lead files
            sync_master_sequence_to_files(new_sequences)
            
            return jsonify({"success": True, "message": "Sequences updated and synchronized successfully"})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
            
    return jsonify(load_json(seq_path, []))


@app.route('/api/lifestyle/state', methods=['GET', 'POST'])
def handle_lifestyle_state():
    state_path = "results/ceo/lifestyle_state.json"
    if request.method == 'POST':
        try:
            updates = request.json
            current = load_json(state_path, {})
            current.update(updates)
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(current, f, indent=4, ensure_ascii=False)
            return jsonify({"success": True, "state": current})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
            
    # GET method
    return jsonify(load_json(state_path, {
        "is_running": True,
        "last_run": None,
        "next_scheduled_run": None,
        "status": "idle",
        "current_task": None,
        "completed_runs": 0,
        "failed_runs": 0
    }))


@app.route('/api/lifestyle/logs')
def get_lifestyle_logs():
    return jsonify(load_json("results/ceo/lifestyle_log.json", []))


@app.route('/api/lifestyle/run', methods=['POST'])
def force_lifestyle_run():
    state_path = "results/ceo/lifestyle_state.json"
    try:
        current = load_json(state_path, {})
        current["next_scheduled_run"] = datetime.now().isoformat()
        current["is_running"] = True
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=4, ensure_ascii=False)
        return jsonify({"success": True, "message": "Daily Lifestyle Loop triggered immediately!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/health')
def health():
    return jsonify({
        "status": "running",
        "time": datetime.now().isoformat(),
        "version": "1.0"
    })


def start_lifestyle_daemon():
    pid_file = "results/ceo/lifestyle_daemon.pid"
    if os.path.exists(pid_file):
        try:
            with open(pid_file, "r") as f:
                pid = int(f.read().strip())
            
            # Check if process exists on Windows
            import ctypes
            PROCESS_QUERY_INFORMATION = 0x0400
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, False, pid)
            if handle != 0:
                ctypes.windll.kernel32.CloseHandle(handle)
                print("Daily Lifestyle Daemon is already running.")
                return
        except Exception as err:
            print(f"Error checking daemon PID: {err}")
            
    try:
        os.makedirs("results/ceo", exist_ok=True)
        # Run python daily_lifestyle_daemon.py in a separate process
        proc = subprocess.Popen([sys.executable, "daily_lifestyle_daemon.py"])
        with open(pid_file, "w") as f:
            f.write(str(proc.pid))
        print(f"Daily Lifestyle Daemon started with PID {proc.pid}.")
    except Exception as e:
        print(f"Failed to start Daily Lifestyle Daemon: {e}")


if __name__ == "__main__":
    print("\nAI CEO Dashboard Server")
    print("=" * 40)
    print("API:       http://localhost:5055/api")
    print("Dashboard: http://localhost:5055/")
    print("=" * 40 + "\n")
    
    # Synchronize sequences on startup
    seq_path = "results/messages/sequences/master_sequence.json"
    if os.path.exists(seq_path):
        try:
            print("🔄 Synchronizing sequence files on startup...")
            with open(seq_path, "r", encoding="utf-8") as f:
                sequences = json.load(f)
            sync_master_sequence_to_files(sequences)
            print("✅ Synchronization complete.")
        except Exception as e:
            print(f"⚠️ Failed to synchronize sequences: {e}")
            
    start_lifestyle_daemon()
    app.run(host="0.0.0.0", port=5055, debug=False)