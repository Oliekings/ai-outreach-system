import json
import os

def load_reply_log() -> dict:
    path = "results/replies/reply_log.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "replies": [],
        "stats": {
            "interested": 0,
            "not_interested": 0,
            "question": 0,
            "out_of_office": 0,
            "total": 0
        }
    }

def save_reply_log(log: dict):
    with open("results/replies/reply_log.json", "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
