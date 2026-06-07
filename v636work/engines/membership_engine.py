PLAN_ORDER = {"FREE": 0, "PRO": 1, "ELITE": 2, "ADMIN": 3}

FEATURE_MIN_PLAN = {
    "live_basic": "FREE",
    "picks_free": "FREE",
    "picks_pro": "PRO",
    "picks_elite": "ELITE",
    "recommendations_basic": "FREE",
    "recommendations_pro": "PRO",
    "auto_picks": "ELITE",
    "combis_basic": "PRO",
    "combis_advanced": "ELITE",
    "shark_basic": "FREE",
    "shark_pro": "PRO",
    "shark_elite": "ELITE",
    "telegram_basic": "FREE",
    "telegram_premium": "PRO",
    "bankroll_tracking": "PRO",
    "advanced_stats": "ELITE",
}

MEMBERSHIP_LIMITS = {
    "FREE": {
        "daily_picks": 2,
        "recommendations": 3,
        "combi_matches": 0,
        "shark_questions": 3,
        "telegram_level": "basic",
        "value_bets": False,
        "auto_picks": False,
    },
    "PRO": {
        "daily_picks": 8,
        "recommendations": 12,
        "combi_matches": 3,
        "shark_questions": 20,
        "telegram_level": "pro",
        "value_bets": "basic",
        "auto_picks": False,
    },
    "ELITE": {
        "daily_picks": 50,
        "recommendations": 50,
        "combi_matches": 8,
        "shark_questions": 999,
        "telegram_level": "priority",
        "value_bets": "advanced",
        "auto_picks": True,
    },
    "ADMIN": {
        "daily_picks": 999,
        "recommendations": 999,
        "combi_matches": 8,
        "shark_questions": 999,
        "telegram_level": "admin",
        "value_bets": "advanced",
        "auto_picks": True,
    },
}

PLAN_BADGES = {
    "FREE": {"label": "FREE", "class": "badge-free", "tone": "Azul básico"},
    "PRO": {"label": "PRO", "class": "badge-pro", "tone": "Azul premium"},
    "ELITE": {"label": "ELITE", "class": "badge-elite", "tone": "Dorado"},
    "ADMIN": {"label": "ADMIN", "class": "badge-admin", "tone": "Operación"},
}

FEATURE_LABELS = {
    "picks_pro": "Picks PRO",
    "picks_elite": "Picks ELITE",
    "recommendations_pro": "Recomendaciones SHARK",
    "auto_picks": "Auto Picks completo",
    "combis_basic": "Combinadas básicas",
    "combis_advanced": "Combinadas automáticas avanzadas",
    "shark_pro": "SHARK PRO",
    "shark_elite": "SHARK completo",
    "telegram_premium": "Telegram premium",
    "bankroll_tracking": "Seguimiento de banca",
    "advanced_stats": "Estadísticas avanzadas",
}


def normalize_membership(value):
    plan = str(value or "FREE").strip().upper()
    return plan if plan in PLAN_ORDER else "FREE"


def get_user_membership(user):
    if not user:
        return "FREE"
    if isinstance(user, dict):
        return normalize_membership(user.get("membership") or user.get("role"))
    return normalize_membership(getattr(user, "membership", None) or getattr(user, "role", None))


def can_access_feature(user, feature_name):
    membership = get_user_membership(user)
    required = FEATURE_MIN_PLAN.get(feature_name, "ELITE")
    return PLAN_ORDER.get(membership, 0) >= PLAN_ORDER.get(required, 2)


def get_membership_limits(membership):
    return dict(MEMBERSHIP_LIMITS.get(normalize_membership(membership), MEMBERSHIP_LIMITS["FREE"]))


def get_upgrade_message(feature_name, current_membership):
    current = normalize_membership(current_membership)
    required = FEATURE_MIN_PLAN.get(feature_name, "ELITE")
    label = FEATURE_LABELS.get(feature_name, feature_name.replace("_", " ").title())
    if PLAN_ORDER[current] >= PLAN_ORDER[required]:
        return f"{label} incluido en tu plan {current}."
    return f"{label}: disponible en {required}. Mejora tu plan para desbloquearlo."


def get_membership_badge(membership):
    plan = normalize_membership(membership)
    return dict(PLAN_BADGES.get(plan, PLAN_BADGES["FREE"]))


def locked_feature(feature_name, current_membership):
    required = FEATURE_MIN_PLAN.get(feature_name, "ELITE")
    return {
        "feature": feature_name,
        "label": FEATURE_LABELS.get(feature_name, feature_name.replace("_", " ").title()),
        "required": required,
        "current": normalize_membership(current_membership),
        "message": get_upgrade_message(feature_name, current_membership),
        "badge": get_membership_badge(required),
    }


def membership_context(user):
    membership = get_user_membership(user)
    limits = get_membership_limits(membership)
    locked = [
        locked_feature(feature, membership)
        for feature in FEATURE_MIN_PLAN
        if not can_access_feature({"membership": membership}, feature)
    ]
    return {
        "membership": membership,
        "badge": get_membership_badge(membership),
        "limits": limits,
        "locked": locked,
        "is_free": membership == "FREE",
        "is_pro": membership == "PRO",
        "is_elite": membership in {"ELITE", "ADMIN"},
    }
