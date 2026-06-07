from datetime import datetime, timedelta


VALID_ROLES = {"FREE", "PRO", "ELITE", "ADMIN"}


def normalize_role(role):
    role = str(role or "FREE").strip().upper()
    return role if role in VALID_ROLES else "FREE"


def parse_iso_date(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except Exception:
        return None


def membership_status_meta(user, today):
    membership = normalize_role((user or {}).get("membership"))
    end_date = parse_iso_date((user or {}).get("membership_end_date"))
    if membership in {"FREE", "ADMIN"}:
        return {"status": "permanent", "days_left": None, "expired": False}
    if not end_date:
        return {"status": "permanent", "days_left": None, "expired": False}
    days_left = (end_date - today).days
    if days_left < 0:
        return {"status": "expired", "days_left": 0, "expired": True}
    return {"status": "active_until", "days_left": days_left, "expired": False}


def membership_end_from_duration(duration, custom_end="", today=None):
    duration = str(duration or "permanent").strip().lower()
    if duration in {"", "permanent", "manual"}:
        return ""
    if duration == "custom":
        return str(custom_end or "").strip()[:10]
    try:
        days = int(duration)
    except Exception:
        return ""
    if days <= 0:
        return ""
    today = today or datetime.now().date()
    return (today + timedelta(days=days)).isoformat()

