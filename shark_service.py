def build_product_context(picks=None, recommendations=None, as_int_func=None):
    picks = list(picks or [])
    recommendations = list(recommendations or [])
    best = picks[0] if picks else (recommendations[0] if recommendations else {})
    to_int = as_int_func or (lambda value, default=0: int(value or default))
    score = to_int(best.get("confidence") or best.get("score"), 0)
    return {
        "score": score,
        "confidence": score,
        "risk": best.get("risk_level") or best.get("risk") or "Medio",
        "reason": best.get("reasoning") or best.get("reason") or "SHARK espera datos suficientes antes de recomendar.",
        "value": best.get("value_label") or ("Detectado" if best.get("odds") else "Pendiente"),
        "summary": "SHARK combina calendario, picks, cuotas disponibles, favoritos e histórico para explicar oportunidades sin inventar datos.",
        "items": picks or recommendations,
    }

