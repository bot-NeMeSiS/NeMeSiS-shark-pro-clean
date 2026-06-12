import hashlib


def dispatch_signature(date_key, alert_type, target_key):
    raw = f"{date_key}:{alert_type}:{target_key}".lower()
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:18]


def build_alert_queue(triggers, date_key, favorites_count=0, picks_count=0):
    queue = []
    for trigger in triggers:
        alert_type = trigger.get("key") or "daily"
        target = f"{alert_type}:{favorites_count}:{picks_count}"
        queue.append(
            {
                "signature": dispatch_signature(date_key, alert_type, target),
                "alert_type": alert_type,
                "target_key": target,
                "priority": int(trigger.get("priority") or 50),
                "label": trigger.get("label") or alert_type,
                "status": "PENDING",
            }
        )
    return sorted(queue, key=lambda item: item["priority"], reverse=True)


def should_skip_duplicate(existing_signatures, signature):
    return signature in set(existing_signatures or [])
