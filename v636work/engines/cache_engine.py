def cache_health(items):
    return {
        "items": len(items or []),
        "status": "READY",
        "policy": "SQLite persistent cache with short TTL for live surfaces.",
    }
