"""
crm.py
Mock CRM – saves client records as JSON and simulates notifications.
"""
from __future__ import annotations

import json
import random
import string
from datetime import datetime, timezone
from pathlib import Path

CRM_DIR = Path(__file__).parent / "crm_data"
CRM_DIR.mkdir(exist_ok=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _gen_crm_id() -> str:
    suffix = "".join(random.choices(string.hexdigits.upper(), k=6))
    return f"ZAP-{datetime.now().strftime('%Y%m%d')}-{suffix}"


def _make_record(
    crm_id: str,
    profile: dict,
    client_card: str,
    onboarding_script: str,
    urls: list[str],
) -> dict:
    return {
        "crm_id": crm_id,
        "created_at": _now(),
        "status": "active",
        "urls_scanned": urls,
        "profile": profile,
        "client_card": client_card,
        "onboarding_script": onboarding_script,
        "notifications_sent": [],
        "activity_log": [
            {
                "timestamp": _now(),
                "action": "record_created",
                "actor": "AI Onboarding Bot",
                "note": "רשומת לקוח נוצרה אוטומטית",
            }
        ],
    }


# ── Public API ────────────────────────────────────────────────────────────────
def _find_duplicate(business_name: str, urls: list[str]) -> Path | None:
    """Return the path of an existing record matching by business name or URL."""
    urls_set = {u.strip().rstrip("/").lower() for u in urls if u}
    for fp in CRM_DIR.glob("*.json"):
        try:
            with open(fp, "r", encoding="utf-8-sig") as f:
                rec = json.load(f)
            existing_name = (
                rec.get("profile", {}).get("business_name", "").strip()
            )
            if existing_name.lower() == business_name.strip().lower():
                return fp
            existing_urls = {
                u.strip().rstrip("/").lower()
                for u in rec.get("urls_scanned", [])
            }
            if urls_set & existing_urls:
                return fp
        except Exception:
            continue
    return None


def save_client(
    profile: dict,
    client_card: str,
    onboarding_script: str,
    urls: list[str],
) -> dict:
    """Create or update a CRM record, replacing any duplicate by name or URL."""
    business_name = profile.get("business_name", "")
    duplicate = _find_duplicate(business_name, urls)
    if duplicate:
        with open(duplicate, "r", encoding="utf-8-sig") as f:
            old = json.load(f)
        crm_id = old["crm_id"]
        duplicate.unlink()
    else:
        crm_id = _gen_crm_id()

    record = _make_record(crm_id, profile, client_card, onboarding_script, urls)
    file_path = CRM_DIR / f"{crm_id}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)
    return record


def add_activity(
    crm_id: str, action: str, note: str, actor: str = "AI Onboarding Bot"
) -> None:
    """Append an activity-log entry to an existing record."""
    file_path = CRM_DIR / f"{crm_id}.json"
    if not file_path.exists():
        return
    with open(file_path, "r", encoding="utf-8-sig") as f:
        record = json.load(f)
    record["activity_log"].append(
        {"timestamp": _now(), "action": action, "actor": actor, "note": note}
    )
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)


def load_client(crm_id: str) -> dict | None:
    """Load and return a single CRM record, or None if not found."""
    file_path = CRM_DIR / f"{crm_id}.json"
    if not file_path.exists():
        return None
    with open(file_path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def list_clients() -> list[dict]:
    """Return a deduplicated summary list of all CRM records, newest first."""
    seen: set[str] = set()
    result: list[dict] = []

    for fp in sorted(CRM_DIR.glob("*.json"), reverse=True):
        try:
            with open(fp, "r", encoding="utf-8-sig") as f:
                rec = json.load(f)
        except Exception:
            continue

        name = rec.get("profile", {}).get("business_name", "").strip().lower()
        if not name or name in seen:
            try:
                fp.unlink()
            except Exception:
                pass
            continue

        seen.add(name)
        result.append(
            {
                "crm_id": rec["crm_id"],
                "created_at": rec["created_at"],
                "business_name": rec["profile"].get("business_name", "—"),
                "owner": rec["profile"].get("owner_name", "—"),
                "phone": rec["profile"].get("phone_primary", "—"),
                "region": rec["profile"].get("region", "—"),
                "status": rec["status"],
            }
        )
    return result


def _append_notification(crm_id: str, entry: dict) -> None:
    file_path = CRM_DIR / f"{crm_id}.json"
    if not file_path.exists():
        return
    with open(file_path, "r", encoding="utf-8-sig") as f:
        record = json.load(f)
    record["notifications_sent"].append(entry)
    record["activity_log"].append(
        {
            "timestamp": entry["timestamp"],
            "action": f"notification_sent_{entry['channel'].lower()}",
            "actor": "AI Onboarding Bot",
            "note": f"נשלח {entry['channel']} ל-{entry['recipient']}",
        }
    )
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)


def simulate_send_whatsapp(crm_id: str, phone: str, message: str) -> None:
    """Simulate sending a WhatsApp message and log it."""
    _append_notification(
        crm_id,
        {
            "timestamp": _now(),
            "channel": "WhatsApp",
            "recipient": phone,
            "message": message,
            "status": "sent_simulated",
        },
    )


def simulate_send_email(
    crm_id: str, email: str, subject: str, body: str
) -> None:
    """Simulate sending an email and log it."""
    _append_notification(
        crm_id,
        {
            "timestamp": _now(),
            "channel": "Email",
            "recipient": email,
            "subject": subject,
            "message": body,
            "status": "sent_simulated",
        },
    )
