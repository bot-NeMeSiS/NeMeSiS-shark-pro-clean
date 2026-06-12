def delivery_health_label(diagnostics=None):
    diagnostics = diagnostics or {}
    if diagnostics.get("configured") or (diagnostics.get("token_present") and diagnostics.get("chat_id_present")):
        return "OK"
    if diagnostics.get("token_present") or diagnostics.get("chat_id_present"):
        return "Revisar"
    return "Pendiente"

