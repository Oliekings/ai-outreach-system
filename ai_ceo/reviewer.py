import os
import json
import sys
from datetime import datetime
from utils.symbols import Symbol

sys.stdout.reconfigure(encoding="utf-8")


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
        email_sequence = [
            m for m in lead_seq.get("sequence", []) if m.get("channel") == "email"
        ]
        if email_sequence:
            os.makedirs("results/emails", exist_ok=True)
            email_path = f"results/emails/{safe_name}_emails.json"
            email_data = {}
            for i, email_msg in enumerate(email_sequence, 1):
                email_data[f"email_{i}"] = {
                    "subject": email_msg.get("subject", ""),
                    "body": email_msg.get("content", ""),
                    "send_day": email_msg.get("day", 1),
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
                    "channel": "whatsapp",
                }
                wa_count += 1
            elif ch == "instagram":
                ig_data[f"ig_{ig_count}"] = {
                    "to": msg.get("to", ""),
                    "message": msg.get("content", ""),
                    "send_day": msg.get("day", 1),
                    "channel": "instagram",
                }
                ig_count += 1
            elif ch == "facebook":
                fb_data[f"fb_{fb_count}"] = {
                    "to": msg.get("to", ""),
                    "message": msg.get("content", ""),
                    "send_day": msg.get("day", 1),
                    "channel": "facebook",
                }
                fb_count += 1

        # Write individual channel files
        if wa_data:
            os.makedirs("results/messages/whatsapp", exist_ok=True)
            with open(
                f"results/messages/whatsapp/{safe_name}_whatsapp.json",
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(wa_data, f, indent=2, ensure_ascii=False)
        if ig_data:
            os.makedirs("results/messages/instagram", exist_ok=True)
            with open(
                f"results/messages/instagram/{safe_name}_instagram.json",
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(ig_data, f, indent=2, ensure_ascii=False)
        if fb_data:
            os.makedirs("results/messages/facebook", exist_ok=True)
            with open(
                f"results/messages/facebook/{safe_name}_facebook.json",
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(fb_data, f, indent=2, ensure_ascii=False)


def review_all_pending_messages(autonomous: bool = False) -> dict:
    """
    Reviews all pending outreach messages in master_sequence.json.
    Approves them if they meet quality standards, or edits/rejects them.
    If autonomous is True, automatically transitions eligible queued messages to approved.
    """
    results = {"reviewed": 0, "approved": 0, "needs_edit": 0, "rejected": 0}

    seq_file = "results/messages/sequences/master_sequence.json"
    if not os.path.exists(seq_file):
        print("   No master sequence found.")
        return results

    try:
        with open(seq_file, "r", encoding="utf-8") as f:
            sequences = json.load(f)
    except Exception as e:
        print(f"   Error loading master sequence: {e}")
        return results

    updated = False

    for lead_seq in sequences:
        lead_name = lead_seq.get("lead", "Unknown")
        for msg in lead_seq.get("sequence", []):
            status = msg.get("status", "queued")
            if status != "queued":
                continue

            results["reviewed"] += 1
            content = msg.get("content", "")
            content_lower = content.lower()

            # Simple heuristic review
            has_placeholders = (
                "[" in content
                or "]" in content
                or "<" in content
                or ">" in content
                or "placeholder" in content_lower
                or "insert here" in content_lower
                or "insert_here" in content_lower
            )

            if len(content.strip()) < 20:
                msg["status"] = "rejected"
                msg["review_notes"] = "Message too short."
                results["rejected"] += 1
                updated = True
                print(f"   {Symbol.WARN} Rejected message for {lead_name} (Too short)")
            elif has_placeholders:
                msg["status"] = "needs_edit"
                msg["review_notes"] = "Contains unreplaced placeholders."
                results["needs_edit"] += 1
                updated = True
                print(f"   ✏️  Flagged message for {lead_name} (Contains placeholders)")
            else:
                if autonomous:
                    msg["status"] = "approved"
                    msg["review_notes"] = "Auto-approved by AI CEO."
                    results["approved"] += 1
                    updated = True
                    print(f"   {Symbol.CHECK} Auto-approved message for {lead_name}")
                else:
                    # Stays queued, but counted as reviewed
                    print(
                        f"   ⏳ Message for {lead_name} meets criteria, waiting for human approval"
                    )

    if updated:
        try:
            os.makedirs(os.path.dirname(seq_file), exist_ok=True)
            with open(seq_file, "w", encoding="utf-8") as f:
                json.dump(sequences, f, indent=2, ensure_ascii=False)
            sync_master_sequence_to_files(sequences)
        except Exception as e:
            print(f"   ⚠️  Failed to save updated master sequence: {e}")

    return results
