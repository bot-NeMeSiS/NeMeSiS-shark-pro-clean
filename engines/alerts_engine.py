"""Premium alerts foundation. Does not send messages by itself."""
from __future__ import annotations


ALERT_TYPES = [
    "gol", "inicio_partido", "pick_nuevo", "cuota_interesante",
    "favorito_en_directo", "resumen_post_partido", "video_resumen_disponible",
    "cambio_estado",
]


def alerts_foundation_snapshot(enabled: bool = False) -> dict:
    return {
        "ok": True,
        "enabled": bool(enabled),
        "status": "ALERTAS_PREPARADAS" if enabled else "DESACTIVADAS_POR_DEFECTO",
        "types": ALERT_TYPES,
        "channels": ["Telegram", "PWA futura"],
        "rules": ["Sin spam", "Configurable", "No enviar automáticamente en validación"],
    }
