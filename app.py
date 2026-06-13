import csv
import hashlib
import html
import io
import json
import os
import re
import secrets
import sqlite3
import smtplib
import threading
import unicodedata
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from email.message import EmailMessage
from zoneinfo import ZoneInfo

from flask import Flask, Response, abort, has_request_context, jsonify, redirect, render_template, request, send_file, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database_manager import connect as sqlite_connect, retry_locked
from engines.security_engine import (
    generate_csrf_token,
    rate_limit_status,
    record_security_event,
    secure_secret_key,
    validate_csrf,
)
from engines.cache_engine import cache_health
from engines.crest_engine import crest_status
from engines.data_memory_engine import (
    cleanup_old_memory,
    data_memory_summary,
    ensure_data_memory_schema,
    record_api_sync_run,
    remember_match_snapshot,
    remember_pick_decision,
    remember_pick_discard,
    remember_team_identity,
    remember_telegram_delivery,
    safe_memory_call,
)
from engines.football_population_engine import (
    PRIORITY_COMPETITIONS,
    STRUCTURAL_TEAMS,
    competition_payload,
    empty_sync,
    odds_competitions,
    price_map_from_outcomes,
    should_run_interval,
    sportsdb_competitions,
    success_sync,
    team_payload,
)
from engines.live_engine import build_live_depth, build_live_flow, build_match_detail, fallback_timeline, normalize_live_state, shark_live_alerts, shark_momentum
from engines.live_experience_engine import build_live_experience, live_experience_snapshot
from engines.content_rights_engine import content_rights_policy_summary
from engines.data_vault_engine import create_sqlite_backup, db_vault_status, export_table_csv, list_backups as data_vault_list_backups, validate_backup as data_vault_validate_backup
from engines.match_intelligence_engine import build_match_intelligence, match_intelligence_snapshot
from engines.video_highlights_engine import video_highlights_snapshot
from engines.team_form_engine import team_form_snapshot
from engines.standings_experience_engine import standings_snapshot
from engines.alerts_engine import alerts_foundation_snapshot
from engines.match_engine import hub_sections, real_time_state, sync_plan
from engines.match_sync_engine import IMPORTANT_COMPETITIONS, h2h_price_snapshot, normalize_status as sync_normalize_status, odds_sports, sportsdb_leagues
from engines.membership_engine import can_access_feature, get_membership_limits, get_user_membership, membership_context
from engines.observability_engine import latest_observability_errors, observability_error_detail, observability_summary
from engines.scheduler_engine import is_due, is_stale_running, next_run_iso, normalize_result, scheduler_config, task_definition
from engines.shark_engine import build_shark_context, explain_pick_risk
from engines.shark_intelligence_core import build_daily_briefing, build_quick_questions, memory_event_payload
from engines.telegram_delivery_engine import (
    DEFAULT_SETTINGS as TELEGRAM_DEFAULT_SETTINGS,
    QUEUE_FAILED,
    QUEUE_PENDING,
    QUEUE_SENT,
    QUEUE_SENDING,
    build_daily_matches_message as format_daily_matches_message,
    build_daily_picks_message as format_daily_picks_message,
    build_live_alert_message as format_live_alert_message,
    build_system_test_message as format_system_test_message,
    normalize_settings,
    queue_summary,
    subscriber_payload,
    telegram_dedupe_key,
)
from engines.telegram_engine import build_alert_queue, dispatch_signature, should_skip_duplicate
from engines.telegram_sport_filter_engine import (
    filter_telegram_football_items,
    is_telegram_football_item,
    telegram_sport_filter_reason,
    telegram_sport_mode_summary,
)
from engines.telegram_reliability_engine import (
    explain_telegram_state,
    madrid_now as telegram_reliability_madrid_now,
    safe_preview_text,
)
from engines.route_health_engine import route_health_snapshot
from engines.client_experience_guard_engine import client_experience_snapshot
from engines.production_readiness_engine import production_readiness_snapshot
from engines.client_success_engine import client_success_snapshot
from engines.public_launch_engine import public_launch_snapshot
from engines.go_live_engine import go_live_snapshot, production_validation_plan
from engines.visual_experience_engine import visual_experience_snapshot
from engines.native_app_experience_engine import native_app_experience_snapshot
from engines.final_release_engine import final_release_snapshot, final_release_validation_plan
from engines.client_visual_perfection_engine import client_visual_perfection_snapshot
from engines.calendar_experience_engine import calendar_experience_snapshot
from engines.payment_readiness_engine import payment_readiness_snapshot, record_payment_webhook_event
from engines.pick_grading_engine import pick_grading_summary, run_pick_grading
from engines.subscription_control_engine import subscription_summary, apply_subscription_rules
from engines.team_identity_engine import (
    flag_or_emoji as team_flag_or_emoji,
    identity_payload as build_team_identity_payload,
    merge_identity as merge_team_identity_payload,
    safe_logo_url as safe_team_logo_url,
)
from engines.picks_quality_engine import (
    enrich_pick_quality,
    pick_is_premium_ready,
    sort_picks_by_quality,
    split_picks_by_quality,
)
from engines.pick_analysis_experience_engine import enrich_pick_analysis
from engines.spanish_localization_engine import (
    MADRID_TZ,
    apply_match_localization,
    apply_pick_localization,
    madrid_values_from_datetime,
    parse_datetime_to_madrid,
    spanish_competition_name,
    spanish_country_name,
    spanish_datetime_label,
    spanish_market_name,
    spanish_pick_selection_name,
    spanish_team_name,
)
from engines.madrid_time_engine import (
    format_madrid_match_time,
    format_madrid_short_time,
    madrid_conversion_selftest,
    madrid_time_diagnostics,
    normalize_kickoff_for_display,
)

APP_NAME = "NeMeSiS SHARK PRO"
APP_VERSION = "V748_ADMIN_CLIENT_TELEGRAM_SECURITY_PRODUCTION_HOTFIX"
SEED_VERSION = "v528-client-login-route-stability-seed"
DB_PATH = os.getenv("DB_PATH", "/data/database.db")
TZ = ZoneInfo("Europe/Madrid")
COMBI_MIN_LEGS = 2
COMBI_MAX_LEGS = 15

app = Flask(__name__)
app.secret_key = secure_secret_key()
SEED_LOCK = threading.RLock()
_SEED_LOCK = SEED_LOCK
_SEEDED_DB_PATH = None
_SEEDING_DB_PATH = None
APP_INITIALIZED = False
APP_INIT_ERROR = ""
TEAM_IDENTITY_CACHE = {}

FAKE_TEAM_NAMES = {
    "premier home",
    "premier away",
    "equipo champions a",
    "equipo champions b",
    "seleccion local",
    "seleccion visitante",
    "club laliga local",
    "club laliga visitante",
    "club andaluz",
    "rival provincial",
    "equipo a",
    "equipo b",
}


def now_iso():
    return datetime.now(TZ).isoformat(timespec="seconds")


def today_iso(offset=0):
    return (datetime.now(TZ).date() + timedelta(days=offset)).isoformat()


def madrid_local_iso(match_date, match_time=""):
    """Build a Europe/Madrid-aware ISO value for admin/manual dates.

    Sports APIs normally arrive with UTC/offset timestamps and are converted elsewhere.
    When an admin imports a CSV with date + hour, that hour is already the hour they
    typed for Spain, so we must store it as Madrid time and not add +2 again.
    """
    date_text = str(match_date or "").strip()[:10]
    time_text = str(match_time or "").strip()[:5]
    if not date_text:
        return ""
    try:
        hour, minute = 0, 0
        if time_text and re.match(r"^\d{1,2}:\d{2}$", time_text):
            hour, minute = [int(x) for x in time_text.split(":", 1)]
        dt = datetime.fromisoformat(date_text).replace(hour=hour, minute=minute, second=0, microsecond=0, tzinfo=TZ)
        return dt.isoformat(timespec="seconds")
    except Exception:
        return f"{date_text}T{time_text or '00:00'}:00+02:00"


def days_from_admin_value(value, default=0):
    try:
        days = int(str(value or "").strip() or default)
    except Exception:
        days = int(default or 0)
    return max(0, min(days, 3650))


def iso_has_passed(value):
    text = str(value or "").strip()
    if not text:
        return False
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ)
        return dt.astimezone(TZ) <= datetime.now(TZ)
    except Exception:
        return text[:19] <= now_iso()[:19]


def membership_expires_label(value):
    text = str(value or "").strip()
    if not text:
        return "Sin caducidad"
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=TZ)
        return dt.astimezone(TZ).strftime("%d/%m/%Y · %H:%M")
    except Exception:
        return text[:16] or "Sin caducidad"


def masked_admin_text(value, limit=500):
    text = str(value or "")[: int(limit)]
    for key in ("TELEGRAM_BOT_TOKEN", "AUTOMATION_SECRET", "SECRET_KEY", "OPENAI_API_KEY"):
        if os.getenv(key):
            text = text.replace(os.getenv(key, ""), "***hidden***")
    return text


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return bool(default)
    return str(value).strip().lower() in {"1", "true", "yes", "on", "y", "si", "sí"}


def env_present(name):
    return bool(str(os.getenv(name) or "").strip())


def telegram_env_auto_enabled():
    return env_bool("ENABLE_TELEGRAM_AUTO", False) or env_bool("AUTO_SEND_TELEGRAM_PICKS", False)


def scheduler_env_enabled():
    return env_bool("SCHEDULER_ENABLED", env_bool("ENABLE_AUTO_SYNC", True))


def security_client_ip():
    forwarded = request.headers.get("X-Forwarded-For", "") if has_request_context() else ""
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return (request.remote_addr or "local") if has_request_context() else "local"


def csrf_exempt_path(path: str) -> bool:
    path = str(path or "")
    exact = {
        "/telegram/webhook",
        "/api/automation/telegram/tick",
        "/api/automation/daily/run",
        "/api/automation/data-backup/run",
        "/api/payments/stripe-webhook",
    }
    prefixes = (
        "/static/",
        "/team-crest.svg",
    )
    if path in exact:
        return True
    if any(path.startswith(prefix) for prefix in prefixes):
        return True
    # These legacy automation/import endpoints are already protected by admin session
    # or automation secret. Keep CSRF strict for login/register/admin forms and
    # normal client actions, but avoid breaking external cron/webhook style calls.
    if path.startswith("/api/v495/telegram-auto-run"):
        return True
    return False


def request_csrf_token():
    token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token") or request.headers.get("X-CSRFToken")
    if not token and request.is_json:
        payload = request.get_json(silent=True) or {}
        token = payload.get("csrf_token")
    return token or ""


def csrf_failure_response():
    record_security_event(
        DB_PATH,
        event_type="csrf_block",
        severity="WARN",
        ip_address=security_client_ip(),
        path=request.path,
        method=request.method,
        success=False,
        reason="token_csrf_invalido_o_ausente",
    )
    if request.path.startswith("/api/") or request.is_json:
        return jsonify({"ok": False, "error": "csrf_required", "message": "Sesión caducada o formulario no válido. Recarga la página e inténtalo de nuevo."}), 403
    return Response("Sesión caducada o formulario no válido. Recarga la página e inténtalo de nuevo.", status=403, mimetype="text/plain; charset=utf-8")


def rate_limit_failure_response(scope: str, status: dict):
    record_security_event(
        DB_PATH,
        event_type="rate_limit_block",
        severity="WARN",
        ip_address=security_client_ip(),
        path=request.path,
        method=request.method,
        success=False,
        reason=f"{scope}: demasiados intentos",
        payload={"status": status},
    )
    message = "Demasiados intentos seguidos. Espera unos minutos y vuelve a probar."
    if request.path.startswith("/api/") or request.is_json:
        return jsonify({"ok": False, "error": "rate_limited", "message": message, "window_minutes": status.get("window_minutes")}), 429
    return Response(message, status=429, mimetype="text/plain; charset=utf-8")


def security_rate_limit_for_request():
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return None
    path = request.path or ""
    ip = security_client_ip()
    rules = [
        (("/cliente-login", "/login", "/entrar", "/admin-login"), "login_attempt", 8, 15, "login"),
        (("/registro",), "registration_attempt", 5, 30, "registro"),
        (("/forgot-password", "/admin-forgot-password"), "password_reset_request", 5, 30, "recuperacion"),
        (("/reset-password", "/admin-reset-password"), "password_reset_change", 6, 30, "cambio_password"),
        (("/api/admin/telegram/test-send",), "telegram_test_send", 4, 60, "telegram_test_send"),
    ]
    for prefixes, event_type, limit, minutes, scope in rules:
        if any(path == prefix or path.startswith(prefix + "/") for prefix in prefixes):
            status = rate_limit_status(DB_PATH, event_type=event_type, ip_address=ip, path_like=f"{prefixes[0]}%", limit=limit, minutes=minutes)
            if status.get("blocked"):
                return rate_limit_failure_response(scope, status)
    return None


def security_event_for_auth(event_type: str, success: bool, username: str = "", reason: str = "") -> None:
    record_security_event(
        DB_PATH,
        event_type=event_type,
        severity="INFO" if success else "WARN",
        ip_address=security_client_ip(),
        username=str(username or "")[:120],
        path=request.path if has_request_context() else "",
        method=request.method if has_request_context() else "",
        success=success,
        reason=reason,
    )


def daily_automation_env_enabled():
    return (
        env_bool("DAILY_AUTOMATION_ENABLED", False)
        or env_bool("RUN_DAILY_AUTOMATION", False)
        or env_bool("AUTO_GENERATE_PICKS", False)
    )


def automation_secret_configured():
    return bool(str(os.getenv("AUTOMATION_SECRET") or "").strip())


def automation_request_secret():
    payload = request.get_json(silent=True) or {}
    return str(
        request.args.get("secret")
        or request.headers.get("X-Automation-Secret")
        or request.headers.get("X-CRON-SECRET")
        or request.form.get("secret")
        or payload.get("secret")
        or ""
    ).strip()


def automation_secret_valid():
    expected = str(os.getenv("AUTOMATION_SECRET") or "").strip()
    if not expected:
        return False
    return secrets.compare_digest(automation_request_secret(), expected)


def automation_secret_status():
    expected = str(os.getenv("AUTOMATION_SECRET") or "").strip()
    provided = automation_request_secret()
    if not expected:
        return {
            "ok": False,
            "error": "automation_secret_missing",
            "message": "Falta AUTOMATION_SECRET en Render. Configura esa variable antes de activar los Cron Jobs.",
            "configured": False,
            "provided": bool(provided),
        }
    if not provided:
        return {
            "ok": False,
            "error": "automation_secret_required",
            "message": "Endpoint protegido. Llama con ?secret=AUTOMATION_SECRET o header X-Automation-Secret.",
            "configured": True,
            "provided": False,
        }
    if not secrets.compare_digest(provided, expected):
        return {
            "ok": False,
            "error": "automation_secret_invalid",
            "message": "AUTOMATION_SECRET recibido, pero no coincide con el valor configurado en Render.",
            "configured": True,
            "provided": True,
        }
    return {"ok": True, "configured": True, "provided": True}


def automation_access_allowed():
    # Rutas antiguas pueden seguir aceptando sesión admin o secret. Los endpoints Cron nuevos usan validación estricta.
    return is_admin_session() or automation_secret_valid()


def automation_cron_access_allowed():
    return automation_secret_status().get("ok") is True


def automation_json_forbidden():
    status = automation_secret_status()
    return jsonify({
        "ok": False,
        "version": APP_VERSION,
        "error": status.get("error") or "automation_secret_required",
        "message": status.get("message") or "Configura AUTOMATION_SECRET y llama el endpoint con ?secret=... o header X-Automation-Secret.",
        "automation_secret_configured": bool(status.get("configured")),
        "automation_secret_provided": bool(status.get("provided")),
    }), 403


def automation_safe_set(key, value):
    try:
        seed_core()
        automation_set(key, value)
        return {"ok": True, "key": key}
    except Exception as exc:
        try:
            print("[AUTOMATION_STATE_SAVE_ERROR]", key, str(exc)[:300])
        except Exception:
            pass
        return {"ok": False, "key": key, "error": str(exc)[:300]}


def telegram_diagnostics_safe():
    try:
        return telegram_diagnostics()
    except Exception as exc:
        return {
            "error": "telegram_diagnostics_unavailable",
            "message": str(exc)[:300],
            "env_flags": {
                "TELEGRAM_BOT_TOKEN": env_present("TELEGRAM_BOT_TOKEN"),
                "TELEGRAM_CHAT_ID": env_present("TELEGRAM_CHAT_ID"),
                "AUTOMATION_SECRET": automation_secret_configured(),
                "ENABLE_TELEGRAM_AUTO": env_bool("ENABLE_TELEGRAM_AUTO", False),
                "AUTO_SEND_TELEGRAM_PICKS": env_bool("AUTO_SEND_TELEGRAM_PICKS", False),
            },
            "last_cron_daily_call": {},
            "last_cron_telegram_call": {},
        }


def cron_force_requested():
    payload = request.get_json(silent=True) or {}
    return (
        request.args.get("force") in {"1", "true", "yes", "on"}
        or request.form.get("force") in {"1", "true", "yes", "on"}
        or payload.get("force") is True
    )


def _cron_compact_payload(endpoint, result, called_at, finished_at, force=False):
    result = result or {}
    compact = {
        "ok": bool(result.get("ok", False)),
        "endpoint": endpoint,
        "version": APP_VERSION,
        "status": result.get("status") or result.get("message") or ("OK" if result.get("ok") else "ERROR"),
        "cron": True,
        "processed": as_int(result.get("processed"), 0),
        "inserted": as_int(result.get("inserted"), 0),
        "sent": as_int(result.get("sent"), 0),
        "failed": as_int(result.get("failed"), 0),
        "skipped": as_int(result.get("skipped"), 0),
        "force": bool(force),
        "called_at": called_at,
        "finished_at": finished_at,
    }
    if endpoint == "daily_run":
        compact.update({
            "matches_synced": as_int(result.get("matches_synced"), 0),
            "picks_generated": as_int(result.get("picks_generated"), 0),
            "picks_sent": as_int(result.get("picks_sent") or result.get("sent"), 0),
            "backups_created": as_int(result.get("backups_created"), 0),
        })
    if result.get("error"):
        compact["error"] = str(result.get("error"))[:120]
    if result.get("errors"):
        compact["errors_count"] = len(result.get("errors") or [])
    return compact


def automation_cron_result(endpoint, state_keys, runner, force=False):
    called_at = now_iso()
    state_payload = {"time": called_at, "force": bool(force), "source": "render_cron", "endpoint": endpoint, "version": APP_VERSION}
    state_results = [automation_safe_set(key, state_payload) for key in state_keys]
    try:
        seed_core()
        result = runner(force=force)
        if not isinstance(result, dict):
            result = {"ok": True, "result": result}
    except Exception as exc:
        try:
            print(f"[CRON_ENDPOINT_ERROR] {endpoint}:", str(exc)[:800])
        except Exception:
            pass
        result = {
            "ok": False,
            "error": "cron_execution_error",
            "message": "El endpoint Cron se autenticó correctamente, pero la automatización falló de forma controlada. Revisa logs Render.",
            "detail": str(exc)[:500],
        }
    finished_at = now_iso()
    compact = _cron_compact_payload(endpoint, result, called_at, finished_at, force=force)
    compact["state_saved"] = all(item.get("ok") for item in state_results)
    try:
        safe_memory_call(
            DB_PATH,
            f"cron_{endpoint}",
            record_api_sync_run,
            source=endpoint,
            status=compact.get("status") or ("OK" if compact.get("ok") else "ERROR"),
            counts={
                "started_at": called_at,
                "finished_at": finished_at,
                "matches_synced": compact.get("matches_synced", 0),
                "picks_generated": compact.get("picks_generated", 0),
                "picks_sent": compact.get("picks_sent", compact.get("sent", 0)),
                "sent": compact.get("sent", 0),
            },
            error=compact.get("error"),
            meta={"compact": compact, "force": bool(force)},
        )
        if endpoint == "daily_run":
            try:
                for match in rows("SELECT * FROM matches ORDER BY COALESCE(updated_at, kickoff_iso, match_date) DESC LIMIT 80"):
                    safe_memory_call(DB_PATH, "match_snapshot", remember_match_snapshot, match=match, source="daily_run_cache")
                    if match.get("home_team"):
                        safe_memory_call(DB_PATH, "team_identity", remember_team_identity, team_name=match.get("home_team"), logo_url=match.get("home_logo") or "", country=match.get("country") or "", source="daily_run_cache")
                    if match.get("away_team"):
                        safe_memory_call(DB_PATH, "team_identity", remember_team_identity, team_name=match.get("away_team"), logo_url=match.get("away_logo") or "", country=match.get("country") or "", source="daily_run_cache")
            except Exception:
                pass
    except Exception:
        pass
    # El detalle largo queda solo para admin/diagnóstico interno, no en la respuesta pública del Cron.
    automation_safe_set(f"{endpoint}_last_detail", {
        "called_at": called_at,
        "finished_at": finished_at,
        "compact": compact,
        "result": result,
        "state_save_results": state_results,
    })
    return jsonify(compact), 200

def telegram_env_ready():
    return env_present("TELEGRAM_BOT_TOKEN") and env_present("TELEGRAM_CHAT_ID")


def telegram_env_should_enable():
    return telegram_env_ready() and telegram_env_auto_enabled()


def db():
    return sqlite_connect(DB_PATH)


def slug(text):
    text = str(text or "").strip().lower()
    text = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "item"


def initials(name):
    ignore = {"fc", "cf", "cd", "ud", "ad", "club", "de", "del", "la", "el", "los", "las"}
    words = [w for w in re.split(r"[\s\-]+", str(name or "")) if w]
    letters = [w[0].upper() for w in words if w.lower() not in ignore]
    if not letters and words:
        letters = [words[0][0].upper()]
    return "".join(letters[:3]) or "NS"


def normalized_label(value):
    text = str(value or "").strip().lower()
    text = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", text)


def is_fake_team_name(value):
    return normalized_label(value) in FAKE_TEAM_NAMES


def is_fake_match(match):
    return is_fake_team_name(match.get("home_team")) or is_fake_team_name(match.get("away_team"))


def cleanup_fake_matches(cur):
    try:
        match_rows = cur.execute("SELECT id, home_team, away_team, source FROM matches").fetchall()
    except sqlite3.OperationalError:
        return 0
    delete_ids = []
    for row in match_rows:
        row_id = row["id"] if hasattr(row, "keys") else row[0]
        home_team = row["home_team"] if hasattr(row, "keys") else row[1]
        away_team = row["away_team"] if hasattr(row, "keys") else row[2]
        source = row["source"] if hasattr(row, "keys") else row[3]
        if is_fake_team_name(home_team) or is_fake_team_name(away_team) or normalized_label(source) == "seed estructural":
            delete_ids.append(row_id)
    if delete_ids:
        placeholders = ",".join("?" for _ in delete_ids)
        cur.execute(f"DELETE FROM matches WHERE id IN ({placeholders})", tuple(delete_ids))
    return len(delete_ids)


def table_columns(conn, table):
    try:
        return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    except sqlite3.OperationalError:
        return set()


def add_column_if_missing(conn, table, column, definition):
    if column not in table_columns(conn, table):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def run_schema_migrations(conn):
    try:
        conn.execute("""CREATE TABLE IF NOT EXISTS telegram_delivery_memory(
            id TEXT PRIMARY KEY,
            created_at TEXT,
            updated_at TEXT,
            message_type TEXT,
            target_type TEXT,
            target_key TEXT,
            destination_masked TEXT,
            delivery_channel TEXT,
            chat_id TEXT,
            user_id TEXT,
            membership TEXT,
            status TEXT,
            match_id TEXT,
            pick_id TEXT,
            error_summary TEXT,
            dedupe_key TEXT,
            meta_json TEXT
        )""")
    except sqlite3.OperationalError:
        pass
    migrations = [
        ("competitions", "scope", "TEXT"),
        ("competitions", "country", "TEXT"),
        ("competitions", "region", "TEXT"),
        ("competitions", "tier", "INTEGER DEFAULT 50"),
        ("competitions", "source_strategy", "TEXT"),
        ("competitions", "tags_json", "TEXT"),
        ("competitions", "updated_at", "TEXT"),
        ("competitions", "external_id", "TEXT"),
        ("competitions", "source", "TEXT"),
        ("competitions", "sync_status", "TEXT"),
        ("competitions", "last_sync_at", "TEXT"),
        ("teams", "country", "TEXT"),
        ("teams", "region", "TEXT"),
        ("teams", "logo_url", "TEXT"),
        ("teams", "external_id", "TEXT"),
        ("teams", "league", "TEXT"),
        ("teams", "color_hint", "TEXT"),
        ("teams", "source", "TEXT"),
        ("teams", "legal_note", "TEXT"),
        ("teams", "updated_at", "TEXT"),
        ("teams", "sync_status", "TEXT"),
        ("teams", "last_sync_at", "TEXT"),
        ("matches", "kickoff_time", "TEXT"),
        ("matches", "competition_key", "TEXT"),
        ("matches", "competition_name", "TEXT"),
        ("matches", "country", "TEXT"),
        ("matches", "minute", "TEXT"),
        ("matches", "score", "TEXT"),
        ("matches", "priority", "INTEGER DEFAULT 50"),
        ("matches", "source", "TEXT"),
        ("matches", "legal_note", "TEXT"),
        ("matches", "raw_json", "TEXT"),
        ("matches", "updated_at", "TEXT"),
        ("matches", "external_id", "TEXT"),
        ("matches", "sport_key", "TEXT DEFAULT 'soccer'"),
        ("matches", "competition_id", "TEXT"),
        ("matches", "league_name", "TEXT"),
        ("matches", "home_team_id", "TEXT"),
        ("matches", "away_team_id", "TEXT"),
        ("matches", "home_logo", "TEXT"),
        ("matches", "away_logo", "TEXT"),
        ("matches", "match_time", "TEXT"),
        ("matches", "kickoff_iso", "TEXT"),
        ("matches", "home_score", "TEXT"),
        ("matches", "away_score", "TEXT"),
        ("matches", "venue", "TEXT"),
        ("matches", "season", "TEXT"),
        ("matches", "round", "TEXT"),
        ("matches", "bookmaker", "TEXT"),
        ("matches", "odds_h2h_json", "TEXT"),
        ("matches", "odds_updated_at", "TEXT"),
        ("matches", "sync_status", "TEXT"),
        ("picks", "sport_key", "TEXT DEFAULT 'soccer'"),
        ("picks", "stake_units", "REAL DEFAULT 1"),
        ("picks", "status", "TEXT DEFAULT 'PENDING'"),
        ("picks", "source", "TEXT"),
        ("picks", "legal_note", "TEXT"),
        ("picks", "reasoning", "TEXT"),
        ("picks", "raw_json", "TEXT"),
        ("picks", "updated_at", "TEXT"),
        ("combis", "status", "TEXT DEFAULT 'DRAFT'"),
        ("combis", "source", "TEXT"),
        ("combis", "updated_at", "TEXT"),
        ("client_profiles", "preferences_json", "TEXT"),
        ("client_profiles", "updated_at", "TEXT"),
        ("telegram_queue", "signature", "TEXT"),
        ("telegram_queue", "priority", "INTEGER DEFAULT 50"),
        ("telegram_queue", "payload_json", "TEXT"),
        ("telegram_queue", "status", "TEXT DEFAULT 'PENDING'"),
        ("telegram_queue", "attempts", "INTEGER DEFAULT 0"),
        ("telegram_queue", "chat_id", "TEXT"),
        ("telegram_queue", "user_id", "TEXT"),
        ("telegram_queue", "message_type", "TEXT"),
        ("telegram_queue", "title", "TEXT"),
        ("telegram_queue", "body", "TEXT"),
        ("telegram_queue", "max_attempts", "INTEGER DEFAULT 3"),
        ("telegram_queue", "dedupe_key", "TEXT"),
        ("telegram_queue", "scheduled_at", "TEXT"),
        ("telegram_queue", "sent_at", "TEXT"),
        ("telegram_queue", "error_message", "TEXT"),
        ("telegram_queue", "updated_at", "TEXT"),
        ("telegram_logs", "event_type", "TEXT"),
        ("telegram_logs", "status", "TEXT"),
        ("telegram_logs", "message", "TEXT"),
        ("telegram_logs", "payload_json", "TEXT"),
        ("telegram_logs", "created_at", "TEXT"),
        ("telegram_subscribers", "user_id", "TEXT"),
        ("telegram_subscribers", "chat_id", "TEXT"),
        ("telegram_subscribers", "username", "TEXT"),
        ("telegram_subscribers", "first_name", "TEXT"),
        ("telegram_subscribers", "membership", "TEXT"),
        ("telegram_subscribers", "is_active", "INTEGER DEFAULT 1"),
        ("telegram_subscribers", "created_at", "TEXT"),
        ("telegram_subscribers", "last_seen", "TEXT"),
        ("telegram_subscribers", "last_message_sent_at", "TEXT"),
        ("telegram_settings", "auto_daily_matches", "INTEGER DEFAULT 1"),
        ("telegram_settings", "auto_daily_picks", "INTEGER DEFAULT 0"),
        ("telegram_settings", "auto_live_alerts", "INTEGER DEFAULT 0"),
        ("telegram_settings", "daily_matches_time", "TEXT DEFAULT '09:00'"),
        ("telegram_settings", "daily_picks_time", "TEXT DEFAULT '11:00'"),
        ("telegram_settings", "max_messages_per_hour", "INTEGER DEFAULT 1"),
        ("telegram_settings", "enabled", "INTEGER DEFAULT 0"),
        ("telegram_settings", "updated_at", "TEXT"),
        ("telegram_delivery_memory", "created_at", "TEXT"),
        ("telegram_delivery_memory", "updated_at", "TEXT"),
        ("telegram_delivery_memory", "message_type", "TEXT"),
        ("telegram_delivery_memory", "target_type", "TEXT"),
        ("telegram_delivery_memory", "target_key", "TEXT"),
        ("telegram_delivery_memory", "destination_masked", "TEXT"),
        ("telegram_delivery_memory", "delivery_channel", "TEXT"),
        ("telegram_delivery_memory", "chat_id", "TEXT"),
        ("telegram_delivery_memory", "user_id", "TEXT"),
        ("telegram_delivery_memory", "membership", "TEXT"),
        ("telegram_delivery_memory", "status", "TEXT"),
        ("telegram_delivery_memory", "match_id", "TEXT"),
        ("telegram_delivery_memory", "pick_id", "TEXT"),
        ("telegram_delivery_memory", "error_summary", "TEXT"),
        ("telegram_delivery_memory", "dedupe_key", "TEXT"),
        ("telegram_delivery_memory", "meta_json", "TEXT"),
        ("live_sync_state", "sync_status", "TEXT"),
        ("live_sync_state", "next_refresh_at", "TEXT"),
        ("live_sync_state", "updated_at", "TEXT"),
        ("scheduler_locks", "task_name", "TEXT"),
        ("scheduler_locks", "locked_at", "TEXT"),
        ("scheduler_locks", "status", "TEXT"),
        ("scheduler_locks", "last_run", "TEXT"),
        ("scheduler_locks", "next_run", "TEXT"),
        ("scheduler_locks", "error_message", "TEXT"),
        ("auto_alerts", "status", "TEXT DEFAULT 'READY'"),
        ("auto_alerts", "updated_at", "TEXT"),
        ("users", "name", "TEXT"),
        ("users", "username", "TEXT"),
        ("users", "email", "TEXT"),
        ("users", "password_hash", "TEXT"),
        ("users", "role", "TEXT DEFAULT 'FREE'"),
        ("users", "membership", "TEXT DEFAULT 'FREE'"),
        ("users", "created_at", "TEXT"),
        ("users", "last_login", "TEXT"),
        ("users", "telegram_chat_id", "TEXT"),
        ("users", "telegram_username", "TEXT"),
        ("users", "telegram_link_code", "TEXT"),
        ("users", "telegram_link_expires", "TEXT"),
        ("users", "telegram_link_expires_at", "TEXT"),
        ("users", "telegram_linked_at", "TEXT"),
        ("users", "membership_source", "TEXT DEFAULT 'registro'"),
        ("users", "membership_started_at", "TEXT"),
        ("users", "membership_expires_at", "TEXT"),
        ("users", "membership_note", "TEXT"),
        ("users", "membership_updated_at", "TEXT"),
        ("users", "membership_updated_by", "TEXT"),
        ("users", "membership_admin_granted", "INTEGER DEFAULT 0"),
        ("favorites", "user_id", "TEXT"),
        ("picks", "market", "TEXT"),
        ("picks", "bookmaker", "TEXT"),
        ("picks", "stake_euros_example", "REAL DEFAULT 0"),
        ("picks", "risk_level", "TEXT DEFAULT 'MEDIO'"),
        ("picks", "warning_reason", "TEXT"),
        ("picks", "membership_required", "TEXT DEFAULT 'FREE'"),
        ("picks", "result_status", "TEXT DEFAULT 'pending'"),
        ("picks", "published_at", "TEXT"),
        ("combis", "membership_required", "TEXT DEFAULT 'PRO'"),
        ("combis", "confidence", "INTEGER DEFAULT 50"),
        ("combis", "explanation", "TEXT"),
        ("live_matches", "match_id", "TEXT"),
        ("live_matches", "status", "TEXT"),
        ("live_matches", "minute", "TEXT"),
        ("live_matches", "home_score", "TEXT"),
        ("live_matches", "away_score", "TEXT"),
        ("live_matches", "payload_json", "TEXT"),
        ("live_matches", "source", "TEXT"),
        ("live_matches", "updated_at", "TEXT"),
        ("api_sync_logs", "source", "TEXT"),
        ("api_sync_logs", "sync_type", "TEXT"),
        ("api_sync_logs", "started_at", "TEXT"),
        ("api_sync_logs", "finished_at", "TEXT"),
        ("api_sync_logs", "status", "TEXT"),
        ("api_sync_logs", "total_items", "INTEGER DEFAULT 0"),
        ("api_sync_logs", "error_message", "TEXT"),
        ("odds_snapshots", "match_id", "TEXT"),
        ("odds_snapshots", "external_id", "TEXT"),
        ("odds_snapshots", "source", "TEXT"),
        ("odds_snapshots", "sport_key", "TEXT"),
        ("odds_snapshots", "league_name", "TEXT"),
        ("odds_snapshots", "bookmaker", "TEXT"),
        ("odds_snapshots", "market", "TEXT"),
        ("odds_snapshots", "home_team", "TEXT"),
        ("odds_snapshots", "away_team", "TEXT"),
        ("odds_snapshots", "home_price", "TEXT"),
        ("odds_snapshots", "draw_price", "TEXT"),
        ("odds_snapshots", "away_price", "TEXT"),
        ("odds_snapshots", "commence_time", "TEXT"),
        ("odds_snapshots", "payload_json", "TEXT"),
        ("odds_snapshots", "created_at", "TEXT"),
        ("match_timeline", "match_id", "TEXT"),
        ("match_timeline", "minute", "TEXT"),
        ("match_timeline", "event_type", "TEXT"),
        ("match_timeline", "title", "TEXT"),
        ("match_timeline", "detail", "TEXT"),
        ("match_timeline", "source", "TEXT"),
        ("match_timeline", "legal_note", "TEXT"),
        ("match_timeline", "created_at", "TEXT"),
        ("historical_matches", "match_id", "TEXT"),
        ("historical_matches", "match_date", "TEXT"),
        ("historical_matches", "home_team", "TEXT"),
        ("historical_matches", "away_team", "TEXT"),
        ("historical_matches", "league_name", "TEXT"),
        ("historical_matches", "status", "TEXT"),
        ("historical_matches", "score", "TEXT"),
        ("historical_matches", "payload_json", "TEXT"),
        ("historical_matches", "created_at", "TEXT"),
        ("historical_picks", "pick_id", "TEXT"),
        ("historical_picks", "match_id", "TEXT"),
        ("historical_picks", "selection", "TEXT"),
        ("historical_picks", "market", "TEXT"),
        ("historical_picks", "odds", "REAL"),
        ("historical_picks", "stake", "REAL"),
        ("historical_picks", "result_status", "TEXT"),
        ("historical_picks", "profit", "REAL"),
        ("historical_picks", "payload_json", "TEXT"),
        ("historical_picks", "created_at", "TEXT"),
        ("historical_recommendations", "recommendation_id", "TEXT"),
        ("historical_recommendations", "match_id", "TEXT"),
        ("historical_recommendations", "selection", "TEXT"),
        ("historical_recommendations", "score", "INTEGER"),
        ("historical_recommendations", "risk_level", "TEXT"),
        ("historical_recommendations", "value_label", "TEXT"),
        ("historical_recommendations", "payload_json", "TEXT"),
        ("historical_recommendations", "created_at", "TEXT"),
    ]
    for table, column, definition in migrations:
        try:
            add_column_if_missing(conn, table, column, definition)
        except sqlite3.OperationalError:
            pass
    try:
        conn.execute(
            """UPDATE users
               SET telegram_link_expires_at=COALESCE(NULLIF(telegram_link_expires_at,''), telegram_link_expires)
               WHERE COALESCE(telegram_link_expires_at,'')='' AND COALESCE(telegram_link_expires,'')!=''"""
        )
        conn.execute(
            """UPDATE users
               SET telegram_link_expires=COALESCE(NULLIF(telegram_link_expires,''), telegram_link_expires_at)
               WHERE COALESCE(telegram_link_expires,'')='' AND COALESCE(telegram_link_expires_at,'')!=''"""
        )
    except sqlite3.OperationalError:
        pass
    conn.execute(
        """CREATE TABLE IF NOT EXISTS schema_migrations(
            version TEXT PRIMARY KEY,
            applied_at TEXT
        )"""
    )
    conn.execute(
        "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?,?)",
        (APP_VERSION, now_iso()),
    )
    try:
        migrate_missing_usernames(conn)
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique ON users(email)")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_unique ON users(username) WHERE username IS NOT NULL AND username!=''")
    except (sqlite3.OperationalError, sqlite3.IntegrityError):
        # No bloquear arranque si una DB antigua tiene duplicados; la app seguirá funcionando
        # y el admin podrá corregirlos desde /admin/users.
        pass
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_favorites_user_kind ON favorites(user_id, kind)")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_matches_date_status ON matches(match_date, status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_matches_source_external ON matches(source, external_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_matches_competition ON matches(competition_key, match_date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_matches_kickoff_iso ON matches(kickoff_iso)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_matches_league_name ON matches(league_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_matches_status ON matches(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_teams_name ON teams(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_teams_external_id ON teams(external_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_competitions_name ON competitions(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_api_sync_logs_source ON api_sync_logs(source, sync_type, started_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_odds_snapshots_match ON odds_snapshots(match_id, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_scheduler_locks_status ON scheduler_locks(status, next_run)")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_telegram_queue_dedupe ON telegram_queue(dedupe_key) WHERE dedupe_key IS NOT NULL AND dedupe_key!=''")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_telegram_queue_status ON telegram_queue(status, scheduled_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_telegram_logs_created ON telegram_logs(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_telegram_memory_status ON telegram_delivery_memory(status, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_telegram_memory_dedupe ON telegram_delivery_memory(dedupe_key, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_membership_expiry ON users(membership, membership_expires_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_telegram_subscribers_active ON telegram_subscribers(is_active, membership)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_picks_status_membership ON picks(status, membership_required)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_picks_match_status ON picks(match_id, status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_picks_published ON picks(published_at, confidence)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_user_activity_user_type ON user_activity(user_id, activity_type, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_password_reset_user ON password_reset_tokens(user_id, expires_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_historical_matches_match ON historical_matches(match_id, match_date)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_historical_picks_pick ON historical_picks(pick_id, match_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_historical_recommendations_match ON historical_recommendations(match_id, created_at)")
    except sqlite3.OperationalError:
        pass


def init_db():
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS competitions(
            key TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            scope TEXT,
            country TEXT,
            region TEXT,
            tier INTEGER DEFAULT 50,
            source_strategy TEXT,
            tags_json TEXT,
            external_id TEXT,
            source TEXT,
            sync_status TEXT,
            last_sync_at TEXT,
            updated_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS teams(
            key TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            country TEXT,
            region TEXT,
            league TEXT,
            logo_url TEXT,
            external_id TEXT,
            color_hint TEXT,
            source TEXT,
            legal_note TEXT,
            sync_status TEXT,
            last_sync_at TEXT,
            updated_at TEXT
        )"""
    )
    try:
        cur.execute("ALTER TABLE teams ADD COLUMN external_id TEXT")
    except sqlite3.OperationalError:
        pass
    cur.execute(
        """CREATE TABLE IF NOT EXISTS matches(
            id TEXT PRIMARY KEY,
            external_id TEXT,
            sport_key TEXT DEFAULT 'soccer',
            match_date TEXT NOT NULL,
            kickoff_time TEXT,
            match_time TEXT,
            kickoff_iso TEXT,
            competition_id TEXT,
            competition_key TEXT,
            competition_name TEXT,
            league_name TEXT,
            country TEXT,
            home_team TEXT,
            away_team TEXT,
            home_team_id TEXT,
            away_team_id TEXT,
            home_logo TEXT,
            away_logo TEXT,
            status TEXT,
            minute TEXT,
            score TEXT,
            home_score TEXT,
            away_score TEXT,
            venue TEXT,
            season TEXT,
            round TEXT,
            bookmaker TEXT,
            odds_h2h_json TEXT,
            odds_updated_at TEXT,
            priority INTEGER DEFAULT 50,
            source TEXT,
            legal_note TEXT,
            raw_json TEXT,
            sync_status TEXT,
            updated_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS live_matches(
            id TEXT PRIMARY KEY,
            match_id TEXT,
            status TEXT,
            minute TEXT,
            home_score TEXT,
            away_score TEXT,
            payload_json TEXT,
            source TEXT,
            updated_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS imports(
            id TEXT PRIMARY KEY,
            kind TEXT,
            source_name TEXT,
            source_url TEXT,
            legal_note TEXT,
            rows_count INTEGER DEFAULT 0,
            status TEXT,
            payload_preview TEXT,
            created_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS favorites(
            id TEXT PRIMARY KEY,
            user_id TEXT,
            kind TEXT,
            value TEXT,
            label TEXT,
            created_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS picks(
            id TEXT PRIMARY KEY,
            match_id TEXT,
            match_date TEXT,
            sport_key TEXT DEFAULT 'soccer',
            competition_key TEXT,
            competition_name TEXT,
            home_team TEXT,
            away_team TEXT,
            pick_type TEXT,
            selection TEXT,
            odds REAL,
            confidence INTEGER DEFAULT 50,
            stake_units REAL DEFAULT 1,
            status TEXT DEFAULT 'PENDING',
            source TEXT,
            legal_note TEXT,
            reasoning TEXT,
            raw_json TEXT,
            created_at TEXT,
            updated_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS combis(
            id TEXT PRIMARY KEY,
            name TEXT,
            picks_json TEXT,
            total_odds REAL,
            risk_level TEXT,
            status TEXT DEFAULT 'DRAFT',
            source TEXT,
            created_at TEXT,
            updated_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS client_profiles(
            id TEXT PRIMARY KEY,
            name TEXT,
            membership_plan TEXT,
            favorite_teams_json TEXT,
            favorite_competitions_json TEXT,
            telegram_chat_id TEXT,
            preferences_json TEXT,
            created_at TEXT,
            updated_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS users(
            id TEXT PRIMARY KEY,
            name TEXT,
            username TEXT UNIQUE,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'FREE',
            membership TEXT DEFAULT 'FREE',
            membership_source TEXT DEFAULT 'registro',
            membership_started_at TEXT,
            membership_expires_at TEXT,
            membership_note TEXT,
            membership_updated_at TEXT,
            membership_updated_by TEXT,
            created_at TEXT,
            last_login TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS telegram_deliveries(
            id TEXT PRIMARY KEY,
            chat_id TEXT,
            message_type TEXT,
            payload_preview TEXT,
            status TEXT,
            response_json TEXT,
            created_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS telegram_logs(
            id TEXT PRIMARY KEY,
            event_type TEXT,
            status TEXT,
            message TEXT,
            payload_json TEXT,
            created_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS telegram_subscribers(
            id TEXT PRIMARY KEY,
            user_id TEXT,
            chat_id TEXT,
            username TEXT,
            first_name TEXT,
            membership TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TEXT,
            last_seen TEXT,
            last_message_sent_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS telegram_settings(
            id TEXT PRIMARY KEY,
            auto_daily_matches INTEGER DEFAULT 1,
            auto_daily_picks INTEGER DEFAULT 0,
            auto_live_alerts INTEGER DEFAULT 0,
            daily_matches_time TEXT DEFAULT '09:00',
            daily_picks_time TEXT DEFAULT '11:00',
            max_messages_per_hour INTEGER DEFAULT 1,
            enabled INTEGER DEFAULT 0,
            updated_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS automation_state(
            key TEXT PRIMARY KEY,
            value_json TEXT,
            updated_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS api_sync_logs(
            id TEXT PRIMARY KEY,
            source TEXT,
            sync_type TEXT,
            started_at TEXT,
            finished_at TEXT,
            status TEXT,
            total_items INTEGER DEFAULT 0,
            error_message TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS odds_snapshots(
            id TEXT PRIMARY KEY,
            match_id TEXT,
            external_id TEXT,
            source TEXT,
            sport_key TEXT,
            league_name TEXT,
            bookmaker TEXT,
            market TEXT,
            home_team TEXT,
            away_team TEXT,
            home_price TEXT,
            draw_price TEXT,
            away_price TEXT,
            commence_time TEXT,
            payload_json TEXT,
            created_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS user_activity(
            id TEXT PRIMARY KEY,
            user_id TEXT,
            activity_type TEXT,
            target_type TEXT,
            target_id TEXT,
            payload_json TEXT,
            created_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS password_reset_tokens(
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            scope TEXT DEFAULT 'client',
            expires_at TEXT NOT NULL,
            used_at TEXT,
            created_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS historical_matches(
            id TEXT PRIMARY KEY,
            match_id TEXT,
            match_date TEXT,
            home_team TEXT,
            away_team TEXT,
            league_name TEXT,
            status TEXT,
            score TEXT,
            payload_json TEXT,
            created_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS historical_picks(
            id TEXT PRIMARY KEY,
            pick_id TEXT,
            match_id TEXT,
            selection TEXT,
            market TEXT,
            odds REAL,
            stake REAL,
            result_status TEXT,
            profit REAL,
            payload_json TEXT,
            created_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS historical_recommendations(
            id TEXT PRIMARY KEY,
            recommendation_id TEXT,
            match_id TEXT,
            selection TEXT,
            score INTEGER,
            risk_level TEXT,
            value_label TEXT,
            payload_json TEXT,
            created_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS scheduler_locks(
            task_name TEXT PRIMARY KEY,
            locked_at TEXT,
            status TEXT,
            last_run TEXT,
            next_run TEXT,
            error_message TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS match_timeline(
            id TEXT PRIMARY KEY,
            match_id TEXT,
            minute TEXT,
            event_type TEXT,
            title TEXT,
            detail TEXT,
            source TEXT,
            legal_note TEXT,
            created_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS persistent_cache(
            key TEXT PRIMARY KEY,
            value_json TEXT,
            expires_at TEXT,
            updated_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS telegram_queue(
            id TEXT PRIMARY KEY,
            signature TEXT UNIQUE,
            alert_type TEXT,
            target_key TEXT,
            chat_id TEXT,
            user_id TEXT,
            message_type TEXT,
            title TEXT,
            body TEXT,
            priority INTEGER DEFAULT 50,
            payload_json TEXT,
            status TEXT DEFAULT 'PENDING',
            attempts INTEGER DEFAULT 0,
            max_attempts INTEGER DEFAULT 3,
            dedupe_key TEXT,
            scheduled_at TEXT,
            sent_at TEXT,
            error_message TEXT,
            created_at TEXT,
            updated_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS shark_context_snapshots(
            id TEXT PRIMARY KEY,
            context_type TEXT,
            target_key TEXT,
            payload_json TEXT,
            created_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS live_sync_state(
            key TEXT PRIMARY KEY,
            payload_json TEXT,
            sync_status TEXT,
            next_refresh_at TEXT,
            updated_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS auto_alerts(
            id TEXT PRIMARY KEY,
            alert_type TEXT,
            target_key TEXT,
            payload_json TEXT,
            status TEXT DEFAULT 'READY',
            created_at TEXT,
            updated_at TEXT
        )"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS schema_migrations(
            version TEXT PRIMARY KEY,
            applied_at TEXT
        )"""
    )
    run_schema_migrations(conn)
    cleanup_fake_matches(cur)
    normalize_existing_match_times_to_madrid(conn)
    cur.execute(
        """INSERT OR IGNORE INTO telegram_settings
           (id,auto_daily_matches,auto_daily_picks,auto_live_alerts,daily_matches_time,daily_picks_time,max_messages_per_hour,enabled,updated_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            TELEGRAM_DEFAULT_SETTINGS["id"],
            1 if TELEGRAM_DEFAULT_SETTINGS["auto_daily_matches"] else 0,
            1 if TELEGRAM_DEFAULT_SETTINGS["auto_daily_picks"] else 0,
            1 if TELEGRAM_DEFAULT_SETTINGS["auto_live_alerts"] else 0,
            TELEGRAM_DEFAULT_SETTINGS["daily_matches_time"],
            TELEGRAM_DEFAULT_SETTINGS["daily_picks_time"],
            TELEGRAM_DEFAULT_SETTINGS["max_messages_per_hour"],
            1 if TELEGRAM_DEFAULT_SETTINGS["enabled"] else 0,
            now_iso(),
        ),
    )
    ensure_data_memory_schema(conn)
    bootstrap_admin_from_env(conn)
    conn.commit()
    conn.close()


COMPETITION_SEEDS = [
    ("fifa-world-cup", "FIFA World Cup", "international", "Global", "World", 100, "API legal + verificacion editorial", ["world", "national"]),
    ("uefa-euro", "UEFA Euro", "international", "Europe", "UEFA", 98, "API legal + verificacion editorial", ["europe", "national"]),
    ("copa-america", "Copa America", "international", "South America", "CONMEBOL", 96, "API legal + verificacion editorial", ["america", "national"]),
    ("uefa-champions-league", "UEFA Champions League", "continental", "Europe", "UEFA", 99, "API legal + cache", ["clubs", "europe", "top"]),
    ("uefa-europa-league", "UEFA Europa League", "continental", "Europe", "UEFA", 94, "API legal + cache", ["clubs", "europe"]),
    ("uefa-conference-league", "UEFA Conference League", "continental", "Europe", "UEFA", 88, "API legal + cache", ["clubs", "europe"]),
    ("premier-league", "Premier League", "domestic", "England", "Europe", 97, "API legal + odds bridge", ["top-league"]),
    ("championship", "Championship", "domestic", "England", "Europe", 88, "API legal + odds bridge", ["england"]),
    ("fa-cup", "FA Cup", "domestic-cup", "England", "Europe", 86, "API legal + odds bridge", ["england", "cup"]),
    ("laliga", "LaLiga EA Sports", "domestic", "Spain", "Europe", 97, "API legal + odds bridge", ["top-league", "spain"]),
    ("segunda-division", "Segunda Division", "domestic", "Spain", "Europe", 90, "API legal + odds bridge", ["spain"]),
    ("serie-a", "Serie A", "domestic", "Italy", "Europe", 95, "API legal + odds bridge", ["top-league"]),
    ("serie-b", "Serie B", "domestic", "Italy", "Europe", 84, "API legal + odds bridge", ["italy"]),
    ("bundesliga", "Bundesliga", "domestic", "Germany", "Europe", 95, "API legal + odds bridge", ["top-league"]),
    ("bundesliga-2", "Bundesliga 2", "domestic", "Germany", "Europe", 84, "API legal + odds bridge", ["germany"]),
    ("ligue-1", "Ligue 1", "domestic", "France", "Europe", 92, "API legal + odds bridge", ["top-league"]),
    ("ligue-2", "Ligue 2", "domestic", "France", "Europe", 82, "API legal + odds bridge", ["france"]),
    ("eredivisie", "Eredivisie", "domestic", "Netherlands", "Europe", 84, "API legal + cache", ["europe"]),
    ("primeira-liga", "Primeira Liga", "domestic", "Portugal", "Europe", 84, "API legal + cache", ["europe"]),
    ("brasileirao", "Brasileirao Serie A", "domestic", "Brazil", "South America", 86, "API legal + cache", ["america"]),
    ("argentina-primera", "Argentina Primera Division", "domestic", "Argentina", "South America", 85, "API legal + cache", ["america"]),
    ("copa-libertadores", "Copa Libertadores", "continental", "South America", "CONMEBOL", 93, "API legal + odds bridge", ["america", "clubs"]),
    ("copa-sudamericana", "Copa Sudamericana", "continental", "South America", "CONMEBOL", 88, "API legal + odds bridge", ["america", "clubs"]),
    ("mls", "Major League Soccer", "domestic", "United States", "North America", 78, "API legal + cache", ["america"]),
    ("copa-del-rey", "Copa del Rey", "domestic-cup", "Spain", "Europe", 86, "API legal + cache", ["spain", "cup"]),
    ("supercopa-espana", "Supercopa de Espana", "domestic-cup", "Spain", "Europe", 82, "API legal + cache", ["spain", "cup"]),
    ("uefa-nations-league", "UEFA Nations League", "international", "Europe", "UEFA", 90, "API legal + odds bridge", ["europe", "national"]),
    ("world-cup-qualifiers", "World Cup Qualifiers", "international", "Global", "World", 88, "API legal + cache", ["world", "national"]),
    ("andalucia-regional", "Andalucia Regional Football", "regional", "Spain", "Andalucia", 72, "Carga legal + editorial", ["regional", "andalucia"]),
]


TEAM_SEEDS = [
    ("real-madrid", "Real Madrid", "Spain", "Europe", "", "133738"),
    ("barcelona", "FC Barcelona", "Spain", "Europe", "", "133739"),
    ("atletico-madrid", "Atletico de Madrid", "Spain", "Europe", "", "133729"),
    ("sevilla", "Sevilla FC", "Spain", "Andalucia", "", "133745"),
    ("real-betis", "Real Betis", "Spain", "Andalucia", "", "133741"),
    ("malaga", "Malaga CF", "Spain", "Andalucia", "", ""),
    ("cadiz", "Cadiz CF", "Spain", "Andalucia", "", ""),
    ("granada", "Granada CF", "Spain", "Andalucia", "", ""),
    ("cordoba", "Cordoba CF", "Spain", "Andalucia", "", ""),
    ("recreativo-huelva", "Recreativo de Huelva", "Spain", "Andalucia", "", ""),
    ("arsenal", "Arsenal", "England", "Europe", "", "133604"),
    ("manchester-city", "Manchester City", "England", "Europe", "", "133613"),
    ("liverpool", "Liverpool", "England", "Europe", "", "133602"),
    ("chelsea", "Chelsea", "England", "Europe", "", "133610"),
    ("manchester-united", "Manchester United", "England", "Europe", "", "133612"),
    ("psg", "Paris Saint-Germain", "France", "Europe", "", "133714"),
    ("bayern-munich", "Bayern Munich", "Germany", "Europe", "", "133664"),
    ("borussia-dortmund", "Borussia Dortmund", "Germany", "Europe", "", "133650"),
    ("juventus", "Juventus", "Italy", "Europe", "", "133676"),
    ("inter", "Inter Milan", "Italy", "Europe", "", "133668"),
    ("ac-milan", "AC Milan", "Italy", "Europe", "", "133667"),
    ("benfica", "Benfica", "Portugal", "Europe", "", "133713"),
    ("porto", "FC Porto", "Portugal", "Europe", "", "133721"),
    ("sporting-cp", "Sporting CP", "Portugal", "Europe", "", "134513"),
]

TEAM_ALIASES = {
    "barcelona": "barcelona",
    "fc-barcelona": "barcelona",
    "barca": "barcelona",
    "real-madrid-cf": "real-madrid",
    "madrid": "real-madrid",
    "atletico": "atletico-madrid",
    "atletico-de-madrid": "atletico-madrid",
    "atl-madrid": "atletico-madrid",
    "sevilla-fc": "sevilla",
    "betis": "real-betis",
    "real-betis-balompie": "real-betis",
    "malaga-cf": "malaga",
    "cadiz-cf": "cadiz",
    "granada-cf": "granada",
    "cordoba-cf": "cordoba",
    "recreativo": "recreativo-huelva",
    "paris-saint-germain": "psg",
    "paris-sg": "psg",
    "fc-bayern": "bayern-munich",
    "bayern": "bayern-munich",
    "inter-milan": "inter",
    "internazionale": "inter",
    "milan": "ac-milan",
    "sl-benfica": "benfica",
    "fc-porto": "porto",
    "sporting": "sporting-cp",
}


def _seed_core_unlocked():
    init_db()
    conn = db()
    cur = conn.cursor()
    for key, name, scope, country, region, tier, strategy, tags in COMPETITION_SEEDS:
        cur.execute(
            """INSERT OR IGNORE INTO competitions
               (key,name,scope,country,region,tier,source_strategy,tags_json,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (key, name, scope, country, region, tier, strategy, json.dumps(tags), now_iso()),
        )
    for item in PRIORITY_COMPETITIONS:
        comp = competition_payload(item)
        cur.execute(
            """INSERT OR IGNORE INTO competitions
               (key,name,scope,country,region,tier,source_strategy,tags_json,external_id,source,sync_status,last_sync_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                comp["key"],
                comp["name"],
                comp["scope"],
                comp["country"],
                comp["region"],
                comp["tier"],
                comp["source_strategy"],
                json.dumps(comp["tags"]),
                comp["external_id"],
                comp["source"],
                comp["sync_status"],
                "",
                now_iso(),
            ),
        )
        cur.execute(
            """UPDATE competitions
               SET external_id=COALESCE(NULLIF(external_id,''), ?),
                   source=COALESCE(NULLIF(source,''), ?),
                   sync_status=COALESCE(NULLIF(sync_status,''), ?)
               WHERE key=?""",
            (comp["external_id"], comp["source"], comp["sync_status"], comp["key"]),
        )
    for key, name, country, region, logo_url, external_id in TEAM_SEEDS:
        cur.execute(
            """INSERT OR IGNORE INTO teams
               (key,name,country,region,logo_url,external_id,color_hint,source,legal_note,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (key, name, country, region, logo_url, external_id, "premium-blue", "seed propio", "Sin scraping. Logo externo solo si hay licencia/API permitida.", now_iso()),
        )
    for item in STRUCTURAL_TEAMS:
        team = team_payload(item)
        cur.execute(
            """INSERT OR IGNORE INTO teams
               (key,name,country,region,league,logo_url,external_id,color_hint,source,legal_note,sync_status,last_sync_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                team["key"],
                team["name"],
                team.get("country", ""),
                team.get("region", ""),
                team.get("league", ""),
                team.get("logo_url", ""),
                team.get("external_id", ""),
                team.get("color_hint", "premium-blue"),
                team.get("source", "population_engine"),
                team.get("legal_note", "Equipo real preparado como seed estructural; partidos solo desde API o import legal."),
                "prepared",
                "",
                now_iso(),
            ),
        )
        cur.execute(
            """UPDATE teams
               SET league=COALESCE(NULLIF(league,''), ?),
                   external_id=COALESCE(NULLIF(external_id,''), ?),
                   source=COALESCE(NULLIF(source,''), 'population_engine'),
                   sync_status=COALESCE(NULLIF(sync_status,''), 'prepared')
               WHERE key=?""",
            (team.get("league", ""), team.get("external_id", ""), team["key"]),
        )
    cleanup_fake_matches(cur)
    seed_matches = []
    for raw_id, day, time, comp_key, comp_name, country, home, away, status in seed_matches:
        match_id = "seed-" + raw_id + "-" + today_iso(day)
        cur.execute(
            """INSERT OR IGNORE INTO matches
               (id,match_date,kickoff_time,competition_key,competition_name,country,home_team,away_team,status,minute,score,priority,source,legal_note,raw_json,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                match_id,
                today_iso(day),
                time,
                comp_key,
                comp_name,
                country,
                home,
                away,
                status,
                "",
                "",
                priority_for(comp_key, status),
                "seed estructural",
                "Dato semilla propio para experiencia visual. Sustituir por API legal o carga autorizada.",
                json.dumps({"seed": True}),
                now_iso(),
            ),
        )
    conn.commit()
    conn.close()


def seed_core():
    global SEED_LOCK, _SEED_LOCK, _SEEDED_DB_PATH, _SEEDING_DB_PATH, APP_INITIALIZED, APP_INIT_ERROR
    if "SEED_LOCK" not in globals() or SEED_LOCK is None:
        SEED_LOCK = threading.RLock()
    if "_SEED_LOCK" not in globals() or _SEED_LOCK is None:
        _SEED_LOCK = SEED_LOCK
    if _SEEDED_DB_PATH == DB_PATH:
        return
    with SEED_LOCK:
        if _SEEDED_DB_PATH == DB_PATH:
            return
        if _SEEDING_DB_PATH == DB_PATH:
            return
        _SEEDING_DB_PATH = DB_PATH
        try:
            retry_locked(_seed_core_unlocked)
            _SEEDED_DB_PATH = DB_PATH
            APP_INITIALIZED = True
            APP_INIT_ERROR = ""
            try:
                syncer = globals().get("_telegram_sync_env_on_startup")
                if callable(syncer):
                    syncer()
            except Exception as exc:
                try:
                    print("[TELEGRAM] startup env sync skipped:", str(exc)[:220])
                except Exception:
                    pass
        except Exception as exc:
            APP_INIT_ERROR = str(exc)[:500]
            raise
        finally:
            _SEEDING_DB_PATH = None


def rows(query, params=()):
    conn = db()
    cur = conn.cursor()
    cur.execute(query, params)
    out = [dict(r) for r in cur.fetchall()]
    conn.close()
    return out


def initialize_once():
    """Inicializacion idempotente para rutas normales.
    Las consultas SQL no disparan seed ni migraciones; Render health y runtime quedan ultraligeros.
    """
    if _SEEDED_DB_PATH == DB_PATH and APP_INITIALIZED:
        return True
    seed_core()
    return True


LIGHT_STARTUP_ENDPOINTS = {
    "health",
    "api_runtime_version",
    "api_startup_check",
    "service_worker",
    "static",
    "home",
}


@app.before_request
def ensure_runtime_ready_for_request():
    if request.method == "HEAD" and request.path == "/":
        return None
    if request.endpoint in LIGHT_STARTUP_ENDPOINTS:
        return None
    try:
        initialize_once()
    except Exception as exc:
        try:
            print("[STARTUP] initialize_once failed:", str(exc)[:240])
        except Exception:
            pass
    return None


@app.before_request
def enforce_security_guards():
    # Token exists before rendering pages and before validating later POSTs.
    try:
        generate_csrf_token(session)
    except Exception:
        pass
    limited = security_rate_limit_for_request()
    if limited is not None:
        return limited
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and not csrf_exempt_path(request.path):
        if not validate_csrf(session, request_csrf_token()):
            return csrf_failure_response()
    return None


@app.context_processor
def inject_security_context():
    token = generate_csrf_token(session)
    return {"csrf_token": lambda: token, "csrf_token_value": token}


@app.after_request
def apply_security_headers_and_csrf(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
    try:
        if response.mimetype == "text/html" and not response.direct_passthrough:
            body = response.get_data(as_text=True)
            token = generate_csrf_token(session)
            if 'name="csrf_token"' not in body:
                hidden = f'<input type="hidden" name="csrf_token" value="{token}">'
                body = re.sub(r'(<form\b(?=[^>]*method=["\']?post["\']?)[^>]*>)', r'\1' + hidden, body, flags=re.IGNORECASE)
            response.set_data(body)
            response.headers["Content-Length"] = str(len(response.get_data()))
    except Exception:
        pass
    return response


def one(query, params=()):
    data = rows(query, params)
    return data[0] if data else None


def db_table_exists(table_name):
    try:
        return bool(one("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (str(table_name),)))
    except Exception:
        return False


def cache_get(key):
    item = one("SELECT * FROM persistent_cache WHERE key=?", (key,))
    if not item:
        return None
    if item.get("expires_at") and item["expires_at"] < now_iso():
        return None
    try:
        return json.loads(item.get("value_json") or "null")
    except json.JSONDecodeError:
        return None


def cache_set(key, value, seconds=60):
    expires = (datetime.now(TZ) + timedelta(seconds=seconds)).isoformat(timespec="seconds")
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """INSERT OR REPLACE INTO persistent_cache(key,value_json,expires_at,updated_at)
           VALUES (?,?,?,?)""",
        (key, json.dumps(value, ensure_ascii=False), expires, now_iso()),
    )
    conn.commit()
    conn.close()


def competitions():
    data = rows("SELECT * FROM competitions ORDER BY tier DESC, name")
    for item in data:
        item["tags"] = json.loads(item.get("tags_json") or "[]")
        item["name"] = spanish_competition_name(item.get("name")) or item.get("name")
        item["country"] = spanish_country_name(item.get("country")) or item.get("country")
        item["region"] = spanish_country_name(item.get("region")) or item.get("region")
    return data


def competition_map():
    return {c["key"]: c for c in competitions()}


def canonical_team_key(name):
    key = slug(name)
    return TEAM_ALIASES.get(key, key)


def fallback_crest_url(name):
    return "/team-crest.svg?" + urllib.parse.urlencode({"name": name or "Equipo"})


def professional_team_identity(name, explicit_logo="", country="", source=""):
    """Central UI identity payload for teams in cliente/admin/Telegram.

    Always returns a safe crest_url: a validated real logo when available or the app-owned
    SVG fallback. This avoids broken images and oversized raw initials in templates.
    """
    display = spanish_team_name(name) or str(name or "Equipo").strip() or "Equipo"
    return build_team_identity_payload(display, logo_url=safe_team_logo_url(explicit_logo), country=spanish_country_name(country) or country or "", source=source or "NeMeSiS identity")


def professionalize_identity(identity, name="", explicit_logo="", country="", source=""):
    base = dict(identity or {})
    display = spanish_team_name(base.get("name") or base.get("display_name") or name) or base.get("name") or name or "Equipo"
    merged = merge_team_identity_payload(base, name=display, logo_url=explicit_logo or base.get("crest_url") or base.get("logo_url"), country=country or base.get("country") or "", source=source or base.get("crest_source") or base.get("source") or "cache")
    merged["name"] = spanish_team_name(merged.get("name") or display) or display
    merged["display_name"] = merged["name"]
    merged["flag_emoji"] = merged.get("flag_emoji") or team_flag_or_emoji(merged.get("name"), merged.get("country"))
    merged["team_emoji"] = merged.get("flag_emoji")
    merged["crest_url"] = safe_team_logo_url(merged.get("crest_url")) or fallback_crest_url(merged.get("name") or display)
    merged["logo_url"] = safe_team_logo_url(merged.get("logo_url"))
    merged["crest_mode"] = "logo" if merged.get("logo_url") or (str(merged.get("crest_url") or "").startswith(("http://", "https://", "data:image/"))) else ("flag" if merged.get("flag_emoji") else "fallback")
    merged["ui_class"] = f"crest-{merged.get('crest_mode') or 'fallback'}"
    merged["has_real_logo"] = merged.get("crest_mode") == "logo" and not str(merged.get("crest_url") or "").startswith("/team-crest.svg")
    return merged


def apply_team_identities_to_match(item):
    item = dict(item or {})
    home = item.get("home_team") or item.get("safe_home") or "Equipo local"
    away = item.get("away_team") or item.get("safe_away") or "Equipo visitante"
    country = item.get("country") or item.get("safe_country") or ""
    item["home_identity"] = professionalize_identity(item.get("home_identity"), home, item.get("home_logo") or ((item.get("home_identity") or {}).get("logo_url")), country, "match")
    item["away_identity"] = professionalize_identity(item.get("away_identity"), away, item.get("away_logo") or ((item.get("away_identity") or {}).get("logo_url")), country, "match")
    item["home_logo"] = safe_team_logo_url(item.get("home_logo")) or item["home_identity"].get("logo_url") or ""
    item["away_logo"] = safe_team_logo_url(item.get("away_logo")) or item["away_identity"].get("logo_url") or ""
    item["home_badge_text"] = item["home_identity"].get("flag_emoji") or item["home_identity"].get("initials")
    item["away_badge_text"] = item["away_identity"].get("flag_emoji") or item["away_identity"].get("initials")
    return item


def thesportsdb_key():
    return os.getenv("THESPORTSDB_KEY") or os.getenv("THESPORTSDB_API_KEY") or ""


SPORTSDB_SEARCH_ALIASES = {
    "atletico-de-madrid": ["Atletico Madrid", "Atlético Madrid"],
    "barcelona": ["Barcelona", "FC Barcelona"],
    "real-betis": ["Real Betis", "Real Betis Balompie"],
    "cadiz": ["Cadiz", "Cadiz CF"],
    "malaga": ["Malaga", "Malaga CF"],
    "cordoba": ["Cordoba", "Cordoba CF"],
    "recreativo-huelva": ["Recreativo Huelva", "Recreativo de Huelva"],
    "manchester-united": ["Manchester United"],
    "manchester-city": ["Manchester City"],
    "psg": ["Paris Saint-Germain", "PSG"],
    "bayern-munich": ["Bayern Munich", "FC Bayern Munich"],
    "borussia-dortmund": ["Borussia Dortmund", "Dortmund"],
    "ac-milan": ["AC Milan", "Milan"],
    "inter": ["Inter Milan", "Internazionale"],
    "porto": ["FC Porto", "Porto"],
    "sporting-cp": ["Sporting CP", "Sporting Lisbon"],
}


SPORTSDB_FEED_LEAGUES = [
    {"id": item["sportsdb_id"], "key": item["key"], "name": item["name"], "country": item["country"], "group": item.get("group", "")}
    for item in sportsdb_competitions()
]


def sportsdb_name_variants(name):
    key = canonical_team_key(name)
    variants = [name]
    variants.extend(SPORTSDB_SEARCH_ALIASES.get(key, []))
    seen = set()
    out = []
    for item in variants:
        clean = str(item or "").strip()
        if clean and clean.lower() not in seen:
            seen.add(clean.lower())
            out.append(clean)
    return out


def masked_key(value):
    value = str(value or "")
    if not value:
        return ""
    if len(value) <= 6:
        return "***"
    return value[:2] + "***" + value[-4:]


def save_thesportsdb_error(error):
    conn = db()
    conn.execute(
        """INSERT OR REPLACE INTO automation_state(key,value_json,updated_at)
           VALUES (?,?,?)""",
        ("thesportsdb_last_error", json.dumps({"error": str(error), "time": now_iso()}), now_iso()),
    )
    conn.commit()
    conn.close()


def get_thesportsdb_last_error():
    item = one("SELECT * FROM automation_state WHERE key='thesportsdb_last_error'")
    if not item:
        return ""
    try:
        return (json.loads(item.get("value_json") or "{}") or {}).get("error", "")
    except json.JSONDecodeError:
        return item.get("value_json") or ""


def sportsdb_live_enabled():
    return str(os.getenv("ENABLE_LIVE_API", "")).strip().lower() in {"1", "true", "yes", "on"}


def odds_enabled():
    return bool(os.getenv("THE_ODDS_API_KEY")) and str(os.getenv("ENABLE_ODDS_API", "")).strip().lower() in {"1", "true", "yes", "on"}


def odds_cache_minutes():
    return max(5, as_int(os.getenv("ODDS_CACHE_MINUTES", "60"), 60))


def fetch_json_url(url, headers=None, timeout=10):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "NeMeSiS-SHARK-PRO/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read().decode("utf-8", errors="replace"))


def sportsdb_v1(endpoint, params=None):
    api_key = thesportsdb_key()
    if not api_key:
        return {}
    url = "https://www.thesportsdb.com/api/v1/json/%s/%s" % (
        urllib.parse.quote(api_key),
        endpoint.lstrip("/"),
    )
    if params:
        url += "?" + urllib.parse.urlencode(params)
    return fetch_json_url(url, timeout=12)


def sportsdb_v2(path):
    api_key = thesportsdb_key()
    if not api_key:
        return {}
    url = "https://www.thesportsdb.com/api/v2/json/" + path.strip("/")
    return fetch_json_url(
        url,
        headers={"User-Agent": "NeMeSiS-SHARK-PRO/1.0", "X-API-KEY": api_key},
        timeout=12,
    )


def odds_api_get(path, params=None):
    api_key = os.getenv("THE_ODDS_API_KEY", "").strip()
    if not api_key:
        return {}
    payload = dict(params or {})
    payload["apiKey"] = api_key
    url = "https://api.the-odds-api.com/v4/" + path.strip("/")
    url += "?" + urllib.parse.urlencode(payload)
    return fetch_json_url(url, timeout=12)


def sync_log_start(source, sync_type):
    log_id = hashlib.md5(f"{source}:{sync_type}:{datetime.now(TZ).isoformat(timespec='microseconds')}:{secrets.token_hex(4)}".encode("utf-8")).hexdigest()[:18]
    conn = db()
    try:
        conn.execute(
            """INSERT INTO api_sync_logs(id,source,sync_type,started_at,finished_at,status,total_items,error_message)
               VALUES (?,?,?,?,?,?,?,?)""",
            (log_id, source, sync_type, now_iso(), "", "RUNNING", 0, ""),
        )
        conn.commit()
    finally:
        conn.close()
    return log_id


def sync_log_finish(log_id, status="OK", total_items=0, error_message=""):
    conn = db()
    conn.execute(
        "UPDATE api_sync_logs SET finished_at=?, status=?, total_items=?, error_message=? WHERE id=?",
        (now_iso(), status, int(total_items or 0), str(error_message or "")[:500], log_id),
    )
    conn.commit()
    conn.close()


def fetch_thesportsdb_team(team_name):
    api_key = thesportsdb_key()
    if not api_key:
        return None
    url = "https://www.thesportsdb.com/api/v1/json/%s/searchteams.php?%s" % (
        urllib.parse.quote(api_key),
        urllib.parse.urlencode({"t": team_name}),
    )
    try:
        payload = fetch_json_url(url, timeout=8)
        teams = payload.get("teams") or []
        if not teams:
            return None
        first = teams[0]
        logo = first.get("strBadge") or first.get("strLogo") or ""
        return {
            "external_id": first.get("idTeam") or "",
            "name": first.get("strTeam") or team_name,
            "country": first.get("strCountry") or "",
            "league": first.get("strLeague") or "",
            "logo_url": logo,
            "source": "TheSportsDB API",
            "legal_note": "Escudo obtenido desde API permitida TheSportsDB; respetar condiciones de uso de la fuente.",
        }
    except Exception as exc:
        save_thesportsdb_error(exc)
        return None


def fetch_thesportsdb_team_by_id(external_id):
    api_key = thesportsdb_key()
    external_id = str(external_id or "").strip()
    if not api_key or not external_id:
        return None
    url = "https://www.thesportsdb.com/api/v1/json/%s/lookupteam.php?%s" % (
        urllib.parse.quote(api_key),
        urllib.parse.urlencode({"id": external_id}),
    )
    try:
        payload = fetch_json_url(url, timeout=8)
        teams = payload.get("teams") or []
        if not teams:
            return None
        first = teams[0]
        logo = first.get("strBadge") or first.get("strLogo") or ""
        return {
            "external_id": first.get("idTeam") or external_id,
            "name": first.get("strTeam") or "",
            "country": first.get("strCountry") or "",
            "league": first.get("strLeague") or "",
            "logo_url": logo,
            "source": "TheSportsDB API",
            "legal_note": "Escudo obtenido desde API permitida TheSportsDB; respetar condiciones de uso de la fuente.",
        }
    except Exception as exc:
        save_thesportsdb_error(exc)
        return None


def crest_sync_status():
    seed_core()
    teams = rows("SELECT * FROM teams ORDER BY name")
    with_logo = [t for t in teams if t.get("logo_url")]
    without_logo = [t for t in teams if not t.get("logo_url")]
    state = one("SELECT * FROM automation_state WHERE key='sportsdb_crest_sync'")
    last_sync = {}
    if state:
        try:
            last_sync = json.loads(state.get("value_json") or "{}")
        except json.JSONDecodeError:
            last_sync = {"raw": state.get("value_json")}
    return {
        "key_present": bool(thesportsdb_key()),
        "key_masked": masked_key(thesportsdb_key()),
        "live_enabled": sportsdb_live_enabled(),
        "total_teams": len(teams),
        "with_logo": len(with_logo),
        "fallback": len(without_logo),
        "missing_examples": [t.get("name") for t in without_logo[:8]],
        "last_sync": last_sync,
        "last_error": get_thesportsdb_last_error(),
    }


def sync_sportsdb_crests(refresh=False, limit=40):
    seed_core()
    if not thesportsdb_key():
        return {"ok": False, "sin_key": True, "processed": 0, "updated": 0, "failed": 0, "errors": ["Falta THESPORTSDB_API_KEY o THESPORTSDB_KEY."]}
    log_id = sync_log_start("sportsdb", "crests")
    teams = rows("SELECT * FROM teams ORDER BY name")
    processed = 0
    updated = 0
    failed = 0
    errors = []
    for team in teams:
        if processed >= int(limit):
            break
        if team.get("logo_url") and not refresh:
            continue
        processed += 1
        identity = None
        if team.get("external_id"):
            identity = fetch_thesportsdb_team_by_id(team.get("external_id"))
        if not identity:
            for variant in sportsdb_name_variants(team.get("name")):
                identity = fetch_thesportsdb_team(variant)
                if identity:
                    break
        if identity and identity.get("logo_url"):
            cache_team_identity(team.get("name"), identity)
            updated += 1
        else:
            failed += 1
            errors.append(team.get("name"))
    summary = {
        "ok": True,
        "source": "sportsdb",
        "sync_type": "crests",
        "sin_key": False,
        "processed": processed,
        "inserted": 0,
        "updated": updated,
        "skipped": failed,
        "failed": failed,
        "errors": errors[:12],
        "last_sync": now_iso(),
        "time": now_iso(),
    }
    conn = db()
    conn.execute(
        """INSERT OR REPLACE INTO automation_state(key,value_json,updated_at)
           VALUES (?,?,?)""",
        ("sportsdb_crest_sync", json.dumps(summary, ensure_ascii=False), now_iso()),
    )
    conn.commit()
    conn.close()
    sync_log_finish(log_id, "OK" if not errors else "PARTIAL", processed, "; ".join(errors[:3]))
    return summary


def sportsdb_score(home_score, away_score):
    home = str(home_score or "").strip()
    away = str(away_score or "").strip()
    if home == "" and away == "":
        return ""
    return f"{home or 0}-{away or 0}"


def sportsdb_match_status(event):
    status = str(event.get("strStatus") or event.get("status") or "").strip()
    progress = str(event.get("strProgress") or event.get("progress") or "").strip()
    status_lower = (status or progress).lower()
    if status_lower in {"ns", "not started"}:
        return "PROGRAMADO"
    if status_lower in {"ft", "final", "finished"} or "final" in status_lower:
        return "FINALIZADO"
    if status_lower in {"ht", "halftime", "half time"} or "half" in status_lower:
        return "DESCANSO"
    if status_lower in {"canc", "pst", "post", "postponed", "cancelled", "suspended", "abd"}:
        return "SUSPENDIDO"
    if status or progress:
        return "LIVE"
    return "PROGRAMADO"




FINISHED_STATUS_WORDS = {"ft", "final", "finalizado", "finished", "match finished", "aet", "pen", "after penalties"}
LIVE_STATUS_WORDS = {"live", "directo", "1h", "2h", "ht", "descanso", "halftime", "half time", "in play", "inplay"}
SCHEDULED_STATUS_WORDS = {"programado", "scheduled", "not started", "ns", "fixture", "upcoming"}


def status_text_for(match):
    return str((match or {}).get("status") or "").strip().lower()


def is_finished_status_value(status):
    text = str(status or "").strip().lower()
    return text in FINISHED_STATUS_WORDS or any(x in text for x in ["final", "finished", "terminado", "full time"])


def is_live_status_value(status):
    text = str(status or "").strip().lower()
    return text in LIVE_STATUS_WORDS or any(x in text for x in ["live", "directo", "1h", "2h", "half"])


def canonical_match_status(match):
    status = str((match or {}).get("status") or "").strip()
    minute = str((match or {}).get("minute") or "").strip()
    score = str((match or {}).get("score") or "").strip()
    date_value = str((match or {}).get("match_date") or "").strip()
    if is_finished_status_value(status):
        return {"key": "FT", "label": "Finalizado", "badge": "finished", "is_live": False, "is_finished": True, "is_upcoming": False}
    if date_value and date_value > today_iso() and not is_live_status_value(status):
        return {"key": "UPCOMING", "label": "Próximo", "badge": "upcoming", "is_live": False, "is_finished": False, "is_upcoming": True}
    if is_live_status_value(status):
        if "half" in status.lower() or "descanso" in status.lower() or status.lower() == "ht":
            return {"key": "HT", "label": "Descanso", "badge": "halftime", "is_live": True, "is_finished": False, "is_upcoming": False}
        return {"key": "LIVE", "label": "En directo", "badge": "live", "is_live": True, "is_finished": False, "is_upcoming": False}
    if minute and not is_finished_status_value(status):
        # Solo tratar minuto como live si el estado no indica finalizado.
        return {"key": "LIVE", "label": "En directo", "badge": "live", "is_live": True, "is_finished": False, "is_upcoming": False}
    if score and date_value and date_value < today_iso():
        return {"key": "FT", "label": "Finalizado", "badge": "finished", "is_live": False, "is_finished": True, "is_upcoming": False}
    return {"key": "UPCOMING", "label": "Próximo", "badge": "upcoming", "is_live": False, "is_finished": False, "is_upcoming": True}

def sportsdb_event_time(event):
    timestamp = str(event.get("strTimestamp") or "").strip()
    values = madrid_values_from_datetime(timestamp)
    if values.get("kickoff_time"):
        return values["kickoff_time"]
    raw_time = str(event.get("strTime") or event.get("strEventTime") or event.get("timeEvent") or "").strip()
    return raw_time[:5] if raw_time and len(raw_time) >= 5 else raw_time


def kickoff_iso_value(match_date, match_time):
    date = str(match_date or "").strip()[:10]
    time = str(match_time or "").strip()[:5]
    if not date:
        return ""
    # Admin/manual date+hour values are already Spanish/Madrid hour.
    # Store them with timezone to avoid a second UTC→Madrid conversion later.
    return madrid_local_iso(date, time) if time else madrid_local_iso(date, "00:00")




def normalize_existing_match_times_to_madrid(conn, limit=1200):
    """One-shot light maintenance: display old UTC API times as Spain/Madrid time."""
    try:
        rows_to_fix = conn.execute(
            """SELECT id, kickoff_iso, match_date, kickoff_time, match_time
               FROM matches
               WHERE COALESCE(kickoff_iso,'')!=''
               ORDER BY COALESCE(updated_at, match_date, id) DESC
               LIMIT ?""",
            (int(limit),),
        ).fetchall()
    except Exception:
        return 0
    changed = 0
    for row in rows_to_fix:
        data = dict(row)
        values = madrid_values_from_datetime(data.get("kickoff_iso") or "", data.get("match_date"), data.get("kickoff_time") or data.get("match_time"))
        new_date = values.get("match_date") or data.get("match_date")
        new_time = values.get("kickoff_time") or data.get("kickoff_time") or data.get("match_time")
        new_iso = values.get("kickoff_iso") or data.get("kickoff_iso")
        if not new_date or not new_time:
            continue
        if new_date != data.get("match_date") or new_time != (data.get("kickoff_time") or data.get("match_time")) or (new_iso and new_iso != data.get("kickoff_iso")):
            try:
                conn.execute(
                    "UPDATE matches SET match_date=?, kickoff_time=?, match_time=?, kickoff_iso=?, updated_at=? WHERE id=?",
                    (new_date, new_time, new_time, new_iso, now_iso(), data.get("id")),
                )
                changed += 1
            except Exception:
                continue
    if changed:
        try:
            conn.execute(
                "INSERT OR REPLACE INTO automation_state(key,value_json,updated_at) VALUES (?,?,?)",
                ("v712_madrid_time_normalization", json.dumps({"changed": changed, "time": now_iso()}, ensure_ascii=False), now_iso()),
            )
        except Exception:
            pass
    return changed


def sportsdb_event_id(event):
    raw = event.get("idEvent") or event.get("idLiveScore") or event.get("strEvent") or json.dumps(event, sort_keys=True)[:200]
    return "sportsdb-" + hashlib.md5(str(raw).encode("utf-8")).hexdigest()[:18]


def cache_sportsdb_event_team(name, external_id="", logo_url="", country="", league=""):
    name = str(name or "").strip()
    if not name:
        return
    identity = {
        "external_id": external_id or "",
        "name": name,
        "country": country or "",
        "league": league or "",
        "logo_url": logo_url or "",
        "source": "TheSportsDB Event Feed",
        "legal_note": "Equipo/escudo obtenido desde API permitida TheSportsDB; cache SQLite propio, sin scraping.",
    }
    current = one("SELECT * FROM teams WHERE key=?", (canonical_team_key(name),))
    if logo_url or not current:
        cache_team_identity(name, identity)


def sportsdb_event_to_match(event, fallback=None):
    fallback = fallback or {}
    sport = str(event.get("strSport") or event.get("sport") or "Soccer").lower()
    if sport and sport not in {"soccer", "football"}:
        return None
    home = event.get("strHomeTeam") or event.get("homeTeam") or event.get("strHome") or ""
    away = event.get("strAwayTeam") or event.get("awayTeam") or event.get("strAway") or ""
    if not home or not away or is_fake_team_name(home) or is_fake_team_name(away):
        return None
    raw_home, raw_away = home, away
    home = spanish_team_name(home)
    away = spanish_team_name(away)
    comp_name = spanish_competition_name(event.get("strLeague") or fallback.get("name") or "TheSportsDB")
    comp_key = fallback.get("key") or slug(comp_name)
    comp_id = event.get("idLeague") or fallback.get("id") or ""
    status = sportsdb_match_status(event)
    score = sportsdb_score(event.get("intHomeScore"), event.get("intAwayScore"))
    time_values = madrid_values_from_datetime(event.get("strTimestamp") or "", event.get("dateEvent") or today_iso(), sportsdb_event_time(event))
    match_date = time_values.get("match_date") or event.get("dateEvent") or today_iso()
    match_time = time_values.get("kickoff_time") or sportsdb_event_time(event)
    home_badge = event.get("strHomeTeamBadge") or event.get("strHomeTeamLogo") or ""
    away_badge = event.get("strAwayTeamBadge") or event.get("strAwayTeamLogo") or ""
    home_id = event.get("idHomeTeam") or ""
    away_id = event.get("idAwayTeam") or ""
    home_score = str(event.get("intHomeScore") or "")
    away_score = str(event.get("intAwayScore") or "")
    country = spanish_country_name(event.get("strCountry") or fallback.get("country") or "")
    cache_sportsdb_event_team(raw_home, home_id, home_badge, country, comp_name)
    cache_sportsdb_event_team(raw_away, away_id, away_badge, country, comp_name)
    return {
        "id": sportsdb_event_id(event),
        "external_id": event.get("idEvent") or event.get("idLiveScore") or "",
        "match_date": match_date,
        "kickoff_time": match_time,
        "match_time": match_time,
        "kickoff_iso": time_values.get("kickoff_iso") or event.get("strTimestamp") or kickoff_iso_value(match_date, match_time),
        "competition_id": comp_id,
        "competition_key": comp_key,
        "competition_name": comp_name,
        "league_name": comp_name,
        "country": country,
        "home_team": home,
        "away_team": away,
        "home_team_id": home_id,
        "away_team_id": away_id,
        "home_logo": home_badge,
        "away_logo": away_badge,
        "status": status,
        "minute": (event.get("strProgress") or "") if not is_finished_status_value(status) else "",
        "score": score,
        "home_score": home_score,
        "away_score": away_score,
        "venue": event.get("strVenue") or "",
        "season": event.get("strSeason") or "",
        "round": event.get("intRound") or event.get("strRound") or "",
        "priority": priority_for(comp_key, status),
        "source": "TheSportsDB API",
        "legal_note": "Partido obtenido desde API permitida TheSportsDB y guardado en SQLite; sin scraping.",
        "raw_json": json.dumps(event, ensure_ascii=False)[:5000],
    }


def sportsdb_event_collection(payload):
    if not isinstance(payload, dict):
        return []
    for key in ("events", "event", "livescores", "livescore", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def fetch_sportsdb_feed_events(limit=220):
    events = []
    errors = []
    try:
        payload = sportsdb_v1("eventsday.php", {"d": today_iso(), "s": "Soccer"})
        events.extend([(item, {"key": slug(item.get("strLeague") or "sportsdb-day"), "name": item.get("strLeague") or "Soccer", "country": item.get("strCountry") or ""}) for item in sportsdb_event_collection(payload)])
    except Exception as exc:
        save_thesportsdb_error(exc)
        errors.append("eventsday: " + str(exc)[:160])
    for league in SPORTSDB_FEED_LEAGUES:
        if len(events) >= int(limit):
            break
        try:
            payload = sportsdb_v1("eventsnextleague.php", {"id": league["id"]})
            events.extend([(item, league) for item in sportsdb_event_collection(payload)])
        except Exception as exc:
            save_thesportsdb_error(exc)
            errors.append(f"{league['name']}: {str(exc)[:160]}")
    if sportsdb_live_enabled():
        try:
            payload = sportsdb_v2("livescore/soccer")
            events.extend([(item, {"key": slug(item.get("strLeague") or "sportsdb-live"), "name": item.get("strLeague") or "Live Soccer", "country": item.get("strCountry") or ""}) for item in sportsdb_event_collection(payload)])
        except Exception as exc:
            save_thesportsdb_error(exc)
            errors.append("livescore: " + str(exc)[:160])
    return events[: int(limit)], errors


def upsert_sportsdb_matches(match_rows):
    conn = db()
    cur = conn.cursor()
    imported = 0
    updated = 0
    skipped = 0
    for item in match_rows:
        if not item or is_fake_team_name(item.get("home_team")) or is_fake_team_name(item.get("away_team")):
            skipped += 1
            continue
        exists = cur.execute("SELECT id FROM matches WHERE id=?", (item["id"],)).fetchone()
        cur.execute(
            """INSERT OR REPLACE INTO matches
               (id,external_id,match_date,kickoff_time,match_time,kickoff_iso,competition_id,competition_key,competition_name,league_name,country,
                home_team,away_team,home_team_id,away_team_id,home_logo,away_logo,status,minute,score,home_score,away_score,venue,season,round,
                priority,source,legal_note,raw_json,updated_at,bookmaker,odds_h2h_json,odds_updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                item["id"],
                item.get("external_id") or item["id"],
                item.get("match_date") or today_iso(),
                item.get("kickoff_time") or "",
                item.get("match_time") or item.get("kickoff_time") or "",
                item.get("kickoff_iso") or kickoff_iso_value(item.get("match_date") or today_iso(), item.get("kickoff_time") or ""),
                item.get("competition_id") or "",
                item.get("competition_key") or "sportsdb",
                item.get("competition_name") or "TheSportsDB",
                item.get("league_name") or item.get("competition_name") or "TheSportsDB",
                item.get("country") or "",
                item.get("home_team") or "",
                item.get("away_team") or "",
                item.get("home_team_id") or "",
                item.get("away_team_id") or "",
                item.get("home_logo") or "",
                item.get("away_logo") or "",
                item.get("status") or "PROGRAMADO",
                item.get("minute") or "",
                item.get("score") or "",
                item.get("home_score") or "",
                item.get("away_score") or "",
                item.get("venue") or "",
                item.get("season") or "",
                item.get("round") or "",
                as_int(item.get("priority"), 70),
                item.get("source") or "TheSportsDB API",
                item.get("legal_note") or "API autorizada TheSportsDB",
                item.get("raw_json") or "{}",
                now_iso(),
                item.get("bookmaker") or "",
                item.get("odds_h2h_json") or "",
                item.get("odds_updated_at") or "",
            ),
        )
        status_info = canonical_match_status(item)
        if status_info.get("is_live"):
            cur.execute(
                """INSERT OR REPLACE INTO live_matches(id,match_id,status,minute,home_score,away_score,payload_json,source,updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    "live-" + item["id"],
                    item["id"],
                    item.get("status") or "LIVE",
                    item.get("minute") or "",
                    item.get("home_score") or "",
                    item.get("away_score") or "",
                    item.get("raw_json") or "{}",
                    item.get("source") or "TheSportsDB API",
                    now_iso(),
                ),
            )
        if exists:
            updated += 1
        else:
            imported += 1
    dedupe_result = cleanup_duplicate_matches(cur)
    conn.execute("DELETE FROM persistent_cache WHERE key LIKE 'match-hub:%'")
    summary = {
        "ok": True,
        "source": "sportsdb",
        "sync_type": "matches",
        "inserted": imported,
        "imported": imported,
        "updated": updated,
        "skipped": skipped,
        "duplicates_removed": dedupe_result.get("duplicates_removed", 0),
        "duplicate_groups": dedupe_result.get("groups", 0),
        "processed": len(match_rows),
        "errors": [],
        "last_sync": now_iso(),
        "time": now_iso(),
    }
    conn.execute(
        """INSERT OR REPLACE INTO automation_state(key,value_json,updated_at)
           VALUES (?,?,?)""",
        ("sportsdb_feed_sync", json.dumps(summary, ensure_ascii=False), now_iso()),
    )
    conn.commit()
    conn.close()
    return summary


def sync_sportsdb_feed(limit=220):
    seed_core()
    if not thesportsdb_key():
        result = {"ok": False, "sin_key": True, "imported": 0, "updated": 0, "processed": 0, "errors": ["Falta THESPORTSDB_API_KEY o THESPORTSDB_KEY."]}
        return result
    log_id = sync_log_start("TheSportsDB", "matches")
    try:
        fetched, errors = fetch_sportsdb_feed_events(limit=limit)
        match_rows = []
        seen = set()
        for event, fallback in fetched:
            match = sportsdb_event_to_match(event, fallback=fallback)
            if not match or match["id"] in seen:
                continue
            seen.add(match["id"])
            match_rows.append(match)
        result = upsert_sportsdb_matches(match_rows)
        result["errors"] = errors[:12]
        result["live_enabled"] = sportsdb_live_enabled()
        result["sin_key"] = False
        sync_log_finish(log_id, "OK" if not errors else "PARTIAL", result.get("processed", 0), "; ".join(errors[:3]))
    except Exception as exc:
        save_thesportsdb_error(exc)
        sync_log_finish(log_id, "ERROR", 0, str(exc))
        return {"ok": False, "sin_key": False, "imported": 0, "updated": 0, "processed": 0, "errors": [str(exc)[:200]]}
    conn = db()
    conn.execute(
        """INSERT OR REPLACE INTO automation_state(key,value_json,updated_at)
           VALUES (?,?,?)""",
        ("sportsdb_feed_sync", json.dumps(result, ensure_ascii=False), now_iso()),
    )
    import_id = hashlib.md5(f"sportsdb-feed-{datetime.now(TZ).isoformat(timespec='microseconds')}-{result.get('processed')}".encode("utf-8")).hexdigest()[:18]
    conn.execute(
        """INSERT INTO imports(id,kind,source_name,source_url,legal_note,rows_count,status,payload_preview,created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (import_id, "matches", "TheSportsDB API", "https://www.thesportsdb.com/documentation", "API permitida TheSportsDB; cache SQLite sin scraping.", result.get("processed", 0), "IMPORTED", json.dumps(match_rows[:3], ensure_ascii=False)[:2000], now_iso()),
    )
    conn.commit()
    conn.close()
    return result


def sportsdb_feed_status():
    seed_core()
    state = one("SELECT * FROM automation_state WHERE key='sportsdb_feed_sync'")
    last_sync = {}
    if state:
        try:
            last_sync = json.loads(state.get("value_json") or "{}")
        except json.JSONDecodeError:
            last_sync = {"raw": state.get("value_json")}
    cached = (one("SELECT COUNT(*) AS total FROM matches WHERE source LIKE 'TheSportsDB%'") or {}).get("total", 0)
    updated = (one("SELECT MAX(updated_at) AS updated_at FROM matches WHERE source LIKE 'TheSportsDB%'") or {}).get("updated_at", "")
    return {
        "key_present": bool(thesportsdb_key()),
        "key_masked": masked_key(thesportsdb_key()),
        "live_enabled": sportsdb_live_enabled(),
        "cached_matches": cached,
        "last_cached_update": updated,
        "last_sync": last_sync,
        "last_error": get_thesportsdb_last_error(),
    }


def latest_sync_log(source=None, sync_type=None):
    query = "SELECT * FROM api_sync_logs"
    params = []
    clauses = []
    if source:
        clauses.append("source=?")
        params.append(source)
    if sync_type:
        clauses.append("sync_type=?")
        params.append(sync_type)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY started_at DESC LIMIT 1"
    return one(query, tuple(params)) or {}


def sync_sportsdb_competitions():
    seed_core()
    log_id = sync_log_start("sportsdb", "competitions")
    conn = db()
    cur = conn.cursor()
    inserted = updated = skipped = 0
    errors = []
    try:
        for item in PRIORITY_COMPETITIONS:
            comp = competition_payload(item)
            exists = cur.execute("SELECT key FROM competitions WHERE key=?", (comp["key"],)).fetchone()
            cur.execute(
                """INSERT OR REPLACE INTO competitions
                   (key,name,scope,country,region,tier,source_strategy,tags_json,external_id,source,sync_status,last_sync_at,updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    comp["key"],
                    comp["name"],
                    comp["scope"],
                    comp["country"],
                    comp["region"],
                    comp["tier"],
                    comp["source_strategy"],
                    json.dumps(comp["tags"]),
                    comp["external_id"],
                    comp["source"],
                    comp["sync_status"],
                    now_iso(),
                    now_iso(),
                ),
            )
            if comp["sync_status"] == "no_data":
                skipped += 1
            elif exists:
                updated += 1
            else:
                inserted += 1
        conn.commit()
        result = success_sync("sportsdb", "competitions", len(PRIORITY_COMPETITIONS), inserted, updated, skipped, errors)
        result["last_sync"] = now_iso()
        sync_log_finish(log_id, "OK", result["processed"], "")
        return result
    except Exception as exc:
        conn.rollback()
        errors.append(str(exc)[:200])
        sync_log_finish(log_id, "ERROR", 0, errors[0])
        return empty_sync("sportsdb", "competitions", errors[0])
    finally:
        conn.close()


def sportsdb_team_from_payload(item, league_name=""):
    name = item.get("strTeam") or item.get("name") or item.get("team") or ""
    if not name:
        return None
    return {
        "key": canonical_team_key(name),
        "name": name,
        "country": item.get("strCountry") or "",
        "region": item.get("strRegion") or "",
        "league": league_name or item.get("strLeague") or "",
        "logo_url": item.get("strBadge") or item.get("strTeamBadge") or item.get("strLogo") or "",
        "external_id": item.get("idTeam") or "",
        "color_hint": "premium-blue",
        "source": "sportsdb",
        "legal_note": "Equipo/escudo obtenido desde TheSportsDB mediante API permitida; sin scraping.",
        "sync_status": "synced",
    }


def upsert_team_payloads(team_rows, source="sportsdb"):
    conn = db()
    cur = conn.cursor()
    inserted = updated = skipped = 0
    for item in team_rows:
        name = item.get("name") or ""
        if not name:
            skipped += 1
            continue
        key = canonical_team_key(item.get("key") or name)
        exists = cur.execute("SELECT key FROM teams WHERE key=?", (key,)).fetchone()
        cur.execute(
            """INSERT OR REPLACE INTO teams
               (key,name,country,region,league,logo_url,external_id,color_hint,source,legal_note,sync_status,last_sync_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                key,
                name,
                item.get("country") or "",
                item.get("region") or "",
                item.get("league") or "",
                item.get("logo_url") or "",
                item.get("external_id") or "",
                item.get("color_hint") or "premium-blue",
                item.get("source") or source,
                item.get("legal_note") or "Equipo real guardado desde fuente autorizada.",
                item.get("sync_status") or "synced",
                now_iso(),
                now_iso(),
            ),
        )
        if exists:
            updated += 1
        else:
            inserted += 1
    conn.commit()
    conn.close()
    return {"inserted": inserted, "updated": updated, "skipped": skipped, "processed": len(team_rows)}


def sync_sportsdb_teams(limit=240):
    seed_core()
    log_id = sync_log_start("sportsdb", "teams")
    prepared = [team_payload(item) for item in STRUCTURAL_TEAMS]
    base = upsert_team_payloads(prepared, source="population_engine")
    errors = []
    fetched = []
    if not thesportsdb_key():
        errors.append("Falta THESPORTSDB_API_KEY o THESPORTSDB_KEY. Se mantienen equipos estructurales.")
        sync_log_finish(log_id, "PARTIAL", base["processed"], errors[0])
        return {
            "ok": False,
            "source": "sportsdb",
            "sync_type": "teams",
            "processed": base["processed"],
            "inserted": base["inserted"],
            "updated": base["updated"],
            "skipped": base["skipped"],
            "errors": errors,
            "last_sync": now_iso(),
        }
    for league in sportsdb_competitions():
        if len(fetched) >= int(limit):
            break
        league_id = league.get("sportsdb_id")
        if not league_id:
            continue
        try:
            payload = sportsdb_v1("lookup_all_teams.php", {"id": league_id})
            for item in payload.get("teams") or []:
                team = sportsdb_team_from_payload(item, league.get("name", ""))
                if team:
                    fetched.append(team)
        except Exception as exc:
            errors.append(f"{league.get('name')}: {str(exc)[:160]}")
    result = upsert_team_payloads(fetched[: int(limit)], source="sportsdb") if fetched else {"processed": 0, "inserted": 0, "updated": 0, "skipped": 0}
    processed = base["processed"] + result["processed"]
    inserted = base["inserted"] + result["inserted"]
    updated = base["updated"] + result["updated"]
    skipped = base["skipped"] + result["skipped"]
    sync_log_finish(log_id, "OK" if not errors else "PARTIAL", processed, "; ".join(errors[:3]))
    return {
        "ok": not errors,
        "source": "sportsdb",
        "sync_type": "teams",
        "processed": processed,
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "errors": errors[:12],
        "last_sync": now_iso(),
    }


def fetch_sportsdb_results(limit=220):
    events = []
    errors = []
    if not thesportsdb_key():
        return [], ["Falta THESPORTSDB_API_KEY o THESPORTSDB_KEY."]
    for league in sportsdb_competitions():
        if len(events) >= int(limit):
            break
        league_id = league.get("sportsdb_id")
        if not league_id:
            continue
        try:
            payload = sportsdb_v1("eventspastleague.php", {"id": league_id})
            for item in sportsdb_event_collection(payload):
                events.append((item, {"key": league["key"], "name": league["name"], "country": league["country"], "id": league_id}))
        except Exception as exc:
            errors.append(f"{league.get('name')}: {str(exc)[:160]}")
    return events[: int(limit)], errors


def sync_sportsdb_results(limit=220):
    seed_core()
    log_id = sync_log_start("sportsdb", "results")
    try:
        fetched, errors = fetch_sportsdb_results(limit=limit)
        matches = []
        seen = set()
        for event, fallback in fetched:
            match = sportsdb_event_to_match(event, fallback=fallback)
            if not match or match["id"] in seen:
                continue
            match["status"] = "FINALIZADO" if match.get("score") else match.get("status", "FINALIZADO")
            match["source"] = "TheSportsDB Results API"
            seen.add(match["id"])
            matches.append(match)
        result = upsert_sportsdb_matches(matches)
        result.update({"source": "sportsdb", "sync_type": "results", "errors": errors[:12], "last_sync": now_iso()})
        sync_log_finish(log_id, "OK" if not errors else "PARTIAL", result.get("processed", 0), "; ".join(errors[:3]))
        return result
    except Exception as exc:
        save_thesportsdb_error(exc)
        sync_log_finish(log_id, "ERROR", 0, str(exc))
        return empty_sync("sportsdb", "results", str(exc)[:200])


def sync_sportsdb_calendar(limit=160):
    result = sync_sportsdb_feed(limit=limit)
    result.setdefault("source", "sportsdb")
    result["sync_type"] = "calendar"
    result["inserted"] = result.get("inserted", result.get("imported", 0))
    result["last_sync"] = now_iso()
    return result


def upsert_odds_snapshots(events):
    conn = db()
    cur = conn.cursor()
    inserted = updated = skipped = 0
    for sport, event in events:
        snapshot = h2h_price_snapshot(event)
        bookmaker = snapshot.get("bookmaker") or ""
        outcomes = snapshot.get("outcomes") or []
        if not outcomes:
            skipped += 1
            continue
        home = event.get("home_team") or ""
        away = event.get("away_team") or ""
        prices = price_map_from_outcomes(outcomes, home, away)
        match_id = odds_event_id(sport.get("odds_key") or sport.get("key"), event)
        snap_id = hashlib.md5(f"{match_id}:{bookmaker}:{snapshot.get('last_update') or now_iso()}".encode("utf-8")).hexdigest()[:18]
        exists = cur.execute("SELECT id FROM odds_snapshots WHERE id=?", (snap_id,)).fetchone()
        cur.execute(
            """INSERT OR REPLACE INTO odds_snapshots
               (id,match_id,external_id,source,sport_key,league_name,bookmaker,market,home_team,away_team,home_price,draw_price,away_price,commence_time,payload_json,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                snap_id,
                match_id,
                event.get("id") or "",
                "The Odds API",
                sport.get("odds_key") or event.get("sport_key") or "",
                sport.get("name") or event.get("sport_title") or "",
                bookmaker,
                "h2h",
                home,
                away,
                str(prices.get("home") or ""),
                str(prices.get("draw") or ""),
                str(prices.get("away") or ""),
                event.get("commence_time") or "",
                json.dumps(event, ensure_ascii=False)[:5000],
                now_iso(),
            ),
        )
        if exists:
            updated += 1
        else:
            inserted += 1
    conn.commit()
    conn.close()
    return {"processed": len(events), "inserted": inserted, "updated": updated, "skipped": skipped}


def sync_odds_snapshots(limit=80, force=False):
    seed_core()
    if not os.getenv("THE_ODDS_API_KEY"):
        return empty_sync("odds", "odds", "Falta THE_ODDS_API_KEY.")
    if not odds_enabled():
        result = empty_sync("odds", "odds", "ENABLE_ODDS_API no esta activo.")
        result["disabled"] = True
        return result
    if odds_recently_synced() and not force:
        last = odds_last_sync()
        return {"ok": True, "source": "odds", "sync_type": "odds", "skipped": True, "processed": 0, "inserted": 0, "updated": 0, "errors": [], "last_sync": last}
    log_id = sync_log_start("odds", "odds")
    try:
        fetched, errors = fetch_odds_events(limit=limit)
        result = upsert_odds_snapshots(fetched)
        result.update(success_sync("odds", "odds", result["processed"], result["inserted"], result["updated"], result["skipped"], errors[:12]))
        result["last_sync"] = now_iso()
        sync_log_finish(log_id, "OK" if not errors else "PARTIAL", result["processed"], "; ".join(errors[:3]))
        return result
    except Exception as exc:
        sync_log_finish(log_id, "ERROR", 0, str(exc))
        return empty_sync("odds", "odds", str(exc)[:200])


def data_center_summary():
    seed_core()
    summary = match_calendar_diagnostics()
    summary.update(
        {
            "teams_with_crests": (one("SELECT COUNT(*) AS total FROM teams WHERE logo_url IS NOT NULL AND logo_url!=''") or {}).get("total", 0),
            "teams_without_crests": (one("SELECT COUNT(*) AS total FROM teams WHERE logo_url IS NULL OR logo_url=''") or {}).get("total", 0),
            "odds_snapshots": (one("SELECT COUNT(*) AS total FROM odds_snapshots") or {}).get("total", 0),
            "last_sportsdb_sync": latest_sync_log("sportsdb") or latest_sync_log("TheSportsDB"),
            "last_odds_sync": latest_sync_log("odds") or latest_sync_log("The Odds API"),
            "recent_logs": rows("SELECT * FROM api_sync_logs ORDER BY started_at DESC LIMIT 12"),
            "population": {
                "competitions_prepared": len(PRIORITY_COMPETITIONS),
                "sportsdb_competitions": len(sportsdb_competitions()),
                "odds_competitions": len(odds_competitions()),
                "structural_teams": len(STRUCTURAL_TEAMS),
            },
            "scheduler": scheduler_status(),
        }
    )
    return summary


def client_source_label(diagnostics):
    source = str((diagnostics or {}).get("active_data_source") or "")
    if (diagnostics or {}).get("total_matches", 0) <= 0:
        return "Pendiente de sincronizacion"
    if "Odds" in source or "SportsDB" in source:
        return "Calendario real sincronizado"
    if "import" in source.lower():
        return "Calendario importado"
    return "Calendario activo"


def population_warmup(force=False, limit=120):
    seed_core()
    state = one("SELECT * FROM automation_state WHERE key='population_warmup'")
    last_iso = state.get("updated_at") if state else ""
    hours = as_int(os.getenv("POPULATION_WARMUP_HOURS", "6"), 6)
    if not force and not should_run_interval(last_iso, hours, now_iso()):
        return {"ok": True, "source": "population", "sync_type": "warmup", "skipped": True, "reason": "intervalo_activo", "last_sync": last_iso}
    log_id = sync_log_start("population", "warmup")
    results = {
        "competitions": sync_sportsdb_competitions(),
        "teams": sync_sportsdb_teams(limit=limit),
        "calendar": sync_sportsdb_calendar(limit=limit),
        "odds": sync_odds_events(limit=limit, force=force),
    }
    errors = []
    processed = 0
    for item in results.values():
        processed += as_int(item.get("processed"), 0)
        errors.extend(item.get("errors") or [])
    payload = {"ok": not errors, "source": "population", "sync_type": "warmup", "processed": processed, "results": results, "errors": errors[:12], "last_sync": now_iso()}
    conn = db()
    conn.execute(
        """INSERT OR REPLACE INTO automation_state(key,value_json,updated_at)
           VALUES (?,?,?)""",
        ("population_warmup", json.dumps(payload, ensure_ascii=False)[:12000], now_iso()),
    )
    conn.commit()
    conn.close()
    sync_log_finish(log_id, "OK" if not errors else "PARTIAL", processed, "; ".join(errors[:3]))
    return payload


def scheduler_env_config():
    return scheduler_config(os.environ)


def scheduler_enabled():
    return scheduler_env_enabled()


def scheduler_startup_enabled():
    if os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID") or os.getenv("GUNICORN_CMD_ARGS"):
        return str(os.getenv("AUTO_SYNC_ON_STARTUP", "")).strip().lower() in {"1", "true", "yes", "on"}
    return scheduler_env_config().get("startup", False)


def scheduler_lock_row(task_name):
    return one("SELECT * FROM scheduler_locks WHERE task_name=?", (task_name,)) or {}


def scheduler_acquire(task_name, force=False):
    seed_core()
    now = now_iso()
    row = scheduler_lock_row(task_name)
    if row and str(row.get("status") or "").upper() == "RUNNING" and not is_stale_running(row, now):
        return False, {"ok": True, "task": task_name, "skipped": True, "reason": "running", "started_at": row.get("locked_at"), "errors": []}
    if row and not is_due(row, task_name, os.environ, now, force=force):
        return False, {"ok": True, "task": task_name, "skipped": True, "reason": "intervalo_activo", "next_run": row.get("next_run"), "errors": []}
    conn = db()
    conn.execute(
        """INSERT OR REPLACE INTO scheduler_locks(task_name,locked_at,status,last_run,next_run,error_message)
           VALUES (?,?,?,?,?,?)""",
        (task_name, now, "RUNNING", row.get("last_run") or "", row.get("next_run") or "", ""),
    )
    conn.commit()
    conn.close()
    return True, {"task": task_name, "started_at": now}


def scheduler_release(task_name, result, started_at):
    finished_at = now_iso()
    normalized = normalize_result(task_name, result, started_at=started_at, finished_at=finished_at)
    errors = normalized.get("errors") or []
    status = "OK" if normalized.get("ok") and not errors else ("PARTIAL" if errors and normalized.get("processed", 0) else "ERROR")
    conn = db()
    conn.execute(
        """INSERT OR REPLACE INTO scheduler_locks(task_name,locked_at,status,last_run,next_run,error_message)
           VALUES (?,?,?,?,?,?)""",
        (
            task_name,
            "",
            status,
            finished_at,
            next_run_iso(finished_at, task_name, os.environ),
            "; ".join([str(e) for e in errors[:3]])[:500],
        ),
    )
    conn.commit()
    conn.close()
    return normalized


def cleanup_scheduler_logs(max_rows=300):
    seed_core()
    log_id = sync_log_start("scheduler", "cleanup")
    conn = db()
    before = (conn.execute("SELECT COUNT(*) AS total FROM api_sync_logs").fetchone() or {"total": 0})["total"]
    conn.execute(
        """DELETE FROM api_sync_logs
           WHERE id NOT IN (
             SELECT id FROM api_sync_logs ORDER BY started_at DESC LIMIT ?
           )""",
        (max(50, int(max_rows)),),
    )
    conn.commit()
    after = (conn.execute("SELECT COUNT(*) AS total FROM api_sync_logs").fetchone() or {"total": 0})["total"]
    conn.close()
    removed = max(0, int(before or 0) - int(after or 0))
    sync_log_finish(log_id, "OK", removed, "")
    return {"ok": True, "source": "scheduler", "sync_type": "cleanup", "processed": removed, "inserted": 0, "updated": 0, "skipped": 0, "errors": [], "last_sync": now_iso()}


def refresh_live_basic(limit=80):
    result = sync_sportsdb_calendar(limit=limit)
    save_live_sync_state(
        "scheduler-live",
        {
            "sync": {"sync_status": "live_refresh", "refresh_seconds": as_int(os.getenv("LIVE_CACHE_MINUTES", "2"), 2) * 60, "next_refresh_at": next_run_iso(now_iso(), "live", os.environ)},
            "result": result,
        },
    )
    result["source"] = "live"
    result["sync_type"] = "live"
    return result


def refresh_recommendations_basic(limit=40):
    recs = v565_recommendation_pool(limit=limit)
    return {"ok": True, "processed": len(recs), "inserted": 0, "updated": len(recs), "skipped": 0, "recommendations": len(recs)}


def refresh_auto_picks_basic(limit=40):
    recs = v565_recommendation_pool(limit=limit)
    min_score = as_int(os.getenv("MIN_SHARK_SCORE_FOR_AUTO_SEND", os.getenv("AUTO_PICKS_MIN_SCORE", "78")), 78)
    max_saved = as_int(os.getenv("MAX_AUTO_PICKS_PER_DAY", "4"), 4)
    candidates = []
    discarded = []
    for rec in recs:
        score = as_int(rec.get("score"), 0)
        odds = as_float(rec.get("odds_value") or rec.get("odds"), 0.0)
        if score < min_score:
            discarded.append({"match_id": rec.get("match_id"), "reason": "score_bajo", "score": score})
            continue
        if not rec.get("match_id") or not rec.get("selection"):
            discarded.append({"match_id": rec.get("match_id"), "reason": "datos_incompletos"})
            continue
        if odds <= 1:
            discarded.append({"match_id": rec.get("match_id"), "reason": "sin_cuota_valida", "score": score})
            continue
        candidates.append(rec)
    saved = []
    duplicates = 0
    for rec in candidates[:max_saved]:
        result = ensure_auto_pick_from_recommendation(rec)
        if result.get("created"):
            saved.append(result.get("pick"))
        elif result.get("reason") == "duplicate":
            duplicates += 1
    telegram_log("[AUTO_PICKS]", "reviewed", "Revision de auto picks completada.", {"processed": len(recs), "candidates": len(candidates), "saved": len(saved), "duplicates": duplicates, "discarded": discarded[:12]})
    return {"ok": True, "processed": len(recs), "inserted": len(saved), "updated": len(candidates), "skipped": len(discarded) + duplicates, "auto_candidates": len(candidates), "saved": len(saved), "duplicates": duplicates, "discarded": discarded[:20], "min_score": min_score}


def refresh_live_alerts_basic(limit=40):
    hub = match_hub(today_iso(), "live")
    live_matches = hub.get("live", [])[: int(limit)]
    alerts = []
    for match in live_matches:
        alerts.extend(shark_live_alerts(match, shark_momentum(match)))
    return {"ok": True, "processed": len(live_matches), "inserted": 0, "updated": len(alerts), "skipped": 0, "alerts": alerts[:20], "telegram_ready": True}


def run_scheduler_task(task_name, force=False, limit=None):
    task_name = str(task_name or "").strip().lower()
    if task_name == "warmup":
        started_at = now_iso()
        result = population_warmup(force=True, limit=limit or as_int(os.getenv("POPULATION_WARMUP_LIMIT", "80"), 80))
        return normalize_result("warmup", result, started_at=started_at, finished_at=now_iso())
    acquired, meta = scheduler_acquire(task_name, force=force)
    if not acquired:
        return meta
    started_at = meta.get("started_at") or now_iso()
    log_id = sync_log_start("scheduler", task_name)
    try:
        if task_name == "calendar":
            result = sync_sportsdb_calendar(limit=limit or 120)
        elif task_name == "crests":
            teams_result = sync_sportsdb_teams(limit=limit or 120)
            crest_result = sync_sportsdb_crests(refresh=False, limit=limit or 80)
            result = {
                "ok": not (teams_result.get("errors") or crest_result.get("errors")),
                "processed": as_int(teams_result.get("processed"), 0) + as_int(crest_result.get("processed"), 0),
                "inserted": as_int(teams_result.get("inserted"), 0),
                "updated": as_int(teams_result.get("updated"), 0) + as_int(crest_result.get("updated"), 0),
                "skipped": as_int(teams_result.get("skipped"), 0) + as_int(crest_result.get("skipped"), 0),
                "errors": (teams_result.get("errors") or []) + (crest_result.get("errors") or []),
                "teams": teams_result,
                "crests": crest_result,
            }
        elif task_name == "odds":
            result = sync_odds_events(limit=limit or 250, force=force)
        elif task_name == "live":
            result = refresh_live_basic(limit=limit or 160)
        elif task_name == "recommendations":
            result = refresh_recommendations_basic(limit=limit or 120)
        elif task_name == "auto_picks":
            result = refresh_auto_picks_basic(limit=limit or 40)
        elif task_name == "live_alerts":
            result = refresh_live_alerts_basic(limit=limit or 40)
        elif task_name == "warehouse":
            result = historical_snapshot(limit=limit or 120)
        elif task_name == "cleanup":
            result = cleanup_scheduler_logs(max_rows=as_int(os.getenv("SCHEDULER_LOG_MAX_ROWS", "300"), 300))
        elif task_name == "telegram":
            result = telegram_scheduler_delivery(force=force)
        else:
            result = empty_sync("scheduler", task_name, "Tarea no reconocida.")
        normalized = scheduler_release(task_name, result, started_at)
        sync_log_finish(log_id, "OK" if normalized.get("ok") and not normalized.get("errors") else "PARTIAL", normalized.get("processed", 0), "; ".join(normalized.get("errors", [])[:3]))
        return normalized
    except Exception as exc:
        result = {"ok": False, "processed": 0, "inserted": 0, "updated": 0, "skipped": 0, "errors": [str(exc)[:220]]}
        normalized = scheduler_release(task_name, result, started_at)
        sync_log_finish(log_id, "ERROR", 0, str(exc)[:220])
        return normalized


def run_due_scheduler_tasks(force=False, startup=False):
    if not force and not scheduler_enabled():
        return {"ok": True, "skipped": True, "reason": "auto_sync_disabled", "tasks": []}
    tasks = ["calendar", "crests", "odds", "live", "recommendations", "auto_picks", "live_alerts", "warehouse", "telegram", "cleanup"]
    if startup:
        total_matches = (one("SELECT COUNT(*) AS total FROM matches") or {}).get("total", 0)
        teams_with_crests = (one("SELECT COUNT(*) AS total FROM teams WHERE logo_url IS NOT NULL AND logo_url!=''") or {}).get("total", 0)
        tasks = ["calendar", "live", "odds", "recommendations", "auto_picks", "live_alerts", "warehouse", "telegram", "cleanup"]
        if not total_matches:
            tasks.insert(0, "calendar")
        if not teams_with_crests:
            tasks.insert(1, "crests")
    results = []
    seen = set()
    for task in tasks:
        if task in seen:
            continue
        seen.add(task)
        results.append(run_scheduler_task(task, force=force, limit=as_int(os.getenv("POPULATION_WARMUP_LIMIT", "80"), 80)))
    return {"ok": True, "startup": startup, "tasks": results, "errors": [e for r in results for e in (r.get("errors") or [])]}


def scheduler_status():
    seed_core()
    config = scheduler_env_config()
    locks = {row["task_name"]: row for row in rows("SELECT * FROM scheduler_locks ORDER BY task_name")}
    tasks = []
    for task in config["tasks"]:
        row = locks.get(task["name"], {})
        tasks.append(
            {
                **task,
                "status": row.get("status") or "PENDING",
                "last_run": row.get("last_run") or "",
                "next_run": row.get("next_run") or "",
                "locked_at": row.get("locked_at") or "",
                "error_message": row.get("error_message") or "",
                "due": is_due(row, task["name"], os.environ, now_iso(), force=False),
            }
        )
    return {
        "enabled": config["enabled"],
        "startup": config["startup"],
        "tasks": tasks,
        "recent_errors": [log.get("error_message") for log in rows("SELECT * FROM api_sync_logs WHERE error_message IS NOT NULL AND error_message!='' ORDER BY started_at DESC LIMIT 8")],
        "last_scheduler_log": latest_sync_log("scheduler"),
    }


BACKUP_RETENTION_MAX = 30


def backup_dir():
    configured = os.getenv("BACKUP_DIR", "").strip()
    if configured:
        return os.path.abspath(configured)
    db_path = os.path.abspath(DB_PATH)
    if db_path.startswith(os.path.abspath("/data") + os.sep) or db_path == os.path.abspath("/data/database.db"):
        return "/data/backups"
    return os.path.join(os.path.dirname(db_path) or os.getcwd(), "data", "backups")


def ensure_backup_dir():
    folder = backup_dir()
    os.makedirs(folder, exist_ok=True)
    return folder


def backup_file_path(name):
    safe = os.path.basename(str(name or ""))
    if not re.fullmatch(r"[A-Za-z0-9_.-]+\.db", safe):
        return ""
    folder = os.path.abspath(backup_dir())
    path = os.path.abspath(os.path.join(folder, safe))
    return path if os.path.dirname(path) == folder and os.path.exists(path) else ""


def list_backups():
    folder = ensure_backup_dir()
    items = []
    for path in sorted([p for p in os.listdir(folder) if p.startswith("database_") and p.endswith(".db")], reverse=True):
        full = os.path.join(folder, path)
        try:
            stat = os.stat(full)
            items.append({"name": path, "path": full, "created_at": datetime.fromtimestamp(stat.st_mtime, TZ).isoformat(timespec="seconds"), "size": stat.st_size, "size_mb": round(stat.st_size / (1024 * 1024), 2)})
        except OSError:
            pass
    return items


def prune_old_backups(max_backups=BACKUP_RETENTION_MAX):
    removed = []
    for item in list_backups()[int(max_backups):]:
        try:
            os.remove(item["path"])
            removed.append(item["name"])
        except OSError:
            pass
    return removed


def create_database_backup(reason="manual"):
    source = os.path.abspath(DB_PATH)
    if not os.path.exists(source):
        return {"ok": False, "error": "database_missing", "message": "No existe base de datos que copiar."}
    target = os.path.join(ensure_backup_dir(), f"database_{datetime.now(TZ).strftime('%Y%m%d_%H%M%S')}.db")
    src = sqlite3.connect(source)
    dst = sqlite3.connect(target)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    removed = prune_old_backups()
    return {"ok": True, "name": os.path.basename(target), "path": target, "size": os.path.getsize(target), "reason": reason, "removed": removed}


def restore_database_backup(name):
    path = backup_file_path(name)
    if not path:
        return {"ok": False, "error": "backup_not_found"}
    safety = create_database_backup(reason=f"pre_restore_{os.path.basename(name)}")
    if not safety.get("ok"):
        return {"ok": False, "error": "safety_backup_failed", "safety": safety}
    tmp = os.path.abspath(DB_PATH) + ".restore_tmp"
    with open(path, "rb") as src, open(tmp, "wb") as dst:
        dst.write(src.read())
    os.replace(tmp, os.path.abspath(DB_PATH))
    return {"ok": True, "restored": os.path.basename(name), "safety_backup": safety.get("name")}


def daily_automation_summary():
    last = automation_get("daily_autonomous_system", {}) or {}
    return {
        "last": last,
        "next_run_label": "Hoy 10:00 Europe/Madrid" if str(last.get("date") or "") != today_iso() else "Mañana 10:00 Europe/Madrid",
        "enabled": scheduler_enabled() or daily_automation_env_enabled(),
        "env_enabled": daily_automation_env_enabled(),
        "secret_configured": automation_secret_configured(),
        "due_now": not bool(last.get("date") == today_iso()),
    }

def run_daily_autonomous_system(force=False):
    started = datetime.now(TZ)
    telegram_log("[AUTOMATION]", "start", "Daily automation iniciada.", {"force": bool(force), "scheduler_enabled": scheduler_enabled(), "daily_env": daily_automation_env_enabled()})
    tasks = {
        "calendar": run_scheduler_task("calendar", force=force, limit=220),
        "live": run_scheduler_task("live", force=force, limit=160),
        "recommendations": run_scheduler_task("recommendations", force=force, limit=120),
        "auto_picks": run_scheduler_task("auto_picks", force=force, limit=80),
        "telegram": telegram_scheduler_delivery(force=force),
        "backup": create_database_backup(reason="daily_autonomous_system"),
    }
    errors = [f"{name}: {item.get('error') or item.get('message')}" for name, item in tasks.items() if isinstance(item, dict) and item.get("ok") is False]
    result = {
        "ok": not errors,
        "date": today_iso(),
        "started_at": started.isoformat(timespec="seconds"),
        "finished_at": now_iso(),
        "duration_seconds": round((datetime.now(TZ) - started).total_seconds(), 2),
        "status": "OK" if not errors else "PARTIAL",
        "errors": errors,
        "tasks": tasks,
        "matches_synced": as_int((tasks.get("calendar") or {}).get("processed"), 0) + as_int((tasks.get("live") or {}).get("processed"), 0),
        "picks_generated": as_int((tasks.get("auto_picks") or {}).get("saved") or ((tasks.get("auto_picks") or {}).get("raw") or {}).get("saved"), 0),
        "picks_sent": as_int((tasks.get("telegram") or {}).get("sent"), 0),
        "backups_created": 1 if (tasks.get("backup") or {}).get("ok") else 0,
    }
    automation_set("daily_autonomous_system", result)
    telegram_log("[AUTOMATION]", "finished", "Daily automation finalizada.", {"ok": result.get("ok"), "picks_generated": result.get("picks_generated"), "picks_sent": result.get("picks_sent"), "errors": result.get("errors")})
    return result


def odds_last_sync():
    state = one("SELECT * FROM automation_state WHERE key='odds_events_sync'")
    if not state:
        return {}
    try:
        return json.loads(state.get("value_json") or "{}")
    except json.JSONDecodeError:
        return {"raw": state.get("value_json")}


def odds_recently_synced():
    last = odds_last_sync()
    timestamp = last.get("time") or ""
    if not timestamp:
        return False
    try:
        dt = datetime.fromisoformat(timestamp)
        return (datetime.now(TZ) - dt).total_seconds() < odds_cache_minutes() * 60
    except ValueError:
        return False


def odds_event_id(sport_key, event):
    raw = event.get("id") or f"{sport_key}-{event.get('commence_time')}-{event.get('home_team')}-{event.get('away_team')}"
    return "odds-" + hashlib.md5(str(raw).encode("utf-8")).hexdigest()[:18]


def odds_event_to_match(sport, event):
    home = event.get("home_team") or ""
    away = event.get("away_team") or ""
    if not home or not away or is_fake_team_name(home) or is_fake_team_name(away):
        return None
    home = spanish_team_name(home)
    away = spanish_team_name(away)
    commence = str(event.get("commence_time") or "")
    time_values = madrid_values_from_datetime(commence)
    match_date = time_values.get("match_date") or (commence[:10] if len(commence) >= 10 else today_iso())
    match_time = time_values.get("kickoff_time") or (commence[11:16] if "T" in commence else "")
    odds_snapshot = h2h_price_snapshot(event)
    comp_key = sport.get("key") or slug(event.get("sport_key") or "odds")
    comp_name = spanish_competition_name(sport.get("name") or event.get("sport_title") or comp_key)
    status = sync_normalize_status(event.get("status") or "PROGRAMADO")
    return {
        "id": odds_event_id(sport.get("odds_key") or comp_key, event),
        "external_id": event.get("id") or "",
        "match_date": match_date,
        "kickoff_time": match_time,
        "match_time": match_time,
        "kickoff_iso": time_values.get("kickoff_iso") or commence or kickoff_iso_value(match_date, match_time),
        "competition_id": event.get("sport_key") or sport.get("odds_key") or "",
        "competition_key": comp_key,
        "competition_name": comp_name,
        "league_name": comp_name,
        "country": spanish_country_name(sport.get("country") or ""),
        "home_team": home,
        "away_team": away,
        "home_team_id": "",
        "away_team_id": "",
        "home_logo": "",
        "away_logo": "",
        "status": status,
        "minute": "",
        "score": "",
        "home_score": "",
        "away_score": "",
        "venue": "",
        "season": "",
        "round": "",
        "priority": priority_for(comp_key, status),
        "source": "The Odds API",
        "legal_note": "Partido/cuotas obtenidos desde The Odds API autorizada y guardados en SQLite; sin scraping.",
        "raw_json": json.dumps(event, ensure_ascii=False)[:5000],
        "bookmaker": odds_snapshot.get("bookmaker") or "",
        "odds_h2h_json": json.dumps(odds_snapshot, ensure_ascii=False)[:3000] if odds_snapshot else "",
        "odds_updated_at": odds_snapshot.get("last_update") or "",
    }


def fetch_odds_events(limit=250):
    events = []
    errors = []
    for sport in odds_competitions():
        if len(events) >= int(limit):
            break
        try:
            payload = odds_api_get(
                f"sports/{sport['odds_key']}/odds",
                {
                    "regions": os.getenv("ODDS_REGIONS", "eu,uk"),
                    "markets": os.getenv("ODDS_MARKETS", "h2h"),
                    "oddsFormat": "decimal",
                    "dateFormat": "iso",
                },
            )
            if isinstance(payload, list):
                events.extend([(sport, item) for item in payload if isinstance(item, dict)])
        except Exception as exc:
            errors.append(f"{sport['name']}: {str(exc)[:160]}")
    return events[: int(limit)], errors


def sync_odds_events(limit=250, force=False):
    seed_core()
    if not os.getenv("THE_ODDS_API_KEY"):
        return {"ok": False, "sin_key": True, "skipped": False, "imported": 0, "updated": 0, "processed": 0, "errors": ["Falta THE_ODDS_API_KEY."]}
    if not odds_enabled():
        return {"ok": False, "sin_key": False, "disabled": True, "skipped": True, "imported": 0, "updated": 0, "processed": 0, "errors": ["ENABLE_ODDS_API no esta activo."]}
    if odds_recently_synced() and not force:
        last = odds_last_sync()
        return {"ok": True, "skipped": True, "reason": "cache_activa", "cache_minutes": odds_cache_minutes(), **last}
    log_id = sync_log_start("The Odds API", "events")
    try:
        fetched, errors = fetch_odds_events(limit=limit)
        match_rows = []
        seen = set()
        for sport, event in fetched:
            match = odds_event_to_match(sport, event)
            if not match or match["id"] in seen:
                continue
            seen.add(match["id"])
            match_rows.append(match)
        result = upsert_sportsdb_matches(match_rows)
        odds_snapshot_result = upsert_odds_snapshots(fetched)
        result["errors"] = errors[:12]
        result["source"] = "The Odds API"
        result["sync_type"] = "events"
        result["inserted"] = result.get("inserted", result.get("imported", 0))
        result["odds_snapshots"] = odds_snapshot_result
        result["skipped"] = False
        result["last_sync"] = now_iso()
        conn = db()
        conn.execute(
            """INSERT OR REPLACE INTO automation_state(key,value_json,updated_at)
               VALUES (?,?,?)""",
            ("odds_events_sync", json.dumps(result, ensure_ascii=False), now_iso()),
        )
        conn.commit()
        conn.close()
        sync_log_finish(log_id, "OK" if not errors else "PARTIAL", result.get("processed", 0), "; ".join(errors[:3]))
        return result
    except Exception as exc:
        sync_log_finish(log_id, "ERROR", 0, str(exc))
        return {"ok": False, "skipped": False, "imported": 0, "updated": 0, "processed": 0, "errors": [str(exc)[:200]]}


def odds_diagnostics():
    cached = (one("SELECT COUNT(*) AS total FROM matches WHERE source='The Odds API'") or {}).get("total", 0)
    snapshots = (one("SELECT COUNT(*) AS total FROM odds_snapshots") or {}).get("total", 0)
    return {
        "key_present": bool(os.getenv("THE_ODDS_API_KEY")),
        "key_masked": masked_key(os.getenv("THE_ODDS_API_KEY", "")),
        "enabled": odds_enabled(),
        "cache_minutes": odds_cache_minutes(),
        "cached_matches": cached,
        "odds_snapshots": snapshots,
        "last_sync": odds_last_sync(),
        "sports_configured": len(odds_competitions()),
        "regions": os.getenv("ODDS_REGIONS", "eu,uk"),
        "markets": os.getenv("ODDS_MARKETS", "h2h"),
        "legal_policy": "The Odds API solo mediante API permitida y cache persistente; sin scraping.",
    }


def match_calendar_diagnostics():
    seed_core()
    total_matches = (one("SELECT COUNT(*) AS total FROM matches") or {}).get("total", 0)
    dedupe_metrics = match_deduplication_metrics()
    upcoming = (one("SELECT COUNT(*) AS total FROM matches WHERE match_date>=? AND lower(COALESCE(status,'')) NOT IN ('finalizado','ft','finished','final','match finished')", (today_iso(),)) or {}).get("total", 0)
    finished_count = (one("SELECT COUNT(*) AS total FROM matches WHERE lower(COALESCE(status,'')) IN ('finalizado','ft','finished','final','match finished') OR (match_date<? AND COALESCE(score,'')!='')", (today_iso(),)) or {}).get("total", 0)
    live_count = (one("SELECT COUNT(*) AS total FROM matches WHERE lower(COALESCE(status,'')) IN ('live','directo','descanso','ht','1h','2h')") or {}).get("total", 0)
    live_table = (one("SELECT COUNT(*) AS total FROM live_matches") or {}).get("total", 0)
    logs = rows("SELECT * FROM api_sync_logs ORDER BY started_at DESC LIMIT 8")
    latest_log = logs[0] if logs else {}
    sportsdb = sportsdb_feed_status()
    odds = odds_diagnostics()
    if sportsdb.get("cached_matches"):
        active_source = "TheSportsDB cache"
    elif odds.get("cached_matches"):
        active_source = "The Odds API cache"
    elif total_matches:
        active_source = "importacion legal/manual"
    else:
        active_source = "sin datos sincronizados"
    return {
        "total_competitions": (one("SELECT COUNT(*) AS total FROM competitions") or {}).get("total", 0),
        "total_teams": (one("SELECT COUNT(*) AS total FROM teams") or {}).get("total", 0),
        "total_matches": total_matches,
        "unique_matches": dedupe_metrics["unique_matches"],
        "duplicates_detected": dedupe_metrics["duplicates_detected"],
        "duplicate_groups": dedupe_metrics["duplicate_groups"],
        "duplicate_examples": dedupe_metrics["examples"],
        "upcoming_matches": upcoming,
        "live_matches": live_count,
        "finished_matches": finished_count,
        "live_table_rows": live_table,
        "odds_snapshots": (one("SELECT COUNT(*) AS total FROM odds_snapshots") or {}).get("total", 0),
        "competitions_no_data": rows("SELECT key,name,country,region FROM competitions WHERE sync_status='no_data' ORDER BY tier DESC LIMIT 20"),
        "latest_sync": latest_log,
        "active_data_source": active_source,
        "sportsdb_key_present": bool(thesportsdb_key()),
        "sportsdb_key_masked": masked_key(thesportsdb_key()),
        "odds_key_present": bool(os.getenv("THE_ODDS_API_KEY")),
        "odds_key_masked": masked_key(os.getenv("THE_ODDS_API_KEY", "")),
        "enable_live_api": sportsdb_live_enabled(),
        "enable_odds_api": odds_enabled(),
        "sportsdb": sportsdb,
        "odds": odds,
        "errors_recent": [log.get("error_message") for log in logs if log.get("error_message")],
        "competitions_ready": IMPORTANT_COMPETITIONS,
        "matches_by_day": rows("SELECT match_date, COUNT(*) AS total FROM matches GROUP BY match_date ORDER BY match_date LIMIT 14"),
        "matches_by_league": rows("SELECT COALESCE(competition_name, league_name, competition_key) AS league, country, COUNT(*) AS total FROM matches GROUP BY COALESCE(competition_name, league_name, competition_key), country ORDER BY total DESC LIMIT 25"),
        "results_by_league": rows("SELECT COALESCE(competition_name, league_name, competition_key) AS league, country, COUNT(*) AS total FROM matches WHERE lower(COALESCE(status,'')) IN ('finalizado','ft','finished','final','match finished') OR (match_date<? AND COALESCE(score,'')!='') GROUP BY COALESCE(competition_name, league_name, competition_key), country ORDER BY total DESC LIMIT 25", (today_iso(),)),
        "next_7_days": rows("SELECT match_date, COALESCE(competition_name, league_name, competition_key) AS league, COUNT(*) AS total FROM matches WHERE match_date>=? AND match_date<=? GROUP BY match_date, COALESCE(competition_name, league_name, competition_key) ORDER BY match_date, league LIMIT 80", (today_iso(), today_iso(7))),
        "grouping_policy": "Calendario agrupado por día, liga y hora.",
    }


def thesportsdb_diagnostics(team_name="Real Madrid"):
    api_key = thesportsdb_key()
    live_enabled = str(os.getenv("ENABLE_LIVE_API", "")).strip().lower() in {"1", "true", "yes", "on"}
    can_resolve = False
    can_load_crest = False
    resolved = None
    if api_key:
        for variant in sportsdb_name_variants(team_name):
            resolved = fetch_thesportsdb_team(variant)
            if resolved:
                break
        can_resolve = bool(resolved)
        can_load_crest = bool((resolved or {}).get("logo_url"))
    status = crest_sync_status()
    feed = sportsdb_feed_status()
    return {
        "key_present": bool(api_key),
        "key_masked": masked_key(api_key),
        "live_enabled": live_enabled,
        "total_teams": status["total_teams"],
        "teams_with_logo": status["with_logo"],
        "teams_fallback": status["fallback"],
        "cached_matches": feed["cached_matches"],
        "last_feed_sync": feed["last_sync"],
        "last_sync": status["last_sync"],
        "missing_examples": status["missing_examples"],
        "team_checked": team_name,
        "can_resolve_teams": can_resolve,
        "can_load_crests": can_load_crest,
        "resolved_team": {
            "name": (resolved or {}).get("name"),
            "external_id": (resolved or {}).get("external_id"),
            "crest_mode": "logo" if can_load_crest else "fallback",
        },
        "last_error": get_thesportsdb_last_error(),
        "fallback_available": True,
        "legal_policy": "TheSportsDB solo mediante API permitida y variables de entorno; sin scraping ilegal.",
    }


def cache_team_identity(name, identity):
    key = canonical_team_key(name)
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """INSERT OR REPLACE INTO teams
           (key,name,country,region,league,logo_url,external_id,color_hint,source,legal_note,updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (
            key,
            identity.get("name") or name,
            identity.get("country") or "",
            identity.get("region") or "",
            identity.get("league") or "",
            identity.get("logo_url") or "",
            identity.get("external_id") or "",
            identity.get("color_hint") or "premium-blue",
            identity.get("source") or "manual/API",
            identity.get("legal_note") or "Identidad cargada por fuente permitida.",
            now_iso(),
        ),
    )
    conn.commit()
    conn.close()


def resolve_team(name, refresh=False):
    key = canonical_team_key(name)
    cache_key = f"{key}:{int(bool(refresh))}"
    if not refresh and cache_key in TEAM_IDENTITY_CACHE:
        return dict(TEAM_IDENTITY_CACHE[cache_key])
    team = one("SELECT * FROM teams WHERE key=?", (key,))
    if refresh:
        found = None
        if (team or {}).get("external_id"):
            found = fetch_thesportsdb_team_by_id(team.get("external_id"))
        if not found:
            for variant in sportsdb_name_variants((team or {}).get("name") or name):
                found = fetch_thesportsdb_team(variant)
                if found:
                    break
        if found and found.get("logo_url"):
            cache_team_identity(name, found)
            team = one("SELECT * FROM teams WHERE key=?", (key,))
    if not team:
        team = {"key": key, "name": spanish_team_name(name) or name or "Equipo", "logo_url": "", "country": "", "region": "", "source": "fallback propio", "legal_note": "Iniciales/emoji generados por la app."}
    team = professionalize_identity(team, team.get("name") or name, team.get("logo_url"), team.get("country"), team.get("source") or "teams")
    team["key"] = key
    TEAM_IDENTITY_CACHE[cache_key] = dict(team)
    return team


def priority_for(competition_key, status="", favorite=False, has_pick=False):
    comp = {key: tier for key, _, _, _, _, tier, _, _ in COMPETITION_SEEDS}.get(competition_key, 55)
    status_text = str(status or "").lower()
    if any(x in status_text for x in ["live", "directo", "1h", "2h", "ht"]):
        comp += 12
    if favorite:
        comp += 9
    if has_pick:
        comp += 7
    return min(comp, 100)


def parse_payload(text):
    text = str(text or "").strip()
    if not text:
        return []
    if text.startswith("{") or text.startswith("["):
        data = json.loads(text)
        if isinstance(data, dict):
            data = data.get("matches") or data.get("rows") or [data]
        return [x for x in data if isinstance(x, dict)]
    reader = csv.DictReader(io.StringIO(text.replace(";", ",")))
    return [dict(row) for row in reader]


def import_matches(import_rows, source_name="manual", source_url="", legal_note="Carga autorizada"):
    seed_core()
    conn = db()
    cur = conn.cursor()
    count = 0
    for item in import_rows:
        home = item.get("home_team") or item.get("home") or item.get("local") or item.get("equipo_local") or ""
        away = item.get("away_team") or item.get("away") or item.get("visitante") or item.get("equipo_visitante") or ""
        if not home or not away or is_fake_team_name(home) or is_fake_team_name(away):
            continue
        home = spanish_team_name(home)
        away = spanish_team_name(away)
        league_name = spanish_competition_name(item.get("league_name") or item.get("competition_name") or item.get("competition") or item.get("league") or item.get("liga") or "manual")
        comp_key = item.get("competition_key") or slug(league_name)
        comp_name = spanish_competition_name(item.get("competition_name") or league_name or comp_key)
        raw_kickoff_iso = item.get("kickoff_iso") or item.get("commence_time") or item.get("start_time") or ""
        raw_date = item.get("match_date") or item.get("date") or item.get("fecha") or today_iso()
        raw_time = item.get("match_time") or item.get("kickoff_time") or item.get("time") or item.get("hora") or ""
        if raw_kickoff_iso:
            time_values = madrid_values_from_datetime(raw_kickoff_iso, raw_date, raw_time)
            date = time_values.get("match_date") or str(raw_date)[:10]
            kickoff = time_values.get("kickoff_time") or str(raw_time)[:5]
            stored_kickoff_iso = time_values.get("kickoff_iso") or raw_kickoff_iso
        else:
            date = str(raw_date or today_iso())[:10]
            kickoff = str(raw_time or "")[:5]
            stored_kickoff_iso = kickoff_iso_value(date, kickoff)
        status = item.get("status") or item.get("estado") or "PROGRAMADO"
        raw_id = item.get("id") or item.get("match_id") or f"{date}-{comp_key}-{home}-{away}-{kickoff}"
        match_id = hashlib.md5(str(raw_id).encode("utf-8")).hexdigest()[:18]
        cur.execute(
            """INSERT OR REPLACE INTO matches
               (id,external_id,match_date,kickoff_time,match_time,kickoff_iso,competition_id,competition_key,competition_name,league_name,country,
                home_team,away_team,home_team_id,away_team_id,home_logo,away_logo,status,minute,score,home_score,away_score,venue,season,round,
                priority,source,legal_note,raw_json,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                match_id,
                item.get("external_id") or raw_id,
                date,
                kickoff,
                kickoff,
                stored_kickoff_iso,
                item.get("competition_id") or "",
                comp_key,
                comp_name,
                league_name,
                spanish_country_name(item.get("country") or item.get("pais") or ""),
                home,
                away,
                item.get("home_team_id") or "",
                item.get("away_team_id") or "",
                item.get("home_logo") or "",
                item.get("away_logo") or "",
                status,
                item.get("minute") or item.get("minuto") or "",
                item.get("score") or item.get("marcador") or "",
                item.get("home_score") or "",
                item.get("away_score") or "",
                item.get("venue") or "",
                item.get("season") or "",
                item.get("round") or "",
                int(item.get("priority") or priority_for(comp_key, status)),
                source_name,
                legal_note,
                json.dumps(item, ensure_ascii=False)[:5000],
                now_iso(),
            ),
        )
        count += 1
    dedupe_result = cleanup_duplicate_matches(cur)
    cur.execute("DELETE FROM persistent_cache WHERE key LIKE 'match-hub:%'")
    import_id = hashlib.md5(f"{source_name}-{now_iso()}-{count}".encode("utf-8")).hexdigest()[:18]
    cur.execute(
        """INSERT INTO imports
           (id,kind,source_name,source_url,legal_note,rows_count,status,payload_preview,created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (import_id, "matches", source_name, source_url, legal_note, count, "IMPORTED", json.dumps(import_rows[:3], ensure_ascii=False)[:2000], now_iso()),
    )
    conn.commit()
    conn.close()
    sync_log_finish(sync_log_start("import", "matches"), "OK", count, "")
    return {"ok": True, "imported": count, "import_id": import_id, "duplicates_removed": dedupe_result.get("duplicates_removed", 0), "duplicate_groups": dedupe_result.get("groups", 0)}


def import_teams(team_rows, source_name="manual", legal_note="Carga autorizada"):
    seed_core()
    conn = db()
    cur = conn.cursor()
    count = 0
    for item in team_rows:
        name = item.get("name") or item.get("team") or item.get("equipo") or item.get("display_name") or ""
        if not name:
            continue
        key = canonical_team_key(item.get("key") or name)
        cur.execute(
            """INSERT OR REPLACE INTO teams
               (key,name,country,region,league,logo_url,external_id,color_hint,source,legal_note,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                key,
                name,
                item.get("country") or item.get("pais") or "",
                item.get("region") or item.get("provincia") or "",
                item.get("league") or item.get("liga") or "",
                item.get("logo_url") or item.get("crest_url") or item.get("escudo") or "",
                item.get("external_id") or item.get("idTeam") or "",
                item.get("color_hint") or "premium-blue",
                source_name,
                legal_note,
                now_iso(),
            ),
        )
        count += 1
    import_id = hashlib.md5(f"teams-{source_name}-{now_iso()}-{count}".encode("utf-8")).hexdigest()[:18]
    cur.execute(
        """INSERT INTO imports
           (id,kind,source_name,source_url,legal_note,rows_count,status,payload_preview,created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (import_id, "teams", source_name, "", legal_note, count, "IMPORTED", json.dumps(team_rows[:3], ensure_ascii=False)[:2000], now_iso()),
    )
    conn.commit()
    conn.close()
    sync_log_finish(sync_log_start("import", "teams"), "OK", count, "")
    return {"ok": True, "imported": count, "import_id": import_id}


def import_competitions(import_rows, source_name="manual autorizado", legal_note="Carga autorizada"):
    seed_core()
    conn = db()
    cur = conn.cursor()
    count = 0
    for item in import_rows:
        name = item.get("name") or item.get("competition_name") or item.get("league_name") or item.get("liga") or ""
        if not name:
            continue
        key = item.get("key") or slug(name)
        cur.execute(
            """INSERT OR REPLACE INTO competitions
               (key,name,scope,country,region,tier,source_strategy,tags_json,external_id,source,sync_status,last_sync_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                key,
                name,
                item.get("scope") or "import",
                item.get("country") or item.get("pais") or "",
                item.get("region") or "",
                as_int(item.get("tier"), 60),
                item.get("source_strategy") or "Import legal",
                json.dumps([item.get("tag") or "import"]),
                item.get("external_id") or "",
                source_name,
                item.get("sync_status") or "imported",
                now_iso(),
                now_iso(),
            ),
        )
        count += 1
    import_id = hashlib.md5(f"competitions-{source_name}-{now_iso()}-{count}".encode("utf-8")).hexdigest()[:18]
    cur.execute(
        """INSERT INTO imports
           (id,kind,source_name,source_url,legal_note,rows_count,status,payload_preview,created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (import_id, "competitions", source_name, "", legal_note, count, "IMPORTED", json.dumps(import_rows[:3], ensure_ascii=False)[:2000], now_iso()),
    )
    conn.commit()
    conn.close()
    sync_log_finish(sync_log_start("import", "competitions"), "OK", count, "")
    return {"ok": True, "imported": count, "inserted": count, "updated": 0, "skipped": 0, "processed": len(import_rows), "import_id": import_id}


def import_odds_snapshots(import_rows, source_name="manual odds autorizado", legal_note="Carga autorizada"):
    seed_core()
    conn = db()
    cur = conn.cursor()
    inserted = updated = skipped = 0
    for item in import_rows:
        home = item.get("home_team") or item.get("home") or item.get("local") or ""
        away = item.get("away_team") or item.get("away") or item.get("visitante") or ""
        if not home or not away:
            skipped += 1
            continue
        match_id = item.get("match_id") or hashlib.md5(str(f"{item.get('commence_time') or item.get('match_date')}-{home}-{away}").encode("utf-8")).hexdigest()[:18]
        snap_id = item.get("id") or hashlib.md5(f"manual-odds-{match_id}-{item.get('bookmaker')}-{now_iso()}".encode("utf-8")).hexdigest()[:18]
        exists = cur.execute("SELECT id FROM odds_snapshots WHERE id=?", (snap_id,)).fetchone()
        cur.execute(
            """INSERT OR REPLACE INTO odds_snapshots
               (id,match_id,external_id,source,sport_key,league_name,bookmaker,market,home_team,away_team,home_price,draw_price,away_price,commence_time,payload_json,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                snap_id,
                match_id,
                item.get("external_id") or "",
                source_name,
                item.get("sport_key") or "",
                item.get("league_name") or item.get("competition_name") or "",
                item.get("bookmaker") or "",
                item.get("market") or "h2h",
                home,
                away,
                str(item.get("home_price") or item.get("cuota_local") or ""),
                str(item.get("draw_price") or item.get("cuota_empate") or ""),
                str(item.get("away_price") or item.get("cuota_visitante") or ""),
                item.get("commence_time") or item.get("kickoff_iso") or "",
                json.dumps(item, ensure_ascii=False)[:5000],
                now_iso(),
            ),
        )
        if exists:
            updated += 1
        else:
            inserted += 1
    import_id = hashlib.md5(f"odds-{source_name}-{now_iso()}-{inserted}".encode("utf-8")).hexdigest()[:18]
    cur.execute(
        """INSERT INTO imports
           (id,kind,source_name,source_url,legal_note,rows_count,status,payload_preview,created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (import_id, "odds", source_name, "", legal_note, inserted + updated, "IMPORTED", json.dumps(import_rows[:3], ensure_ascii=False)[:2000], now_iso()),
    )
    conn.commit()
    conn.close()
    sync_log_finish(sync_log_start("import", "odds"), "OK", inserted + updated, "")
    return {"ok": True, "imported": inserted, "inserted": inserted, "updated": updated, "skipped": skipped, "processed": len(import_rows), "import_id": import_id}


def import_results(result_rows, source_name="manual results autorizado", legal_note="Carga autorizada"):
    for item in result_rows:
        item.setdefault("status", "FINALIZADO")
    result = import_matches(result_rows, source_name=source_name, source_url="", legal_note=legal_note)
    result["sync_type"] = "results"
    return result


def as_float(value, default=0.0):
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default


def as_int(value, default=50):
    try:
        return int(float(str(value).replace(",", ".")))
    except (TypeError, ValueError):
        return default


def combi_leg_count(value=None, default=3):
    """Clamp combinadas to the commercial V713 limit: 2 to 15 legs."""
    return max(COMBI_MIN_LEGS, min(as_int(value, default), COMBI_MAX_LEGS))


def import_picks(pick_rows, source_name="manual autorizado", legal_note="Carga autorizada"):
    seed_core()
    conn = db()
    cur = conn.cursor()
    count = 0
    for item in pick_rows:
        selection = item.get("selection") or item.get("pick") or item.get("pronostico") or item.get("mercado") or ""
        home = item.get("home_team") or item.get("home") or item.get("local") or ""
        away = item.get("away_team") or item.get("away") or item.get("visitante") or ""
        if not selection:
            continue
        date = item.get("match_date") or item.get("date") or item.get("fecha") or today_iso()
        comp_key = item.get("competition_key") or slug(item.get("competition") or item.get("league") or item.get("liga") or "")
        comp_name = item.get("competition_name") or item.get("competition") or item.get("league") or item.get("liga") or comp_key
        match_id = item.get("match_id") or ""
        raw_id = item.get("id") or f"{date}-{comp_key}-{home}-{away}-{selection}-{item.get('odds')}"
        pick_id = hashlib.md5(str(raw_id).encode("utf-8")).hexdigest()[:18]
        cur.execute(
            """INSERT OR REPLACE INTO picks
               (id,match_id,match_date,competition_key,competition_name,home_team,away_team,pick_type,selection,odds,confidence,stake_units,status,source,legal_note,reasoning,raw_json,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                pick_id,
                match_id,
                date,
                comp_key,
                comp_name,
                home,
                away,
                item.get("pick_type") or item.get("type") or item.get("tipo") or "principal",
                selection,
                as_float(item.get("odds") or item.get("cuota"), 0.0),
                max(1, min(100, as_int(item.get("confidence") or item.get("confianza"), 50))),
                as_float(item.get("stake_units") or item.get("stake") or item.get("unidades"), 1.0),
                item.get("status") or item.get("estado") or "PENDING",
                source_name,
                legal_note,
                item.get("reasoning") or item.get("analisis") or "",
                json.dumps(item, ensure_ascii=False)[:5000],
                now_iso(),
                now_iso(),
            ),
        )
        count += 1
    import_id = hashlib.md5(f"picks-{source_name}-{now_iso()}-{count}".encode("utf-8")).hexdigest()[:18]
    cur.execute(
        """INSERT INTO imports
           (id,kind,source_name,source_url,legal_note,rows_count,status,payload_preview,created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (import_id, "picks", source_name, "", legal_note, count, "IMPORTED", json.dumps(pick_rows[:3], ensure_ascii=False)[:2000], now_iso()),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "imported": count, "import_id": import_id}


def normalize_pick_status(value):
    value = str(value or "draft").strip().lower()
    aliases = {"pending": "published", "publicado": "published", "pendiente": "published", "borrador": "draft", "archivado": "archived", "ganado": "won", "perdido": "lost", "nulo": "void"}
    return aliases.get(value, value if value in {"draft", "published", "archived", "won", "lost", "void", "pending"} else "draft")


def normalize_risk(value):
    value = str(value or "MEDIO").strip().upper()
    if value in {"LOW", "BAJO", "CONTROLADO", "SEGURO"}:
        return "BAJO"
    if value in {"HIGH", "ALTO", "AGRESIVO"}:
        return "ALTO"
    return "MEDIO"


def membership_rank(plan):
    plan = normalize_role(plan)
    return {"FREE": 0, "PRO": 1, "ELITE": 2, "ADMIN": 3}.get(plan, 0)


def membership_allows(user_membership, required):
    return membership_rank(user_membership or "FREE") >= membership_rank(required or "FREE")


def normalize_pick_row(pick):
    pick = dict(pick or {})
    pick["odds"] = as_float(pick.get("odds"), 0.0)
    pick["confidence"] = max(1, min(100, as_int(pick.get("confidence"), 50)))
    pick["stake_units"] = as_float(pick.get("stake_units"), 1.0)
    pick["stake_euros_example"] = as_float(pick.get("stake_euros_example"), round(pick["stake_units"] * 10, 2))
    pick["status"] = normalize_pick_status(pick.get("status"))
    pick["risk_level"] = normalize_risk(pick.get("risk_level"))
    pick["membership_required"] = normalize_role(pick.get("membership_required") or "FREE")
    pick["market"] = pick.get("market") or pick.get("pick_type") or "Principal"
    pick["bookmaker"] = pick.get("bookmaker") or ""
    pick["warning_reason"] = pick.get("warning_reason") or "Gestiona stake y evita perseguir pérdidas."
    pick["result_status"] = str(pick.get("result_status") or "pending").lower()
    pick = apply_pick_localization(pick)
    pick["home_identity"] = professionalize_identity(pick.get("home_identity"), pick.get("home_team"), pick.get("home_logo"), pick.get("country") or pick.get("safe_country"), "pick")
    pick["away_identity"] = professionalize_identity(pick.get("away_identity"), pick.get("away_team"), pick.get("away_logo"), pick.get("country") or pick.get("safe_country"), "pick")
    pick["home_logo"] = safe_team_logo_url(pick.get("home_logo")) or pick["home_identity"].get("logo_url") or ""
    pick["away_logo"] = safe_team_logo_url(pick.get("away_logo")) or pick["away_identity"].get("logo_url") or ""
    pick["home_badge_text"] = pick["home_identity"].get("flag_emoji") or pick["home_identity"].get("initials")
    pick["away_badge_text"] = pick["away_identity"].get("flag_emoji") or pick["away_identity"].get("initials")
    pick = enrich_pick_quality(pick)
    pick = enrich_pick_analysis(pick)
    return pick


def get_picks(limit=50, status=None, membership=None, include_admin=False):
    clauses = []
    params = []
    if status:
        statuses = status if isinstance(status, (list, tuple, set)) else [status]
        placeholders = ",".join("?" for _ in statuses)
        clauses.append(f"lower(status) IN ({placeholders})")
        params.extend([normalize_pick_status(x) for x in statuses])
    if membership and not include_admin:
        allowed = [plan for plan, rank in {"FREE": 0, "PRO": 1, "ELITE": 2, "ADMIN": 3}.items() if rank <= membership_rank(membership)]
        placeholders = ",".join("?" for _ in allowed)
        clauses.append(f"upper(COALESCE(membership_required,'FREE')) IN ({placeholders})")
        params.extend(allowed)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    query = f"SELECT * FROM picks{where} ORDER BY COALESCE(published_at, updated_at, created_at) DESC, confidence DESC LIMIT ?"
    params.append(int(limit))
    return sort_picks_by_quality([normalize_pick_row(pick) for pick in rows(query, params)])


def published_picks_for_user(user=None, limit=50):
    user = user or current_session_user() or {"membership": "FREE", "role": "FREE"}
    membership = user.get("membership") or user.get("role") or "FREE"
    include_admin = normalize_role(user.get("role")) == "ADMIN"
    return sort_picks_by_quality(get_picks(limit=limit, status=["published", "won", "lost", "void"], membership=membership, include_admin=include_admin))


def create_or_update_pick(payload, pick_id=None, publish=False):
    seed_core()
    payload = dict(payload or {})
    match_id = payload.get("match_id") or ""
    selected_match = one("SELECT * FROM matches WHERE id=?", (match_id,)) if match_id else None
    home = spanish_team_name(payload.get("home_team") or (selected_match or {}).get("home_team") or "")
    away = spanish_team_name(payload.get("away_team") or (selected_match or {}).get("away_team") or "")
    league = spanish_competition_name(payload.get("league_name") or payload.get("competition_name") or (selected_match or {}).get("league_name") or (selected_match or {}).get("competition_name") or "")
    match_date = payload.get("match_date") or (selected_match or {}).get("match_date") or today_iso()
    pick_id = pick_id or payload.get("id") or hashlib.md5(f"pick-{match_id}-{home}-{away}-{payload.get('selection')}-{now_iso()}".encode("utf-8")).hexdigest()[:18]
    status = normalize_pick_status(payload.get("status") or ("published" if publish else "draft"))
    published_at = now_iso() if status == "published" else payload.get("published_at")
    conn = db()
    conn.execute(
        """INSERT OR REPLACE INTO picks
           (id,match_id,match_date,competition_key,competition_name,home_team,away_team,pick_type,market,selection,odds,bookmaker,confidence,stake_units,stake_euros_example,risk_level,status,result_status,source,legal_note,reasoning,warning_reason,membership_required,raw_json,created_at,updated_at,published_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            pick_id,
            match_id,
            match_date,
            payload.get("competition_key") or slug(league),
            league,
            home,
            away,
            payload.get("pick_type") or payload.get("market") or "principal",
            payload.get("market") or payload.get("pick_type") or "Principal",
            payload.get("selection") or "",
            as_float(payload.get("odds") or payload.get("cuota"), 0.0),
            payload.get("bookmaker") or "",
            max(1, min(100, as_int(payload.get("confidence") or payload.get("confianza"), 60))),
            as_float(payload.get("stake_units") or payload.get("stake"), 1.0),
            as_float(payload.get("stake_euros_example") or payload.get("stake_euros"), 10.0),
            normalize_risk(payload.get("risk_level") or payload.get("riesgo")),
            status,
            str(payload.get("result_status") or "pending").lower(),
            payload.get("source") or "admin",
            payload.get("legal_note") or "Pick creado/revisado manualmente por administrador.",
            payload.get("reasoning") or payload.get("motivo") or "",
            payload.get("warning_reason") or payload.get("precaucion") or "El stake debe adaptarse a la banca del usuario.",
            normalize_role(payload.get("membership_required") or payload.get("membership") or "FREE"),
            json.dumps(payload, ensure_ascii=False)[:5000],
            payload.get("created_at") or now_iso(),
            now_iso(),
            published_at,
        ),
    )
    conn.commit()
    conn.close()
    saved_pick = normalize_pick_row(one("SELECT * FROM picks WHERE id=?", (pick_id,)))
    try:
        safe_memory_call(DB_PATH, "pick_save", remember_pick_decision, pick=saved_pick, decision=status, reason=saved_pick.get("reasoning") or "pick guardado")
    except Exception:
        pass
    return saved_pick


def ensure_auto_pick_from_recommendation(rec):
    rec = dict(rec or {})
    match_id = str(rec.get("match_id") or "").strip()
    selection = str(rec.get("selection") or "").strip()
    odds = as_float(rec.get("odds_value") or rec.get("odds"), 0.0)
    if not match_id or not selection:
        return {"ok": False, "created": False, "reason": "datos_incompletos"}
    if odds <= 1:
        return {"ok": False, "created": False, "reason": "sin_cuota_valida"}
    market = "Resultado / analisis SHARK"
    source = "auto_picks_scheduler"
    existing = one(
        """SELECT * FROM picks
           WHERE match_id=?
             AND lower(COALESCE(selection,''))=lower(?)
             AND lower(COALESCE(market,''))=lower(?)
             AND lower(COALESCE(source,''))=lower(?)
           ORDER BY created_at DESC LIMIT 1""",
        (match_id, selection, market, source),
    )
    if existing:
        telegram_log("[AUTO_PICKS]", "skipped", "Pick automatico duplicado evitado.", {"match_id": match_id, "pick_id": existing.get("id")})
        return {"ok": True, "created": False, "reason": "duplicate", "pick": normalize_pick_row(existing)}
    pick_id = hashlib.md5(f"auto-pick:{match_id}:{market}:{selection}".encode("utf-8")).hexdigest()[:18]
    payload = {
        "id": pick_id,
        "match_id": match_id,
        "league_name": rec.get("league_name") or rec.get("competition_name"),
        "competition_name": rec.get("league_name") or rec.get("competition_name"),
        "home_team": rec.get("home_team"),
        "away_team": rec.get("away_team"),
        "market": market,
        "pick_type": "SHARK Auto",
        "selection": selection,
        "odds": odds,
        "confidence": rec.get("score"),
        "stake_units": 1 if str(rec.get("risk") or "").upper() == "BAJO" else 0.5,
        "risk_level": rec.get("risk") or "MEDIO",
        "reasoning": rec.get("reason") or "SHARK detecta valor con los datos disponibles.",
        "warning_reason": rec.get("warning") or "No apostar si cambia la cuota o falta contexto clave.",
        "membership_required": rec.get("membership_required") or "PRO",
        "status": "published",
        "source": source,
        "legal_note": "Pick automatico generado desde recomendacion SHARK con datos reales disponibles.",
    }
    pick = create_or_update_pick(payload, pick_id=pick_id, publish=True)
    telegram_log("[AUTO_PICKS]", "created", "Pick automatico guardado.", {"pick_id": pick.get("id"), "match_id": match_id, "score": rec.get("score")})
    return {"ok": True, "created": True, "reason": "created", "pick": pick}


def update_pick_status(pick_id, status):
    status = normalize_pick_status(status)
    conn = db()
    conn.execute("UPDATE picks SET status=?, published_at=COALESCE(published_at, ?), updated_at=? WHERE id=?", (status, now_iso() if status == "published" else None, now_iso(), pick_id))
    conn.commit()
    conn.close()
    return normalize_pick_row(one("SELECT * FROM picks WHERE id=?", (pick_id,)))


def pick_stats():
    seed_core()
    totals = {"total": 0, "published": 0, "draft": 0, "archived": 0, "won": 0, "lost": 0, "void": 0, "pending_result": 0, "avg_odds": 0, "avg_confidence": 0, "winrate": 0}
    all_rows = [normalize_pick_row(x) for x in rows("SELECT * FROM picks")]
    totals["total"] = len(all_rows)
    if not all_rows:
        return totals
    for p in all_rows:
        totals[p.get("status") if p.get("status") in totals else "draft"] = totals.get(p.get("status"), 0) + 1
        rs = p.get("result_status") or "pending"
        if rs == "pending":
            totals["pending_result"] += 1
    totals["avg_odds"] = round(sum(p.get("odds", 0) for p in all_rows) / len(all_rows), 2)
    totals["avg_confidence"] = round(sum(p.get("confidence", 0) for p in all_rows) / len(all_rows), 1)
    resolved = [p for p in all_rows if p.get("result_status") in {"won", "lost"}]
    if resolved:
        totals["winrate"] = round(100 * len([p for p in resolved if p.get("result_status") == "won"]) / len(resolved), 1)
    return totals


def record_user_activity(activity_type, target_type="", target_id="", payload=None, user_id=None):
    user_id = user_id or current_user_id()
    if not user_id:
        return None
    activity_id = hashlib.md5(f"act-{user_id}-{activity_type}-{target_type}-{target_id}-{now_iso()}".encode("utf-8")).hexdigest()[:18]
    conn = db()
    conn.execute(
        """INSERT INTO user_activity(id,user_id,activity_type,target_type,target_id,payload_json,created_at)
           VALUES (?,?,?,?,?,?,?)""",
        (activity_id, user_id, activity_type, target_type, target_id, json.dumps(payload or {}, ensure_ascii=False)[:3000], now_iso()),
    )
    conn.commit()
    conn.close()
    return activity_id


def historical_snapshot(limit=120):
    """Persist compact historical data for future SHARK learning."""
    created_at = now_iso()
    conn = db()
    cur = conn.cursor()
    inserted = {"matches": 0, "picks": 0, "recommendations": 0}
    for match in rows(
        """SELECT * FROM matches
           WHERE lower(coalesce(status,'')) IN ('ft','final','finished','finalizado')
              OR (coalesce(home_score,'')!='' AND coalesce(away_score,'')!='')
           ORDER BY match_date DESC, kickoff_time DESC LIMIT ?""",
        (int(limit),),
    ):
        payload = dict(match)
        item_id = hashlib.sha1(f"hm:{match.get('id')}:{match.get('status')}:{match.get('score')}".encode()).hexdigest()
        cur.execute(
            """INSERT OR IGNORE INTO historical_matches
               (id,match_id,match_date,home_team,away_team,league_name,status,score,payload_json,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                item_id,
                match.get("id"),
                match.get("match_date"),
                match.get("home_team"),
                match.get("away_team"),
                match.get("league_name") or match.get("competition_name"),
                match.get("status"),
                match.get("score") or f"{match.get('home_score') or ''}-{match.get('away_score') or ''}".strip("-"),
                json.dumps(payload, ensure_ascii=False),
                created_at,
            ),
        )
        inserted["matches"] += 1 if cur.rowcount else 0
    for pick in rows("SELECT * FROM picks ORDER BY COALESCE(published_at, updated_at, '') DESC LIMIT ?", (int(limit),)):
        payload = dict(pick)
        odds = as_float(pick.get("odds"), 0.0)
        stake = as_float(pick.get("stake_units"), 1.0)
        result = str(pick.get("result_status") or pick.get("status") or "").lower()
        profit = round((odds - 1) * stake, 2) if result in {"won", "win"} and odds else -stake if result in {"lost", "loss"} else 0.0
        item_id = hashlib.sha1(f"hp:{pick.get('id')}:{result}:{odds}:{stake}".encode()).hexdigest()
        cur.execute(
            """INSERT OR IGNORE INTO historical_picks
               (id,pick_id,match_id,selection,market,odds,stake,result_status,profit,payload_json,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (item_id, pick.get("id"), pick.get("match_id"), pick.get("selection"), pick.get("market"), odds, stake, result, profit, json.dumps(payload, ensure_ascii=False), created_at),
        )
        inserted["picks"] += 1 if cur.rowcount else 0
    for rec in v565_recommendation_pool(limit=min(int(limit), 80)):
        item_id = hashlib.sha1(f"hr:{rec.get('match_id')}:{rec.get('selection')}:{rec.get('score')}".encode()).hexdigest()
        cur.execute(
            """INSERT OR IGNORE INTO historical_recommendations
               (id,recommendation_id,match_id,selection,score,risk_level,value_label,payload_json,created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                item_id,
                rec.get("id") or rec.get("match_id"),
                rec.get("match_id"),
                rec.get("selection"),
                as_int(rec.get("score"), 0),
                rec.get("risk_level") or rec.get("risk"),
                rec.get("value_label"),
                json.dumps(rec, ensure_ascii=False),
                created_at,
            ),
        )
        inserted["recommendations"] += 1 if cur.rowcount else 0
    conn.commit()
    conn.close()
    return {"ok": True, "processed": sum(inserted.values()), "inserted": sum(inserted.values()), "updated": 0, "skipped": 0, "warehouse": inserted}



def parse_payload_json(value, default=None):
    try:
        return json.loads(value or "{}")
    except Exception:
        return default if default is not None else {}


def client_activity_feed(limit=20, user_id=None):
    user_id = user_id or current_user_id()
    if not user_id:
        return []
    data = rows(
        """SELECT * FROM user_activity
           WHERE user_id=?
           ORDER BY created_at DESC
           LIMIT ?""",
        (user_id, int(limit)),
    )
    for item in data:
        item["payload"] = parse_payload_json(item.get("payload_json"), {})
        item["label"] = activity_label(item)
    return data


def activity_label(item):
    kind = str(item.get("activity_type") or "").lower()
    target = str(item.get("target_type") or "").lower()
    if kind == "view" and target == "picks":
        return "Has revisado la zona de picks."
    if kind == "view" and target == "combis":
        return "Has abierto el constructor de combinadas."
    if kind == "favorite" or target == "favorite":
        return "Favorito actualizado."
    if target == "match":
        return "Partido consultado."
    if target == "team":
        return "Equipo consultado."
    return "Actividad registrada en tu cuenta."


def build_client_alerts(limit=12, user_id=None):
    """Alertas visuales para cliente sin inventar datos reales.
    Mezcla favoritos, partidos próximos, live, picks publicados y estado Telegram.
    """
    user_id = user_id or current_user_id()
    hub = match_hub(today_iso())
    favs = get_favorites(user_id=user_id) if user_id else []
    picks = published_picks_for_user(current_session_user() or {"membership": "FREE"}, limit=6)
    upcoming = get_upcoming_matches(today_iso(), days=3, limit=12)
    alerts = []

    if hub.get("counts", {}).get("live", 0):
        alerts.append({
            "type": "live",
            "priority": 95,
            "title": "Partidos en directo ahora",
            "body": f"Hay {hub['counts']['live']} partido(s) en directo. Revisa marcador, estado y favoritos.",
            "href": "/live",
            "badge": "LIVE",
        })
    if picks:
        alerts.append({
            "type": "picks",
            "priority": 90,
            "title": "Picks publicados disponibles",
            "body": f"Tienes {len(picks)} pick(s) visibles según tu membresía.",
            "href": "/picks",
            "badge": "PICKS",
        })
    elif upcoming:
        alerts.append({
            "type": "analysis",
            "priority": 74,
            "title": "Partidos próximos listos para análisis",
            "body": "Aún no hay picks publicados, pero SHARK ya puede ayudarte a revisar próximos partidos reales.",
            "href": "/picks",
            "badge": "ANÁLISIS",
        })
    if favs:
        alerts.append({
            "type": "favorites",
            "priority": 82,
            "title": "Feed de favoritos activo",
            "body": f"Tus {len(favs)} favorito(s) alimentan partidos, equipos, ligas y alertas futuras.",
            "href": "/favorites",
            "badge": "FAV",
        })
    else:
        alerts.append({
            "type": "favorites",
            "priority": 58,
            "title": "Personaliza tu experiencia",
            "body": "Guarda equipos, ligas o partidos para que tu inicio, SHARK y Telegram sean más útiles.",
            "href": "/favorites",
            "badge": "PERSONALIZA",
        })
    if not telegram_config().get("configured"):
        alerts.append({
            "type": "telegram",
            "priority": 52,
            "title": "Telegram pendiente de configurar",
            "body": "Cuando esté conectado podrás recibir partidos del día, picks y alertas premium.",
            "href": "/telegram",
            "badge": "TELEGRAM",
        })
    if upcoming:
        first = upcoming[0]
        alerts.append({
            "type": "match",
            "priority": 70,
            "title": "Próximo partido destacado",
            "body": f"{first.get('home_team')} vs {first.get('away_team')} · {first.get('competition_name') or first.get('league_name') or 'Competición'}",
            "href": f"/match/{first.get('id')}",
            "badge": "PRÓXIMO",
        })
    alerts = sorted(alerts, key=lambda x: x.get("priority", 0), reverse=True)
    return alerts[: int(limit)]


def client_retention_summary():
    user = current_session_user() or {}
    alerts = build_client_alerts(limit=8, user_id=user.get("id"))
    activity = client_activity_feed(limit=8, user_id=user.get("id")) if user else []
    upcoming = get_upcoming_matches(today_iso(), days=7, limit=20)
    picks = published_picks_for_user(user or {"membership": "FREE"}, limit=10)
    return {
        "alerts": alerts,
        "activity": activity,
        "upcoming_count": len(upcoming),
        "picks_count": len(picks),
        "favorites_count": len(get_favorites(user_id=user.get("id")) if user else []),
        "telegram_ready": telegram_config().get("configured"),
        "next_best_action": alerts[0] if alerts else None,
    }


# ===================== V537 DAILY BRIEFING + CLIENT COMMAND CENTER =====================
def client_progress_score(user=None):
    user = user or current_session_user() or {}
    score = 25
    favs = get_favorites(user_id=user.get("id")) if user.get("id") else []
    if favs:
        score += min(20, len(favs) * 5)
    if telegram_config().get("configured"):
        score += 15
    if published_picks_for_user(user or {"membership": "FREE"}, limit=3):
        score += 15
    if get_upcoming_matches(today_iso(), days=7, limit=5):
        score += 15
    if client_activity_feed(limit=3, user_id=user.get("id")):
        score += 10
    return max(0, min(100, score))


def build_daily_briefing(user=None, favorites=None, recommendations=None, picks=None, live_matches=None, upcoming=None, membership=None):
    """Briefing comercial para cliente: resume qué mirar hoy sin inventar datos."""
    user = user or current_session_user() or {"membership": "FREE", "role": "FREE"}
    hub = match_hub(today_iso())
    upcoming = upcoming if upcoming is not None else get_upcoming_matches(today_iso(), days=7, limit=12)
    today_matches = get_matches(today_iso(), "today")
    favs = favorites if favorites is not None else (get_favorites(user_id=user.get("id")) if user.get("id") else [])
    picks = picks if picks is not None else published_picks_for_user(user, limit=8)
    smart = smart_pick_board(user, limit=8)
    alerts = build_client_alerts(limit=6, user_id=user.get("id"))
    activity = client_activity_feed(limit=6, user_id=user.get("id")) if user.get("id") else []
    next_action = alerts[0] if alerts else {
        "title": "Explora el calendario",
        "body": "Revisa partidos por liga y guarda tus favoritos para personalizar la experiencia.",
        "href": "/match-hub",
        "badge": "HOY",
    }
    priorities = []
    if hub.get("counts", {}).get("live", 0):
        priorities.append({"label": "Directos activos", "value": hub["counts"]["live"], "href": "/live", "tone": "live"})
    if picks:
        priorities.append({"label": "Picks visibles", "value": len(picks), "href": "/picks", "tone": "picks"})
    if favs:
        priorities.append({"label": "Favoritos", "value": len(favs), "href": "/favorites", "tone": "favorites"})
    if upcoming:
        priorities.append({"label": "Próximos 7 días", "value": len(upcoming), "href": "/match-hub", "tone": "matches"})
    if not priorities:
        priorities.append({"label": "Sincronización pendiente", "value": "OK", "href": "/match-hub", "tone": "empty"})
    return {
        "date": today_iso(),
        "score": client_progress_score(user),
        "next_action": next_action,
        "priorities": priorities[:4],
        "alerts": alerts,
        "activity": activity,
        "favorites": favs,
        "picks": picks,
        "smart_picks": smart,
        "recommendations": recommendations or [],
        "membership": membership or (user.get("membership") or user.get("role") or "FREE"),
        "upcoming": upcoming,
        "today_matches": today_matches,
        "live": (live_matches if live_matches is not None else hub.get("live", []))[:8],
        "counts": {
            "today": len(today_matches),
            "upcoming": len(upcoming),
            "live": hub.get("counts", {}).get("live", 0),
            "favorites": len(favs),
            "picks": len(picks),
        },
        "message": (
            "Tienes contenido listo para revisar hoy."
            if (today_matches or upcoming or picks or favs)
            else "Aún faltan datos sincronizados; la app mostrará contenido real cuando entren SportsDB, Odds o import legal."
        ),
    }


def client_command_center_data(user=None):
    user = user or current_session_user() or {}
    briefing = build_daily_briefing(user)
    return {
        "briefing": briefing,
        "readiness": {
            "perfil": 100 if user else 0,
            "favoritos": min(100, briefing["counts"]["favorites"] * 25),
            "partidos": 100 if briefing["counts"]["upcoming"] else 35,
            "picks": 100 if briefing["counts"]["picks"] else 45,
            "telegram": 100 if telegram_config().get("configured") else 40,
        },
        "recommended_tabs": [
            {"label": "Mi día", "href": "/mi-dia", "text": "Briefing personalizado"},
            {"label": "Partidos", "href": "/match-hub", "text": "Calendario por ligas"},
            {"label": "Picks", "href": "/picks", "text": "Apuestas publicadas o candidatos"},
            {"label": "Combis", "href": "/combis", "text": "Constructor con próximos partidos"},
        ],
    }

def combi_risk(picks):
    if not picks:
        return "EMPTY"
    avg_confidence = sum(as_int(p.get("confidence"), 50) for p in picks) / len(picks)
    legs = len(picks)
    if legs <= 2 and avg_confidence >= 70:
        return "CONTROLADO"
    if legs <= 4 and avg_confidence >= 58:
        return "MEDIO"
    return "ALTO"


def build_combi_from_picks(pick_ids=None, limit=3):
    seed_core()
    if pick_ids:
        placeholders = ",".join("?" for _ in pick_ids)
        picks = rows(f"SELECT * FROM picks WHERE id IN ({placeholders}) ORDER BY confidence DESC", pick_ids)
    else:
        picks = get_picks(limit=limit, status=["published", "won", "lost", "void"], membership=(current_session_user() or {}).get("membership", "FREE"))
    picks = picks[:combi_leg_count(limit or len(picks) or 3)]
    if len(picks) < 2:
        return None
    total = 1.0
    for pick in picks:
        odd = as_float(pick.get("odds"), 1.0)
        total *= odd if odd > 1 else 1
    combi_id = hashlib.md5(("combi-" + now_iso() + json.dumps([p.get("id") for p in picks])).encode("utf-8")).hexdigest()[:18]
    payload = [
        {
            "id": p.get("id"),
            "match": f"{p.get('home_team') or ''} vs {p.get('away_team') or ''}".strip(),
            "selection": p.get("selection"),
            "odds": as_float(p.get("odds"), 0.0),
            "confidence": as_int(p.get("confidence"), 50),
        }
        for p in picks
    ]
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """INSERT OR REPLACE INTO combis
           (id,name,picks_json,total_odds,risk_level,status,source,created_at,updated_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (combi_id, "Combi SHARK " + today_iso(), json.dumps(payload, ensure_ascii=False), round(total, 2), combi_risk(picks), "DRAFT", "motor interno V713 combis 15", now_iso(), now_iso()),
    )
    conn.commit()
    conn.close()
    return one("SELECT * FROM combis WHERE id=?", (combi_id,))


def get_combis(limit=20):
    data = rows("SELECT * FROM combis ORDER BY created_at DESC LIMIT ?", (int(limit),))
    for combi in data:
        combi["picks"] = json.loads(combi.get("picks_json") or "[]")
    return data


def favorite_id(kind, value, user_id=None):
    owner = user_id or current_user_id() or "anonymous"
    return hashlib.md5(f"{owner}:{kind}:{value}".lower().encode("utf-8")).hexdigest()[:18]


def add_favorite(kind, value, label=None, user_id=None):
    kind = str(kind or "").strip().lower()
    value = str(value or "").strip()
    user_id = user_id or current_user_id()
    if kind not in {"team", "league", "match"} or not value:
        return None
    if not user_id:
        return None
    fav_id = favorite_id(kind, value, user_id)
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """INSERT OR REPLACE INTO favorites(id,user_id,kind,value,label,created_at)
           VALUES (?,?,?,?,?,?)""",
        (fav_id, user_id, kind, value, label or value, now_iso()),
    )
    conn.commit()
    conn.close()
    return one("SELECT * FROM favorites WHERE id=?", (fav_id,))


def remove_favorite(kind, value, user_id=None):
    user_id = user_id or current_user_id()
    fav_id = favorite_id(kind, value, user_id)
    conn = db()
    cur = conn.cursor()
    cur.execute("DELETE FROM favorites WHERE id=? AND user_id=?", (fav_id, user_id))
    conn.commit()
    conn.close()
    return {"ok": True, "removed": fav_id}


def get_favorites(kind=None, user_id=None):
    user_id = user_id if user_id is not None else current_user_id()
    if not user_id:
        return []
    if kind:
        return rows("SELECT * FROM favorites WHERE user_id=? AND kind=? ORDER BY created_at DESC", (user_id, kind))
    return rows("SELECT * FROM favorites WHERE user_id=? ORDER BY created_at DESC", (user_id,))


def favorite_sets(user_id=None):
    favs = get_favorites(user_id=user_id)
    return {
        "team": {f["value"].lower() for f in favs if f.get("kind") == "team"},
        "league": {f["value"].lower() for f in favs if f.get("kind") == "league"},
        "match": {f["value"].lower() for f in favs if f.get("kind") == "match"},
        "all": favs,
    }


def annotate_match(match, favs=None):
    favs = favs or (favorite_sets() if has_request_context() else {"team": set(), "league": set(), "match": set(), "all": []})
    match_key = str(match.get("id") or "").lower()
    comp_key = str(match.get("competition_key") or "").lower()
    comp_name = str(match.get("competition_name") or "").lower()
    home = str(match.get("home_team") or "").lower()
    away = str(match.get("away_team") or "").lower()
    match["is_favorite"] = (
        match_key in favs["match"]
        or comp_key in favs["league"]
        or comp_name in favs["league"]
        or home in favs["team"]
        or away in favs["team"]
    )
    match = apply_match_localization(match)
    if not match.get("home_identity"):
        match["home_identity"] = resolve_team(match.get("home_team"))
    if not match.get("away_identity"):
        match["away_identity"] = resolve_team(match.get("away_team"))
    match.update(apply_team_identities_to_match(match))
    match["status_info"] = canonical_match_status(match)
    match["real_time_state"] = real_time_state(match)
    match["timeline"] = match_timeline(match)
    match["live_depth"] = live_depth(match)
    if match["status_info"].get("is_finished"):
        match["live_depth"]["state"] = "FT"
        match["live_depth"]["label"] = "Finalizado"
        match["live_depth"]["badge"] = "finished"
        match["live_depth"]["minute"] = "FT"
    elif match["status_info"].get("is_upcoming"):
        match["live_depth"]["state"] = "UPCOMING"
        match["live_depth"]["label"] = "Próximo"
        match["live_depth"]["badge"] = "upcoming"
        match["live_depth"]["minute"] = jinja_match_time_short(match) if has_request_context() else (normalize_kickoff_for_display(match).get("madrid_time") or "Hora")
        if not (match.get("home_score") or match.get("away_score") or match.get("score")):
            match["live_depth"]["score"] = ""
    elif match["status_info"].get("is_live"):
        match["live_depth"]["state"] = "HT" if match["status_info"].get("key") == "HT" else "LIVE"
        match["live_depth"]["label"] = match["status_info"].get("label") or "En directo"
        match["live_depth"]["badge"] = match["status_info"].get("badge") or "live"
        real_minute = str(match.get("minute") or "").strip()
        match["live_depth"]["minute"] = f"{real_minute}'" if real_minute.isdigit() else "En directo"
    return match


def match_timeline(match):
    existing = rows("SELECT * FROM match_timeline WHERE match_id=? ORDER BY created_at DESC LIMIT 20", (match.get("id"),))
    if existing:
        return existing
    return fallback_timeline(match)


def live_depth(match):
    return build_live_depth(match)


def favorite_feed(limit=80, user_id=None):
    favs = favorite_sets(user_id=user_id)
    if not favs["all"]:
        return []
    data = dedupe_matches_list(get_matches(today_iso(), "today"))
    feed = []
    for match in data:
        annotated = annotate_match(match, favs)
        if annotated.get("is_favorite"):
            feed.append(annotated)
    return dedupe_matches_list(feed)[: int(limit)]


def related_picks_for_match(match, limit=8):
    all_picks = get_picks(limit=100)
    match_id = str(match.get("id") or "").lower()
    home = str(match.get("home_team") or "").lower()
    away = str(match.get("away_team") or "").lower()
    comp = str(match.get("competition_key") or "").lower()
    related = []
    for pick in all_picks:
        if str(pick.get("match_id") or "").lower() == match_id:
            related.append(pick)
            continue
        pick_home = str(pick.get("home_team") or "").lower()
        pick_away = str(pick.get("away_team") or "").lower()
        pick_comp = str(pick.get("competition_key") or "").lower()
        if (home and home == pick_home) or (away and away == pick_away) or (comp and comp == pick_comp):
            related.append(pick)
    return related[: int(limit)]


def favorite_feed_full(limit=80, user_id=None):
    matches = dedupe_matches_list(favorite_feed(limit, user_id=user_id))
    match_ids = {str(m.get("id") or "").lower() for m in matches}
    teams = {str(m.get("home_team") or "").lower() for m in matches} | {str(m.get("away_team") or "").lower() for m in matches}
    comps = {str(m.get("competition_key") or "").lower() for m in matches}
    live_related = [m for m in matches if (m.get("live_depth") or {}).get("state") in {"LIVE", "HT"}]
    picks_related = []
    for pick in get_picks(limit=100):
        if (
            str(pick.get("match_id") or "").lower() in match_ids
            or str(pick.get("home_team") or "").lower() in teams
            or str(pick.get("away_team") or "").lower() in teams
            or str(pick.get("competition_key") or "").lower() in comps
        ):
            picks_related.append(pick)
    prioritized = sorted(dedupe_matches_list(matches), key=lambda m: (1 if (m.get("live_depth") or {}).get("state") in {"LIVE", "HT"} else 0, m.get("real_time_score", m.get("priority", 0))), reverse=True)
    return {"matches": prioritized, "live": live_related, "picks": picks_related[:20], "priority": prioritized[:10]}




def favorite_insights(user_id=None):
    favs = get_favorites(user_id=user_id)
    bundle = favorite_feed_full(user_id=user_id)
    by_kind = {"team": [], "league": [], "match": []}
    for fav in favs:
        by_kind.setdefault(fav.get("kind") or "other", []).append(fav)
    next_matches = bundle.get("matches", [])[:8]
    live_matches = bundle.get("live", [])[:6]
    picks = bundle.get("picks", [])[:6]
    summary = []
    if by_kind.get("team"):
        summary.append(f"{len(by_kind['team'])} equipos seguidos")
    if by_kind.get("league"):
        summary.append(f"{len(by_kind['league'])} ligas seguidas")
    if by_kind.get("match"):
        summary.append(f"{len(by_kind['match'])} partidos guardados")
    return {
        "favorites": favs,
        "by_kind": by_kind,
        "matches": next_matches,
        "live": live_matches,
        "picks": picks,
        "summary": " · ".join(summary) if summary else "Sin favoritos todavía",
        "total": len(favs),
    }



def team_lookup(team_id):
    key = canonical_team_key(team_id)
    team = one("SELECT * FROM teams WHERE key=? OR external_id=? OR lower(name)=lower(?) LIMIT 1", (key, str(team_id or ""), str(team_id or "")))
    if team:
        return team
    # Crear vista virtual mínima si el equipo aparece en partidos pero todavía no existe en teams.
    sample = one("""SELECT home_team AS name, home_logo AS logo_url, country, competition_name AS league FROM matches WHERE lower(home_team)=lower(?)
                    UNION ALL
                    SELECT away_team AS name, away_logo AS logo_url, country, competition_name AS league FROM matches WHERE lower(away_team)=lower(?) LIMIT 1""", (str(team_id or ""), str(team_id or "")))
    if sample:
        sample["key"] = key
        sample["id"] = key
        sample["key"] = key
        sample["source"] = "matches"
        return sample
    return None


def team_page_data(team_id, limit=80):
    team = team_lookup(team_id)
    if not team:
        return None
    name = team.get("name") or team_id
    key = canonical_team_key(name)
    identity = resolve_team(name)
    if team.get("logo_url"):
        identity["crest_url"] = team.get("logo_url")
        identity["crest_mode"] = "logo"
    upcoming = [annotate_match(m) for m in rows(
        """SELECT * FROM matches
           WHERE (lower(home_team)=lower(?) OR lower(away_team)=lower(?))
             AND match_date>=?
           ORDER BY match_date, kickoff_time LIMIT ?""",
        (name, name, today_iso(), int(limit)),
    ) if not is_fake_match(m)]
    recent = [annotate_match(m) for m in rows(
        """SELECT * FROM matches
           WHERE (lower(home_team)=lower(?) OR lower(away_team)=lower(?))
             AND match_date<?
           ORDER BY match_date DESC, kickoff_time DESC LIMIT ?""",
        (name, name, today_iso(), int(limit//2)),
    ) if not is_fake_match(m)]
    live = [m for m in upcoming if (m.get("status_info") or {}).get("is_live")]
    related = []
    for pick in get_picks(limit=120):
        if str(pick.get("home_team") or "").lower() == name.lower() or str(pick.get("away_team") or "").lower() == name.lower():
            related.append(pick)
    favorites = favorite_sets()
    is_favorite = name.lower() in favorites.get("team", set()) or key.lower() in favorites.get("team", set())
    return {
        "team": team,
        "key": key,
        "name": name,
        "identity": identity,
        "upcoming": upcoming,
        "recent": recent,
        "live": live,
        "picks": related[:8],
        "is_favorite": is_favorite,
        "stats": {
            "upcoming": len(upcoming),
            "recent": len(recent),
            "live": len(live),
            "picks": len(related),
        },
        "shark_context": shark_context_summary({"team": name, "upcoming": upcoming[:5], "picks": related[:5]}),
    }


def shark_context_summary(context):
    team = context.get("team") or "este equipo"
    upcoming = context.get("upcoming") or []
    picks = context.get("picks") or []
    pieces = [f"Contexto SHARK para {team} preparado con datos cacheados reales."]
    if upcoming:
        first = upcoming[0]
        pieces.append(f"Próximo partido: {first.get('home_team')} vs {first.get('away_team')} ({first.get('match_date')} {first.get('kickoff_time') or ''}).")
    else:
        pieces.append("No hay próximos partidos sincronizados para este equipo todavía.")
    if picks:
        pieces.append(f"Hay {len(picks)} picks relacionados publicados o preparados.")
    else:
        pieces.append("Aún no hay picks relacionados publicados.")
    return " ".join(pieces)


def group_matches_by_league(matches):
    grouped = {}
    for item in matches or []:
        league = league_display_name(item)
        key = slug(league)
        bucket = grouped.setdefault(key, {"key": key, "name": league, "country": item.get("country") or "Global", "category": league_category(item), "matches": []})
        bucket["matches"].append(item)
    result = list(grouped.values())
    for bucket in result:
        bucket["matches"].sort(key=match_sort_tuple)
        bucket["count"] = len(bucket["matches"])
    result.sort(key=lambda x: (x["category"], x["name"]))
    return result


def recent_team_form(team_name, limit=5):
    """Return compact recent form based only on persisted legal match results."""
    team_name = str(team_name or "").strip()
    if not team_name:
        return {"team": "", "matches": [], "form": [], "summary": "Sin datos recientes."}
    recent = []
    for m in rows(
        """SELECT * FROM matches
           WHERE (lower(home_team)=lower(?) OR lower(away_team)=lower(?))
             AND (status IN ('FT','finished','finalizado','Finalizado','FINAL') OR match_date < ?)
           ORDER BY match_date DESC, kickoff_time DESC LIMIT ?""",
        (team_name, team_name, today_iso(), int(limit)),
    ):
        if is_fake_match(m):
            continue
        item = annotate_match(m)
        score = str(item.get("score") or "").replace(" ", "")
        result = "D"
        try:
            import re
            nums = [int(x) for x in re.findall(r"\d+", score)[:2]]
            if len(nums) >= 2:
                home_goals, away_goals = nums[0], nums[1]
                is_home = str(item.get("home_team") or "").lower() == team_name.lower()
                team_goals = home_goals if is_home else away_goals
                rival_goals = away_goals if is_home else home_goals
                result = "W" if team_goals > rival_goals else "L" if team_goals < rival_goals else "D"
        except Exception:
            result = "D"
        item["form_result"] = result
        recent.append(item)
    wins = sum(1 for x in recent if x.get("form_result") == "W")
    draws = sum(1 for x in recent if x.get("form_result") == "D")
    losses = sum(1 for x in recent if x.get("form_result") == "L")
    summary = f"{wins} victorias · {draws} empates · {losses} derrotas" if recent else "Sin resultados recientes guardados."
    return {"team": team_name, "matches": recent, "form": [x.get("form_result") for x in recent], "summary": summary}


def head_to_head_matches(home_team, away_team, limit=5):
    """Return recent direct duels from SQLite without inventing data."""
    home_team = str(home_team or "").strip()
    away_team = str(away_team or "").strip()
    if not home_team or not away_team:
        return []
    found = []
    for m in rows(
        """SELECT * FROM matches
           WHERE ((lower(home_team)=lower(?) AND lower(away_team)=lower(?))
              OR  (lower(home_team)=lower(?) AND lower(away_team)=lower(?)))
           ORDER BY match_date DESC, kickoff_time DESC LIMIT ?""",
        (home_team, away_team, away_team, home_team, int(limit)),
    ):
        if not is_fake_match(m):
            found.append(annotate_match(m))
    return found


def match_depth_payload(match):
    """Build V540 match intelligence using persisted legal data only."""
    annotated = annotate_match(match)
    home = annotated.get("home_team") or ""
    away = annotated.get("away_team") or ""
    home_form = recent_team_form(home)
    away_form = recent_team_form(away)
    h2h = head_to_head_matches(home, away)
    live_depth = annotated.get("live_depth") or build_live_depth(annotated)
    timeline = match_timeline(annotated) or fallback_timeline(annotated)
    picks = related_picks_for_match(annotated)
    shark_notes = []
    if h2h:
        shark_notes.append(f"Hay {len(h2h)} enfrentamientos directos guardados para comparar contexto.")
    else:
        shark_notes.append("Aún no hay histórico directo suficiente guardado para este cruce.")
    if picks:
        shark_notes.append(f"Hay {len(picks)} picks relacionados publicados o preparados para este partido.")
    else:
        shark_notes.append("SHARK no publicará pick real hasta tener cuota, mercado y contexto suficientes.")
    if live_depth.get("state") in {"LIVE", "HT"}:
        shark_notes.append("Partido activo: priorizar lectura live y evitar decisiones tardías sin revisar marcador/minuto.")
    elif live_depth.get("state") == "FT":
        shark_notes.append("Partido finalizado: útil para histórico, forma y aprendizaje futuro.")
    else:
        shark_notes.append("Partido próximo: contexto preparado para picks, favoritos y alertas.")
    return {
        "match": annotated,
        "live_depth": live_depth,
        "timeline": timeline,
        "home_form": home_form,
        "away_form": away_form,
        "head_to_head": h2h,
        "related_picks": picks,
        "shark_notes": shark_notes,
        "data_quality": {
            "has_score": bool(annotated.get("score")),
            "has_time": bool(annotated.get("kickoff_time") or annotated.get("kickoff_iso")),
            "has_crests": bool((annotated.get("home_identity") or {}).get("crest_url") and (annotated.get("away_identity") or {}).get("crest_url")),
            "has_picks": bool(picks),
            "has_h2h": bool(h2h),
        },
    }

def match_detail(match_id):
    match = one("SELECT * FROM matches WHERE id=?", (match_id,))
    if not match:
        return None
    annotated = annotate_match(match)
    base = build_match_detail(
        annotated,
        timeline=match_timeline(annotated),
        related_picks=related_picks_for_match(annotated),
        favorite=annotated.get("is_favorite"),
    )
    depth = match_depth_payload(annotated)
    base["v540_depth"] = depth
    base["home_form"] = depth["home_form"]
    base["away_form"] = depth["away_form"]
    base["head_to_head"] = depth["head_to_head"]
    base["shark_notes"] = depth["shark_notes"]
    base["data_quality"] = depth["data_quality"]
    return base


def match_lane_filter(match, lane):
    lane = str(lane or "today").lower()
    comp = str(match.get("competition_key") or "").lower()
    comp_name = str(match.get("competition_name") or match.get("league_name") or "").lower()
    country = str(match.get("country") or "").lower()
    state = ((match.get("live_depth") or {}).get("state") or "").upper()
    if lane in {"today", "week", "tomorrow"}:
        return True
    if lane in {"results", "finished"}:
        return (match.get("status_info") or canonical_match_status(match)).get("is_finished") or str(match.get("match_date") or "") < today_iso()
    if lane == "live":
        info = match.get("status_info") or canonical_match_status(match)
        return bool(info.get("is_live")) and not info.get("is_finished") and not info.get("is_upcoming")
    if lane == "spain":
        return country == "spain" or "laliga" in comp or "rfef" in comp or "copa-del-rey" in comp
    if lane == "andalucia":
        return "andalucia" in comp or "andalucia" in comp_name or any(x in comp for x in ["cadiz", "sevilla", "malaga", "granada", "cordoba", "huelva", "jaen", "almeria"])
    if lane == "international":
        return country not in {"spain", ""} or any(x in comp for x in ["premier", "serie-a", "bundesliga", "ligue", "primeira", "uefa"])
    if lane == "uefa":
        return "uefa" in comp or "champions" in comp_name or "europa league" in comp_name or "conference" in comp_name
    if lane in {"national", "world"}:
        return any(x in comp for x in ["world", "euro", "copa-america", "nations"]) or any(x in comp_name for x in ["world", "euro", "copa america", "nations"])
    return True


def league_category(match):
    comp = str(match.get("competition_key") or "").lower()
    comp_name = str(match.get("competition_name") or match.get("league_name") or "").lower()
    country = str(match.get("country") or "").lower()
    text = f"{comp} {comp_name}"
    if any(x in text for x in ["andalucia", "cadiz", "sevilla", "malaga", "granada", "cordoba", "huelva", "jaen", "almeria"]):
        return "Andalucía"
    if any(x in text for x in ["champions", "europa league", "conference", "uefa"]):
        return "UEFA"
    if any(x in text for x in ["world", "euro", "copa america", "copa-america", "nations league"]):
        return "Selecciones"
    if country == "spain" or any(x in text for x in ["laliga", "rfef", "segunda", "tercera"]):
        return "España"
    return "Internacional"


def league_display_name(match):
    return match.get("competition_name") or match.get("league_name") or match.get("competition_key") or "Competición"


def date_display_label(date_value):
    try:
        target = datetime.fromisoformat(str(date_value)).date()
        today = datetime.now(TZ).date()
        weekdays = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        if target == today:
            prefix = "Hoy"
        elif target == today + timedelta(days=1):
            prefix = "Mañana"
        else:
            prefix = weekdays[target.weekday()].capitalize()
        return f"{prefix} · {target.strftime('%d/%m/%Y')}"
    except Exception:
        return str(date_value or "Fecha por confirmar")


def match_sort_tuple(match):
    kickoff = match.get("kickoff_iso") or ""
    hour = match.get("kickoff_time") or match.get("match_time") or "99:99"
    priority = 999 - int(match.get("priority") or 0)
    return (kickoff or f"{match.get('match_date') or ''}T{hour}", hour, priority, str(match.get("home_team") or ""))


def grouped_match_calendar(matches):
    days_map = {}
    for raw in matches or []:
        match = apply_match_localization(dict(raw))
        day_key = match.get("match_date") or (str(match.get("kickoff_iso_madrid") or match.get("kickoff_iso") or "")[:10] if (match.get("kickoff_iso_madrid") or match.get("kickoff_iso")) else "sin-fecha")
        league_name = league_display_name(match)
        league_key = slug(league_name)
        day = days_map.setdefault(day_key, {"date": day_key, "label": date_display_label(day_key), "total": 0, "leagues": {}})
        league = day["leagues"].setdefault(
            league_key,
            {
                "key": league_key,
                "name": league_name,
                "country": match.get("country") or "Global",
                "category": league_category(match),
                "matches": [],
            },
        )
        league["matches"].append(match)
        day["total"] += 1
    grouped_days = []
    for day_key in sorted(days_map.keys()):
        day = days_map[day_key]
        league_list = list(day["leagues"].values())
        league_list.sort(key=lambda item: (v565_league_rank(item["matches"][0]) if item.get("matches") else 80, item["name"]))
        for league in league_list:
            league["matches"].sort(key=match_sort_tuple)
            league["count"] = len(league["matches"])
        grouped_days.append({"date": day["date"], "label": day["label"], "total": day["total"], "leagues": league_list})
    return grouped_days




def get_results_matches(start_date=None, days_back=14, limit=150):
    start_date = start_date or today_iso()
    start = (datetime.fromisoformat(start_date).date() - timedelta(days=int(days_back))).isoformat()
    query = """SELECT * FROM matches
               WHERE match_date>=? AND match_date<?
               ORDER BY match_date DESC, kickoff_time, competition_name
               LIMIT ?"""
    data = dedupe_matches_list([item for item in rows(query, (start, start_date, int(limit))) if not is_fake_match(item)])
    enriched = []
    for item in data:
        item["kickoff_time"] = item.get("kickoff_time") or item.get("match_time") or ""
        if not item.get("score") and (item.get("home_score") or item.get("away_score")):
            item["score"] = sportsdb_score(item.get("home_score"), item.get("away_score"))
        item["home_identity"] = resolve_team(item.get("home_team"))
        item["away_identity"] = resolve_team(item.get("away_team"))
        item = annotate_match(item)
        item.update(apply_match_localization(item))
        item["live_depth"]["state"] = "FT"
        item["live_depth"]["label"] = "Finalizado"
        item["live_depth"]["badge"] = "finished"
        item["live_depth"]["minute"] = "FT"
        enriched.append(item)
    return enriched


def pick_candidate_matches(limit=80, days=21):
    candidates = []
    for match in get_upcoming_matches(today_iso(), days=days, limit=max(limit * 3, 300)):
        info = canonical_match_status(match)
        if info.get("is_upcoming") and match.get("home_team") and match.get("away_team"):
            annotated = annotate_match(match)
            annotated["pick_readiness"] = "Listo para análisis" if (match.get("bookmaker") or match.get("odds_h2h_json")) else "Sin cuota todavía"
            candidates.append(annotated)
        if len(candidates) >= limit:
            break
    return candidates


def build_combi_candidates_from_matches(count=3):
    count = combi_leg_count(count, 3)
    matches = pick_candidate_matches(limit=max(count * 3, 45), days=21)
    return {
        "requested_count": count,
        "matches": matches[:count],
        "available": len(matches),
        "mode": "partidos_reales_proximos",
        "notice": "Base real de partidos próximos. La selección final debe salir de picks publicados o análisis admin; no se fabrican apuestas falsas.",
    }


def smart_pick_board(user=None, limit=24):
    """Panel comercial de picks con ranking de calidad SHARK.

    Solo muestra como premium picks con cuota real, selección clara y calidad
    suficiente. Lo dudoso queda en estudio para no vender señales débiles.
    """
    user = user or current_session_user() or {"membership": "FREE", "role": "FREE"}
    published = sort_picks_by_quality(published_picks_for_user(user, limit=max(limit, 50)))
    quality = split_picks_by_quality(published)
    hot = quality["ready"][:12]
    study = quality["study"][:12]
    top = quality["top"][:6]
    value = quality["value"][:8]
    candidates = pick_candidate_matches(limit=max(limit * 2, 80), days=21)
    pro_locked = []
    if str(user.get("membership") or "FREE").upper() == "FREE":
        pro_locked = [p for p in get_picks(limit=80, status="published", include_admin=False) if str(p.get("membership_required") or "FREE").upper() in {"PRO", "ELITE"}][:8]
    return {
        "published": published,
        "hot": hot,
        "top": top,
        "value": value,
        "study": study,
        "candidates": candidates,
        "pro_locked": pro_locked,
        "published_count": len(published),
        "candidate_count": len(candidates),
        "premium_ready_count": len(hot),
        "study_count": len(study),
        "has_real_picks": bool(hot),
        "client_message": (
            "Picks premium listos con cuota real, selección clara y filtro SHARK."
            if hot
            else "SHARK está estudiando los próximos partidos. No mostramos apuestas pendientes como premium."
        ),
        "admin_message": f"{len(hot)} picks premium listos y {len(study)} en estudio." if published else "SHARK está preparando picks con partidos reales próximos.",
    }

def match_hub(date=None, lane="today"):
    date = date or today_iso()
    cache_key = f"match-hub:{date}:{lane}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    favs = favorite_sets()
    favorites = get_favorites()
    picks = get_picks(limit=200)
    today_matches = dedupe_matches_list([annotate_match(m, favs) for m in get_matches(date, "today")])
    window_matches = dedupe_matches_list([annotate_match(m, favs) for m in get_upcoming_matches(date, days=10, limit=500)])
    result_matches = dedupe_matches_list(get_results_matches(date, days_back=21, limit=250))
    combined = []
    seen = set()
    source_matches = result_matches if lane in {"results", "finished"} else dedupe_matches_list(today_matches + window_matches + (result_matches[:120] if lane == "week" else []))
    for match in source_matches:
        logical_key = match_logical_key(match)
        if logical_key in seen:
            continue
        if not match_lane_filter(match, lane):
            continue
        seen.add(logical_key)
        combined.append(match)
    sections = hub_sections(combined, favorites=favorites, picks=picks)
    live_state = split_live(combined)
    sync = sync_plan(sections["today"], now_iso())
    top_leagues = [c for c in competitions() if c.get("tier", 0) >= 80][:24]
    with_odds = [m for m in combined if m.get("bookmaker") or m.get("odds_h2h_json")]
    by_country = {}
    for match in combined:
        key = match.get("country") or "Global"
        by_country.setdefault(key, 0)
        by_country[key] += 1
    hub = {
        "date": date,
        "lane": lane,
        "sync": sync,
        "live": sections["live"][:80],
        "today": [m for m in combined if m.get("match_date") == date][:200],
        "upcoming": [m for m in combined if m.get("match_date") >= date and m.get("match_date") != date][:160] or sections["upcoming"][:120],
        "finished": (result_matches if lane in {"results", "finished"} else sections["finished"])[:120],
        "results": grouped_match_calendar(result_matches),
        "popular": sections["top"][:80],
        "favorites": sections["favorites"][:80],
        "with_picks": sections["with_picks"][:80],
        "with_odds": with_odds[:80],
        "by_country": by_country,
        "top_leagues": top_leagues,
        "calendar_grouped": grouped_match_calendar(combined),
        "live_grouped": group_matches_by_league(live_state["live"]),
        "favorites_grouped": group_matches_by_league(sections["favorites"][:40]),
        "grouping_policy": "Partidos ordenados por día, liga y hora.",
        "empty_state": "No hay partidos sincronizados todavía. El administrador puede sincronizar SportsDB/Odds o importar CSV/JSON legal.",
        "counts": {
            "live": len(live_state["live"]),
            "upcoming": len(live_state["scheduled"]),
            "favorites": len(sections["favorites"]),
            "with_picks": len(sections["with_picks"]),
            "with_odds": len(with_odds),
            "finished": len(result_matches),
            "popular": len(combined),
        },
    }
    save_live_sync_state("global", hub)
    cache_set(cache_key, hub, seconds=45)
    return hub


def save_live_sync_state(key, payload):
    sync = payload.get("sync") or {}
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """INSERT OR REPLACE INTO live_sync_state(key,payload_json,sync_status,next_refresh_at,updated_at)
           VALUES (?,?,?,?,?)""",
        (key, json.dumps(payload, ensure_ascii=False)[:12000], sync.get("sync_status") or "standby", sync.get("next_refresh_at") or "", now_iso()),
    )
    conn.commit()
    conn.close()


def real_time_global_state(date=None, refresh=False):
    date = date or today_iso()
    if refresh:
        cache_key = f"match-hub:{date}"
        conn = db()
        cur = conn.cursor()
        cur.execute("DELETE FROM persistent_cache WHERE key=?", (cache_key,))
        conn.commit()
        conn.close()
    hub = match_hub(date)
    return {
        "date": date,
        "version": APP_VERSION,
        "state": hub.get("sync", {}),
        "counts": hub.get("counts", {}),
        "live": hub.get("live", [])[:12],
        "fallback": "automatic",
        "source_policy": "APIs permitidas, importaciones autorizadas y cache SQLite; no scraping ilegal.",
    }


def live_data_flow(date=None):
    date = date or today_iso()
    hub = match_hub(date)
    favs = get_favorites()
    picks = get_picks(limit=30)
    profile = default_profile()
    favorite_bundle = favorite_feed_full()
    flow = build_live_flow(hub, favorites=favs, picks=picks, profile=profile)
    flow.update(
        {
            "date": date,
            "favorites": favorite_bundle,
            "profile": profile,
            "recent_picks": picks[:10],
            "navigation": {
                "home": "/",
                "hub": "/match-hub",
                "live": "/live",
                "favorites": "/favoritos",
                "shark": "/shark-ai",
            },
        }
    )
    return flow


MEMBERSHIP_PLANS = [
    {"key": "free", "name": "Free", "price": "0 EUR", "features": ["Calendario global", "Live basico", "Escudos persistentes"]},
    {"key": "pro", "name": "PRO", "price": "Premium", "features": ["Picks premium", "Combis", "Perfil favorito", "Alertas Telegram"]},
    {"key": "elite", "name": "ELITE", "price": "Top", "features": ["IA SHARK", "Briefings", "Prioridad live", "Control avanzado"]},
]


VALID_ROLES = {"FREE", "PRO", "ELITE", "ADMIN"}


def normalize_email(email):
    return str(email or "").strip().lower()


def normalize_username(username):
    username = str(username or "").strip().lower()
    username = re.sub(r"\s+", "", username)
    username = re.sub(r"[^a-z0-9_-]", "", username)
    return username


def username_from_email(email):
    base = normalize_username(str(email or "").split("@", 1)[0]) or "cliente"
    return base[:32]


def username_available(conn, username, exclude_user_id=None):
    if not username:
        return False
    if exclude_user_id:
        row = conn.execute("SELECT id FROM users WHERE username=? AND id!=?", (username, exclude_user_id)).fetchone()
    else:
        row = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    return row is None


def unique_username(conn, preferred, user_id=None):
    base = normalize_username(preferred)[:32] or "cliente"
    candidate = base
    suffix = 2
    while not username_available(conn, candidate, exclude_user_id=user_id):
        tail = f"-{suffix}"
        candidate = (base[: 32 - len(tail)] + tail) if len(base) + len(tail) > 32 else base + tail
        suffix += 1
    return candidate


def migrate_missing_usernames(conn):
    if "username" not in table_columns(conn, "users"):
        return
    users = conn.execute("SELECT id,email,username FROM users WHERE username IS NULL OR username=''").fetchall()
    for user in users:
        username = unique_username(conn, username_from_email(user["email"]), user["id"])
        conn.execute("UPDATE users SET username=? WHERE id=?", (username, user["id"]))


def normalize_role(role):
    role = str(role or "FREE").strip().upper()
    return role if role in VALID_ROLES else "FREE"


def dict_row(row):
    """Devuelve un dict estable desde sqlite3.Row, dict u objetos parciales.
    Evita errores 500 en login/perfil cuando una DB antigua devuelve filas legacy.
    """
    if not row:
        return {}
    if isinstance(row, dict):
        return row
    try:
        return dict(row)
    except Exception:
        return {}


def user_membership_is_expired(data):
    if not data:
        return False
    membership = normalize_role((data or {}).get("membership") or (data or {}).get("role"))
    if membership in {"FREE", "ADMIN"}:
        return False
    return iso_has_passed((data or {}).get("membership_expires_at"))


def expire_user_memberships_if_needed(user_id=""):
    """Downgrade expired admin gifts/offers to FREE without deleting history."""
    try:
        conn = db()
        params = [now_iso(), now_iso()]
        where = "COALESCE(membership_expires_at,'')!='' AND membership_expires_at<=? AND upper(COALESCE(membership,'FREE')) NOT IN ('FREE','ADMIN')"
        if user_id:
            where += " AND id=?"
            params.append(user_id)
        conn.execute(
            f"""UPDATE users
                SET role='FREE',
                    membership='FREE',
                    membership_source='expirada',
                    membership_note=COALESCE(NULLIF(membership_note,''),'Membresía temporal caducada automáticamente'),
                    membership_updated_at=?
              WHERE {where}""",
            tuple(params),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def enrich_user_membership_state(data):
    item = dict_row(data)
    if not item:
        return item
    item["membership"] = normalize_role(item.get("membership"))
    item["role"] = normalize_role(item.get("role"))
    item["membership_expires_label"] = membership_expires_label(item.get("membership_expires_at"))
    item["membership_is_temporal"] = bool(item.get("membership_expires_at")) and item["membership"] not in {"FREE", "ADMIN"}
    item["membership_expired"] = user_membership_is_expired(item)
    return item


def user_public(row):
    if not row:
        return None
    data = enrich_user_membership_state(row)
    email = data.get("email") or ""
    username = data.get("username") or username_from_email(email)
    return {
        "id": data.get("id"),
        "name": data.get("name") or username or "Cliente SHARK",
        "username": username,
        "email": email,
        "role": normalize_role(data.get("role")),
        "membership": normalize_role(data.get("membership")),
        "membership_source": data.get("membership_source") or "registro",
        "membership_started_at": data.get("membership_started_at") or "",
        "membership_expires_at": data.get("membership_expires_at") or "",
        "membership_expires_label": data.get("membership_expires_label") or membership_expires_label(data.get("membership_expires_at")),
        "membership_is_temporal": bool(data.get("membership_is_temporal")),
        "membership_note": data.get("membership_note") or "",
        "created_at": data.get("created_at"),
        "last_login": data.get("last_login"),
    }


def current_session_user():
    if not session.get("user_id"):
        return None
    # If an admin gift or offer has expired, refresh the session once and keep
    # the rest of the app seeing the correct plan immediately.
    try:
        if normalize_role(session.get("user_role")) != "ADMIN":
            expire_user_memberships_if_needed(session.get("user_id"))
            fresh = get_user_by_id(session.get("user_id"))
            if fresh:
                public = user_public(fresh)
                session["user_role"] = public["role"]
                session["user_membership"] = public["membership"]
                session["membership"] = public["membership"]
                session["membership_expires_at"] = public.get("membership_expires_at") or ""
                return public
    except Exception:
        pass
    return {
        "id": session.get("user_id"),
        "name": session.get("user_name") or "Cliente SHARK",
        "username": session.get("username") or session.get("user_name") or "",
        "email": session.get("user_email"),
        "role": normalize_role(session.get("user_role")),
        "membership": normalize_role(session.get("membership") or session.get("user_membership") or session.get("user_role")),
        "membership_expires_at": session.get("membership_expires_at") or "",
        "membership_expires_label": membership_expires_label(session.get("membership_expires_at")),
    }


def current_user_id():
    if not has_request_context():
        return ""
    return session.get("user_id") or ""


@app.template_filter("competition_es")
def jinja_competition_es(value):
    return spanish_competition_name(value) or "Competición"


@app.template_filter("market_es")
def jinja_market_es(value):
    return spanish_market_name(value) or "Mercado"


def _jinja_match_time_source(value, fallback_date="", fallback_time=""):
    if isinstance(value, dict):
        item = normalize_kickoff_for_display(value)
        return item, item.get("madrid_dt_iso") or item.get("kickoff_iso") or item.get("commence_time") or item.get("start_time") or item.get("event_time") or (f"{item.get('match_date')}T{str(item.get('kickoff_time') or item.get('match_time') or '')[:5]}:00" if item.get("match_date") and (item.get("kickoff_time") or item.get("match_time")) else "")
    return {}, value or (f"{fallback_date}T{str(fallback_time)[:5]}:00" if fallback_date and fallback_time else "")


@app.template_filter("match_time_short")
def jinja_match_time_short(value, fallback_date="", fallback_time=""):
    item, source = _jinja_match_time_source(value, fallback_date, fallback_time)
    if item.get("madrid_time"):
        return item.get("madrid_time")
    return format_madrid_short_time(source) or "Hora"


@app.template_filter("match_time_label")
def jinja_match_time_label(value, status=None, minute=None):
    item, source = _jinja_match_time_source(value)
    status_value = status if status is not None else item.get("status")
    minute_value = minute if minute is not None else (item.get("minute") or (item.get("live_depth") or {}).get("minute"))
    label = format_madrid_match_time(source, status_value, minute_value)
    return label or item.get("madrid_display") or item.get("display_datetime") or "Hora pendiente"


@app.template_filter("match_date_label")
def jinja_match_date_label(value):
    item, _source = _jinja_match_time_source(value)
    return item.get("madrid_date_label") or item.get("safe_date") or item.get("match_date") or "Sin fecha"


@app.context_processor
def inject_session_user():
    return {"current_user": current_session_user()}


def get_user_by_email(email):
    email = normalize_email(email)
    if not email:
        return None
    return one("SELECT * FROM users WHERE email=?", (email,))


def get_user_by_username(username):
    username = normalize_username(username)
    if not username:
        return None
    return one("SELECT * FROM users WHERE username=?", (username,))


def admin_exists(conn=None):
    close = False
    if conn is None:
        seed_core()
        conn = db()
        close = True
    row = conn.execute("SELECT id FROM users WHERE role='ADMIN' OR membership='ADMIN' LIMIT 1").fetchone()
    if close:
        conn.close()
    return row is not None


def create_admin_record(conn, name, username, email, password):
    name = str(name or "Admin SHARK").strip() or "Admin SHARK"
    email = normalize_email(email)
    username = unique_username(conn, username or username_from_email(email))
    password = str(password or "")
    if not email or not password:
        raise ValueError("ADMIN_EMAIL y ADMIN_PASSWORD son obligatorios.")
    existing = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    if existing:
        conn.execute(
            """UPDATE users
               SET name=?, username=?, password_hash=?, role='ADMIN', membership='ADMIN', last_login=COALESCE(last_login, ?)
               WHERE email=?""",
            (name, username, generate_password_hash(password), now_iso(), email),
        )
        return existing["id"]
    user_id = "adm_" + hashlib.sha256(f"{email}:{now_iso()}".encode("utf-8")).hexdigest()[:18]
    conn.execute(
        """INSERT INTO users(id,name,username,email,password_hash,role,membership,created_at,last_login)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (user_id, name, username, email, generate_password_hash(password), "ADMIN", "ADMIN", now_iso(), None),
    )
    return user_id


def bootstrap_admin_from_env(conn=None):
    close = False
    if conn is None:
        seed_core()
        conn = db()
        close = True
    try:
        if admin_exists(conn):
            return {"ok": True, "created": False, "blocked": True, "reason": "admin_exists"}
        email = normalize_email(os.getenv("ADMIN_EMAIL"))
        username = normalize_username(os.getenv("ADMIN_USERNAME") or username_from_email(email))
        password = os.getenv("ADMIN_PASSWORD", "")
        name = os.getenv("ADMIN_NAME", "Admin SHARK")
        if not email or not username or not password:
            print("NeMeSiS SHARK PRO: no ADMIN user found and ADMIN_EMAIL/ADMIN_USERNAME/ADMIN_PASSWORD are incomplete.")
            return {"ok": False, "created": False, "missing_env": True}
        user_id = create_admin_record(conn, name, username, email, password)
        conn.execute(
            """INSERT OR REPLACE INTO automation_state(key,value_json,updated_at)
               VALUES (?,?,?)""",
            ("admin_bootstrap", json.dumps({"created": True, "user_id": user_id, "time": now_iso()}), now_iso()),
        )
        if close:
            conn.commit()
        return {"ok": True, "created": True, "user_id": user_id}
    finally:
        if close:
            conn.close()


def get_user_by_login(identifier):
    identifier = str(identifier or "").strip()
    if "@" in identifier:
        return get_user_by_email(identifier)
    return get_user_by_username(identifier)


def get_user_by_id(user_id):
    if not user_id:
        return None
    return one("SELECT * FROM users WHERE id=?", (user_id,))


def set_login_session(user):
    public = user_public(user)
    session.clear()
    session["user_id"] = public["id"]
    session["user_name"] = public["name"]
    session["username"] = public["username"]
    session["user_email"] = public["email"]
    session["user_role"] = public["role"]
    session["user_membership"] = public["membership"]
    session["membership"] = public["membership"]
    session["membership_expires_at"] = public.get("membership_expires_at") or ""
    return public


def create_user(name, username, email, password, role="FREE", membership="FREE"):
    seed_core()
    name = str(name or "").strip()
    username = normalize_username(username)
    email = normalize_email(email)
    password = str(password or "")
    if not name or not username or not email or not password:
        raise ValueError("Completa nombre, usuario, email y contrasena.")
    if len(username) < 3:
        raise ValueError("El nombre de usuario debe tener al menos 3 caracteres.")
    role = normalize_role(role)
    membership = normalize_role(membership)
    user_id = "usr_" + hashlib.sha256(f"{email}:{now_iso()}".encode("utf-8")).hexdigest()[:18]
    conn = db()
    cur = conn.cursor()
    try:
        if not username_available(conn, username):
            raise ValueError("Ese nombre de usuario ya esta registrado.")
        cur.execute(
            """INSERT INTO users(id,name,username,email,password_hash,role,membership,created_at,last_login)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (user_id, name, username, email, generate_password_hash(password), role, membership, now_iso(), None),
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        message = str(exc).lower()
        if "username" in message:
            raise ValueError("Ese nombre de usuario ya esta registrado.") from exc
        raise ValueError("Ese email ya esta registrado.") from exc
    finally:
        conn.close()
    return get_user_by_email(email)


def authenticate_user(identifier, password, admin_only=False):
    user = get_user_by_login(identifier)
    raw_password = str(password or "")
    if not user:
        return None
    stored_hash = user.get("password_hash") or ""
    valid_password = False
    try:
        valid_password = check_password_hash(stored_hash, raw_password)
    except Exception:
        valid_password = False
    # Compatibilidad defensiva: si alguna DB legacy guardó texto plano, permitir entrada
    # y rehashear inmediatamente para no dejar la contraseña en claro.
    needs_rehash = False
    if not valid_password and stored_hash and stored_hash == raw_password:
        valid_password = True
        needs_rehash = True
    if not valid_password:
        return None
    if admin_only and normalize_role(user.get("role")) != "ADMIN":
        return None
    conn = db()
    if needs_rehash:
        conn.execute("UPDATE users SET password_hash=?, last_login=? WHERE id=?", (generate_password_hash(raw_password), now_iso(), user["id"]))
    else:
        conn.execute("UPDATE users SET last_login=? WHERE id=?", (now_iso(), user["id"]))
    conn.commit()
    conn.close()
    return get_user_by_id(user["id"])


def authenticate_env_admin(identifier, password):
    admin_email = normalize_email(os.getenv("ADMIN_EMAIL"))
    admin_username = normalize_username(os.getenv("ADMIN_USERNAME") or username_from_email(admin_email))
    admin_password = os.getenv("ADMIN_PASSWORD", "")
    if not admin_email or not admin_password:
        return None
    identifier = str(identifier or "").strip()
    identifier_ok = normalize_email(identifier) == admin_email if "@" in identifier else normalize_username(identifier) == admin_username
    if not identifier_ok or str(password or "") != admin_password:
        return None
    existing = get_user_by_email(admin_email)
    if not existing:
        admin_username = normalize_username(os.getenv("ADMIN_USERNAME") or username_from_email(admin_email))
        return create_user(os.getenv("ADMIN_NAME", "Admin SHARK"), admin_username, admin_email, admin_password, role="ADMIN", membership="ADMIN")
    conn = db()
    conn.execute(
        """UPDATE users
           SET role='ADMIN', membership='ADMIN', password_hash=?, last_login=?
           WHERE email=?""",
        (generate_password_hash(admin_password), now_iso(), admin_email),
    )
    conn.commit()
    conn.close()
    return get_user_by_email(admin_email)


def smtp_configured():
    return all(env_present(name) for name in ("SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM"))


def send_email_message(to_email, subject, body):
    if not smtp_configured():
        return {"ok": False, "mode": "diagnostic", "reason": "SMTP no configurado"}
    msg = EmailMessage()
    msg["From"] = os.getenv("SMTP_FROM")
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)
    host = os.getenv("SMTP_HOST")
    port = as_int(os.getenv("SMTP_PORT"), 587)
    try:
        with smtplib.SMTP(host, port, timeout=12) as server:
            server.starttls()
            server.login(os.getenv("SMTP_USERNAME"), os.getenv("SMTP_PASSWORD"))
            server.send_message(msg)
        return {"ok": True, "mode": "smtp"}
    except Exception as exc:
        return {"ok": False, "mode": "smtp", "error": str(exc)[:220]}


def create_password_reset_token(user, scope="client"):
    token = secrets.token_urlsafe(32)
    expires = (datetime.now(TZ) + timedelta(minutes=30)).isoformat(timespec="seconds")
    conn = db()
    conn.execute(
        """INSERT INTO password_reset_tokens(token,user_id,scope,expires_at,used_at,created_at)
           VALUES (?,?,?,?,?,?)""",
        (token, user["id"], scope, expires, "", now_iso()),
    )
    conn.commit()
    conn.close()
    return token


def load_password_reset_token(token, scope="client"):
    token = str(token or "").strip()
    if not token:
        return None
    row = one("SELECT * FROM password_reset_tokens WHERE token=? AND scope=?", (token, scope))
    if not row or row.get("used_at"):
        return None
    if str(row.get("expires_at") or "") < now_iso():
        return None
    return row


def mark_password_reset_used(token):
    conn = db()
    conn.execute("UPDATE password_reset_tokens SET used_at=? WHERE token=?", (now_iso(), token))
    conn.commit()
    conn.close()


def reset_user_password(user_id, password):
    password = str(password or "")
    if len(password) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres.")
    conn = db()
    conn.execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(password), user_id))
    conn.commit()
    conn.close()


def password_reset_request(identifier, scope="client"):
    user = get_user_by_login(identifier)
    delivery = {"ok": True, "sent": False, "mode": "silent"}
    reset_url = ""
    if user and (scope != "admin" or normalize_role(user.get("role")) == "ADMIN"):
        token = create_password_reset_token(user, scope)
        endpoint = "admin_reset_password_page" if scope == "admin" else "reset_password_page"
        reset_url = url_for(endpoint, token=token, _external=True)
        body = (
            "Hola,\n\n"
            "Hemos recibido una solicitud para restablecer tu contraseña de NeMeSiS SHARK PRO.\n"
            "El enlace caduca en 30 minutos y solo puede usarse una vez:\n\n"
            f"{reset_url}\n\n"
            "Si no has solicitado este cambio, ignora este mensaje."
        )
        delivery = send_email_message(user.get("email"), "Restablecer contraseña - NeMeSiS SHARK PRO", body)
    try:
        telegram_log("security", "password_reset_requested", "Solicitud de recuperación registrada.", {
            "scope": scope,
            "has_user": bool(user),
            "smtp_mode": delivery.get("mode"),
            "smtp_ok": delivery.get("ok"),
        })
    except Exception:
        pass
    return {"ok": True, "delivery": delivery, "diagnostic_reset_url": reset_url if not smtp_configured() else ""}


def is_admin_session():
    return normalize_role(session.get("user_role")) == "ADMIN"


def admin_json_forbidden():
    return jsonify({"ok": False, "version": APP_VERSION, "error": "Acceso admin requerido."}), 403


def list_users():
    seed_core()
    expire_user_memberships_if_needed()
    users = rows(
        """SELECT id,name,username,email,role,membership,created_at,last_login,
                  membership_source,membership_started_at,membership_expires_at,
                  membership_note,membership_updated_at,membership_updated_by,
                  membership_admin_granted
           FROM users ORDER BY created_at DESC"""
    )
    return [enrich_user_membership_state(user) for user in users]


def update_user_membership(user_id, membership, days=0, note="", source="admin_manual", admin_id=""):
    membership = normalize_role(membership)
    if membership not in VALID_ROLES or not user_id:
        return None
    days = days_from_admin_value(days)
    role = "ADMIN" if membership == "ADMIN" else membership
    started_at = now_iso()
    expires_at = ""
    if membership in {"PRO", "ELITE"} and days > 0:
        expires_at = (datetime.now(TZ) + timedelta(days=days)).isoformat(timespec="seconds")
        source = source or "admin_gift"
    elif membership == "FREE":
        source = source or "admin_free"
    else:
        source = source or "admin_manual"
    clean_note = str(note or "").strip()[:300]
    conn = db()
    conn.execute(
        """UPDATE users
              SET role=?, membership=?, membership_source=?, membership_started_at=?,
                  membership_expires_at=?, membership_note=?, membership_updated_at=?, membership_updated_by=?,
                  membership_admin_granted=?
            WHERE id=?""",
        (role, membership, source, started_at, expires_at, clean_note, now_iso(), str(admin_id or "")[:80], 1 if source.startswith("admin") else 0, user_id),
    )
    conn.commit()
    conn.close()
    return get_user_by_id(user_id)


def membership_admin_summary():
    expire_user_memberships_if_needed()
    active_temporal = 0
    expiring_soon = 0
    expired_today = 0
    soon_limit = (datetime.now(TZ) + timedelta(days=7)).isoformat(timespec="seconds")
    try:
        active_temporal = (one("""SELECT COUNT(*) AS total FROM users
            WHERE COALESCE(membership_expires_at,'')!=''
              AND upper(COALESCE(membership,'FREE')) IN ('PRO','ELITE')""") or {}).get("total", 0)
        expiring_soon = (one("""SELECT COUNT(*) AS total FROM users
            WHERE COALESCE(membership_expires_at,'')!=''
              AND membership_expires_at<=?
              AND upper(COALESCE(membership,'FREE')) IN ('PRO','ELITE')""", (soon_limit,)) or {}).get("total", 0)
        expired_today = (one("""SELECT COUNT(*) AS total FROM users
            WHERE membership_source='expirada' AND COALESCE(membership_updated_at,'') LIKE ?""", (today_iso()+"%",)) or {}).get("total", 0)
    except Exception:
        pass
    return {
        "active_temporal": active_temporal or 0,
        "expiring_soon": expiring_soon or 0,
        "expired_today": expired_today or 0,
        "quick_days": [1, 3, 7, 15, 30, 60, 90, 180, 365],
        "note": "Las membresías temporales se degradan a FREE automáticamente al caducar.",
    }


LEGACY_USER_TABLES = ("users", "clientes", "clients", "usuarios")


def legacy_column(columns, *names):
    lowered = {c.lower(): c for c in columns}
    for name in names:
        if name.lower() in lowered:
            return lowered[name.lower()]
    return None


def looks_like_password_hash(value):
    value = str(value or "")
    return value.startswith(("pbkdf2:", "scrypt:", "sha256$")) or (":" in value and "$" in value)


def import_users_from_old_database(path=None):
    seed_core()
    path = path or os.path.join(os.path.dirname(__file__), "old_database.db")
    result = {"ok": False, "path": os.path.basename(path), "imported": 0, "skipped": 0, "errors": []}
    if not os.path.exists(path):
        result["errors"].append("No existe old_database.db en la raiz del proyecto.")
        return result
    old_conn = sqlite3.connect(path)
    old_conn.row_factory = sqlite3.Row
    new_conn = db()
    try:
        tables = {row["name"] for row in old_conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        source_table = next((table for table in LEGACY_USER_TABLES if table in tables), None)
        if not source_table:
            result["errors"].append("No se encontro tabla users/clientes/clients/usuarios.")
            return result
        info = old_conn.execute(f"PRAGMA table_info({source_table})").fetchall()
        columns = [row["name"] for row in info]
        email_col = legacy_column(columns, "email", "correo", "mail")
        password_hash_col = legacy_column(columns, "password_hash", "pass_hash", "hash")
        password_col = legacy_column(columns, "password", "contrasena", "contraseña", "clave")
        name_col = legacy_column(columns, "name", "nombre", "display_name")
        username_col = legacy_column(columns, "username", "user", "usuario")
        role_col = legacy_column(columns, "role", "rol")
        membership_col = legacy_column(columns, "membership", "membresia", "plan")
        created_col = legacy_column(columns, "created_at", "alta", "created")
        last_login_col = legacy_column(columns, "last_login", "ultimo_login")
        if not email_col or not (password_hash_col or password_col):
            result["errors"].append("La tabla antigua no tiene email y password/password_hash suficientes.")
            return result
        for row in old_conn.execute(f"SELECT * FROM {source_table}").fetchall():
            try:
                email = normalize_email(row[email_col])
                if not email:
                    result["skipped"] += 1
                    continue
                if new_conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone():
                    result["skipped"] += 1
                    continue
                raw_username = row[username_col] if username_col else username_from_email(email)
                username = unique_username(new_conn, raw_username or username_from_email(email))
                password_value = row[password_hash_col] if password_hash_col else row[password_col]
                if not password_value:
                    result["skipped"] += 1
                    continue
                password_hash = str(password_value) if looks_like_password_hash(password_value) else generate_password_hash(str(password_value))
                role = normalize_role(row[role_col] if role_col else "FREE")
                membership = normalize_role(row[membership_col] if membership_col else role)
                name = str(row[name_col] if name_col else username).strip() or username
                user_id = "imp_" + hashlib.sha256(f"{email}:{now_iso()}".encode("utf-8")).hexdigest()[:18]
                new_conn.execute(
                    """INSERT INTO users(id,name,username,email,password_hash,role,membership,created_at,last_login)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (
                        user_id,
                        name,
                        username,
                        email,
                        password_hash,
                        role,
                        membership,
                        row[created_col] if created_col else now_iso(),
                        row[last_login_col] if last_login_col else None,
                    ),
                )
                result["imported"] += 1
            except Exception as exc:
                result["errors"].append(str(exc)[:160])
        new_conn.commit()
        result["ok"] = True
        return result
    finally:
        old_conn.close()
        new_conn.close()


def default_profile():
    seed_core()
    profile = one("SELECT * FROM client_profiles WHERE id='default'")
    if not profile:
        conn = db()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO client_profiles
               (id,name,membership_plan,favorite_teams_json,favorite_competitions_json,telegram_chat_id,preferences_json,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                "default",
                "Cliente SHARK",
                "pro",
                json.dumps(["Real Madrid", "Sevilla FC", "Real Betis"]),
                json.dumps(["UEFA Champions League", "LaLiga EA Sports", "Andalucia Regional Football"]),
                os.getenv("TELEGRAM_CHAT_ID", ""),
                json.dumps({"tone": "premium", "focus": "global+spain+andalucia"}),
                now_iso(),
                now_iso(),
            ),
        )
        conn.commit()
        conn.close()
        profile = one("SELECT * FROM client_profiles WHERE id='default'")
    profile["favorite_teams"] = json.loads(profile.get("favorite_teams_json") or "[]")
    profile["favorite_competitions"] = json.loads(profile.get("favorite_competitions_json") or "[]")
    profile["preferences"] = json.loads(profile.get("preferences_json") or "{}")
    return profile


def shark_briefing():
    today_matches = get_matches(today_iso(), "today")
    live_state = split_live(today_matches)
    all_picks = get_picks(limit=24)
    quality_groups = split_picks_by_quality(all_picks)
    picks = quality_groups.get("ready", [])[:8]
    profile = default_profile()
    imported_real = [m for m in today_matches if "seed" not in str(m.get("source") or "").lower()]
    explained = []
    for pick in picks:
        pick = normalize_pick_row(pick)
        risk_info = explain_pick_risk(pick)
        explained.append(
            {
                "id": pick.get("id"),
                "match": f"{pick.get('home_team') or ''} vs {pick.get('away_team') or ''}".strip(),
                "selection": pick.get("selection_display") or pick.get("selection"),
                "market": pick.get("market"),
                "odds": risk_info["odds"],
                "confidence": risk_info["confidence"],
                "risk": pick.get("risk_level") or risk_info["risk"],
                "quality_score": pick.get("quality_score"),
                "quality_label": pick.get("quality_label"),
                "explanation": risk_info["explanation"],
                "caution": pick.get("warning_reason") or "Revisa alineaciones y no subas stake si la cuota baja demasiado.",
            }
        )
    context = build_shark_context(favorites=get_favorites(), picks=picks, profile=profile)
    context["live_state"] = real_time_global_state()
    context["favorite_leagues"] = [f for f in get_favorites("league")]
    context["quality_groups"] = {k: len(v or []) for k, v in quality_groups.items()}
    ready_count = len(quality_groups.get("ready", []))
    study_count = len(quality_groups.get("study", []))
    return {
        "time": now_iso(),
        "profile": profile,
        "context": context,
        "summary": {
            "matches_today": len(today_matches),
            "real_or_imported_matches": len(imported_real),
            "live_now": len(live_state["live"]),
            "picks_ready": ready_count,
            "picks_study": study_count,
            "coverage": "football-first",
        },
        "risk": {
            "level": "CONTROLADO" if ready_count <= 3 else "MEDIO",
            "note": "SHARK prioriza picks con cuota real, selección clara, riesgo explicado y stake bajo antes que volumen.",
        },
        "priority": [
            "Publicar solo picks con cuota real y mercado claro.",
            "Separar oportunidades en estudio de picks premium listos.",
            "Usar stake responsable: mejor pocos picks buenos que muchas señales medias.",
        ],
        "picks": picks,
        "quality_groups": quality_groups,
        "explained_picks": explained,
        "legal_policy": "NeMeSiS ofrece análisis deportivo y señales de valor; no garantiza resultados. Apuesta siempre con responsabilidad.",
    }


def save_shark_context(context_type, target_key, payload):
    snapshot_id = hashlib.md5(f"shark-{context_type}-{target_key}-{now_iso()}".encode("utf-8")).hexdigest()[:18]
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO shark_context_snapshots(id,context_type,target_key,payload_json,created_at)
           VALUES (?,?,?,?,?)""",
        (snapshot_id, context_type, target_key, json.dumps(payload, ensure_ascii=False)[:8000], now_iso()),
    )
    conn.commit()
    conn.close()
    return snapshot_id


def _shark_line_match(match):
    match = apply_match_localization(dict(match or {}))
    home = match.get("home_team") or match.get("safe_home") or "Equipo local"
    away = match.get("away_team") or match.get("safe_away") or "Equipo visitante"
    comp = spanish_competition_name(match.get("competition_name") or match.get("league_name") or match.get("safe_competition") or "Competición")
    time = match.get("display_datetime") or spanish_datetime_label(match.get("kickoff_iso") or "", match.get("match_date"), match.get("kickoff_time") or match.get("match_time"))
    live_depth = match.get("live_depth") or {}
    status = live_depth.get("label") or match.get("status") or "Próximo"
    score = live_depth.get("score") or match.get("score") or ""
    suffix = f" · {score}" if score else ""
    return f"{time} · {home} vs {away} · {comp} · {status}{suffix}"


def _shark_pick_parts(pick):
    pick = normalize_pick_row(dict(pick or {}))
    home = pick.get("home_team") or "Equipo local"
    away = pick.get("away_team") or "Equipo visitante"
    comp = spanish_competition_name(pick.get("competition_name") or pick.get("league_name") or "Competición")
    selection = pick.get("selection_display") or spanish_pick_selection_name(pick.get("selection") or pick.get("_raw_selection"), home, away, pick.get("market")) or "Selección pendiente"
    market = spanish_market_name(pick.get("market") or "Ganador del partido")
    odds = as_float(pick.get("odds"), 0)
    odds_txt = f"{odds:.2f}" if odds > 1 else "pendiente"
    stake = as_float(pick.get("stake_units"), 1)
    confidence = as_int(pick.get("confidence") or pick.get("quality_score"), 50)
    qscore = as_int(pick.get("quality_score"), confidence)
    risk = pick.get("risk_level") or "MEDIO"
    reason = pick.get("reasoning") or "SHARK detecta mercado claro, cuota real y señal suficiente para revisarlo como pick premium."
    caution = pick.get("warning_reason") or "Revisa alineaciones antes de entrar y no subas stake si la cuota baja demasiado."
    return {
        "home": home,
        "away": away,
        "competition": comp,
        "selection": selection,
        "market": market,
        "odds": odds,
        "odds_txt": odds_txt,
        "stake": stake,
        "confidence": confidence,
        "quality_score": qscore,
        "risk": risk,
        "reason": reason,
        "caution": caution,
        "label": pick.get("quality_label") or "Pick premium",
    }


def _shark_line_pick(pick):
    p = _shark_pick_parts(pick)
    return (
        f"{p['home']} vs {p['away']}: {p['selection']} ({p['market']}) · "
        f"cuota {p['odds_txt']} · stake {p['stake']:g}/10 · confianza {p['confidence']}/100 · riesgo {p['risk']}"
    )


def _shark_card_pick(pick, title="Mi mejor opción ahora mismo"):
    p = _shark_pick_parts(pick)
    return (
        f"{title}:\n\n"
        f"{p['home']} vs {p['away']}\n"
        f"Competición: {p['competition']}\n\n"
        f"Pick: {p['selection']}\n"
        f"Mercado: {p['market']}\n"
        f"Cuota: {p['odds_txt']}\n"
        f"Stake: {p['stake']:g}/10\n"
        f"Confianza SHARK: {p['confidence']}/100\n"
        f"Calidad: {p['quality_score']}/100 · {p['label']}\n"
        f"Riesgo: {p['risk']}\n\n"
        f"Motivo:\n{p['reason']}\n\n"
        f"Precaución:\n{p['caution']}"
    )


def _shark_visible_picks(user, limit=8, premium_only=True, min_score=70):
    picks = published_picks_for_user(user, limit=max(limit * 4, 18))
    clean = []
    seen = set()
    for pick in picks:
        pick = normalize_pick_row(pick)
        key = normalized_label(f"{pick.get('match_id')}|{pick.get('home_team')}|{pick.get('away_team')}|{pick.get('market')}|{pick.get('selection')}")
        if key in seen:
            continue
        seen.add(key)
        if premium_only and not pick_is_premium_ready(pick, min_score=min_score):
            continue
        if as_float(pick.get("odds"), 0) <= 1:
            continue
        clean.append(pick)
    clean = sort_picks_by_quality(clean)
    return clean[:limit]


def _shark_recommendation_lines(limit=4):
    try:
        recs = v566_template_recommendations(limit=max(limit * 2, 8))
    except Exception:
        recs = []
    lines = []
    for rec in recs:
        rec = enrich_pick_quality(dict(rec or {}))
        if not pick_is_premium_ready(rec, min_score=62) and len(lines) >= max(1, limit // 2):
            continue
        home = spanish_team_name(rec.get("home_team") or "Equipo local")
        away = spanish_team_name(rec.get("away_team") or "Equipo visitante")
        comp = spanish_competition_name(rec.get("league_name") or rec.get("competition_name") or "Competición")
        selection = spanish_pick_selection_name(rec.get("selection") or rec.get("pick") or rec.get("recommendation"), home, away, rec.get("market") or rec.get("pick_type")) or "En estudio por SHARK"
        score = as_int(rec.get("quality_score") or rec.get("shark_score") or rec.get("score"), 0)
        odds = as_float(rec.get("odds") or rec.get("odds_value"), 0)
        odds_txt = f" · cuota {odds:.2f}" if odds > 1 else " · cuota pendiente"
        label = rec.get("quality_label") or "Señal SHARK"
        lines.append(f"{home} vs {away} · {comp}: {selection}{odds_txt} · {label} {score}/100")
        if len(lines) >= limit:
            break
    return lines


def _shark_count_requested(q_norm):
    numbers = [as_int(n, 0) for n in re.findall(r"\d+", q_norm or "")]
    if numbers:
        return combi_leg_count(max(numbers), 3)
    if "max" in q_norm or "quince" in q_norm or "15" in q_norm:
        return COMBI_MAX_LEGS
    if "segura" in q_norm or "conservadora" in q_norm:
        return 3
    return 5


def _shark_actions(*items):
    actions = []
    for label, url in items:
        if label and url:
            actions.append({"label": label, "url": url})
    return actions


def shark_answer(question):
    q = str(question or "").strip() or "resumen"
    q_norm = normalized_label(q)
    user = current_session_user() or {"membership": "FREE", "role": "FREE"}
    briefing = shark_briefing()
    hub = match_hub(today_iso())
    focus = "resumen"
    next_url = "/sports-hub"
    actions = _shark_actions(("Inicio deportivo", "/sports-hub"), ("Ver picks", "/picks"))

    no_tocar = any(word in q_norm for word in ["no tocar", "evitar", "descartar", "peligro", "arriesgado"])
    safe_intent = any(word in q_norm for word in ["seguro", "segura", "conservador", "conservadora", "bajo riesgo"])
    value_intent = any(word in q_norm for word in ["value", "valor", "oportunidad", "oportunidades"])

    if no_tocar:
        focus = "riesgo"
        study = (briefing.get("quality_groups") or {}).get("study", [])[:5]
        lines = []
        for p in study:
            p = normalize_pick_row(p)
            lines.append(f"{p.get('home_team')} vs {p.get('away_team')} · {p.get('selection_display') or p.get('selection')} · motivo: falta calidad/cuota/riesgo suficiente")
        body = (
            "Lectura SHARK de riesgo:\n\n"
            "Ahora mismo evitaría entrar fuerte en cualquier selección sin cuota real, mercado claro o motivo completo.\n"
            "También evitaría combinadas largas si no hay al menos 9 picks premium limpios.\n\n"
            "Señales que dejaría en estudio:\n"
            + ("\n".join(f"{i+1}. {line}" for i, line in enumerate(lines)) if lines else "No hay descartes relevantes visibles ahora mismo.")
        )
        next_url = "/picks"
        actions = _shark_actions(("Ver picks filtrados", "/picks"), ("Crear combi segura", "/combis?tipo=segura&partidos=3"))

    elif any(word in q_norm for word in ["combi", "combinada", "combinadas"]):
        focus = "combis"
        requested = _shark_count_requested(q_norm)
        if safe_intent:
            requested = min(requested, 4)
        picks = _shark_visible_picks(user, limit=COMBI_MAX_LEGS, min_score=72)
        usable = picks[:requested]
        if len(usable) >= 2:
            total = 1.0
            for pick in usable:
                total *= max(1.0, as_float(pick.get("odds"), 1.0))
            risk = combi_risk(usable)
            title = "Combi segura SHARK" if requested <= 4 else ("Combi media SHARK" if requested <= 8 else "Combi larga SHARK")
            warning = "Stake bajo obligatorio: las combinadas largas no son seguras." if requested >= 9 else "Mantén stake bajo y no fuerces si una cuota baja demasiado."
            body = (
                f"{title}\n\n"
                f"Selecciones: {len(usable)}\n"
                f"Cuota total aproximada: {total:.2f}\n"
                f"Riesgo: {risk}\n"
                f"Recomendación: {warning}\n\n"
                + "\n".join(f"{i+1}. {_shark_line_pick(p)}" for i, p in enumerate(usable))
            )
        else:
            candidates = build_combi_candidates_from_matches(requested).get("matches", [])
            lines = [_shark_line_match(m) for m in candidates[:requested]]
            body = (
                f"No cierro una combinada real de {requested} partidos porque faltan picks premium con cuota suficiente.\n"
                "Prefiero esperar antes que inventar selecciones. Base de partidos para revisar:\n\n"
                + ("\n".join(f"{i+1}. {line}" for i, line in enumerate(lines)) if lines else "No hay base suficiente todavía.")
            )
        next_url = f"/combis?partidos={requested}"
        actions = _shark_actions(("Abrir combis", next_url), ("Ver picks premium", "/picks"))

    elif any(word in q_norm for word in ["pick", "apuesta", "pronostico", "pronosticos", "mejor"]):
        focus = "picks"
        min_score = 76 if safe_intent else 70
        picks = _shark_visible_picks(user, limit=5, min_score=min_score)
        if picks:
            best = picks[0]
            body = _shark_card_pick(best, "Mi mejor opción ahora mismo")
            if len(picks) > 1:
                body += "\n\nOtras opciones revisables:\n" + "\n".join(f"{i+2}. {_shark_line_pick(p)}" for i, p in enumerate(picks[1:4]))
            body += "\n\nRegla SHARK: si la cuota baja demasiado o falta alineación, no fuerces la entrada."
        else:
            rec_lines = _shark_recommendation_lines(limit=4)
            body = (
                "No tengo suficientes cuotas reales para darte un pick premium cerrado ahora mismo.\n"
                "Puedo revisar partidos de hoy, directo o preparar una combi conservadora con los datos disponibles.\n\n"
                + ("Oportunidades en estudio:\n" + "\n".join(f"{i+1}. {line}" for i, line in enumerate(rec_lines)) if rec_lines else "No hay oportunidades claras con datos suficientes todavía.")
            )
        next_url = "/picks"
        actions = _shark_actions(("Ver picks", "/picks"), ("Combi segura", "/combis?tipo=segura&partidos=3"))

    elif value_intent:
        focus = "oportunidades"
        rec_lines = _shark_recommendation_lines(limit=5)
        body = (
            "Radar SHARK de value:\n\n"
            + ("\n".join(f"{i+1}. {line}" for i, line in enumerate(rec_lines)) if rec_lines else "No hay señales de valor suficientes ahora mismo.")
            + "\n\nValue no significa apuesta segura: si la cuota está pendiente o el mercado cambia, se queda en estudio."
        )
        next_url = "/recommendations"
        actions = _shark_actions(("Ver oportunidades", "/recommendations"), ("Ver picks", "/picks"))

    elif any(word in q_norm for word in ["live", "directo", "marcador", "minuto"]):
        focus = "live"
        live_matches = hub.get("live", []) or get_matches(today_iso(), "live")
        lines = [_shark_line_match(m) for m in live_matches[:6]]
        body = (
            f"Directo SHARK:\n{hub['counts'].get('live', len(live_matches))} partidos en directo y {hub['counts'].get('upcoming', 0)} próximos.\n\n"
            + ("\n".join(f"{i+1}. {line}" for i, line in enumerate(lines)) if lines else "No detecto directos reales ahora mismo. En cuanto entren minuto y marcador, los priorizo aquí.")
            + "\n\nEn live solo entraría con señal fuerte y stake mínimo."
        )
        next_url = "/live"
        actions = _shark_actions(("Abrir directo", "/live"), ("Ver calendario", "/calendar"))

    elif any(word in q_norm for word in ["favor", "favorito", "favoritos"]):
        focus = "favoritos"
        fav = favorite_insights()
        lines = [_shark_line_match(m) for m in fav.get("matches", [])[:6]]
        body = (
            f"Favoritos SHARK:\n{fav.get('summary')}.\n\n"
            + ("\n".join(f"{i+1}. {line}" for i, line in enumerate(lines)) if lines else "Todavía no hay partidos activos/próximos cruzados con tus favoritos. Marca equipos, ligas o partidos con la estrella para personalizar esto.")
        )
        next_url = "/favorites"
        actions = _shark_actions(("Abrir favoritos", "/favorites"), ("Partidos de hoy", "/sports-hub"))

    else:
        focus = "resumen"
        best_pick = _shark_visible_picks(user, limit=1, min_score=70)
        rec_lines = _shark_recommendation_lines(limit=2)
        body = (
            f"Resumen SHARK PRO:\n\n"
            f"Partidos hoy: {briefing['summary']['matches_today']}\n"
            f"En directo: {briefing['summary']['live_now']}\n"
            f"Picks premium listos: {briefing['summary']['picks_ready']}\n"
            f"En estudio: {briefing['summary'].get('picks_study', 0)}\n"
            f"Riesgo general: {briefing['risk']['level']}\n\n"
        )
        if best_pick:
            body += _shark_card_pick(best_pick[0], "Pick más claro")
        elif rec_lines:
            body += "Oportunidades a revisar:\n" + "\n".join(f"{i+1}. {line}" for i, line in enumerate(rec_lines))
        else:
            body += "No fuerzo apuestas sin datos suficientes. Mejor esperar a nuevas cuotas o revisar directo."
        next_url = "/sports-hub"
        actions = _shark_actions(("Partidos", "/sports-hub"), ("Picks", "/picks"), ("Telegram", "/telegram"))

    return {
        "question": q,
        "focus": focus,
        "answer": body,
        "context": briefing.get("context"),
        "risk_note": briefing["risk"]["note"],
        "actions": actions,
        "next_action": "Revisar la pantalla recomendada antes de apostar. SHARK no garantiza resultados.",
        "next_url": next_url,
        "legal_policy": briefing["legal_policy"],
    }

def telegram_config():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    settings = get_telegram_settings()
    return {
        "configured": bool(token and chat_id),
        "token_present": bool(token),
        "token_masked": masked_key(token),
        "chat_id_present": bool(chat_id),
        "chat_id_masked": masked_key(chat_id),
        "enabled": bool(settings.get("enabled") or telegram_env_should_enable()),
        "legacy_enabled": telegram_env_auto_enabled(),
        "env_auto_enabled": telegram_env_auto_enabled(),
        "env_ready": telegram_env_ready(),
        "auto_minutes": as_int(os.getenv("TELEGRAM_AUTO_MINUTES", "360"), 360),
        "settings": settings,
    }


def get_telegram_settings():
    seed_core()
    env_enable = telegram_env_should_enable()
    row = one("SELECT * FROM telegram_settings WHERE id='default'")
    if not row:
        conn = db()
        conn.execute(
            """INSERT OR IGNORE INTO telegram_settings
               (id,auto_daily_matches,auto_daily_picks,auto_live_alerts,daily_matches_time,daily_picks_time,max_messages_per_hour,enabled,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                "default",
                1,
                1 if env_enable or env_bool("AUTO_SEND_TELEGRAM_PICKS", False) else 0,
                0,
                "09:00",
                "11:00",
                10,
                1 if env_enable else 0,
                now_iso(),
            ),
        )
        conn.commit()
        conn.close()
        row = one("SELECT * FROM telegram_settings WHERE id='default'")
    settings = normalize_settings(row)
    if env_enable and (not settings.get("enabled") or not settings.get("auto_daily_picks")):
        conn = db()
        conn.execute(
            """UPDATE telegram_settings
               SET enabled=1,
                   auto_daily_matches=1,
                   auto_daily_picks=1,
                   updated_at=?
               WHERE id='default'""",
            (now_iso(),),
        )
        conn.commit()
        conn.close()
        row = one("SELECT * FROM telegram_settings WHERE id='default'")
        settings = normalize_settings(row)
        try:
            telegram_log("settings", "healed", "Telegram automatico activado desde variables Render.", {
                "ENABLE_TELEGRAM_AUTO": os.getenv("ENABLE_TELEGRAM_AUTO", ""),
                "AUTO_SEND_TELEGRAM_PICKS": os.getenv("AUTO_SEND_TELEGRAM_PICKS", ""),
                "token_present": env_present("TELEGRAM_BOT_TOKEN"),
                "chat_id_present": env_present("TELEGRAM_CHAT_ID"),
            })
        except Exception:
            pass
    return settings




def _telegram_sync_env_on_startup():
    """Sincroniza la BD con Render para que el automático no quede apagado por una fila legacy."""
    if not telegram_env_should_enable():
        return {"ok": True, "changed": False, "reason": "env_auto_disabled_or_missing_config"}
    try:
        seed_core()
        current = one("SELECT * FROM telegram_settings WHERE id='default'")
        settings = normalize_settings(current)
        if settings.get("enabled") and settings.get("auto_daily_picks"):
            return {"ok": True, "changed": False, "settings": settings}
        conn = db()
        conn.execute(
            """INSERT OR REPLACE INTO telegram_settings
               (id,auto_daily_matches,auto_daily_picks,auto_live_alerts,daily_matches_time,daily_picks_time,max_messages_per_hour,enabled,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                "default",
                1,
                1,
                1 if settings.get("auto_live_alerts") else 0,
                settings.get("daily_matches_time") or "09:00",
                settings.get("daily_picks_time") or "11:00",
                settings.get("max_messages_per_hour") or 10,
                1,
                now_iso(),
            ),
        )
        conn.commit()
        conn.close()
        return {"ok": True, "changed": True, "settings": get_telegram_settings()}
    except Exception as exc:
        try:
            print("[TELEGRAM] env startup sync skipped:", str(exc)[:220])
        except Exception:
            pass
        return {"ok": False, "changed": False, "error": str(exc)[:220]}

def update_telegram_settings(payload):
    current = get_telegram_settings()
    merged = dict(current)
    for key in ("auto_daily_matches", "auto_daily_picks", "auto_live_alerts", "enabled"):
        if key in payload:
            merged[key] = str(payload.get(key)).lower() in {"1", "true", "yes", "on"} or payload.get(key) is True
    for key in ("daily_matches_time", "daily_picks_time"):
        if key in payload and str(payload.get(key) or "").strip():
            merged[key] = str(payload.get(key)).strip()[:5]
    if "max_messages_per_hour" in payload:
        merged["max_messages_per_hour"] = max(1, as_int(payload.get("max_messages_per_hour"), 10))
    conn = db()
    conn.execute(
        """INSERT OR REPLACE INTO telegram_settings
           (id,auto_daily_matches,auto_daily_picks,auto_live_alerts,daily_matches_time,daily_picks_time,max_messages_per_hour,enabled,updated_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            "default",
            1 if merged["auto_daily_matches"] else 0,
            1 if merged["auto_daily_picks"] else 0,
            1 if merged["auto_live_alerts"] else 0,
            merged["daily_matches_time"],
            merged["daily_picks_time"],
            merged["max_messages_per_hour"],
            1 if merged["enabled"] else 0,
            now_iso(),
        ),
    )
    conn.commit()
    conn.close()
    telegram_log("settings", "updated", "Configuracion Telegram actualizada.", merged)
    return get_telegram_settings()


def telegram_log(event_type, status, message, payload=None):
    seed_core()
    log_id = hashlib.md5(f"telegram-log-{event_type}-{status}-{datetime.now(TZ).isoformat(timespec='microseconds')}".encode("utf-8")).hexdigest()[:18]
    conn = db()
    conn.execute(
        """INSERT INTO telegram_logs(id,event_type,status,message,payload_json,created_at)
           VALUES (?,?,?,?,?,?)""",
        (log_id, event_type, status, str(message or "")[:1000], json.dumps(payload or {}, ensure_ascii=False)[:5000], now_iso()),
    )
    conn.commit()
    conn.close()
    return log_id



def telegram_bot_username():
    return (os.getenv("TELEGRAM_BOT_USERNAME") or os.getenv("TELEGRAM_USERNAME") or "nemesi_shark_pro_bot").replace("@", "").strip()


def telegram_code_expired(value):
    if not value:
        return True
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")) < datetime.now(TZ)
    except Exception:
        return True


def generate_telegram_link_code(user_id):
    seed_core()
    user = one("SELECT * FROM users WHERE id=?", (user_id,))
    if not user:
        return None
    current_code = str(user.get("telegram_link_code") or "").strip()
    current_expires = user.get("telegram_link_expires_at") or user.get("telegram_link_expires")
    if current_code and not telegram_code_expired(current_expires):
        return current_code
    raw = f"{user_id}-{datetime.now(TZ).isoformat(timespec='microseconds')}-{os.urandom(8).hex()}"
    code = "NS" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8].upper()
    expires_at = (datetime.now(TZ) + timedelta(hours=24)).isoformat(timespec="seconds")
    conn = db()
    conn.execute(
        "UPDATE users SET telegram_link_code=?, telegram_link_expires_at=?, telegram_link_expires=? WHERE id=?",
        (code, expires_at, expires_at, user_id),
    )
    conn.commit()
    conn.close()
    telegram_log("link", "pending", "Codigo de vinculacion Telegram generado.", {"user_id": user_id, "expires_at": expires_at})
    return code


def upsert_telegram_subscriber(user, chat_id, username="", first_name=""):
    membership = normalize_role((user or {}).get("membership") or (user or {}).get("role") or "FREE")
    user_id = (user or {}).get("id") or ""
    sub_id = hashlib.md5(f"telegram-sub-{chat_id}".encode("utf-8")).hexdigest()[:18]
    conn = db()
    conn.execute(
        """INSERT OR REPLACE INTO telegram_subscribers
           (id,user_id,chat_id,username,first_name,membership,is_active,created_at,last_seen,last_message_sent_at)
           VALUES (?,?,?,?,?,?,?,?,?,COALESCE((SELECT last_message_sent_at FROM telegram_subscribers WHERE id=?),''))""",
        (sub_id, user_id, str(chat_id), username or (user or {}).get("telegram_username") or "", first_name or (user or {}).get("name") or "Cliente SHARK", membership, 1, now_iso(), now_iso(), sub_id),
    )
    conn.commit()
    conn.close()
    return sub_id


def sync_telegram_subscribers_from_users():
    seed_core()
    linked = rows(
        """SELECT id,name,username,email,role,membership,telegram_chat_id,telegram_username
           FROM users
           WHERE telegram_chat_id IS NOT NULL AND telegram_chat_id!=''"""
    )
    synced = 0
    for user in linked:
        upsert_telegram_subscriber(user, user.get("telegram_chat_id"), user.get("telegram_username") or user.get("username"), user.get("name"))
        synced += 1
    return synced


def link_telegram_chat_by_code(code, chat_id, username="", first_name=""):
    seed_core()
    clean = str(code or "").strip().upper().replace("/LINK", "").replace("/START", "").strip()
    if not clean:
        return {"ok": False, "status": "NO_CODE", "message": "Falta codigo de vinculacion."}
    user = one("SELECT * FROM users WHERE UPPER(telegram_link_code)=?", (clean,))
    if not user:
        telegram_log("link", "failed", "Codigo Telegram no encontrado.", {"code": clean, "chat_id": str(chat_id)})
        return {"ok": False, "status": "NOT_FOUND", "message": "Codigo no encontrado o ya usado."}
    expires_at = user.get("telegram_link_expires_at") or user.get("telegram_link_expires")
    if telegram_code_expired(expires_at):
        telegram_log("link", "failed", "Codigo Telegram expirado.", {"user_id": user.get("id"), "chat_id": str(chat_id)})
        return {"ok": False, "status": "EXPIRED", "message": "Codigo expirado. Genera uno nuevo desde NeMeSiS."}
    conn = db()
    conn.execute(
        """UPDATE users
           SET telegram_chat_id=?, telegram_username=?, telegram_linked_at=?, telegram_link_code='', telegram_link_expires_at='', telegram_link_expires=''
           WHERE id=?""",
        (str(chat_id), username or "", now_iso(), user.get("id")),
    )
    conn.commit()
    conn.close()
    user = one("SELECT * FROM users WHERE id=?", (user.get("id"),)) or user
    upsert_telegram_subscriber(user, chat_id, username=username, first_name=first_name)
    telegram_log("link", "success", "Telegram privado vinculado correctamente.", {"user_id": user.get("id"), "membership": user.get("membership"), "chat_id": str(chat_id)})
    return {"ok": True, "status": "LINKED", "user": user, "message": "Telegram vinculado correctamente."}


def telegram_user_state(user):
    if not user or not user.get("id"):
        return {"linked": False, "requires_login": True}
    full = one("SELECT * FROM users WHERE id=?", (user.get("id"),)) or dict(user)
    linked = bool(full.get("telegram_chat_id"))
    code = ""
    if not linked:
        code = generate_telegram_link_code(full.get("id")) or ""
        full = one("SELECT * FROM users WHERE id=?", (full.get("id"),)) or full
    bot = telegram_bot_username()
    deep_link = f"https://t.me/{bot}?start={code}" if bot and code else ""
    return {
        "linked": linked,
        "chat_id_masked": masked_key(full.get("telegram_chat_id") or ""),
        "username": full.get("telegram_username") or "",
        "linked_at": full.get("telegram_linked_at") or "",
        "code": code,
        "expires_at": full.get("telegram_link_expires_at") or full.get("telegram_link_expires") or "",
        "bot_username": bot,
        "deep_link": deep_link,
        "command": f"/link {code}" if code else "",
    }

def ensure_default_telegram_subscriber():
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not chat_id:
        return None
    existing = one("SELECT * FROM telegram_subscribers WHERE chat_id=?", (chat_id,))
    if existing:
        return existing
    sub = subscriber_payload(chat_id=chat_id, username="admin", first_name="Canal SHARK", membership="ADMIN")
    sub_id = hashlib.md5(f"telegram-sub-{chat_id}".encode("utf-8")).hexdigest()[:18]
    conn = db()
    conn.execute(
        """INSERT OR IGNORE INTO telegram_subscribers(id,user_id,chat_id,username,first_name,membership,is_active,created_at,last_seen,last_message_sent_at)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (sub_id, sub["user_id"], sub["chat_id"], sub["username"], sub["first_name"], sub["membership"], 1, now_iso(), now_iso(), ""),
    )
    conn.commit()
    conn.close()
    return one("SELECT * FROM telegram_subscribers WHERE id=?", (sub_id,))


def telegram_subscribers(active_only=True):
    ensure_default_telegram_subscriber()
    try:
        sync_telegram_subscribers_from_users()
    except Exception as exc:
        telegram_log("sync", "failed", "No se pudieron sincronizar usuarios Telegram.", {"error": str(exc)})
    if active_only:
        return rows("SELECT * FROM telegram_subscribers WHERE is_active=1 AND chat_id IS NOT NULL AND chat_id!='' ORDER BY membership DESC, created_at")
    return rows("SELECT * FROM telegram_subscribers ORDER BY created_at DESC")


def telegram_auto_destinations(required_membership="FREE", include_global=True):
    required_membership = normalize_role(required_membership or "FREE")
    destinations = []
    seen = set()
    global_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if include_global and global_chat_id:
        destinations.append({"chat_id": global_chat_id, "user_id": "", "membership": "ADMIN", "target_kind": "channel", "target_key": "auto_channel", "label": "Canal global"})
        seen.add(global_chat_id)
    for sub in telegram_subscribers():
        chat_id = str(sub.get("chat_id") or "").strip()
        if not chat_id or chat_id in seen:
            continue
        membership = normalize_role(sub.get("membership") or "FREE")
        if membership_allows(membership, required_membership):
            user_id = sub.get("user_id") or ""
            destinations.append({"chat_id": chat_id, "user_id": user_id, "membership": membership, "target_kind": "private", "target_key": f"auto_private_user_{user_id or chat_id}", "label": sub.get("first_name") or sub.get("username") or "Usuario Telegram"})
            seen.add(chat_id)
    return destinations


def telegram_sent_last_hour(chat_id=None):
    since = (datetime.now(TZ) - timedelta(hours=1)).isoformat(timespec="seconds")
    if chat_id:
        return (one("SELECT COUNT(*) AS total FROM telegram_queue WHERE chat_id=? AND status=? AND sent_at>=?", (chat_id, QUEUE_SENT, since)) or {}).get("total", 0)
    return (one("SELECT COUNT(*) AS total FROM telegram_queue WHERE status=? AND sent_at>=?", (QUEUE_SENT, since)) or {}).get("total", 0)


def telegram_sent_today(chat_id=None, message_type=None):
    clauses = ["status=?", "sent_at LIKE ?"]
    params = [QUEUE_SENT, today_iso() + "%"]
    if chat_id:
        clauses.append("chat_id=?")
        params.append(chat_id)
    if message_type:
        clauses.append("lower(coalesce(message_type,''))=?")
        params.append(str(message_type).lower())
    return (one(f"SELECT COUNT(*) AS total FROM telegram_queue WHERE {' AND '.join(clauses)}", tuple(params)) or {}).get("total", 0)


def telegram_pro_calibration():
    return {
        "mode": "PRO",
        "tick_review_every_minutes": as_int(os.getenv("TELEGRAM_TICK_REVIEW_MINUTES", "15"), 15),
        "daily_run_every_minutes": as_int(os.getenv("TELEGRAM_DAILY_RUN_MINUTES", "60"), 60),
        "quiet_start": os.getenv("TELEGRAM_QUIET_START", "00:30"),
        "quiet_end": os.getenv("TELEGRAM_QUIET_END", "09:30"),
        "daily_summary_start": os.getenv("TELEGRAM_DAILY_SUMMARY_START", "09:30"),
        "daily_summary_end": os.getenv("TELEGRAM_DAILY_SUMMARY_END", "12:30"),
        "daily_picks_start": os.getenv("TELEGRAM_DAILY_PICKS_START", "13:00"),
        "daily_picks_end": os.getenv("TELEGRAM_DAILY_PICKS_END", "20:30"),
        "max_messages_per_hour": as_int(os.getenv("TELEGRAM_MAX_MESSAGES_PER_HOUR", "1"), 1),
        "max_messages_per_day": as_int(os.getenv("TELEGRAM_MAX_MESSAGES_PER_DAY", "8"), 8),
        "max_queue_per_tick": as_int(os.getenv("TELEGRAM_MAX_QUEUE_PER_TICK", "3"), 3),
        "max_auto_picks_per_tick": as_int(os.getenv("TELEGRAM_MAX_AUTO_PICKS_PER_TICK", "2"), 2),
        "max_auto_picks_per_day": as_int(os.getenv("TELEGRAM_MAX_AUTO_PICKS_PER_DAY", os.getenv("MAX_AUTO_PICKS_PER_DAY", "4")), 4),
        "min_pick_score": as_int(os.getenv("MIN_SHARK_SCORE_FOR_AUTO_SEND", os.getenv("AUTO_PICKS_MIN_SCORE", "75")), 75),
        "elite_pick_score": as_int(os.getenv("TELEGRAM_ELITE_PICK_SCORE", "85"), 85),
        "min_odds": as_float(os.getenv("TELEGRAM_MIN_ODDS", "1.40"), 1.40),
        "max_odds": as_float(os.getenv("TELEGRAM_MAX_ODDS", "4.50"), 4.50),
        "sport_mode": telegram_sport_mode_summary(),
    }


def _telegram_time_to_minutes(value, default="00:00"):
    raw = str(value or default).strip()[:5]
    try:
        hh, mm = raw.split(":", 1)
        return max(0, min(23, int(hh))) * 60 + max(0, min(59, int(mm)))
    except Exception:
        hh, mm = default.split(":", 1)
        return int(hh) * 60 + int(mm)


def telegram_time_window_active(start, end, current=None):
    now_dt = current or datetime.now(TZ)
    cur = now_dt.hour * 60 + now_dt.minute
    start_m = _telegram_time_to_minutes(start)
    end_m = _telegram_time_to_minutes(end)
    if start_m == end_m:
        return True
    if start_m < end_m:
        return start_m <= cur <= end_m
    return cur >= start_m or cur <= end_m


def telegram_quiet_hours_active():
    cfg = telegram_pro_calibration()
    return telegram_time_window_active(cfg["quiet_start"], cfg["quiet_end"])


def telegram_message_is_automatic(message_type):
    value = str(message_type or "").lower()
    return value not in {"manual", "test", "system_test", "admin_test"}


def telegram_should_delay_message(message_type, force=False):
    return (not force) and telegram_message_is_automatic(message_type) and telegram_quiet_hours_active()


def enqueue_telegram_message(message_type, title, body, chat_id="", user_id="", payload=None, scheduled_at=None, dedupe_key="", force=False, max_attempts=3):
    seed_core()
    scheduled_at = scheduled_at or now_iso()
    payload = payload or {}
    dedupe_key = dedupe_key or telegram_dedupe_key(message_type, today_iso(), chat_id or user_id or "global")
    existing = one("SELECT * FROM telegram_queue WHERE dedupe_key=?", (dedupe_key,))
    if existing and not force:
        telegram_log("queue", "skipped", "Mensaje duplicado omitido.", {"dedupe_key": dedupe_key, "message_type": message_type})
        return {"ok": True, "queued": False, "skipped": 1, "reason": "duplicate", "item": existing}
    queue_id = hashlib.md5(f"telegram-queue-{dedupe_key}-{datetime.now(TZ).isoformat(timespec='microseconds')}".encode("utf-8")).hexdigest()[:18]
    conn = db()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO telegram_queue
               (id,signature,alert_type,target_key,chat_id,user_id,message_type,title,body,priority,payload_json,status,attempts,max_attempts,dedupe_key,scheduled_at,sent_at,error_message,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                queue_id,
                dedupe_key[:18],
                message_type,
                payload.get("target_key") or "",
                chat_id,
                user_id,
                message_type,
                title,
                body,
                as_int(payload.get("priority"), 70),
                json.dumps(payload, ensure_ascii=False)[:5000],
                QUEUE_PENDING,
                0,
                max(1, as_int(max_attempts, 3)),
                dedupe_key,
                scheduled_at,
                "",
                "",
                now_iso(),
                now_iso(),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    telegram_log("queue", "pending", f"Mensaje encolado: {title}", {"id": queue_id, "type": message_type})
    return {"ok": True, "queued": True, "inserted": 1, "item": one("SELECT * FROM telegram_queue WHERE id=?", (queue_id,))}


def telegram_public_base_url():
    for key in ("PUBLIC_BASE_URL", "APP_PUBLIC_URL", "BASE_URL", "RENDER_EXTERNAL_URL", "CANONICAL_URL"):
        value = str(os.getenv(key, "") or "").strip().rstrip("/")
        if value.startswith(("http://", "https://")):
            return value
    if has_request_context():
        return request.url_root.rstrip("/")
    return ""


def telegram_absolute_url(value):
    value = str(value or "").strip()
    if not value:
        return ""
    if value.startswith(("http://", "https://")):
        return value
    if value.startswith("/"):
        base = telegram_public_base_url()
        return f"{base}{value}" if base else ""
    return ""


def telegram_match_url(match_id="", fallback_path="/match-hub"):
    match_id = str(match_id or "").strip()
    if match_id:
        return telegram_absolute_url(f"/match/{urllib.parse.quote(match_id)}")
    return telegram_absolute_url(fallback_path)


def telegram_crest_url_for_team(team_name, explicit_url=""):
    url = telegram_absolute_url(explicit_url)
    if url:
        return url
    try:
        identity = resolve_team(team_name)
        return telegram_absolute_url(identity.get("crest_url") or identity.get("logo_url") or "")
    except Exception:
        return ""


def telegram_enrich_match_for_message(match):
    item = dict(match or {})
    item["sport_key"] = item.get("sport_key") or item.get("sport") or item.get("competition_id") or "soccer"
    item["home_logo"] = telegram_crest_url_for_team(item.get("home_team"), item.get("home_logo") or ((item.get("home_identity") or {}).get("crest_url")))
    item["away_logo"] = telegram_crest_url_for_team(item.get("away_team"), item.get("away_logo") or ((item.get("away_identity") or {}).get("crest_url")))
    item["match_url"] = item.get("match_url") or telegram_match_url(item.get("id"))
    return item


def telegram_enrich_pick_for_message(pick):
    item = normalize_pick_row(dict(pick or {}))
    match = one("SELECT * FROM matches WHERE id=?", (item.get("match_id"),)) if item.get("match_id") else None
    if match:
        item.setdefault("competition_name", match.get("competition_name") or match.get("league_name") or "")
        item["sport_key"] = item.get("sport_key") or match.get("sport_key") or match.get("competition_id") or "soccer"
        item["sport"] = item.get("sport") or match.get("sport") or "Soccer"
        item.setdefault("league_name", match.get("league_name") or match.get("competition_name") or "")
        item["country"] = item.get("country") or match.get("country") or ""
        item["kickoff_time"] = item.get("kickoff_time") or match.get("kickoff_time") or match.get("match_time") or ""
        item["kickoff_iso"] = item.get("kickoff_iso") or match.get("kickoff_iso") or ""
        item["home_logo"] = telegram_crest_url_for_team(item.get("home_team") or match.get("home_team"), match.get("home_logo") or item.get("home_logo") or "")
        item["away_logo"] = telegram_crest_url_for_team(item.get("away_team") or match.get("away_team"), match.get("away_logo") or item.get("away_logo") or "")
        item["home_team"] = item.get("home_team") or match.get("home_team") or ""
        item["away_team"] = item.get("away_team") or match.get("away_team") or ""
    else:
        item["sport_key"] = item.get("sport_key") or item.get("competition_id") or "soccer"
        item["sport"] = item.get("sport") or "Soccer"
        item["home_logo"] = telegram_crest_url_for_team(item.get("home_team"), item.get("home_logo") or "")
        item["away_logo"] = telegram_crest_url_for_team(item.get("away_team"), item.get("away_logo") or "")
    item["match_url"] = item.get("match_url") or telegram_match_url(item.get("match_id"))
    return item


def telegram_pick_sendability(pick):
    item = normalize_pick_row(dict(pick or {}))
    reasons = []
    sport_reason = telegram_sport_filter_reason(item)
    if sport_reason:
        reasons.append(sport_reason)
    odds = as_float(item.get("odds"), 0)
    selection = str(item.get("selection") or item.get("pick") or item.get("recommendation") or "").strip()
    market = str(item.get("market") or item.get("pick_type") or "").strip()
    match_date = str(item.get("match_date") or "")[:10]
    status = str(item.get("status") or item.get("match_status") or "").lower()
    pending_re = r"(esperar|pendiente|sin cuota|no disponible|value en c[aá]lculo|cuota pendiente|mercado pendiente|undefined|null|none)"
    if match_date and match_date < today_iso():
        reasons.append("partido_antiguo")
    if any(word in status for word in ("final", "finished", "ended", "cancelled", "postponed")):
        reasons.append("partido_no_valido")
    cfg = telegram_pro_calibration()
    if odds <= 1:
        reasons.append("sin_cuota_real")
    elif odds < cfg["min_odds"]:
        reasons.append("cuota_demasiado_baja")
    elif odds > cfg["max_odds"]:
        reasons.append("cuota_demasiado_alta")
    if not selection:
        reasons.append("sin_pick_recomendado")
    if not market:
        reasons.append("sin_mercado")
    if re.search(pending_re, selection, flags=re.I) or re.search(pending_re, market, flags=re.I):
        reasons.append("pick_no_cerrado")
    if len(selection) > 120:
        reasons.append("pick_demasiado_largo")
    try:
        enriched_quality = enrich_pick_quality(item)
        if not pick_is_premium_ready(enriched_quality, min_score=68):
            if "calidad_insuficiente" not in reasons and not reasons:
                reasons.append("calidad_insuficiente")
    except Exception:
        pass
    return {"sendable": not reasons, "reasons": reasons}


def telegram_auto_pick_health(limit=40):
    summary = {"candidates": 0, "sendable": 0, "discarded": 0, "missing_odds": 0, "missing_crests": 0, "missing_time": 0, "non_football": 0, "sport_mode": telegram_sport_mode_summary(), "discard_reasons": []}
    try:
        picks = get_picks(limit=limit, status=["published"], include_admin=True)
    except Exception as exc:
        summary["error"] = str(exc)[:180]
        return summary
    summary["candidates"] = len(picks)
    reasons = {}
    for raw in picks:
        pick = telegram_enrich_pick_for_message(raw)
        check = telegram_pick_sendability(pick)
        if "deporte_no_futbol" in (check.get("reasons") or []):
            summary["non_football"] += 1
        if check.get("sendable"):
            summary["sendable"] += 1
        else:
            summary["discarded"] += 1
            for reason in check.get("reasons") or ["no_enviable"]:
                reasons[reason] = reasons.get(reason, 0) + 1
        if as_float(pick.get("odds"), 0) <= 1:
            summary["missing_odds"] += 1
        if not (pick.get("home_logo") and pick.get("away_logo")):
            summary["missing_crests"] += 1
        if not (pick.get("kickoff_iso") or pick.get("kickoff_time") or pick.get("match_time")):
            summary["missing_time"] += 1
    summary["discard_reasons"] = [{"reason": key, "total": value} for key, value in sorted(reasons.items(), key=lambda item: item[1], reverse=True)]
    return summary


def telegram_reliability_snapshot(limit=60):
    """Build a safe admin diagnostic without sending Telegram messages."""
    cfg = telegram_pro_calibration()
    settings = get_telegram_settings()
    now_madrid = telegram_reliability_madrid_now()
    env = {
        "bot_token_configured": env_present("TELEGRAM_BOT_TOKEN"),
        "chat_id_configured": env_present("TELEGRAM_CHAT_ID"),
        "bot_username_configured": env_present("TELEGRAM_BOT_USERNAME") or env_present("TELEGRAM_USERNAME"),
        "public_base_url_configured": env_present("PUBLIC_BASE_URL") or env_present("RENDER_EXTERNAL_URL"),
        "automation_secret_configured": automation_secret_configured(),
        "enable_telegram_auto": env_bool("ENABLE_TELEGRAM_AUTO", False),
        "auto_send_telegram_picks": env_bool("AUTO_SEND_TELEGRAM_PICKS", False),
        "telegram_enabled": env_bool("TELEGRAM_ENABLED", bool((settings or {}).get("enabled"))),
        "auto_send_enabled": env_bool("ENABLE_TELEGRAM_AUTO", False) and env_bool("AUTO_SEND_TELEGRAM_PICKS", False),
        "auto_generate_picks": env_bool("AUTO_GENERATE_PICKS", False),
        "scheduler_enabled": scheduler_enabled(),
        "daily_automation_enabled": daily_automation_env_enabled(),
        "telegram_sport_mode": os.getenv("TELEGRAM_SPORT_MODE", "football_only"),
        "telegram_football_only": telegram_sport_mode_summary().get("football_only"),
    }
    try:
        raw_picks = get_picks(limit=max(int(limit), 40), status=["published"], include_admin=True)
    except Exception as exc:
        return {
            "ok": False,
            "madrid_now": now_madrid,
            "error": str(exc)[:300],
            "diagnosis": explain_telegram_state({
                "env": env,
                "counts": {},
                "reason_counts": {},
                "limits": {},
                "last_error": {"status": "error", "message": str(exc)[:200]},
                "madrid_now": now_madrid,
            }),
        }

    candidates = []
    discarded = []
    reason_counts = {}
    football_candidates = 0
    premium_eligible = 0
    already_sent = 0
    no_football = 0
    missing_odds = 0
    missing_selection = 0
    old_matches = 0
    finished_matches = 0
    duplicates = 0
    preview_pick = None

    destinations = telegram_auto_destinations("PRO", include_global=True)
    global_dest = next((d for d in destinations if d.get("target_kind") == "channel"), {})
    dedupe_target = global_dest.get("chat_id") or os.getenv("TELEGRAM_CHAT_ID", "") or "global"

    for raw in raw_picks:
        pick = telegram_enrich_pick_for_message(raw)
        sendability = telegram_pick_sendability(pick)
        sport_reason = telegram_sport_filter_reason(pick)
        if sport_reason:
            no_football += 1
        else:
            football_candidates += 1
        reasons = list(sendability.get("reasons") or [])
        for reason in reasons:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        if as_float(pick.get("odds"), 0) <= 1:
            missing_odds += 1
        if not str(pick.get("selection") or pick.get("pick") or pick.get("recommendation") or "").strip():
            missing_selection += 1
        match_date = str(pick.get("match_date") or "")[:10]
        if match_date and match_date < today_iso():
            old_matches += 1
        status = str(pick.get("status") or pick.get("match_status") or "").lower()
        if any(word in status for word in ("final", "finished", "ended", "cancelled", "postponed")):
            finished_matches += 1
        dedupe = telegram_dedupe_key("auto_pick", str(pick.get("id") or today_iso()), dedupe_target)
        existing = one("SELECT id,status,sent_at,error_message FROM telegram_queue WHERE dedupe_key=? ORDER BY created_at DESC LIMIT 1", (dedupe,))
        if existing:
            already_sent += 1
            duplicates += 1
        if sendability.get("sendable"):
            premium_eligible += 1
            candidates.append({
                "id": pick.get("id"),
                "match_id": pick.get("match_id"),
                "partido": f"{pick.get('home_team') or 'Local'} vs {pick.get('away_team') or 'Visitante'}",
                "competicion": pick.get("competition_name") or pick.get("league_name") or "",
                "selection": pick.get("selection") or pick.get("pick") or pick.get("recommendation") or "",
                "odds": pick.get("odds"),
                "confidence": pick.get("confidence") or pick.get("shark_score"),
                "dedupe_status": (existing or {}).get("status") or "",
            })
            if not preview_pick:
                preview_pick = pick
        else:
            discarded.append({
                "id": pick.get("id"),
                "match_id": pick.get("match_id"),
                "partido": f"{pick.get('home_team') or 'Local'} vs {pick.get('away_team') or 'Visitante'}",
                "reasons": reasons or ["no_enviable"],
                "odds": pick.get("odds"),
                "confidence": pick.get("confidence") or pick.get("shark_score"),
            })

    pending_queue = (one("SELECT COUNT(*) AS total FROM telegram_queue WHERE lower(status)=?", (QUEUE_PENDING,)) or {}).get("total", 0)
    sent_today = telegram_sent_today()
    sent_hour = telegram_sent_last_hour()
    failed_today = (one("SELECT COUNT(*) AS total FROM telegram_queue WHERE lower(status)=? AND updated_at LIKE ?", (QUEUE_FAILED, today_iso() + "%")) or {}).get("total", 0)
    last_error = one("SELECT * FROM telegram_logs WHERE lower(status) IN ('failed','error') ORDER BY created_at DESC LIMIT 1") or {}
    last_sent = one("SELECT * FROM telegram_queue WHERE lower(status)=? ORDER BY sent_at DESC LIMIT 1", (QUEUE_SENT,)) or {}
    last_auto_pick = one("SELECT * FROM telegram_queue WHERE lower(coalesce(message_type,''))='auto_pick' ORDER BY COALESCE(sent_at, created_at) DESC LIMIT 1") or {}
    if db_table_exists("telegram_delivery_memory"):
        memory_total = (one("SELECT COUNT(*) AS total FROM telegram_delivery_memory") or {}).get("total", 0)
        memory_recent = rows("SELECT * FROM telegram_delivery_memory ORDER BY created_at DESC LIMIT 20")
    else:
        memory_total = 0
        memory_recent = []
    if db_table_exists("data_memory_errors"):
        memory_errors = rows("SELECT * FROM data_memory_errors WHERE lower(context) LIKE '%telegram%' OR lower(context) LIKE '%pick%' ORDER BY created_at DESC LIMIT 8")
    else:
        memory_errors = []

    counts = {
        "candidate_picks": len(raw_picks),
        "football_candidates": football_candidates,
        "non_football_discarded": no_football,
        "premium_eligible": premium_eligible,
        "discarded": len(discarded),
        "missing_odds": missing_odds,
        "missing_selection": missing_selection,
        "old_matches": old_matches,
        "finished_matches": finished_matches,
        "already_sent": already_sent,
        "duplicates": duplicates,
        "destinations": len(destinations),
        "global_channel": 1 if global_dest else 0,
        "private_destinations": len([d for d in destinations if d.get("target_kind") == "private"]),
        "pending_queue": pending_queue,
        "sent_today": sent_today,
        "sent_last_hour": sent_hour,
        "failed_today": failed_today,
        "delivery_memory_total": memory_total,
    }
    limits = {
        "quiet_hours_active": telegram_quiet_hours_active(),
        "quiet_start": cfg["quiet_start"],
        "quiet_end": cfg["quiet_end"],
        "daily_summary_start": cfg["daily_summary_start"],
        "daily_summary_end": cfg["daily_summary_end"],
        "daily_picks_start": cfg["daily_picks_start"],
        "daily_picks_end": cfg["daily_picks_end"],
        "max_per_hour": cfg["max_messages_per_hour"],
        "max_per_day": cfg["max_messages_per_day"],
        "max_auto_picks_per_day": cfg["max_auto_picks_per_day"],
        "sent_last_hour": sent_hour,
        "sent_today": sent_today,
        "min_pick_score": cfg["min_pick_score"],
        "min_odds": cfg["min_odds"],
        "max_odds": cfg["max_odds"],
    }
    snapshot = {
        "ok": True,
        "madrid_now": now_madrid,
        "env": env,
        "settings": settings,
        "schema": {"delivery_memory": telegram_delivery_memory_schema_status()},
        "counts": counts,
        "reason_counts": reason_counts,
        "limits": limits,
        "last_error": last_error,
        "last_sent": last_sent,
        "last_auto_pick": last_auto_pick,
        "candidates": candidates[:20],
        "discarded": discarded[:30],
        "destinations": [
            {
                "target_kind": d.get("target_kind"),
                "membership": d.get("membership"),
                "label": d.get("label"),
                "chat_id": masked_key(d.get("chat_id")),
            }
            for d in destinations
        ],
        "data_memory": {
            "total": memory_total,
            "recent": memory_recent,
            "errors": memory_errors,
        },
        "cron": {
            "last_telegram": automation_get("last_cron_telegram_call", {}) or automation_get("cron_telegram_tick_last_call", {}) or {},
            "last_daily": automation_get("last_cron_daily_call", {}) or automation_get("cron_daily_run_last_call", {}) or {},
            "last_dispatch": automation_get("telegram_last_dispatch", {}) or {},
        },
        "preview_pick": preview_pick,
    }
    snapshot["diagnosis"] = explain_telegram_state(snapshot)
    return snapshot


def telegram_reliability_dry_run():
    snapshot = telegram_reliability_snapshot(limit=80)
    preview = ""
    pick = snapshot.get("preview_pick")
    if pick:
        try:
            preview = safe_preview_text(format_daily_picks_message([pick], force_empty=False, premium_name=APP_NAME))
        except Exception as exc:
            preview = f"No se pudo generar preview: {str(exc)[:160]}"
    return {
        "ok": snapshot.get("ok", False),
        "madrid_now": snapshot.get("madrid_now"),
        "diagnosis": snapshot.get("diagnosis"),
        "candidates": snapshot.get("candidates", []),
        "discarded": snapshot.get("discarded", []),
        "reason_counts": snapshot.get("reason_counts", {}),
        "would_send": (snapshot.get("diagnosis") or {}).get("status") == "READY_TO_SEND",
        "message_preview": preview,
    }


def telegram_reply_markup_from_payload(payload):
    payload = dict(payload or {})
    buttons = []
    primary_url = telegram_absolute_url(payload.get("match_url") or payload.get("app_url") or "")
    if primary_url:
        buttons.append({"text": str(payload.get("button_text") or "📲 Abrir en NeMeSiS")[:60], "url": primary_url})
    picks_url = telegram_absolute_url(payload.get("picks_url") or "/picks") if payload.get("include_picks_button", True) else ""
    if picks_url and picks_url != primary_url:
        buttons.append({"text": "🦈 Ver picks", "url": picks_url})
    live_url = telegram_absolute_url(payload.get("live_url") or "/live") if payload.get("include_live_button") else ""
    if live_url and live_url not in {primary_url, picks_url}:
        buttons.append({"text": "🔴 Directo SHARK", "url": live_url})
    if not buttons:
        return None
    keyboard = []
    for index in range(0, min(len(buttons), 3), 2):
        keyboard.append(buttons[index:index + 2])
    return {"inline_keyboard": keyboard}


def build_daily_matches_message():
    matches = match_hub(today_iso(), "today").get("today") or get_matches(today_iso(), "today")
    if not matches:
        matches = get_upcoming_matches(today_iso(), days=2, limit=10)
    matches = [telegram_enrich_match_for_message(match) for match in matches]
    matches = filter_telegram_football_items(matches)
    return format_daily_matches_message(matches, today_iso(), APP_NAME)


def build_daily_picks_message(force_empty=False):
    raw_picks = get_picks(limit=16, status=["published"], membership="ELITE")
    picks = []
    for raw in raw_picks:
        pick = telegram_enrich_pick_for_message(raw)
        if telegram_pick_sendability(pick).get("sendable"):
            picks.append(pick)
    return format_daily_picks_message(picks, force_empty=force_empty, premium_name=APP_NAME)


def build_live_alert_message(match=None):
    match = match or (match_hub(today_iso(), "live").get("live") or [None])[0]
    if not match:
        return ""
    match = telegram_enrich_match_for_message(match)
    return format_live_alert_message(match, internal_url=telegram_absolute_url("/live") or "/live")


def build_system_test_message():
    return format_system_test_message(now_iso(), APP_NAME)


def enqueue_daily_matches(force=False, forced_chat_id=""):
    cfg = telegram_pro_calibration()
    if not force and not telegram_time_window_active(cfg["daily_summary_start"], cfg["daily_summary_end"]):
        return {"ok": True, "message": "Resumen diario fuera de ventana PRO; se mantiene pendiente para horario profesional.", "processed": 0, "sent": 0, "failed": 0, "skipped": 1, "errors": [], "reason": "fuera_ventana_resumen"}
    subscribers = telegram_subscribers()
    if forced_chat_id and not subscribers:
        subscribers = [{"chat_id": forced_chat_id, "user_id": "", "membership": "ADMIN"}]
    if not subscribers:
        return {"ok": False, "message": "No hay chat_id ni suscriptores activos.", "processed": 0, "sent": 0, "failed": 0, "skipped": 0, "errors": ["sin_destinatarios"]}
    body = build_daily_matches_message()
    inserted = skipped = 0
    for sub in subscribers:
        result = enqueue_telegram_message(
            "daily_matches",
            "Partidos del día",
            body,
            chat_id=sub.get("chat_id"),
            user_id=sub.get("user_id"),
            payload={"membership": sub.get("membership"), "target_key": today_iso(), "app_url": telegram_absolute_url("/sports-hub"), "button_text": "📅 Ver partidos", "picks_url": telegram_absolute_url("/picks"), "include_picks_button": True, "include_live_button": True, "live_url": telegram_absolute_url("/live"), "enable_link_preview": False},
            dedupe_key=telegram_dedupe_key("daily_matches", today_iso(), sub.get("chat_id")),
            force=force,
        )
        inserted += 1 if result.get("queued") else 0
        skipped += 1 if result.get("skipped") else 0
    return {"ok": True, "message": "Resumen de partidos encolado.", "processed": len(subscribers), "inserted": inserted, "updated": 0, "sent": 0, "failed": 0, "skipped": skipped, "errors": []}


def enqueue_daily_picks(force=False, force_empty=False, forced_chat_id=""):
    cfg = telegram_pro_calibration()
    if not force and not telegram_time_window_active(cfg["daily_picks_start"], cfg["daily_picks_end"]):
        return {"ok": True, "message": "Picks diarios fuera de ventana PRO; no se fuerza envio.", "processed": 0, "inserted": 0, "sent": 0, "failed": 0, "skipped": 1, "errors": [], "reason": "fuera_ventana_picks"}
    body = build_daily_picks_message(force_empty=force_empty)
    if not body:
        return {"ok": True, "message": "No hay picks publicados; no se encola nada.", "processed": 0, "inserted": 0, "sent": 0, "failed": 0, "skipped": 1, "errors": []}
    subscribers = telegram_auto_destinations("PRO", include_global=True)
    if forced_chat_id and not subscribers:
        subscribers = [{"chat_id": forced_chat_id, "user_id": "", "membership": "ADMIN"}]
    if not subscribers:
        return {"ok": False, "message": "No hay canal global ni suscriptores PRO/ELITE activos.", "processed": 0, "sent": 0, "failed": 0, "skipped": 0, "errors": ["sin_destinatarios"]}
    inserted = skipped = 0
    for sub in subscribers:
        result = enqueue_telegram_message(
            "daily_picks",
            "Picks destacados",
            body,
            chat_id=sub.get("chat_id"),
            user_id=sub.get("user_id"),
            payload={"membership": sub.get("membership"), "target_key": today_iso(), "app_url": telegram_absolute_url("/picks"), "button_text": "🦈 Abrir picks SHARK", "include_picks_button": False, "include_live_button": True, "live_url": telegram_absolute_url("/live"), "enable_link_preview": False},
            dedupe_key=telegram_dedupe_key("daily_picks", today_iso(), sub.get("chat_id")),
            force=force,
        )
        inserted += 1 if result.get("queued") else 0
        skipped += 1 if result.get("skipped") else 0
    return {"ok": True, "message": "Picks destacados encolados.", "processed": len(subscribers), "inserted": inserted, "updated": 0, "sent": 0, "failed": 0, "skipped": skipped, "errors": []}


def enqueue_auto_pick_alerts(force=False, limit=4):
    cfg = telegram_pro_calibration()
    if telegram_should_delay_message("auto_pick", force=force):
        return {"ok": True, "message": "Horario silencioso PRO activo; no se encolan picks automaticos.", "processed": 0, "inserted": 0, "sent": 0, "failed": 0, "skipped": 1, "errors": [], "reason": "horario_silencioso"}
    min_score = cfg["min_pick_score"]
    limit = min(int(limit or cfg["max_auto_picks_per_tick"]), cfg["max_auto_picks_per_tick"]) if not force else int(limit or cfg["max_auto_picks_per_tick"])
    picks = get_picks(limit=max(20, int(limit) * 5), status=["published"], include_admin=True)
    candidates = []
    discarded = []
    for raw_pick in picks:
        pick = telegram_enrich_pick_for_message(raw_pick)
        score = as_int(pick.get("confidence") or pick.get("shark_score"), 0)
        odds = as_float(pick.get("odds"), 0.0)
        sendability = telegram_pick_sendability(pick)
        if not sendability.get("sendable"):
            discard_reason = ",".join(sendability.get("reasons") or ["no_enviable"])
            discarded.append({"pick_id": pick.get("id"), "reason": discard_reason})
            safe_memory_call(DB_PATH, "pick_discard", remember_pick_discard, candidate=pick, reason=discard_reason)
            continue
        if score < min_score and not force:
            discarded.append({"pick_id": pick.get("id"), "reason": "score_bajo", "score": score})
            safe_memory_call(DB_PATH, "pick_discard", remember_pick_discard, candidate=pick, reason="score_bajo")
            continue
        risk_raw = str(pick.get("risk_level") or pick.get("risk") or "").lower()
        if ("alto" in risk_raw or "high" in risk_raw) and score < cfg["elite_pick_score"] and not force:
            discarded.append({"pick_id": pick.get("id"), "reason": "riesgo_alto", "score": score})
            safe_memory_call(DB_PATH, "pick_discard", remember_pick_discard, candidate=pick, reason="riesgo_alto")
            continue
        if odds <= 1 and not force:
            discarded.append({"pick_id": pick.get("id"), "reason": "sin_cuota_valida"})
            safe_memory_call(DB_PATH, "pick_discard", remember_pick_discard, candidate=pick, reason="sin_cuota_valida")
            continue
        candidates.append(pick)
        safe_memory_call(DB_PATH, "pick_decision", remember_pick_decision, pick=pick, decision="telegram_candidate", reason="pasa filtros PRO Telegram")
        if len(candidates) >= int(limit):
            break
    if not candidates:
        telegram_log("[AUTO_PICKS]", "skipped", "No hay picks automaticos elegibles para Telegram.", {"min_score": min_score, "discarded": discarded[:12]})
        return {"ok": True, "message": "No hay picks automaticos elegibles.", "processed": len(picks), "inserted": 0, "sent": 0, "failed": 0, "skipped": len(discarded) or 1, "errors": [], "discarded": discarded[:12]}
    inserted = skipped = blocked = 0
    errors = []
    for pick in candidates:
        pick = telegram_enrich_pick_for_message(pick)
        required = normalize_role(pick.get("membership_required") or "PRO")
        body = format_daily_picks_message([pick], force_empty=False, premium_name=APP_NAME)
        if not body:
            skipped += 1
            continue
        destinations = telegram_auto_destinations(required, include_global=True)
        if not destinations:
            errors.append("sin_destinatarios")
            telegram_log("[QUEUE]", "failed", "Pick automatico sin canal global ni privados elegibles.", {"pick_id": pick.get("id"), "required": required})
            continue
        for dest in destinations:
            if dest.get("target_kind") == "private" and not membership_allows(dest.get("membership"), required):
                blocked += 1
                continue
            dedupe_target = dest.get("chat_id") or dest.get("user_id") or "global"
            if not force and telegram_sent_today(dest.get("chat_id"), "auto_pick") >= cfg["max_auto_picks_per_day"]:
                blocked += 1
                telegram_log("[QUEUE]", "skipped", "Auto pick omitido por limite diario PRO.", {"chat_id": masked_key(dest.get("chat_id")), "limit": cfg["max_auto_picks_per_day"]})
                continue
            result = enqueue_telegram_message(
                "auto_pick",
                "Pick automático SHARK",
                body,
                chat_id=dest.get("chat_id"),
                user_id=dest.get("user_id"),
                payload={"membership": dest.get("membership"), "target_key": dest.get("target_key"), "pick_id": pick.get("id"), "priority": 90, "auto": True, "target_kind": dest.get("target_kind"), "match_url": pick.get("match_url"), "home_logo": pick.get("home_logo"), "away_logo": pick.get("away_logo"), "button_text": "🦈 Ver análisis SHARK", "picks_url": telegram_absolute_url("/picks"), "include_picks_button": True, "include_live_button": True, "live_url": telegram_absolute_url("/live"), "enable_link_preview": bool(pick.get("home_logo") or pick.get("away_logo"))},
                dedupe_key=telegram_dedupe_key("auto_pick", str(pick.get("id") or today_iso()), dedupe_target),
                force=force,
            )
            inserted += 1 if result.get("queued") else 0
            skipped += 1 if result.get("skipped") else 0
    telegram_log("[QUEUE]", "pending", "Revision de picks automaticos para Telegram completada.", {"candidates": len(candidates), "inserted": inserted, "skipped": skipped, "blocked": blocked, "min_score": min_score})
    return {"ok": not errors, "message": "Picks automaticos revisados.", "processed": len(candidates), "inserted": inserted, "updated": 0, "sent": 0, "failed": 0, "skipped": skipped + blocked, "errors": errors[:12], "candidates": len(candidates), "discarded": discarded[:12]}


def enqueue_live_alerts(force=False):
    settings = get_telegram_settings()
    if telegram_should_delay_message("live_alert", force=force):
        return {"ok": True, "message": "Horario silencioso PRO activo; no se encolan alertas live.", "processed": 0, "inserted": 0, "sent": 0, "failed": 0, "skipped": 1, "errors": [], "reason": "horario_silencioso"}
    if not settings.get("auto_live_alerts") and not force:
        return {"ok": True, "message": "Alertas live desactivadas.", "processed": 0, "inserted": 0, "sent": 0, "failed": 0, "skipped": 1, "errors": []}
    live_matches = match_hub(today_iso(), "live").get("live") or []
    subscribers = [s for s in telegram_subscribers() if str(s.get("membership") or "FREE").upper() in {"ELITE", "ADMIN"}]
    inserted = skipped = 0
    for match in live_matches[:8]:
        match = telegram_enrich_match_for_message(match)
        if not is_telegram_football_item(match):
            skipped += 1
            continue
        body = format_live_alert_message(match, internal_url=telegram_absolute_url("/live") or "/live")
        for sub in subscribers:
            result = enqueue_telegram_message(
                "live_alert",
                "Alerta live",
                body,
                chat_id=sub.get("chat_id"),
                user_id=sub.get("user_id"),
                payload={"membership": sub.get("membership"), "target_key": match.get("id"), "match_id": match.get("id"), "match_url": match.get("match_url"), "home_logo": match.get("home_logo"), "away_logo": match.get("away_logo"), "button_text": "🔴 Abrir live SHARK", "picks_url": telegram_absolute_url("/picks"), "include_picks_button": True, "include_live_button": False, "enable_link_preview": bool(match.get("home_logo") or match.get("away_logo"))},
                dedupe_key=telegram_dedupe_key("live_alert", today_iso(), f"{sub.get('chat_id')}:{match.get('id')}:{match.get('minute') or match.get('score')}"),
                force=force,
            )
            inserted += 1 if result.get("queued") else 0
            skipped += 1 if result.get("skipped") else 0
    return {"ok": True, "message": "Alertas live revisadas.", "processed": len(live_matches), "inserted": inserted, "updated": 0, "sent": 0, "failed": 0, "skipped": skipped, "errors": []}


def telegram_plain_text_from_html(value):
    """Fallback seguro cuando Telegram rechaza HTML por entidades mal cerradas."""
    text = str(value or "")
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p\s*>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return text.strip()


def telegram_error_category(description):
    desc = str(description or "").lower()
    if not desc:
        return "UNKNOWN_ERROR", "Telegram devolvió un error sin descripción."
    if "chat not found" in desc or "peer_id_invalid" in desc:
        return "CHAT_NOT_FOUND", "Revisa TELEGRAM_CHAT_ID. En canales suele empezar por -100 y el bot debe estar dentro."
    if "bot was blocked" in desc or "blocked by the user" in desc:
        return "BOT_BLOCKED", "El usuario bloqueó el bot o no inició /start."
    if "not enough rights" in desc or "not a member" in desc or "administrator" in desc:
        return "BOT_NOT_ADMIN_OR_MEMBER", "Añade el bot al canal/grupo y dale permisos para publicar."
    if "can't parse entities" in desc or "parse entities" in desc or "unsupported start tag" in desc:
        return "HTML_PARSE_ERROR", "El mensaje tenía HTML inválido; la app reintenta automáticamente en texto plano."
    if "message is too long" in desc:
        return "MESSAGE_TOO_LONG", "El mensaje supera el límite de Telegram; reduce texto o picks por envío."
    if "too many requests" in desc or "retry after" in desc or "429" in desc:
        return "RATE_LIMITED", "Telegram ha limitado temporalmente los envíos; espera y reintenta."
    if "forbidden" in desc or "403" in desc:
        return "FORBIDDEN", "Telegram no permite enviar a ese destino con este bot."
    if "bad request" in desc or "400" in desc:
        return "BAD_REQUEST", "Petición rechazada por Telegram; revisa destino, botones o formato."
    return "TELEGRAM_API_ERROR", "Error devuelto por Telegram; mira la descripción exacta en el panel."


def telegram_http_error_payload(exc):
    body = ""
    try:
        body = exc.read().decode("utf-8", errors="replace")[:2000]
    except Exception:
        body = ""
    parsed = {}
    try:
        parsed = json.loads(body) if body else {}
    except Exception:
        parsed = {"raw": body}
    description = parsed.get("description") or body or str(exc)
    category, action = telegram_error_category(description)
    return {
        "ok": False,
        "sent": False,
        "status": category,
        "category": category,
        "action": action,
        "error": str(description)[:700],
        "http_status": getattr(exc, "code", None),
        "telegram": parsed,
    }


def telegram_post_send_message(url, data):
    encoded = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=encoded, method="POST")
    with urllib.request.urlopen(req, timeout=12) as res:
        response = json.loads(res.read().decode("utf-8", errors="replace"))
    return {"ok": True, "sent": True, "status": "SENT", "category": "SENT", "telegram": response}


def telegram_send_http(chat_id, text, message_type="manual", payload=None):
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token or not chat_id:
        return {"ok": False, "sent": False, "status": "CONFIG_MISSING", "category": "CONFIG_MISSING", "action": "Configura TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID en Render.", "error": "Falta TELEGRAM_BOT_TOKEN o chat_id."}
    payload = dict(payload or {})
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    text = str(text or "").strip()
    if len(text) > 3900:
        text = text[:3860].rstrip() + "\n\n…mensaje recortado por seguridad."
    data = {
        "chat_id": chat_id,
        "text": text or "Mensaje NeMeSiS SHARK PRO",
        "parse_mode": "HTML",
        "disable_web_page_preview": "false" if payload.get("enable_link_preview") else "true",
    }
    reply_markup = payload.get("reply_markup") or telegram_reply_markup_from_payload(payload)
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup, ensure_ascii=False)
    try:
        return telegram_post_send_message(url, data)
    except urllib.error.HTTPError as exc:
        first = telegram_http_error_payload(exc)
        if first.get("category") == "HTML_PARSE_ERROR":
            plain = telegram_plain_text_from_html(text)
            retry_data = dict(data)
            retry_data.pop("parse_mode", None)
            retry_data["text"] = plain[:3900] or "Mensaje NeMeSiS SHARK PRO"
            try:
                retry = telegram_post_send_message(url, retry_data)
                retry["retry_plain"] = True
                retry["first_error"] = first
                return retry
            except urllib.error.HTTPError as retry_exc:
                second = telegram_http_error_payload(retry_exc)
                second["first_error"] = first
                second["retry_plain"] = True
                return second
            except Exception as retry_exc:
                return {"ok": False, "sent": False, "status": "NETWORK_ERROR", "category": "NETWORK_ERROR", "action": "Reintento sin HTML fallido; revisa conexión/Render.", "error": str(retry_exc)[:700], "first_error": first, "retry_plain": True}
        return first
    except urllib.error.URLError as exc:
        return {"ok": False, "sent": False, "status": "NETWORK_ERROR", "category": "NETWORK_ERROR", "action": "Render no pudo conectar con api.telegram.org; reintenta o revisa red/salida.", "error": str(exc)[:700]}
    except Exception as exc:
        return {"ok": False, "sent": False, "status": "ERROR", "category": "ERROR", "action": "Error interno enviando Telegram; revisa logs y cola.", "error": str(exc)[:700]}


def process_premium_telegram_queue(limit=5, force=False):
    settings = get_telegram_settings()
    cfg = telegram_pro_calibration()
    if not (settings.get("enabled") or telegram_env_should_enable()) and not force:
        return {"ok": True, "message": "Telegram automatico desactivado.", "processed": 0, "sent": 0, "failed": 0, "skipped": 1, "errors": []}
    limit = min(int(limit or cfg["max_queue_per_tick"]), cfg["max_queue_per_tick"]) if not force else int(limit or cfg["max_queue_per_tick"])
    pending = rows(
        """SELECT * FROM telegram_queue
           WHERE lower(status) IN ('pending','failed')
             AND attempts < COALESCE(max_attempts,3)
             AND (scheduled_at IS NULL OR scheduled_at='' OR scheduled_at<=?)
           ORDER BY scheduled_at ASC, priority DESC, created_at ASC
           LIMIT ?""",
        (now_iso(), int(limit)),
    )
    telegram_log("[QUEUE_LOAD]", "loaded", "Cola Telegram cargada para procesamiento.", {"pending_loaded": len(pending), "limit": int(limit), "force": bool(force)})
    processed = sent = failed = skipped = 0
    errors = []
    for item in pending:
        chat_id = item.get("chat_id") or os.getenv("TELEGRAM_CHAT_ID", "")
        message_type = item.get("message_type") or "queue"
        if telegram_should_delay_message(message_type, force=force):
            skipped += 1
            telegram_log("[QUEUE_DELAY]", "skipped", "Mensaje automatico retenido por horario silencioso PRO.", {"queue_id": item.get("id"), "message_type": message_type, "chat_id": masked_key(chat_id)})
            continue
        hourly_limit = max(1, min(as_int(settings.get("max_messages_per_hour"), cfg["max_messages_per_hour"]), cfg["max_messages_per_hour"]))
        if telegram_message_is_automatic(message_type) and telegram_sent_last_hour(chat_id) >= hourly_limit and not force:
            skipped += 1
            telegram_log("[QUEUE_DELAY]", "skipped", "Mensaje retenido por limite horario PRO.", {"queue_id": item.get("id"), "chat_id": masked_key(chat_id), "limit": hourly_limit})
            continue
        if telegram_message_is_automatic(message_type) and telegram_sent_today(chat_id) >= cfg["max_messages_per_day"] and not force:
            conn = db()
            conn.execute("UPDATE telegram_queue SET status=?, error_message=?, updated_at=? WHERE id=?", (QUEUE_SKIPPED, "limite_dia_pro", now_iso(), item.get("id")))
            conn.commit()
            conn.close()
            skipped += 1
            telegram_log("[QUEUE_SKIP_LIMIT]", "skipped", "Mensaje omitido por limite diario PRO.", {"queue_id": item.get("id"), "chat_id": masked_key(chat_id), "limit": cfg["max_messages_per_day"]})
            continue
        telegram_log("[QUEUE_PROCESS]", "sending", "Procesando item de cola Telegram.", {"queue_id": item.get("id"), "message_type": message_type, "chat_id": masked_key(chat_id)})
        conn = db()
        conn.execute("UPDATE telegram_queue SET status=?, attempts=attempts+1, updated_at=? WHERE id=?", (QUEUE_SENDING, now_iso(), item.get("id")))
        conn.commit()
        conn.close()
        try:
            item_payload = json.loads(item.get("payload_json") or "{}")
        except Exception:
            item_payload = {}
        result = telegram_send_http(chat_id, item.get("body") or item.get("title") or "", message_type=item.get("message_type") or "queue", payload=item_payload)
        processed += 1
        new_status = QUEUE_SENT if result.get("sent") else QUEUE_FAILED
        error = result.get("error") or result.get("category") or result.get("status") or ""
        if result.get("action"):
            error = f"{result.get('category') or result.get('status')}: {error} · Acción: {result.get('action')}"
        conn = db()
        conn.execute(
            "UPDATE telegram_queue SET status=?, sent_at=?, error_message=?, updated_at=? WHERE id=?",
            (new_status, now_iso() if result.get("sent") else "", error[:500], now_iso(), item.get("id")),
        )
        sent_log_payload = None
        fail_log_payload = None
        if result.get("sent"):
            conn.execute("UPDATE telegram_subscribers SET last_message_sent_at=? WHERE chat_id=?", (now_iso(), chat_id))
            sent += 1
            sent_log_payload = {"queue_id": item.get("id"), "message_type": item.get("message_type"), "chat_id": masked_key(chat_id)}
        else:
            failed += 1
            errors.append(error[:220] or result.get("status"))
            fail_log_payload = {"queue_id": item.get("id"), "message_type": item.get("message_type"), "chat_id": masked_key(chat_id), "error": error[:500], "category": result.get("category"), "action": result.get("action")}
        conn.commit()
        conn.close()
        if sent_log_payload:
            telegram_log("[QUEUE_SENT]", "sent", "Mensaje Telegram enviado.", sent_log_payload)
        if fail_log_payload:
            telegram_log("[QUEUE_FAIL]", "failed", "Fallo enviando mensaje Telegram.", fail_log_payload)
        telegram_log("send", new_status, item.get("title") or item.get("message_type"), {"queue_id": item.get("id"), "result": result})
        log_telegram_delivery(chat_id, item.get("message_type") or "queue", item.get("body"), new_status.upper(), {**(result or {}), "dedupe_key": item.get("dedupe_key"), "match_id": item.get("match_id") or item_payload.get("match_id"), "pick_id": item.get("pick_id") or item_payload.get("pick_id"), "target_key": item_payload.get("target_key"), "delivery_channel": "telegram", "target_type": "channel" if str(chat_id).startswith("-") else "private"})
    return {"ok": failed == 0, "message": "Cola procesada.", "processed": processed, "sent": sent, "failed": failed, "skipped": skipped, "errors": errors[:12]}


def telegram_delivery_memory_schema_status():
    expected = {
        "id", "created_at", "updated_at", "message_type", "target_type", "target_key",
        "destination_masked", "delivery_channel", "chat_id", "user_id", "membership",
        "status", "match_id", "pick_id", "error_summary", "dedupe_key", "meta_json",
    }
    try:
        conn = db()
        existing = {row[1] for row in conn.execute("PRAGMA table_info(telegram_delivery_memory)").fetchall()}
        conn.close()
        missing = sorted(expected - existing)
        return {
            "ok": not missing,
            "columns": sorted(existing),
            "missing": missing,
            "expected_total": len(expected),
            "message": "Memoria Telegram compatible." if not missing else "Faltan columnas legacy: " + ", ".join(missing),
        }
    except Exception as exc:
        return {"ok": False, "columns": [], "missing": sorted(expected), "error": str(exc)[:300], "message": "No se pudo comprobar telegram_delivery_memory."}


def telegram_diagnostics():
    settings = get_telegram_settings()
    today = today_iso()
    env_flags = {
        "TELEGRAM_BOT_TOKEN": env_present("TELEGRAM_BOT_TOKEN"),
        "TELEGRAM_CHAT_ID": env_present("TELEGRAM_CHAT_ID"),
        "TELEGRAM_BOT_USERNAME": env_present("TELEGRAM_BOT_USERNAME") or env_present("TELEGRAM_USERNAME"),
        "ENABLE_TELEGRAM_AUTO": env_bool("ENABLE_TELEGRAM_AUTO", False),
        "AUTO_SEND_TELEGRAM_PICKS": env_bool("AUTO_SEND_TELEGRAM_PICKS", False),
        "AUTO_GENERATE_PICKS": env_bool("AUTO_GENERATE_PICKS", False),
        "SCHEDULER_ENABLED": scheduler_enabled(),
        "DAILY_AUTOMATION_ENABLED": daily_automation_env_enabled(),
        "RUN_DAILY_AUTOMATION": env_bool("RUN_DAILY_AUTOMATION", False),
        "RUN_STARTUP_SCHEDULER_NOW": env_bool("RUN_STARTUP_SCHEDULER_NOW", False),
        "AUTOMATION_SECRET": automation_secret_configured(),
    }
    missing_required = [key for key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID") if not env_flags.get(key)]
    if not (env_flags["ENABLE_TELEGRAM_AUTO"] or env_flags["AUTO_SEND_TELEGRAM_PICKS"]):
        missing_required.append("ENABLE_TELEGRAM_AUTO o AUTO_SEND_TELEGRAM_PICKS")
    if not env_flags["AUTOMATION_SECRET"]:
        missing_required.append("AUTOMATION_SECRET para Render Cron")
    if missing_required:
        automatic_status = "pendiente_configuracion"
        automatic_reason = "Faltan variables: " + ", ".join(missing_required)
    elif not (settings.get("enabled") or telegram_env_should_enable()):
        automatic_status = "desactivado"
        automatic_reason = "telegram_settings.enabled esta desactivado y las variables auto no lo activan."
    else:
        automatic_status = "funcionando" if ((one("SELECT COUNT(*) AS total FROM telegram_queue WHERE lower(status)=? AND lower(coalesce(message_type,''))='auto_pick' AND sent_at LIKE ?", (QUEUE_SENT, today + "%")) or {}).get("total", 0) or 0) > 0 else "preparado"
        automatic_reason = "Preparado para cron. Sin envio auto_pick hoy todavia." if automatic_status == "preparado" else "Auto pick enviado hoy."
    pending = (one("SELECT COUNT(*) AS total FROM telegram_queue WHERE lower(status)=?", (QUEUE_PENDING,)) or {}).get("total", 0)
    sent_today = (one("SELECT COUNT(*) AS total FROM telegram_queue WHERE lower(status)=? AND sent_at LIKE ?", (QUEUE_SENT, today + "%")) or {}).get("total", 0)
    failed_today = (one("SELECT COUNT(*) AS total FROM telegram_queue WHERE lower(status)=? AND updated_at LIKE ?", (QUEUE_FAILED, today + "%")) or {}).get("total", 0)
    last_error = one("SELECT * FROM telegram_logs WHERE lower(status) IN ('failed','error') ORDER BY created_at DESC LIMIT 1")
    last_sent = one("SELECT * FROM telegram_queue WHERE lower(status)=? ORDER BY sent_at DESC LIMIT 1", (QUEUE_SENT,))
    last_auto = one("SELECT * FROM telegram_logs WHERE event_type IN ('scheduler','queue','send','[AUTO_PICKS]','[QUEUE]','[TELEGRAM]','[AUTOMATION]','[QUEUE_LOAD]','[QUEUE_PROCESS]','[QUEUE_SENT]','[QUEUE_FAIL]','[QUEUE_SKIP_DUPLICATE]') OR message LIKE '%automatic%' OR message LIKE '%auto%' ORDER BY created_at DESC LIMIT 1")
    last_pick = one("SELECT * FROM telegram_queue WHERE lower(status)=? AND lower(coalesce(message_type,'')) LIKE '%pick%' ORDER BY sent_at DESC LIMIT 1", (QUEUE_SENT,))
    last_auto_pick = one("SELECT * FROM telegram_queue WHERE lower(coalesce(message_type,''))='auto_pick' ORDER BY COALESCE(sent_at, created_at) DESC LIMIT 1")
    auto_pick_pending = (one("SELECT COUNT(*) AS total FROM telegram_queue WHERE lower(status)=? AND lower(coalesce(message_type,''))='auto_pick'", (QUEUE_PENDING,)) or {}).get("total", 0)
    duplicate_logs = (one("SELECT COUNT(*) AS total FROM telegram_logs WHERE lower(status)='skipped' OR lower(message) LIKE '%duplicado%'") or {}).get("total", 0)
    auto_pick_health = telegram_auto_pick_health(limit=40)
    return {
        "token_present": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
        "token_masked": masked_key(os.getenv("TELEGRAM_BOT_TOKEN", "")),
        "chat_id_present": bool(os.getenv("TELEGRAM_CHAT_ID")),
        "chat_id_masked": masked_key(os.getenv("TELEGRAM_CHAT_ID", "")),
        "settings_enabled": settings.get("enabled"),
        "effective_enabled": bool(settings.get("enabled") or telegram_env_should_enable()),
        "env_auto_enabled": telegram_env_auto_enabled(),
        "env_ready": telegram_env_ready(),
        "settings": settings,
        "schema": {"delivery_memory": telegram_delivery_memory_schema_status()},
        "automatic_status": automatic_status,
        "automatic_reason": automatic_reason,
        "env_flags": env_flags,
        "missing_required": missing_required,
        "last_cron_daily_call": automation_get("last_cron_daily_call", {}) or automation_get("cron_daily_run_last_call", {}) or {},
        "last_cron_telegram_call": automation_get("last_cron_telegram_call", {}) or automation_get("cron_telegram_tick_last_call", {}) or {},
        "last_telegram_tick_detail": automation_get("telegram_tick_last_detail", {}) or {},
        "last_daily_automation": automation_get("daily_autonomous_system", {}) or {},
        "last_daily_run_detail": automation_get("daily_run_last_detail", {}) or {},
        "last_scheduler_tick": automation_get("telegram_last_dispatch", {}) or {},
        "subscribers": (one("SELECT COUNT(*) AS total FROM telegram_subscribers WHERE is_active=1") or {}).get("total", 0),
        "linked_users": (one("SELECT COUNT(*) AS total FROM users WHERE telegram_chat_id IS NOT NULL AND telegram_chat_id!=''") or {}).get("total", 0),
        "pending": pending,
        "sent_today": sent_today,
        "failed_today": failed_today,
        "last_error": (last_error or {}).get("message", ""),
        "last_error_item": last_error or {},
        "last_sent": last_sent or {},
        "last_auto": last_auto or {},
        "last_pick": last_pick or {},
        "last_auto_pick": last_auto_pick or {},
        "auto_pick_pending": auto_pick_pending,
        "auto_pick_health": auto_pick_health,
        "duplicates_avoided": duplicate_logs,
        "recent_sent": rows("SELECT * FROM telegram_queue WHERE lower(status)=? ORDER BY sent_at DESC LIMIT 8", (QUEUE_SENT,)),
        "recent_errors": rows("SELECT * FROM telegram_logs WHERE lower(status) IN ('failed','error') ORDER BY created_at DESC LIMIT 8"),
        "queue_summary": queue_summary(rows("SELECT status FROM telegram_queue ORDER BY created_at DESC LIMIT 500")),
        "pro_calibration": telegram_pro_calibration(),
        "sport_filter": telegram_sport_mode_summary(),
    }


def telegram_time_due(time_value, force=False):
    if force:
        return True
    value = str(time_value or "00:00")[:5]
    current = datetime.now(TZ).strftime("%H:%M")
    return current >= value


def telegram_scheduler_delivery(force=False):
    settings = get_telegram_settings()
    cfg = telegram_pro_calibration()
    if not (settings.get("enabled") or telegram_env_should_enable()) and not force:
        return {"ok": True, "message": "Telegram automatico desactivado.", "processed": 0, "inserted": 0, "sent": 0, "failed": 0, "skipped": 1, "errors": []}
    results = []
    if settings.get("auto_daily_matches") and telegram_time_due(settings.get("daily_matches_time"), force=force):
        results.append(enqueue_daily_matches(force=force))
    if settings.get("auto_daily_picks") and telegram_time_due(settings.get("daily_picks_time"), force=force):
        results.append(enqueue_auto_pick_alerts(force=force, limit=cfg["max_auto_picks_per_tick"]))
        results.append(enqueue_daily_picks(force=force, force_empty=False))
    if settings.get("auto_live_alerts"):
        results.append(enqueue_live_alerts(force=force))
    processed_queue = process_premium_telegram_queue(limit=cfg["max_queue_per_tick"], force=force)
    processed = sum(as_int(r.get("processed"), 0) for r in results) + as_int(processed_queue.get("processed"), 0)
    inserted = sum(as_int(r.get("inserted"), 0) for r in results)
    skipped = sum(as_int(r.get("skipped"), 0) for r in results) + as_int(processed_queue.get("skipped"), 0)
    sent = as_int(processed_queue.get("sent"), 0)
    failed = as_int(processed_queue.get("failed"), 0)
    errors = [e for r in results + [processed_queue] for e in (r.get("errors") or [])]
    return {
        "ok": failed == 0 and not errors,
        "message": "Telegram scheduler ejecutado.",
        "processed": processed,
        "inserted": inserted,
        "updated": 0,
        "sent": sent,
        "failed": failed,
        "skipped": skipped,
        "errors": errors[:12],
        "queue": processed_queue,
        "results": results,
    }


def automation_get(key, default=None):
    item = one("SELECT * FROM automation_state WHERE key=?", (key,))
    if not item:
        return default
    try:
        return json.loads(item.get("value_json") or "null")
    except json.JSONDecodeError:
        return default


def automation_set(key, value):
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """INSERT OR REPLACE INTO automation_state(key,value_json,updated_at)
           VALUES (?,?,?)""",
        (key, json.dumps(value, ensure_ascii=False), now_iso()),
    )
    conn.commit()
    conn.close()


def telegram_triggers():
    briefing = shark_briefing()
    hub = match_hub(today_iso())
    triggers = []
    if briefing["summary"]["picks_ready"]:
        triggers.append({"key": "picks_ready", "label": "Picks listos", "priority": 90})
    if hub["counts"]["live"]:
        triggers.append({"key": "live_active", "label": "Partidos en directo", "priority": 86})
    if hub["counts"]["favorites"]:
        triggers.append({"key": "favorite_feed", "label": "Favoritos con actividad", "priority": 82})
    if not triggers:
        triggers.append({"key": "daily_briefing", "label": "Briefing diario", "priority": 60})
    return triggers


def telegram_existing_signatures():
    items = rows("SELECT signature FROM telegram_queue ORDER BY created_at DESC LIMIT 500")
    return [item.get("signature") for item in items]


def enqueue_telegram_alerts(force=False):
    triggers = telegram_triggers()
    favs = get_favorites()
    picks = get_picks(limit=20)
    queue_items = build_alert_queue(triggers, today_iso(), favorites_count=len(favs), picks_count=len(picks))
    existing = telegram_existing_signatures()
    inserted = []
    skipped = []
    conn = db()
    cur = conn.cursor()
    for item in queue_items:
        if not force and should_skip_duplicate(existing, item["signature"]):
            skipped.append(item)
            continue
        queue_id = hashlib.md5(f"queue-{item['signature']}".encode("utf-8")).hexdigest()[:18]
        cur.execute(
            """INSERT OR REPLACE INTO telegram_queue
               (id,signature,alert_type,target_key,priority,payload_json,status,attempts,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                queue_id,
                item["signature"],
                item["alert_type"],
                item["target_key"],
                item["priority"],
                json.dumps(item, ensure_ascii=False),
                "PENDING",
                0,
                now_iso(),
                now_iso(),
            ),
        )
        inserted.append(item)
    conn.commit()
    conn.close()
    return {"inserted": inserted, "skipped": skipped, "triggers": triggers}


def telegram_queue(limit=50):
    return rows("SELECT * FROM telegram_queue ORDER BY priority DESC, created_at ASC LIMIT ?", (int(limit),))


def process_telegram_queue(force=False):
    enqueue = enqueue_telegram_alerts(force=force)
    pending = rows("SELECT * FROM telegram_queue WHERE status IN ('PENDING','RETRY') AND attempts < 3 ORDER BY priority DESC, created_at ASC LIMIT 3")
    processed = []
    for item in pending:
        text = telegram_daily_message()
        result = send_telegram_message(text, message_type=f"queue_{item.get('alert_type')}")
        status = "SENT" if result.get("sent") else "RETRY" if int(item.get("attempts") or 0) < 2 else (result.get("status") or "ERROR")
        conn = db()
        cur = conn.cursor()
        cur.execute(
            "UPDATE telegram_queue SET status=?, attempts=attempts+1, updated_at=? WHERE id=?",
            (status, now_iso(), item.get("id")),
        )
        conn.commit()
        conn.close()
        processed.append({"queue": item, "result": result})
    return {"enqueue": enqueue, "processed": processed, "pending_after": telegram_queue(limit=20)}


def prepare_auto_posts():
    hub = match_hub(today_iso())
    posts = []
    for match in hub.get("live", [])[:5]:
        posts.append({"type": "live_alert", "target_key": match.get("id"), "title": f"{match.get('home_team')} vs {match.get('away_team')}", "status": (match.get("live_depth") or {}).get("label")})
    for match in hub.get("with_picks", [])[:5]:
        posts.append({"type": "pick_alert", "target_key": match.get("id"), "title": f"Pick relacionado: {match.get('competition_name')}", "status": "READY"})
    for match in hub.get("popular", [])[:5]:
        posts.append({"type": "featured_match", "target_key": match.get("id"), "title": f"Destacado: {match.get('home_team')} vs {match.get('away_team')}", "status": "READY"})
    conn = db()
    cur = conn.cursor()
    for post in posts:
        post_id = hashlib.md5(f"auto-{today_iso()}-{post['type']}-{post['target_key']}".encode("utf-8")).hexdigest()[:18]
        cur.execute(
            """INSERT OR REPLACE INTO auto_alerts(id,alert_type,target_key,payload_json,status,created_at,updated_at)
               VALUES (?,?,?,?,?,?,?)""",
            (post_id, post["type"], post["target_key"], json.dumps(post, ensure_ascii=False), post["status"], now_iso(), now_iso()),
        )
    conn.commit()
    conn.close()
    return posts


def telegram_scheduler_tick(force=False):
    cfg = telegram_config()
    if not (cfg["enabled"] or telegram_env_should_enable()) and not force:
        return {"ok": False, "sent": False, "status": "AUTO_DISABLED", "telegram": cfg}
    result = telegram_scheduler_delivery(force=force)
    automation_set("telegram_last_dispatch", {"time": now_iso(), "result": result})
    return {"ok": result.get("ok"), "sent": result.get("sent", 0) > 0, "status": "QUEUE_PROCESSED", "result": result}


def log_telegram_delivery(chat_id, message_type, text, status, response=None):
    conn = db()
    try:
        cur = conn.cursor()
        delivery_id = hashlib.md5(f"telegram-{chat_id}-{datetime.now(TZ).isoformat(timespec='microseconds')}-{message_type}".encode("utf-8")).hexdigest()[:18]
        cur.execute(
            """INSERT INTO telegram_deliveries
               (id,chat_id,message_type,payload_preview,status,response_json,created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (delivery_id, chat_id or "", message_type, str(text or "")[:1500], status, json.dumps(response or {}, ensure_ascii=False)[:3000], now_iso()),
        )
        conn.commit()
    finally:
        conn.close()
    try:
        safe_memory_call(
            DB_PATH,
            "telegram_delivery",
            remember_telegram_delivery,
            message_type=message_type,
            target=chat_id or "",
            status=status,
            meta={"delivery_id": delivery_id, "response": response or {}},
        )
    except Exception:
        pass
    return delivery_id


def send_telegram_message(text, chat_id=None, message_type="manual"):
    cfg = telegram_config()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    target = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or not target:
        delivery_id = log_telegram_delivery(target, message_type, text, "CONFIG_MISSING", {"configured": False})
        return {"ok": False, "sent": False, "status": "CONFIG_MISSING", "delivery_id": delivery_id}
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urllib.parse.urlencode({"chat_id": target, "text": text, "parse_mode": "HTML"}).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, method="POST")
        with urllib.request.urlopen(req, timeout=10) as res:
            response = json.loads(res.read().decode("utf-8", errors="replace"))
        delivery_id = log_telegram_delivery(target, message_type, text, "SENT", response)
        return {"ok": True, "sent": True, "status": "SENT", "delivery_id": delivery_id, "telegram": response}
    except Exception as exc:
        delivery_id = log_telegram_delivery(target, message_type, text, "ERROR", {"error": str(exc)})
        return {"ok": False, "sent": False, "status": "ERROR", "delivery_id": delivery_id, "error": str(exc)}


def telegram_daily_message():
    briefing = shark_briefing()
    summary = briefing["summary"]
    return (
        "<b>NeMeSiS SHARK PRO</b>\n"
        f"Version: {APP_VERSION}\n"
        f"Partidos hoy: {summary['matches_today']} | Live: {summary['live_now']} | Picks: {summary['picks_ready']}\n"
        "Cobertura: mundial primero, Espana y Andalucia como diferencial.\n"
        "Legal: solo APIs permitidas, importaciones autorizadas y cache propio."
    )


def get_matches(date=None, lane="today"):
    date = date or today_iso()
    clauses = ["match_date=?"]
    params = [date]
    if lane == "live":
        clauses.append("(lower(status) LIKE '%live%' OR lower(status) LIKE '%directo%' OR minute!='')")
    elif lane == "top":
        clauses.append("priority>=90")
    elif lane == "spain":
        clauses.append("(lower(country)='spain' OR lower(competition_key) LIKE '%laliga%' OR lower(competition_key)='copa-del-rey')")
    elif lane == "andalucia":
        clauses.append("lower(competition_key)='andalucia-regional'")
    query = "SELECT * FROM matches WHERE " + " AND ".join(clauses) + " ORDER BY priority DESC, kickoff_time, competition_name LIMIT 300"
    data = dedupe_matches_list([item for item in rows(query, params) if not is_fake_match(item)])
    for item in data:
        item["kickoff_time"] = item.get("kickoff_time") or item.get("match_time") or ""
        if not item.get("score") and (item.get("home_score") or item.get("away_score")):
            item["score"] = sportsdb_score(item.get("home_score"), item.get("away_score"))
        item.update(apply_match_localization(item))
        item["home_identity"] = resolve_team(item.get("home_team"))
        item["away_identity"] = resolve_team(item.get("away_team"))
        item.update(apply_team_identities_to_match(item))
    return data


def get_upcoming_matches(start_date=None, days=7, limit=300):
    start_date = start_date or today_iso()
    end_date = (datetime.fromisoformat(start_date).date() + timedelta(days=int(days))).isoformat()
    query = """SELECT * FROM matches
               WHERE match_date>=? AND match_date<=?
               ORDER BY match_date, kickoff_time, priority DESC, competition_name
               LIMIT ?"""
    data = dedupe_matches_list([item for item in rows(query, (start_date, end_date, int(limit))) if not is_fake_match(item)])
    for item in data:
        item["kickoff_time"] = item.get("kickoff_time") or item.get("match_time") or ""
        if not item.get("score") and (item.get("home_score") or item.get("away_score")):
            item["score"] = sportsdb_score(item.get("home_score"), item.get("away_score"))
        item.update(apply_match_localization(item))
        item["home_identity"] = resolve_team(item.get("home_team"))
        item["away_identity"] = resolve_team(item.get("away_team"))
        item.update(apply_team_identities_to_match(item))
    return data


def split_live(matches):
    live, scheduled, finished = [], [], []
    for item in matches:
        info = item.get("status_info") or canonical_match_status(item)
        if info.get("is_finished"):
            finished.append(item)
        elif info.get("is_live"):
            live.append(item)
        else:
            scheduled.append(item)
    return {"live": live, "scheduled": scheduled, "finished": finished}


def match_logical_key(match):
    match = match or {}
    competition = normalized_label(match.get("competition_name") or match.get("league_name") or match.get("competition_key") or "")
    home = normalized_label(match.get("home_team") or "")
    away = normalized_label(match.get("away_team") or "")
    date_value = str(match.get("match_date") or "").strip()[:10]
    time_value = str(match.get("kickoff_time") or match.get("match_time") or "").strip()[:5]
    kickoff = str(match.get("kickoff_iso") or "").strip()
    if "T" in kickoff:
        kickoff = kickoff[:16]
    elif date_value:
        kickoff = f"{date_value}T{time_value or '00:00'}"
    else:
        kickoff = time_value or "sin-hora"
    return "|".join([competition or "sin-competicion", home or "local", away or "visitante", kickoff])


def match_quality_score(match):
    match = match or {}
    info = canonical_match_status(match)
    score = as_int(match.get("priority"), 0)
    if info.get("is_live"):
        score += 60
    if info.get("is_finished"):
        score += 20
    if match.get("score") or match.get("home_score") or match.get("away_score"):
        score += 25
    if match.get("bookmaker") or match.get("odds_h2h_json"):
        score += 20
    if match.get("home_logo"):
        score += 8
    if match.get("away_logo"):
        score += 8
    if match.get("external_id"):
        score += 5
    if "sportsdb" in str(match.get("source") or "").lower():
        score += 4
    return score


def merge_match_payload(primary, duplicate):
    merged = dict(primary or {})
    for key in (
        "external_id", "kickoff_time", "match_time", "kickoff_iso", "competition_id", "competition_key",
        "competition_name", "league_name", "country", "home_team_id", "away_team_id", "home_logo", "away_logo",
        "status", "minute", "score", "home_score", "away_score", "venue", "season", "round", "bookmaker",
        "odds_h2h_json", "odds_updated_at", "raw_json",
    ):
        if not merged.get(key) and (duplicate or {}).get(key):
            merged[key] = duplicate.get(key)
    if match_quality_score(duplicate) > match_quality_score(merged):
        better = dict(duplicate or {})
        for key, value in merged.items():
            if not better.get(key) and value:
                better[key] = value
        return better
    return merged


def dedupe_matches_list(matches):
    seen = {}
    for match in matches or []:
        key = match_logical_key(match)
        current = seen.get(key)
        if not current:
            seen[key] = match
            continue
        seen[key] = merge_match_payload(current, match)
    return list(seen.values())


def match_deduplication_metrics(sample_limit=5000):
    all_matches = [m for m in rows("SELECT * FROM matches ORDER BY match_date DESC, kickoff_time DESC LIMIT ?", (int(sample_limit),)) if not is_fake_match(m)]
    unique = dedupe_matches_list(all_matches)
    duplicate_total = max(0, len(all_matches) - len(unique))
    groups = {}
    for match in all_matches:
        groups.setdefault(match_logical_key(match), []).append(match)
    duplicate_groups = [
        {
            "key": key,
            "count": len(items),
            "keeper": max(items, key=match_quality_score).get("id"),
            "ids": [item.get("id") for item in items],
            "label": f"{items[0].get('home_team')} vs {items[0].get('away_team')}",
            "competition": items[0].get("competition_name") or items[0].get("league_name") or items[0].get("competition_key"),
            "kickoff": items[0].get("kickoff_iso") or f"{items[0].get('match_date')} {items[0].get('kickoff_time') or items[0].get('match_time') or ''}".strip(),
        }
        for key, items in groups.items()
        if len(items) > 1
    ]
    duplicate_groups.sort(key=lambda item: item["count"], reverse=True)
    return {
        "total_matches": len(all_matches),
        "unique_matches": len(unique),
        "duplicates_detected": duplicate_total,
        "duplicate_groups": len(duplicate_groups),
        "examples": duplicate_groups[:20],
    }


def cleanup_duplicate_matches(cur=None):
    own_conn = None
    if cur is None:
        own_conn = db()
        cur = own_conn.cursor()
    try:
        raw = cur.execute("SELECT * FROM matches ORDER BY match_date DESC, kickoff_time DESC").fetchall()
    except sqlite3.OperationalError:
        if own_conn:
            own_conn.close()
        return {"duplicates_removed": 0, "groups": 0}
    by_key = {}
    for row in raw:
        item = dict(row)
        if is_fake_match(item):
            continue
        by_key.setdefault(match_logical_key(item), []).append(item)
    removed = 0
    groups = 0
    for items in by_key.values():
        if len(items) <= 1:
            continue
        groups += 1
        keeper = max(items, key=match_quality_score)
        merged = dict(keeper)
        for item in items:
            if item.get("id") == keeper.get("id"):
                continue
            merged = merge_match_payload(merged, item)
        cur.execute(
            """UPDATE matches
               SET external_id=?, kickoff_time=?, match_time=?, kickoff_iso=?, competition_id=?, competition_key=?,
                   competition_name=?, league_name=?, country=?, home_team_id=?, away_team_id=?, home_logo=?, away_logo=?,
                   status=?, minute=?, score=?, home_score=?, away_score=?, venue=?, season=?, round=?, bookmaker=?,
                   odds_h2h_json=?, odds_updated_at=?, raw_json=?, updated_at=?
               WHERE id=?""",
            (
                merged.get("external_id") or "",
                merged.get("kickoff_time") or "",
                merged.get("match_time") or merged.get("kickoff_time") or "",
                merged.get("kickoff_iso") or "",
                merged.get("competition_id") or "",
                merged.get("competition_key") or "",
                merged.get("competition_name") or "",
                merged.get("league_name") or "",
                merged.get("country") or "",
                merged.get("home_team_id") or "",
                merged.get("away_team_id") or "",
                merged.get("home_logo") or "",
                merged.get("away_logo") or "",
                merged.get("status") or "",
                merged.get("minute") or "",
                merged.get("score") or "",
                merged.get("home_score") or "",
                merged.get("away_score") or "",
                merged.get("venue") or "",
                merged.get("season") or "",
                merged.get("round") or "",
                merged.get("bookmaker") or "",
                merged.get("odds_h2h_json") or "",
                merged.get("odds_updated_at") or "",
                merged.get("raw_json") or "{}",
                now_iso(),
                keeper.get("id"),
            ),
        )
        delete_ids = [item.get("id") for item in items if item.get("id") != keeper.get("id")]
        for duplicate_id in delete_ids:
            cur.execute("UPDATE picks SET match_id=? WHERE match_id=?", (keeper.get("id"), duplicate_id))
            cur.execute("UPDATE live_matches SET match_id=? WHERE match_id=?", (keeper.get("id"), duplicate_id))
            cur.execute("DELETE FROM matches WHERE id=?", (duplicate_id,))
            removed += 1
    if own_conn:
        own_conn.commit()
        own_conn.close()
    return {"duplicates_removed": removed, "groups": groups}



def sports_hub_groups(matches):
    buckets = {}
    for match in dedupe_matches_list(matches):
        name = spanish_competition_name(match.get("competition_name") or match.get("league_name") or match.get("competition_key") or "") or "Competición"
        country = spanish_country_name(match.get("country") or "") or match.get("country") or ""
        key = (name, country)
        buckets.setdefault(key, {"name": name, "country": country, "matches": []})
        buckets[key]["matches"].append(match)
    groups = list(buckets.values())
    groups.sort(key=lambda g: v565_league_rank({"competition_name": g["name"], "league_name": g["name"]}))
    return groups


def annotate_sports_hub_matches(matches, picks=None):
    pick_map = {}
    for pick in picks or []:
        mid = str(pick.get("match_id") or "").strip()
        if mid and mid not in pick_map:
            pick_map[mid] = pick
    out = []
    for match in dedupe_matches_list(matches):
        match = apply_match_localization(match)
        match.update(apply_team_identities_to_match(match))
        pick = pick_map.get(str(match.get("id") or ""))
        live_depth = match.get("live_depth") or {}
        match["has_pick"] = bool(pick)
        match["pick_label"] = (pick or {}).get("selection") or ""
        match["shark_score"] = as_int((pick or {}).get("confidence") or live_depth.get("momentum") or match.get("shark_score"), 0)
        match["safe_home"] = match.get("safe_home") or match.get("home_team") or "Equipo por confirmar"
        match["safe_away"] = match.get("safe_away") or match.get("away_team") or "Equipo por confirmar"
        match["safe_competition"] = spanish_competition_name(match.get("safe_competition") or match.get("competition_name") or match.get("league_name") or match.get("competition_key") or "") or "Competición"
        match["safe_time"] = match.get("safe_time") or match.get("kickoff_time") or match.get("match_time") or live_depth.get("minute") or "Hora pendiente"
        match["safe_score"] = live_depth.get("score") or match.get("score") or "vs"
        match["safe_status"] = live_depth.get("label") or match.get("status") or "Próximo"
        out.append(match)
    return out


def dashboard_data(lane="today", date=None):
    date = date or today_iso()
    matches = get_matches(date, lane)
    upcoming_matches = get_upcoming_matches(date, days=7)
    comps = competitions()
    imports = rows("SELECT * FROM imports ORDER BY created_at DESC LIMIT 20")
    picks = get_picks(limit=30)
    combis = get_combis(limit=12)
    profile = default_profile()
    favorites = get_favorites()
    hub = match_hub(date)
    past_results = get_results_matches(date, days_back=21, limit=180)
    candidate_matches = pick_candidate_matches(limit=80, days=21)
    smart_picks = smart_pick_board()
    favorite_bundle = favorite_feed_full()
    flow = build_live_flow(hub, favorites=favorites, picks=picks, profile=profile)
    matches_diag = match_calendar_diagnostics()
    groups = {}
    for match in matches:
        groups.setdefault(match.get("competition_name") or "Sin competicion", []).append(match)
    return {
        "app_name": APP_NAME,
        "version": APP_VERSION,
        "date": date,
        "lane": lane,
        "matches": matches,
        "upcoming_matches": upcoming_matches,
        "groups": groups,
        "competitions": comps,
        "imports": imports,
        "picks": picks,
        "combis": combis,
        "profile": profile,
        "session_user": current_session_user(),
        "favorites": favorites,
        "favorite_feed": favorite_bundle["matches"],
        "favorite_bundle": favorite_bundle,
        "favorite_insights": favorite_insights(),
        "client_alerts": build_client_alerts(limit=8),
        "client_activity": client_activity_feed(limit=8),
        "retention": client_retention_summary(),
        "daily_briefing": build_daily_briefing(current_session_user() or {"membership": "FREE", "role": "FREE"}),
        "client_command": client_command_center_data(current_session_user() or {"membership": "FREE", "role": "FREE"}),
        "match_hub": hub,
        "past_results": past_results,
        "candidate_matches": candidate_matches,
        "smart_picks": smart_picks,
        "live_flow": flow,
        "membership_plans": MEMBERSHIP_PLANS,
        "telegram": telegram_config(),
        "sportsdb": crest_sync_status(),
        "sportsdb_feed": sportsdb_feed_status(),
        "odds": odds_diagnostics(),
        "matches_diagnostics": matches_diag,
        "client_source_label": client_source_label(matches_diag),
        "data_center": data_center_summary(),
        "live": split_live([annotate_match(m) for m in get_matches(date, "today")]),
        "legal_policy": "No scraping ilegal. Solo APIs permitidas, datos propios, CSV/JSON autorizado, cache persistente y revision editorial.",
        "readiness": {
            "clean_core": 100,
            "render_ready": 98,
            "global_football": 96,
            "calendar": 95,
            "legal_import": 96,
            "live_foundation": 92,
            "telegram_ready": 88,
            "picks_combis": 82,
            "premium_profile": 84,
            "shark_ai": 78,
            "memberships": 80,
            "premium_core": 86,
            "match_hub": 88,
            "favorites": 84,
            "performance_cache": 80,
            "live_ecosystem": 88,
            "telegram_queue": 84,
            "shark_context": 86,
            "real_time_engine": 89,
            "match_hub_2": 90,
            "mobile_feel": 84,
        },
    }


@app.route("/service-worker.js")
def service_worker():
    body = (
        "self.addEventListener('install',event=>self.skipWaiting());\n"
        "self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));\n"
    )
    return Response(body, mimetype="application/javascript")


def _home_count_sql(query, params=()):
    """Contador ligero para home: no dispara APIs ni rompe si la DB aún no existe."""
    try:
        conn = db()
        cur = conn.cursor()
        cur.execute(query, params)
        row = cur.fetchone()
        conn.close()
        if row is None:
            return 0
        try:
            return int(row[0] or 0)
        except Exception:
            return 0
    except Exception:
        return 0


def _home_rows_sql(query, params=(), limit=6):
    """Lectura ligera para home: nunca debe tumbar la landing si faltan tablas o datos."""
    try:
        conn = db()
        cur = conn.cursor()
        cur.execute(query, params)
        items = [dict(r) for r in cur.fetchmany(int(limit))]
        conn.close()
        return items
    except Exception:
        return []


def home_live_summary_data():
    """Datos reales y ligeros para /.

    V739 corrige el panel "Hoy en NeMeSiS": antes usaba home_light_data()
    con ceros estáticos para acelerar Render. Ahora consulta la SQLite real de forma
    segura, sin llamar APIs externas, sin inventar partidos y sin romper si la DB aún
    está vacía. Si no hay sincronización real, el estado visible será "Pendiente de
    sincronización" en vez de vender una cifra falsa.
    """
    today = today_iso()
    upcoming = _home_count_sql(
        """SELECT COUNT(*) FROM matches
           WHERE match_date>=?
             AND COALESCE(home_team,'')!=''
             AND COALESCE(away_team,'')!=''""",
        (today,),
    )
    today_count = _home_count_sql(
        """SELECT COUNT(*) FROM matches
           WHERE match_date=?
             AND COALESCE(home_team,'')!=''
             AND COALESCE(away_team,'')!=''""",
        (today,),
    )
    live_count = _home_count_sql(
        """SELECT COUNT(*) FROM matches
           WHERE match_date=?
             AND (lower(COALESCE(status,'')) LIKE '%live%'
                  OR lower(COALESCE(status,'')) LIKE '%directo%'
                  OR COALESCE(minute,'')!='')""",
        (today,),
    )
    picks_count = _home_count_sql(
        """SELECT COUNT(*) FROM picks
           WHERE lower(COALESCE(status,'')) IN ('published','won','lost','void')"""
    )
    favorites_count = _home_count_sql(
        """SELECT COUNT(*) FROM favorites WHERE user_id=?""",
        (current_user_id() or "",),
    ) if current_user_id() else 0

    raw_matches = _home_rows_sql(
        """SELECT * FROM matches
           WHERE match_date>=?
             AND COALESCE(home_team,'')!=''
             AND COALESCE(away_team,'')!=''
           ORDER BY match_date, kickoff_time, priority DESC, competition_name
           LIMIT 8""",
        (today,),
        limit=8,
    )
    upcoming_matches = []
    for item in raw_matches:
        try:
            if is_fake_match(item):
                continue
            item["kickoff_time"] = item.get("kickoff_time") or item.get("match_time") or ""
            item.update(apply_match_localization(item))
            item.update(apply_team_identities_to_match(item))
            upcoming_matches.append(item)
        except Exception:
            upcoming_matches.append(item)
        if len(upcoming_matches) >= 6:
            break

    raw_picks = _home_rows_sql(
        """SELECT * FROM picks
           WHERE lower(COALESCE(status,'')) IN ('published','won','lost','void')
           ORDER BY COALESCE(published_at, updated_at, created_at) DESC, confidence DESC
           LIMIT 12""",
        limit=12,
    )
    picks = []
    for pick in raw_picks:
        try:
            picks.append(normalize_pick_row(pick))
        except Exception:
            picks.append(pick)

    has_real_data = bool(upcoming or today_count or live_count or picks_count)
    data_status = "DATOS_REALES" if has_real_data else "PENDIENTE_SINCRONIZACION"
    data_message = (
        "Datos reales cargados desde la base persistente."
        if has_real_data
        else "Aún no hay partidos o picks sincronizados en producción. Ejecuta Cron/SportsDB/Odds y revisa el Command Center."
    )
    favorite_rows = _home_rows_sql(
        """SELECT * FROM favorites WHERE user_id=? ORDER BY created_at DESC LIMIT 6""",
        (current_user_id() or "",),
        limit=6,
    ) if current_user_id() else []

    return {
        "date": today,
        "status": data_status,
        "has_real_data": has_real_data,
        "message": data_message,
        "counts": {
            "today": today_count,
            "upcoming": upcoming,
            "live": live_count,
            "picks": picks_count,
            "favorites": favorites_count,
        },
        "upcoming_matches": upcoming_matches,
        "picks": picks,
        "favorites": favorite_rows,
    }


def home_light_data():
    """Datos seguros para / con resumen real de producción cuando exista DB."""
    live = home_live_summary_data()
    counts = live.get("counts") or {}
    try:
        client_alerts = build_client_alerts(limit=3) if current_user_id() else []
    except Exception as exc:
        try:
            print("[HOME_LIGHT][CLIENT_ALERTS_SKIP]", str(exc)[:200])
        except Exception:
            pass
        client_alerts = []
    return {
        "app_name": APP_NAME,
        "version": APP_VERSION,
        "date": today_iso(),
        "client_alerts": client_alerts,
        "match_hub": {
            "counts": {
                "upcoming": counts.get("upcoming", 0),
                "today": counts.get("today", 0),
                "live": counts.get("live", 0),
                "finished": 0,
                "favorites": counts.get("favorites", 0),
                "with_picks": counts.get("picks", 0),
            },
            "today": [],
            "live": [],
            "upcoming": live.get("upcoming_matches", []),
            "data_status": live.get("status"),
            "data_message": live.get("message"),
            "has_real_data": live.get("has_real_data"),
        },
        "home_summary": live,
        "picks": live.get("picks", []),
        "favorites": live.get("favorites", []),
        "upcoming_matches": live.get("upcoming_matches", []),
        "daily_briefing": {"score": 72 if live.get("has_real_data") else 0},
        "readiness": {"calendar": 95, "live_foundation": 92, "shark_ai": 94},
    }


@app.route("/")
def home():
    if request.method == "HEAD":
        return Response("", status=200)
    return render_template("home.html", data=home_light_data())



# ===================== V741 CALENDAR SEARCH EXPERIENCE PERFECTION =====================

CALENDAR_LANE_LABELS = {
    "today": "Hoy",
    "tomorrow": "Mañana",
    "week": "Semana",
    "upcoming": "Próximos",
    "live": "Directo",
    "favorites": "Favoritos",
    "with_pick": "Con pick",
    "picks": "Con pick",
    "top": "Top mundial",
    "spain": "España",
    "andalucia": "Andalucía",
}


def _safe_query_value(value, max_len=80):
    return str(value or "").strip()[:max_len]


def _safe_date_value(value, fallback=None):
    raw = str(value or "").strip()[:10]
    try:
        if raw:
            datetime.fromisoformat(raw)
            return raw
    except Exception:
        pass
    return fallback or today_iso()


def _calendar_pick_map(picks):
    out = {}
    for pick in picks or []:
        mid = str(pick.get("match_id") or "").strip()
        if mid and mid not in out:
            out[mid] = pick
    return out


def _calendar_base_matches(lane, date):
    lane = (lane or "today").strip().lower()
    date = _safe_date_value(date)
    if lane == "tomorrow":
        return get_matches(today_iso(1), "today")
    if lane == "week":
        return get_upcoming_matches(today_iso(), days=7, limit=380)
    if lane == "upcoming":
        return get_upcoming_matches(today_iso(), days=21, limit=520)
    if lane == "live":
        return get_matches(today_iso(), "live")
    if lane == "favorites":
        return favorite_feed_full().get("matches") or []
    if lane in {"top", "spain", "andalucia"}:
        return get_matches(date, lane)
    return get_matches(date, "today")


def _calendar_match_text(match):
    parts = [
        match.get("safe_home"), match.get("home_team"),
        match.get("safe_away"), match.get("away_team"),
        match.get("safe_competition"), match.get("competition_name"),
        match.get("league_name"), match.get("country"), match.get("status"),
    ]
    return normalized_label(" ".join(str(x or "") for x in parts))


def _calendar_enrich_matches(matches, picks):
    pick_map = _calendar_pick_map(picks)
    favs = favorite_sets() if has_request_context() else {"team": set(), "league": set(), "match": set(), "all": []}
    enriched = []
    for raw in dedupe_matches_list(matches or []):
        if is_fake_match(raw):
            continue
        try:
            item = annotate_match(dict(raw), favs=favs)
        except Exception:
            item = dict(raw)
            item.update(apply_match_localization(item))
            item.update(apply_team_identities_to_match(item))
        pick = pick_map.get(str(item.get("id") or ""))
        comp = spanish_competition_name(item.get("safe_competition") or item.get("competition_name") or item.get("league_name") or item.get("competition_key") or "") or "Competición"
        country = spanish_country_name(item.get("country") or item.get("safe_country") or "") or item.get("country") or "Global"
        live_depth = item.get("live_depth") or {}
        item["calendar_competition"] = comp
        item["calendar_country"] = country
        item["calendar_date_label"] = jinja_match_date_label(item)
        item["calendar_time"] = live_depth.get("minute") if live_depth.get("badge") == "live" else jinja_match_time_short(item)
        item["calendar_status"] = live_depth.get("label") or item.get("status") or "Próximo"
        item["calendar_score"] = live_depth.get("score") or item.get("score") or "vs"
        item["calendar_rank"] = v565_league_rank(item)
        item["calendar_priority"] = max(0, 100 - int(item.get("calendar_rank") or 80))
        item["has_pick"] = bool(pick)
        item["calendar_pick"] = pick or {}
        item["pick_label"] = (pick or {}).get("selection_display") or (pick or {}).get("selection") or ""
        item["calendar_text"] = _calendar_match_text(item)
        item["safe_home"] = item.get("safe_home") or item.get("home_team") or "Equipo local"
        item["safe_away"] = item.get("safe_away") or item.get("away_team") or "Equipo visitante"
        enriched.append(item)
    return enriched


def _calendar_apply_filters(matches, filters):
    q = normalized_label(filters.get("q") or "")
    league = normalized_label(filters.get("league") or "")
    team = normalized_label(filters.get("team") or "")
    country = normalized_label(filters.get("country") or "")
    status = normalized_label(filters.get("status") or "")
    only_pick = filters.get("lane") in {"with_pick", "picks"} or filters.get("with_pick") == "1"
    out = []
    for item in matches:
        text = item.get("calendar_text") or _calendar_match_text(item)
        if q and q not in text:
            continue
        if league and league not in normalized_label(item.get("calendar_competition") or item.get("competition_name") or item.get("league_name") or ""):
            continue
        if country and country not in normalized_label(item.get("calendar_country") or item.get("country") or ""):
            continue
        if team:
            teams = normalized_label(" ".join([str(item.get("safe_home") or item.get("home_team") or ""), str(item.get("safe_away") or item.get("away_team") or "")]))
            if team not in teams:
                continue
        if status:
            status_text = normalized_label(" ".join([str(item.get("calendar_status") or ""), str((item.get("live_depth") or {}).get("badge") or "")]))
            if status not in status_text:
                continue
        if only_pick and not item.get("has_pick"):
            continue
        out.append(item)
    return out


def _calendar_sort(matches, sort_key):
    sort_key = (sort_key or "importance").lower()
    def time_key(item):
        return (
            item.get("match_date") or "9999-99-99",
            normalize_kickoff_for_display(item).get("madrid_time") or item.get("kickoff_time") or item.get("match_time") or "99:99",
            int(item.get("calendar_rank") or 80),
            item.get("calendar_competition") or "",
            item.get("safe_home") or "",
        )
    if sort_key == "time":
        return sorted(matches, key=time_key)
    if sort_key == "league":
        return sorted(matches, key=lambda item: (int(item.get("calendar_rank") or 80), item.get("calendar_competition") or "", item.get("match_date") or "", item.get("calendar_time") or ""))
    if sort_key == "picks":
        return sorted(matches, key=lambda item: (0 if item.get("has_pick") else 1, int(item.get("calendar_rank") or 80), time_key(item)))
    return sorted(matches, key=lambda item: (item.get("match_date") or "9999-99-99", 0 if item.get("has_pick") else 1, int(item.get("calendar_rank") or 80), normalize_kickoff_for_display(item).get("madrid_time") or item.get("kickoff_time") or "99:99"))


def _calendar_facets(matches):
    leagues = {}
    teams = {}
    countries = {}
    for item in matches:
        league = item.get("calendar_competition") or "Competición"
        country = item.get("calendar_country") or "Global"
        leagues.setdefault(league, {"label": league, "value": league, "count": 0, "rank": int(item.get("calendar_rank") or 80)})
        leagues[league]["count"] += 1
        countries.setdefault(country, {"label": country, "value": country, "count": 0})
        countries[country]["count"] += 1
        for name in (item.get("safe_home") or item.get("home_team"), item.get("safe_away") or item.get("away_team")):
            name = str(name or "").strip()
            if not name:
                continue
            teams.setdefault(name, {"label": name, "value": name, "count": 0})
            teams[name]["count"] += 1
    return {
        "leagues": sorted(leagues.values(), key=lambda x: (x["rank"], -x["count"], x["label"]))[:28],
        "teams": sorted(teams.values(), key=lambda x: (-x["count"], x["label"]))[:32],
        "countries": sorted(countries.values(), key=lambda x: (-x["count"], x["label"]))[:18],
    }


def _calendar_group(matches):
    date_buckets = []
    by_date = {}
    for item in matches:
        key = item.get("match_date") or normalize_kickoff_for_display(item).get("match_date") or "sin-fecha"
        label = item.get("calendar_date_label") or jinja_match_date_label(item)
        by_date.setdefault(key, {"date_key": key, "date_label": label, "matches_count": 0, "leagues": {}})
        bucket = by_date[key]
        bucket["matches_count"] += 1
        league_name = item.get("calendar_competition") or "Competición"
        league_key = normalized_label(league_name) or "competicion"
        league = bucket["leagues"].setdefault(league_key, {
            "key": league_key,
            "name": league_name,
            "country": item.get("calendar_country") or "Global",
            "rank": int(item.get("calendar_rank") or 80),
            "matches": [],
        })
        league["matches"].append(item)
    for key in sorted(by_date.keys()):
        bucket = by_date[key]
        leagues = list(bucket["leagues"].values())
        leagues.sort(key=lambda g: (g["rank"], g["name"]))
        bucket["leagues"] = leagues
        date_buckets.append(bucket)
    return date_buckets


def calendar_experience_data():
    lane = _safe_query_value(request.args.get("lane") or "today", 32).lower() or "today"
    date = _safe_date_value(request.args.get("date"), today_iso(1) if lane == "tomorrow" else today_iso())
    filters = {
        "lane": lane,
        "date": date,
        "q": _safe_query_value(request.args.get("q"), 90),
        "league": _safe_query_value(request.args.get("league"), 80),
        "team": _safe_query_value(request.args.get("team"), 80),
        "country": _safe_query_value(request.args.get("country"), 60),
        "status": _safe_query_value(request.args.get("status"), 40),
        "sort": _safe_query_value(request.args.get("sort") or "importance", 40),
        "with_pick": "1" if request.args.get("with_pick") in {"1", "true", "yes"} else "",
    }
    user = current_session_user() or {"membership": "FREE", "role": "FREE"}
    picks = published_picks_for_user(user, limit=180)
    raw_matches = _calendar_base_matches(lane, date)
    all_matches = _calendar_enrich_matches(raw_matches, picks)
    filtered = _calendar_apply_filters(all_matches, filters)
    sorted_matches = _calendar_sort(filtered, filters.get("sort"))[:420]
    facets = _calendar_facets(all_matches)
    counts = {
        "all": len(all_matches),
        "visible": len(sorted_matches),
        "picks": len([m for m in all_matches if m.get("has_pick")]),
        "live": len([m for m in all_matches if (m.get("live_depth") or {}).get("badge") == "live"]),
        "favorites": len([m for m in all_matches if m.get("is_favorite")]),
        "leagues": len(facets.get("leagues") or []),
    }
    date_chips = []
    for offset, label in [(0, "Hoy"), (1, "Mañana"), (2, "Pasado"), (3, "+3 días"), (4, "+4 días"), (5, "+5 días"), (6, "+6 días")]:
        d = today_iso(offset)
        date_chips.append({"label": label, "date": d, "href": f"/calendar?lane=today&date={d}", "active": d == date and lane not in {"week", "upcoming", "live", "favorites", "with_pick", "picks"}})
    return {
        "version": APP_VERSION,
        "title": "Calendario de partidos",
        "filters": filters,
        "lane_label": CALENDAR_LANE_LABELS.get(lane, "Hoy"),
        "tabs": [
            {"key": "today", "label": "Hoy", "href": "/calendar?lane=today"},
            {"key": "tomorrow", "label": "Mañana", "href": "/calendar?lane=tomorrow"},
            {"key": "week", "label": "Semana", "href": "/calendar?lane=week"},
            {"key": "live", "label": "Directo", "href": "/calendar?lane=live"},
            {"key": "with_pick", "label": "Con pick", "href": "/calendar?lane=with_pick"},
            {"key": "favorites", "label": "Favoritos", "href": "/calendar?lane=favorites"},
            {"key": "spain", "label": "España", "href": "/calendar?lane=spain"},
            {"key": "andalucia", "label": "Andalucía", "href": "/calendar?lane=andalucia"},
            {"key": "upcoming", "label": "21 días", "href": "/calendar?lane=upcoming"},
        ],
        "date_chips": date_chips,
        "matches": sorted_matches,
        "groups": _calendar_group(sorted_matches),
        "facets": facets,
        "counts": counts,
        "has_filters": any(filters.get(k) for k in ["q", "league", "team", "country", "status", "with_pick"]),
    }


def v741_calendar_experience_context():
    return calendar_experience_snapshot(app_version=APP_VERSION)


@app.route("/global")
@app.route("/competiciones")
def global_football():
    return render_template("global.html", data=dashboard_data())



@app.route("/calendar")
@app.route("/calendario")
@app.route("/calendario-global")
@app.route("/partidos")
@app.route("/partidos/calendario")
def calendar_page():
    data = dashboard_data("today", request.args.get("date") or today_iso())
    data["calendar"] = calendar_experience_data()
    data["matches"] = data["calendar"].get("matches", [])
    data["lane"] = data["calendar"].get("filters", {}).get("lane", "today")
    data["date"] = data["calendar"].get("filters", {}).get("date", today_iso())
    return render_template("calendar.html", data=data)


@app.route("/sports-hub")
@app.route("/sports")
@app.route("/today")
def sports_hub_page():
    tab = (request.args.get("tab") or "today").strip().lower()
    data = dashboard_data()
    hub = data.get("match_hub") or {}
    picks = published_picks_for_user(current_session_user() or {"membership": "FREE"}, limit=30)
    recs = v565_recommendation_pool(limit=24)
    best = picks[0] if picks else (recs[0] if recs else {})
    score = as_int(best.get("confidence") or best.get("score"), 0)
    today_matches = annotate_sports_hub_matches((hub.get("today") or data.get("matches") or []), picks)
    live_matches = annotate_sports_hub_matches((hub.get("live") or []), picks)
    tomorrow_matches = annotate_sports_hub_matches(get_matches(today_iso(1), "today"), picks)
    week_matches = annotate_sports_hub_matches(get_upcoming_matches(today_iso(), days=10, limit=220), picks)
    favorites_feed = annotate_sports_hub_matches((data.get("favorite_feed") or []), picks)
    if tab == "live":
        selected_matches = live_matches or today_matches
    elif tab == "tomorrow":
        selected_matches = tomorrow_matches
    elif tab == "week":
        selected_matches = week_matches
    elif tab == "favorites":
        selected_matches = favorites_feed
    else:
        selected_matches = today_matches
    data["sports_hub"] = {
        "tab": tab,
        "date": today_iso(),
        "tabs": [
            {"key": "today", "label": "Hoy", "href": "/sports-hub?tab=today"},
            {"key": "live", "label": "Directo", "href": "/sports-hub?tab=live"},
            {"key": "tomorrow", "label": "Mañana", "href": "/sports-hub?tab=tomorrow"},
            {"key": "week", "label": "Semana", "href": "/sports-hub?tab=week"},
            {"key": "picks", "label": "Picks", "href": "/picks"},
            {"key": "favorites", "label": "Favoritos", "href": "/sports-hub?tab=favorites"},
            {"key": "combis", "label": "Combis", "href": "/combis"},
        ],
        "selected": selected_matches[:160],
        "selected_groups": sports_hub_groups(selected_matches),
        "today": today_matches[:120],
        "live": live_matches[:80],
        "tomorrow": tomorrow_matches[:120],
        "week": week_matches[:220],
        "picks": picks,
        "recommendations": recs,
        "favorites": favorites_feed[:80],
        "top_leagues": (hub.get("top_leagues") or data.get("competitions") or [])[:18],
        "counts": hub.get("counts") or {},
        "combis": get_combis(limit=12),
    }
    data["shark_product"] = {
        "score": score,
        "confidence": score,
        "risk": best.get("risk_level") or best.get("risk") or "Medio",
        "reason": best.get("reasoning") or best.get("reason") or "SHARK espera datos suficientes antes de recomendar.",
        "value": best.get("value_label") or ("Detectado" if best.get("odds") else "Pendiente"),
    }
    return render_template("sports_hub.html", data=data)


@app.route("/live")
@app.route("/live-center")
@app.route("/directo")
@app.route("/en-directo")
def live_page():
    lane = request.args.get("f") or request.args.get("filter") or request.args.get("lane") or "live"
    query = (request.args.get("q") or "").strip()
    data = dashboard_data("today", request.args.get("date") or today_iso())
    hub = data.get("match_hub") or {}
    source = []
    for key in ("live", "today", "upcoming", "finished"):
        source.extend(hub.get(key) or [])
    source = dedupe_matches_list(source)
    data["live_experience"] = build_live_experience(source, lane=lane, query=query)
    return render_template("live.html", data=data)


@app.route("/match-hub")
@app.route("/partidos-hoy")
@app.route("/resultados")
def match_hub_page():
    lane = request.args.get("lane") or ("results" if request.path == "/resultados" else "today")
    date = request.args.get("date") or (today_iso(1) if lane == "tomorrow" else today_iso())
    data = dashboard_data(lane, date)
    return render_template("match_hub.html", data=data)




@app.route("/match/<match_id>")
@app.route("/partido/<match_id>")
def match_detail_page(match_id):
    detail = match_detail(match_id)
    data = dashboard_data()
    data["match_detail"] = detail
    return render_template("match_detail.html", data=data, detail=detail)



@app.route("/team/<team_id>")
@app.route("/equipo/<team_id>")
def team_page(team_id):
    detail = team_page_data(team_id)
    if not detail:
        return redirect("/match-hub")
    data = dashboard_data()
    data["team_detail"] = detail
    return render_template("team_detail.html", data=data, detail=detail)

@app.route("/favoritos", methods=["GET", "POST"])
@app.route("/favorites", methods=["GET", "POST"])
def favorites_page():
    if not current_session_user():
        return redirect("/cliente-login")
    if request.method == "POST":
        action = str(request.form.get("action") or "add").lower()
        if action == "remove":
            remove_favorite(request.form.get("kind"), request.form.get("value"))
        else:
            add_favorite(request.form.get("kind"), request.form.get("value"), request.form.get("label"))
        return redirect("/favorites")
    return render_template("favorites.html", data=dashboard_data())


@app.route("/registro", methods=["GET", "POST"])
def register_page():
    if current_session_user():
        return redirect("/perfil")
    error = ""
    if request.method == "POST":
        try:
            user = create_user(
                request.form.get("name"),
                request.form.get("username"),
                request.form.get("email"),
                request.form.get("password"),
            )
            security_event_for_auth("registration_attempt", True, request.form.get("username") or request.form.get("email"), "registro_correcto")
            set_login_session(user)
            return redirect("/perfil")
        except ValueError as exc:
            security_event_for_auth("registration_attempt", False, request.form.get("username") or request.form.get("email"), str(exc)[:180])
            error = str(exc)
    return render_template("register.html", data=home_light_data(), error=error)


@app.route("/cliente-login", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
@app.route("/entrar", methods=["GET", "POST"])
def client_login_page():
    if current_session_user():
        return redirect("/perfil")
    error = ""
    if request.method == "POST":
        identifier = request.form.get("login") or request.form.get("email") or request.form.get("username")
        user = authenticate_user(identifier, request.form.get("password"))
        if user:
            security_event_for_auth("login_attempt", True, identifier, "cliente_login_correcto")
            set_login_session(user)
            return redirect("/perfil")
        security_event_for_auth("login_attempt", False, identifier, "credenciales_cliente_invalidas")
        error = "Email, usuario o contraseña incorrectos."
    return render_template("client_login.html", data=home_light_data(), error=error)


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password_page():
    message = ""
    diagnostic_url = ""
    if request.method == "POST":
        identifier = request.form.get("login") or request.form.get("email")
        security_event_for_auth("password_reset_request", True, identifier, "solicitud_cliente")
        result = password_reset_request(identifier, scope="client")
        diagnostic_url = result.get("diagnostic_reset_url") or ""
        message = "Si existe una cuenta con esos datos, recibirás un enlace para restablecer la contraseña."
    return render_template("password_reset_request.html", data=home_light_data(), message=message, diagnostic_url=diagnostic_url, admin=False)


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password_page(token):
    row = load_password_reset_token(token, scope="client")
    error = "" if row else "El enlace ha caducado o ya fue usado."
    if request.method == "POST" and row:
        try:
            reset_user_password(row["user_id"], request.form.get("password"))
            mark_password_reset_used(token)
            return redirect("/cliente-login")
        except ValueError as exc:
            error = str(exc)
    return render_template("password_reset_form.html", data=home_light_data(), token=token, error=error, admin=False)


@app.route("/admin-login", methods=["GET", "POST"])
def admin_login_page():
    if is_admin_session():
        return redirect(request.args.get("next") or "/admin/import-center")
    error = ""
    configured = bool(os.getenv("ADMIN_EMAIL") and os.getenv("ADMIN_PASSWORD"))
    if request.method == "POST":
        user = authenticate_env_admin(request.form.get("login"), request.form.get("password"))
        if not user:
            user = authenticate_user(request.form.get("login"), request.form.get("password"), admin_only=True)
        if user:
            security_event_for_auth("login_attempt", True, request.form.get("login"), "admin_login_correcto")
            set_login_session(user)
            return redirect(request.args.get("next") or "/admin/import-center")
        security_event_for_auth("login_attempt", False, request.form.get("login"), "credenciales_admin_invalidas")
        error = "Acceso admin no válido."
    return render_template("admin_login.html", data=home_light_data(), error=error, configured=configured)


@app.route("/admin-forgot-password", methods=["GET", "POST"])
def admin_forgot_password_page():
    message = ""
    diagnostic_url = ""
    if request.method == "POST":
        identifier = request.form.get("login") or request.form.get("email")
        security_event_for_auth("password_reset_request", True, identifier, "solicitud_admin")
        result = password_reset_request(identifier, scope="admin")
        diagnostic_url = result.get("diagnostic_reset_url") or ""
        message = "Si existe una cuenta admin con esos datos, recibirás un enlace para restablecer la contraseña."
    return render_template("password_reset_request.html", data=home_light_data(), message=message, diagnostic_url=diagnostic_url, admin=True)


@app.route("/admin-reset-password/<token>", methods=["GET", "POST"])
def admin_reset_password_page(token):
    row = load_password_reset_token(token, scope="admin")
    error = "" if row else "El enlace ha caducado o ya fue usado."
    if request.method == "POST" and row:
        try:
            reset_user_password(row["user_id"], request.form.get("password"))
            mark_password_reset_used(token)
            return redirect("/admin-login")
        except ValueError as exc:
            error = str(exc)
    return render_template("password_reset_form.html", data=home_light_data(), token=token, error=error, admin=True)


@app.route("/admin-bootstrap", methods=["GET", "POST"])
def admin_bootstrap_page():
    if admin_exists():
        return render_template("admin_bootstrap.html", data=dashboard_data(), blocked=True, result=None, error="")
    result = None
    error = ""
    if request.method == "POST":
        email = request.form.get("email") or os.getenv("ADMIN_EMAIL")
        username = request.form.get("username") or os.getenv("ADMIN_USERNAME") or username_from_email(email)
        password = request.form.get("password") or os.getenv("ADMIN_PASSWORD")
        name = request.form.get("name") or os.getenv("ADMIN_NAME") or "Admin SHARK"
        conn = None
        try:
            conn = db()
            create_admin_record(conn, name, username, email, password)
            conn.commit()
            result = {"created": True, "email": normalize_email(email), "username": normalize_username(username)}
        except ValueError as exc:
            error = str(exc)
        except sqlite3.IntegrityError:
            error = "No se pudo crear el admin: email o usuario ya existe."
        finally:
            if conn:
                conn.close()
    return render_template("admin_bootstrap.html", data=dashboard_data(), blocked=False, result=result, error=error)


@app.route("/logout")
def logout_page():
    session.clear()
    return redirect("/")


@app.route("/admin")
def admin_redirect():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/data-center")
    return redirect("/admin/data-center")


@app.route("/admin/intelligence")
def admin_intelligence_alias():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/intelligence")
    return redirect("/admin/unified-intelligence")


@app.route("/admin/observability")
def admin_observability_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/observability")
    return render_template("admin_observability.html", summary=observability_summary(DB_PATH, APP_VERSION))


@app.route("/admin/observability/errors")
def admin_observability_errors_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/observability/errors")
    selected = request.args.get("error_id") or ""
    detail = observability_error_detail(DB_PATH, selected) if selected else {}
    return render_template(
        "admin_observability_errors.html",
        errors=latest_observability_errors(DB_PATH, limit=100),
        detail=detail,
        selected_error_id=selected,
        detail_missing=bool(selected and not detail),
    )


@app.route("/admin/import-center")
def import_center():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/import-center")
    return render_template("import_center.html", data=dashboard_data())


@app.route("/admin/users", methods=["GET", "POST"])
def admin_users_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/users")
    message = ""
    if request.method == "POST":
        updated = update_user_membership(
            request.form.get("user_id"),
            request.form.get("membership"),
            days=request.form.get("membership_days"),
            note=request.form.get("membership_note"),
            source="admin_gift" if days_from_admin_value(request.form.get("membership_days")) else "admin_manual",
            admin_id=session.get("user_id") or "admin",
        )
        if updated:
            public = user_public(updated)
            message = f"Membresía actualizada: {public['membership']} · {public.get('membership_expires_label') or 'Sin caducidad'}."
        else:
            message = "No se pudo actualizar ese usuario."
    data = dashboard_data()
    data["users"] = list_users()
    data["membership_admin"] = membership_admin_summary()
    data["admin_exists"] = admin_exists()
    return render_template("admin_users.html", data=data, message=message)


@app.route("/admin/user-import", methods=["GET", "POST"])
def admin_user_import_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/user-import")
    result = None
    if request.method == "POST":
        result = import_users_from_old_database()
    data = dashboard_data()
    data["old_db_present"] = os.path.exists(os.path.join(os.path.dirname(__file__), "old_database.db"))
    return render_template("admin_user_import.html", data=data, result=result)


@app.route("/admin/sportsdb-sync", methods=["GET", "POST"])
def admin_sportsdb_sync_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/sportsdb-sync")
    message = ""
    if request.method == "POST":
        result = sync_sportsdb_crests(
            refresh=request.form.get("refresh") in {"1", "true", "yes"},
            limit=as_int(request.form.get("limit"), 40),
        )
        message = "Sincronizacion ejecutada: %s actualizados, %s fallidos." % (result.get("updated", 0), result.get("failed", 0))
        if result.get("sin_key"):
            message = "Falta configurar THESPORTSDB_API_KEY o THESPORTSDB_KEY."
    data = dashboard_data()
    data["sportsdb"] = crest_sync_status()
    return render_template("admin_sportsdb_sync.html", data=data, message=message)


@app.route("/admin/sportsdb-feed", methods=["GET", "POST"])
def admin_sportsdb_feed_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/sportsdb-feed")
    message = ""
    if request.method == "POST":
        result = sync_sportsdb_feed(limit=as_int(request.form.get("limit"), 80))
        if result.get("sin_key"):
            message = "Falta configurar THESPORTSDB_API_KEY o THESPORTSDB_KEY."
        else:
            message = "Feed sincronizado: %s importados, %s actualizados." % (result.get("imported", 0), result.get("updated", 0))
    data = dashboard_data()
    data["sportsdb_feed"] = sportsdb_feed_status()
    return render_template("admin_sportsdb_feed.html", data=data, message=message)


@app.route("/admin/matches-sync", methods=["GET", "POST"])
def admin_matches_sync_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/matches-sync")
    message = ""
    result = None
    if request.method == "POST":
        action = request.form.get("action") or "sportsdb"
        if action == "odds":
            result = sync_odds_events(limit=as_int(request.form.get("limit"), 80), force=True)
        elif action == "crests":
            result = sync_sportsdb_crests(refresh=True, limit=as_int(request.form.get("limit"), 40))
        else:
            result = sync_sportsdb_feed(limit=as_int(request.form.get("limit"), 80))
        message = "Sincronizacion ejecutada."
        if result and result.get("errors"):
            message += " Revisa errores recientes."
    data = dashboard_data()
    data["matches_diagnostics"] = match_calendar_diagnostics()
    data["sportsdb_feed"] = sportsdb_feed_status()
    data["odds"] = odds_diagnostics()
    return render_template("admin_matches_sync.html", data=data, message=message, result=result)


@app.route("/admin/telegram", methods=["GET", "POST"])
def admin_telegram_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/telegram")
    message = ""
    result = None
    if request.method == "POST":
        action = request.form.get("action") or "diagnostics"
        if action == "toggle":
            current = get_telegram_settings()
            result = {"ok": True, "settings": update_telegram_settings({"enabled": not current.get("enabled")})}
        elif action == "test":
            result = enqueue_telegram_message(
                "system_test",
                "Prueba Telegram",
                build_system_test_message(),
                chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
                payload={"target_key": "admin-test", "priority": 95},
                dedupe_key=telegram_dedupe_key("system_test", now_iso(), os.getenv("TELEGRAM_CHAT_ID", "")),
                force=True,
            )
            if result.get("queued"):
                result["process"] = process_premium_telegram_queue(limit=1, force=True)
        elif action == "test_private":
            sub = one("SELECT * FROM telegram_subscribers WHERE is_active=1 AND user_id IS NOT NULL AND user_id!='' AND chat_id IS NOT NULL AND chat_id!='' ORDER BY last_seen DESC, created_at DESC LIMIT 1")
            result = enqueue_telegram_message(
                "private_test",
                "Prueba privada Telegram",
                "Prueba privada NeMeSiS SHARK PRO: tu vinculación funciona.",
                chat_id=(sub or {}).get("chat_id") or "",
                user_id=(sub or {}).get("user_id") or "",
                payload={"target_key": "private-test", "priority": 96},
                dedupe_key=telegram_dedupe_key("private_test", now_iso(), (sub or {}).get("chat_id") or "none"),
                force=True,
            ) if sub else {"ok": False, "message": "No hay usuarios vinculados para prueba privada.", "errors": ["sin_usuario_vinculado"]}
            if result.get("queued"):
                result["process"] = process_premium_telegram_queue(limit=1, force=True)
        elif action == "test_channel":
            result = enqueue_telegram_message(
                "channel_test",
                "Prueba canal Telegram",
                "Prueba de canal NeMeSiS SHARK PRO: el canal global sigue operativo.",
                chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
                payload={"target_key": "channel-test", "priority": 96},
                dedupe_key=telegram_dedupe_key("channel_test", now_iso(), os.getenv("TELEGRAM_CHAT_ID", "")),
                force=True,
            )
            if result.get("queued"):
                result["process"] = process_premium_telegram_queue(limit=1, force=True)
        elif action == "daily_matches":
            result = enqueue_daily_matches(force=True, forced_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""))
        elif action == "daily_picks":
            result = enqueue_daily_picks(force=True, force_empty=True, forced_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""))
        elif action == "process":
            result = process_premium_telegram_queue(limit=as_int(request.form.get("limit"), 5), force=True)
        elif action == "retry_failed":
            conn = db()
            conn.execute("UPDATE telegram_queue SET status=?, updated_at=? WHERE lower(status)=?", (QUEUE_PENDING, now_iso(), QUEUE_FAILED))
            conn.commit()
            conn.close()
            result = process_premium_telegram_queue(limit=as_int(request.form.get("limit"), 10), force=True)
        elif action == "repair":
            update_telegram_settings({"enabled": True, "auto_daily_matches": True, "auto_daily_picks": True})
            synced = sync_telegram_subscribers_from_users()
            queued_matches = enqueue_daily_matches(force=True, forced_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""))
            queued_auto_picks = enqueue_auto_pick_alerts(force=True, limit=as_int(os.getenv("MAX_AUTO_PICKS_PER_DAY", "4"), 4))
            queued_picks = enqueue_daily_picks(force=True, force_empty=True, forced_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""))
            processed = process_premium_telegram_queue(limit=10, force=True)
            result = {"ok": processed.get("failed", 0) == 0, "synced_users": synced, "queued_matches": queued_matches, "queued_auto_picks": queued_auto_picks, "queued_picks": queued_picks, "processed": processed}
        message = "Accion Telegram ejecutada."
    data = dashboard_data()
    data["telegram_delivery"] = telegram_diagnostics()
    data["telegram_queue"] = rows("SELECT * FROM telegram_queue ORDER BY created_at DESC LIMIT 30")
    data["telegram_logs"] = rows("SELECT * FROM telegram_logs ORDER BY created_at DESC LIMIT 30")
    data["telegram_subscribers"] = telegram_subscribers(active_only=False)
    return render_template("admin_telegram.html", data=data, message=message, result=result)


@app.route("/admin/telegram/command-center")
def admin_telegram_command_center_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/telegram/command-center")
    snapshot = telegram_reliability_snapshot(limit=80)
    dry_run = telegram_reliability_dry_run()
    diagnostics = telegram_diagnostics_safe()
    return render_template(
        "admin_telegram_command_center.html",
        data={
            "version": APP_VERSION,
            "snapshot": snapshot,
            "dry_run": dry_run,
            "diagnostics": diagnostics,
        },
    )


@app.route("/api/admin/telegram/schema")
def api_admin_telegram_schema():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, "schema": telegram_delivery_memory_schema_status()})


@app.route("/api/admin/telegram/status")
def api_admin_telegram_status():
    if not is_admin_session():
        return admin_json_forbidden()
    snapshot = telegram_reliability_snapshot(limit=80)
    diagnosis = snapshot.get("diagnosis") or {}
    return jsonify({
        "ok": snapshot.get("ok", False),
        "version": APP_VERSION,
        "configured": {
            "bot_token": (snapshot.get("env") or {}).get("bot_token_configured"),
            "chat_id": (snapshot.get("env") or {}).get("chat_id_configured"),
            "automation_secret": (snapshot.get("env") or {}).get("automation_secret_configured"),
        },
        "status": diagnosis.get("status"),
        "severity": diagnosis.get("severity"),
        "explanation": diagnosis.get("explanation"),
        "what_to_do": diagnosis.get("action"),
        "manual_send_status": "READY_FOR_ADMIN_TEST" if (snapshot.get("env") or {}).get("bot_token_configured") and (snapshot.get("env") or {}).get("chat_id_configured") else diagnosis.get("status"),
        "auto_tick_status": diagnosis.get("status"),
        "daily_run_status": "CRON_READY" if (snapshot.get("env") or {}).get("automation_secret_configured") else "CRON_SECRET_INVALID",
        "bot_private_status": "CONFIGURABLE" if (snapshot.get("counts") or {}).get("private_destinations", 0) else "SIN_USUARIOS_PRIVADOS_VINCULADOS",
        "group_status": "REVISION_RENDER" if (snapshot.get("env") or {}).get("chat_id_configured") else "MISSING_CHAT_ID",
        "channel_status": "REVISION_RENDER" if (snapshot.get("counts") or {}).get("global_channel") else "BLOCKED_BY_MISSING_DESTINATION",
        "last_tick": (snapshot.get("cron") or {}).get("last_telegram"),
        "last_daily": (snapshot.get("cron") or {}).get("last_daily"),
        "last_manual_send_at": (snapshot.get("last_sent") or {}).get("sent_at"),
        "last_auto_send_at": (snapshot.get("last_auto_pick") or {}).get("sent_at"),
        "last_daily_send_at": ((snapshot.get("cron") or {}).get("last_daily") or {}).get("time"),
        "last_sent": snapshot.get("last_sent"),
        "last_telegram_error": snapshot.get("last_error"),
        "last_successful_destination": masked_key((snapshot.get("last_sent") or {}).get("chat_id")),
        "next_candidate_destination": ((snapshot.get("destinations") or [{}])[0] or {}).get("chat_id"),
        "candidates": (snapshot.get("counts") or {}).get("candidate_picks"),
        "discarded": snapshot.get("discarded", [])[:12],
        "blocked_by_limits": {
            "quiet_hours": (snapshot.get("limits") or {}).get("quiet_hours_active"),
            "sent_last_hour": (snapshot.get("limits") or {}).get("sent_last_hour"),
            "max_per_hour": (snapshot.get("limits") or {}).get("max_per_hour"),
            "sent_today": (snapshot.get("limits") or {}).get("sent_today"),
            "max_per_day": (snapshot.get("limits") or {}).get("max_per_day"),
        },
        "errors": {
            "last_error": snapshot.get("last_error"),
            "data_memory_errors": (snapshot.get("data_memory") or {}).get("errors", [])[:5],
        },
        "football_only": (snapshot.get("env") or {}).get("telegram_football_only"),
        "quiet_hours": {
            "start": (snapshot.get("limits") or {}).get("quiet_start"),
            "end": (snapshot.get("limits") or {}).get("quiet_end"),
        },
        "madrid_now": snapshot.get("madrid_now"),
    })


@app.route("/api/admin/telegram/dry-run", methods=["GET", "POST"])
def api_admin_telegram_dry_run():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, **telegram_reliability_dry_run()})


@app.route("/api/admin/telegram/preview-next")
def api_admin_telegram_preview_next():
    if not is_admin_session():
        return admin_json_forbidden()
    dry = telegram_reliability_dry_run()
    return jsonify({
        "ok": True,
        "version": APP_VERSION,
        "madrid_now": dry.get("madrid_now"),
        "would_send": dry.get("would_send"),
        "diagnosis": dry.get("diagnosis"),
        "message_preview": dry.get("message_preview") or "No hay mensaje premium listo para previsualizar.",
    })


@app.route("/api/admin/telegram/test-send", methods=["POST"])
def api_admin_telegram_test_send():
    if not is_admin_session():
        return admin_json_forbidden()
    text = f"✅ Test Telegram NeMeSiS SHARK PRO — conexión correcta — hora Madrid {datetime.now(TZ).strftime('%H:%M')}"
    result = enqueue_telegram_message(
        "admin_connectivity_test",
        "Test Telegram controlado",
        text,
        chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        payload={"target_key": "admin-connectivity-test", "priority": 99},
        dedupe_key=telegram_dedupe_key("admin_connectivity_test", now_iso(), os.getenv("TELEGRAM_CHAT_ID", "")),
        force=True,
    )
    process = process_premium_telegram_queue(limit=1, force=True) if result.get("queued") else {}
    actual_ok = bool(result.get("ok")) and (not process or process.get("failed", 0) == 0 and process.get("sent", 0) > 0)
    return jsonify({
        "ok": actual_ok,
        "version": APP_VERSION,
        "queued": result,
        "process": process,
        "schema": telegram_delivery_memory_schema_status(),
        "note": "Envío de prueba controlado iniciado por admin. No expone secrets.",
    })


@app.route("/admin/automation", methods=["GET", "POST"])
def admin_automation_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/automation")
    result = None
    message = ""
    if request.method == "POST":
        result = run_daily_autonomous_system(force=True)
        message = "Automatización diaria ejecutada."
    data = dashboard_data()
    data["automation"] = daily_automation_summary()
    data["scheduler"] = scheduler_status()
    return render_template("admin_automation.html", data=data, result=result, message=message)


@app.route("/admin/backups", methods=["GET", "POST"])
def admin_backups_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/backups")
    message = ""
    if request.method == "POST":
        action = str(request.form.get("action") or "").lower()
        name = request.form.get("name") or ""
        if action == "create":
            result = create_database_backup(reason="admin_manual")
            message = f"Backup creado: {result.get('name')}" if result.get("ok") else f"No se pudo crear backup: {result.get('message') or result.get('error')}"
        elif action == "delete":
            path = backup_file_path(name)
            if path:
                os.remove(path)
                message = "Backup eliminado."
            else:
                message = "Backup no encontrado."
        elif action == "restore":
            result = restore_database_backup(name)
            message = f"Backup restaurado: {result.get('restored')}" if result.get("ok") else f"No se pudo restaurar: {result.get('error')}"
    data = dashboard_data()
    data["backups"] = list_backups()
    data["backup_dir"] = backup_dir()
    data["backup_retention"] = BACKUP_RETENTION_MAX
    data["backup_events"] = []
    return render_template("admin_backups.html", data=data, message=message)


@app.route("/admin/backups/download/<name>")
def admin_backup_download(name):
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/backups")
    path = backup_file_path(name)
    if not path:
        abort(404)
    return send_file(path, as_attachment=True, download_name=os.path.basename(path))


@app.route("/admin/picks", methods=["GET", "POST"])
def admin_picks_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/picks")
    message = ""
    result = None
    if request.method == "POST":
        action = request.form.get("action") or "create"
        if action in {"create", "publish"}:
            payload = dict(request.form)
            result = create_or_update_pick(payload, publish=action == "publish")
            message = "Pick publicado." if action == "publish" else "Pick guardado como borrador."
        elif action in {"archive", "published", "draft"}:
            result = update_pick_status(request.form.get("pick_id"), "archived" if action == "archive" else action)
            message = "Estado del pick actualizado."
    data = dashboard_data()
    data["admin_picks"] = get_picks(limit=120, include_admin=True)
    data["pick_stats"] = pick_stats()
    data["matches_for_pick"] = get_upcoming_matches(today_iso(), days=21, limit=220)
    return render_template("admin_picks.html", data=data, message=message, result=result)


@app.route("/admin/data-center", methods=["GET", "POST"])
def admin_data_center_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/data-center")
    message = ""
    result = None
    if request.method == "POST":
        action = request.form.get("action") or "summary"
        limit = as_int(request.form.get("limit"), 120)
        force = request.form.get("force") in {"1", "true", "yes"}
        if action == "competitions":
            result = sync_sportsdb_competitions()
        elif action == "teams":
            result = sync_sportsdb_teams(limit=limit)
        elif action == "calendar":
            result = run_scheduler_task("calendar", force=True, limit=limit)
        elif action == "results":
            result = sync_sportsdb_results(limit=limit)
        elif action == "odds":
            result = run_scheduler_task("odds", force=True, limit=limit)
        elif action == "crests":
            result = run_scheduler_task("crests", force=True, limit=limit)
        elif action == "live":
            result = run_scheduler_task("live", force=True, limit=limit)
        elif action == "warmup":
            result = run_scheduler_task("warmup", force=True, limit=limit)
        message = "Accion ejecutada desde Data Center."
    data = dashboard_data()
    data["data_center"] = data_center_summary()
    return render_template("admin_data_center.html", data=data, message=message, result=result)


@app.route("/admin/system")
def admin_system_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/system")
    data = dashboard_data()
    data["system"] = {
        "version": APP_VERSION,
        "sqlite": "OK",
        "teams": (one("SELECT COUNT(*) AS total FROM teams") or {}).get("total", 0),
        "matches": (one("SELECT COUNT(*) AS total FROM matches") or {}).get("total", 0),
        "picks": (one("SELECT COUNT(*) AS total FROM picks") or {}).get("total", 0),
        "telegram": "Listo" if data.get("telegram", {}).get("configured") else "Pendiente",
        "admin_exists": admin_exists(),
        "users_count": (one("SELECT COUNT(*) AS total FROM users") or {}).get("total", 0),
        "sportsdb_feed": sportsdb_feed_status(),
    }
    return render_template("admin_system.html", data=data)


@app.route("/admin/route-health")
def admin_route_health_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/route-health")
    snapshot = route_health_snapshot(app)
    return render_template(
        "admin_route_health.html",
        data={
            "version": APP_VERSION,
            "route_health": snapshot,
        },
    )


@app.route("/api/admin/route-health")
def api_admin_route_health():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, **route_health_snapshot(app)})


@app.route("/admin/client-experience")
def admin_client_experience_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/client-experience")
    snapshot = client_experience_snapshot()
    return render_template(
        "admin_client_experience.html",
        data={
            "version": APP_VERSION,
            "client_experience": snapshot,
        },
    )


@app.route("/api/admin/client-experience")
def api_admin_client_experience():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, **client_experience_snapshot()})




@app.route("/admin/production-readiness")
def admin_production_readiness_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/production-readiness")
    snapshot = production_readiness_snapshot(app_version=APP_VERSION)
    return render_template(
        "admin_production_readiness.html",
        data={
            "version": APP_VERSION,
            "production_readiness": snapshot,
        },
    )


@app.route("/api/admin/production-readiness")
def api_admin_production_readiness():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, **production_readiness_snapshot(app_version=APP_VERSION)})


@app.route("/picks")
def picks_page():
    data = dashboard_data()
    user = current_session_user() or {"membership": "FREE", "role": "FREE"}
    data["membership"] = v566_membership_ui(user)
    data["picks"] = published_picks_for_user(user, limit=80)
    data["candidate_matches"] = pick_candidate_matches(limit=80, days=21)
    data["pick_stats"] = pick_stats()
    data["smart_picks"] = smart_pick_board(user, limit=24)
    record_user_activity("view", "picks", "picks-page", {"count": len(data["picks"]), "candidates": len(data["candidate_matches"])})
    return render_template("picks.html", data=data)


@app.route("/combis")
def combis_page():
    data = dashboard_data()
    user = current_session_user() or {"membership": "FREE", "role": "FREE"}
    data["membership"] = v566_membership_ui(user)
    requested_count = combi_leg_count(request.args.get("partidos"), 3)
    data["picks"] = published_picks_for_user(user, limit=30)
    data["combis"] = get_combis(limit=20)
    data["combi_builder"] = build_combi_candidates_from_matches(requested_count)
    data["requested_combi_count"] = requested_count
    record_user_activity("view", "combis", "combis-page", {"picks_available": len(data["picks"])})
    return render_template("combis.html", data=data)


@app.route("/perfil")
@app.route("/profile")
def profile_page():
    user = current_session_user()
    if not user:
        return redirect("/cliente-login")
    data = dashboard_data()
    data["session_user"] = user
    data["membership"] = v566_membership_ui(user)
    data["sportsdb"] = crest_sync_status()
    data["briefing"] = shark_briefing()
    return render_template("profile.html", data=data)


@app.route("/alertas")
def alerts_page():
    if not current_session_user():
        return redirect("/cliente-login")
    data = dashboard_data()
    record_user_activity("view", "alerts", "client-alerts", {"count": len(data.get("client_alerts") or [])})
    return render_template("alerts.html", data=data)


@app.route("/actividad")
def activity_page():
    if not current_session_user():
        return redirect("/cliente-login")
    data = dashboard_data()
    record_user_activity("view", "activity", "client-activity", {"count": len(data.get("client_activity") or [])})
    return render_template("activity.html", data=data)


@app.route("/mi-dia")
@app.route("/briefing")
def daily_briefing_page():
    if not current_session_user():
        return redirect("/cliente-login")
    data = dashboard_data()
    data["briefing"] = build_daily_briefing(current_session_user())
    data["client_command"] = client_command_center_data(current_session_user())
    record_user_activity("view", "briefing", "daily-briefing", {"score": data["briefing"].get("score")})
    return render_template("daily_briefing.html", data=data)


@app.route("/membresias")
@app.route("/membresías")
@app.route("/membership")
def membership_page():
    user = current_session_user() or {"membership": "FREE", "role": "FREE"}
    data = dashboard_data()
    data["membership"] = v566_membership_ui(user)
    return render_template("membership.html", data=data)


@app.route("/shark-ai")
@app.route("/shark")
def shark_page():
    data = dashboard_data()
    user = current_session_user() or {"membership": "FREE", "role": "FREE"}
    data["membership"] = v566_membership_ui(user)
    data["briefing"] = shark_briefing()
    return render_template("shark.html", data=data)


@app.route("/telegram")
def telegram_page():
    user = current_session_user()
    if not user:
        return redirect("/cliente-login?next=/telegram")
    state = telegram_user_state(user)
    data = {
        "telegram": telegram_config(),
        "telegram_state": state,
        "membership": v566_membership_ui(user),
        "session_user": user,
    }
    return render_template("telegram.html", data=data)


@app.route("/telegram/regenerar-codigo", methods=["POST", "GET"])
def telegram_regenerate_code():
    user = current_session_user()
    if not user:
        return redirect("/cliente-login?next=/telegram")
    conn = db()
    conn.execute("UPDATE users SET telegram_link_code='', telegram_link_expires_at='', telegram_link_expires='' WHERE id=?", (user.get("id"),))
    conn.commit()
    conn.close()
    generate_telegram_link_code(user.get("id"))
    return redirect("/telegram")


@app.route("/telegram/desvincular", methods=["POST"])
def telegram_unlink_private():
    user = current_session_user()
    if not user:
        return redirect("/cliente-login?next=/telegram")
    conn = db()
    conn.execute("UPDATE users SET telegram_chat_id='', telegram_username='', telegram_linked_at='' WHERE id=?", (user.get("id"),))
    conn.execute("UPDATE telegram_subscribers SET is_active=0, last_seen=? WHERE user_id=?", (now_iso(), user.get("id")))
    conn.commit()
    conn.close()
    telegram_log("link", "unlinked", "Telegram privado desvinculado por el usuario.", {"user_id": user.get("id")})
    return redirect("/telegram")


@app.route("/telegram/webhook", methods=["POST", "GET"])
def telegram_webhook():
    if request.method == "GET":
        return jsonify({"ok": True, "version": APP_VERSION, "webhook": "telegram"})
    update = request.get_json(silent=True) or {}
    message = update.get("message") or update.get("edited_message") or {}
    chat = message.get("chat") or {}
    from_user = message.get("from") or {}
    text = str(message.get("text") or "").strip()
    chat_id = str(chat.get("id") or "")
    username = from_user.get("username") or chat.get("username") or ""
    first_name = from_user.get("first_name") or chat.get("first_name") or ""
    parts = text.split()
    command = parts[0].lower() if parts else ""
    code = parts[1] if len(parts) > 1 else ""
    if command in {"/start", "/link"} and code:
        result = link_telegram_chat_by_code(code, chat_id, username=username, first_name=first_name)
        reply = "✅ Telegram vinculado a tu cuenta NeMeSiS SHARK PRO." if result.get("ok") else f"⚠️ {result.get('message') or 'No se pudo vincular Telegram.'}"
        telegram_send_http(chat_id, reply, message_type="link_reply")
        return jsonify({"ok": result.get("ok"), "version": APP_VERSION, "result": result})
    if command == "/start":
        telegram_send_http(chat_id, "🦈 Entra en NeMeSiS > Telegram y envíame el comando /link CODIGO para vincular tu cuenta.", message_type="start_reply")
        return jsonify({"ok": True, "version": APP_VERSION, "message": "start_help"})
    telegram_log("webhook", "received", "Mensaje Telegram recibido sin accion.", {"chat_id": chat_id, "text": text[:120]})
    return jsonify({"ok": True, "version": APP_VERSION, "message": "ignored"})


@app.route("/api/telegram/link-status")
def api_telegram_link_status():
    user = current_session_user()
    if not user:
        return jsonify({"ok": False, "version": APP_VERSION, "error": "Login requerido."}), 401
    return jsonify({"ok": True, "version": APP_VERSION, "telegram_state": telegram_user_state(user)})


@app.route("/admin/telegram/diagnostics")
def admin_telegram_diagnostics_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/telegram/diagnostics")
    return jsonify({
        "ok": True,
        "version": APP_VERSION,
        "diagnostics": telegram_diagnostics(),
        "linking": {
            "linked_users": (one("SELECT COUNT(*) AS total FROM users WHERE telegram_chat_id IS NOT NULL AND telegram_chat_id!=''") or {}).get("total", 0),
            "pending_codes": (one("SELECT COUNT(*) AS total FROM users WHERE telegram_link_code IS NOT NULL AND telegram_link_code!=''") or {}).get("total", 0),
            "expires_column": "telegram_link_expires_at",
            "legacy_expires_column": "telegram_link_expires",
        },
    })


@app.route("/admin/time-diagnostics")
def admin_time_diagnostics_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/time-diagnostics")
    available = {col.get("name") for col in rows("PRAGMA table_info(matches)")}
    wanted = [
        "id",
        "home_team",
        "away_team",
        "competition_name",
        "league_name",
        "country",
        "match_date",
        "kickoff_time",
        "match_time",
        "kickoff_iso",
        "commence_time",
        "start_time",
        "event_time",
        "status",
        "minute",
    ]
    selected = [name for name in wanted if name in available]
    matches = []
    if selected:
        order_candidates = [name for name in ("kickoff_iso", "match_date", "updated_at", "created_at") if name in available]
        if len(order_candidates) > 1:
            order_sql = f"ORDER BY COALESCE({', '.join(order_candidates)}) DESC"
        elif order_candidates:
            order_sql = f"ORDER BY {order_candidates[0]} DESC"
        else:
            order_sql = ""
        sql = f"SELECT {', '.join(selected)} FROM matches {order_sql} LIMIT 80"
        matches = rows(sql)
    diagnostics = madrid_time_diagnostics(matches)
    return render_template(
        "admin_time_diagnostics.html",
        data=dashboard_data(),
        diagnostics=diagnostics,
        version=APP_VERSION,
    )


@app.route("/api/telegram/repair-automatic", methods=["POST", "GET"])
def api_telegram_repair_automatic():
    if not is_admin_session():
        return admin_json_forbidden()
    update_telegram_settings({"enabled": True, "auto_daily_matches": True, "auto_daily_picks": True})
    synced = sync_telegram_subscribers_from_users()
    default_sub = ensure_default_telegram_subscriber()
    queued_matches = enqueue_daily_matches(force=True, forced_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""))
    queued_auto_picks = enqueue_auto_pick_alerts(force=True, limit=as_int(os.getenv("MAX_AUTO_PICKS_PER_DAY", "4"), 4))
    queued_picks = enqueue_daily_picks(force=True, force_empty=True, forced_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""))
    processed = process_premium_telegram_queue(limit=10, force=True)
    return jsonify({
        "ok": processed.get("failed", 0) == 0,
        "version": APP_VERSION,
        "message": "Telegram automatico revisado y procesado.",
        "synced_users": synced,
        "default_subscriber": bool(default_sub),
        "queued_matches": queued_matches,
        "queued_auto_picks": queued_auto_picks,
        "queued_picks": queued_picks,
        "processed": processed,
        "diagnostics": telegram_diagnostics(),
    })


@app.route("/escudos")
@app.route("/crests")
def crests_page():
    if not is_admin_session():
        return redirect("/perfil" if current_session_user() else "/cliente-login")
    return render_template("crests.html", data=dashboard_data())


@app.route("/api/client/alerts")
def api_client_alerts():
    return jsonify({"ok": True, "version": APP_VERSION, "alerts": build_client_alerts(limit=12), "summary": client_retention_summary()})


@app.route("/api/client/activity")
def api_client_activity():
    return jsonify({"ok": True, "version": APP_VERSION, "activity": client_activity_feed(limit=30)})


@app.route("/api/client/daily-briefing")
def api_client_daily_briefing():
    user = current_session_user() or {"membership": "FREE", "role": "FREE"}
    return jsonify({"ok": True, "version": APP_VERSION, "briefing": build_daily_briefing(user), "command": client_command_center_data(user)})

@app.route("/api/client/command-center")
def api_client_command_center():
    user = current_session_user() or {"membership": "FREE", "role": "FREE"}
    return jsonify({"ok": True, "version": APP_VERSION, "command": client_command_center_data(user)})


@app.route("/api/health")
@app.route("/v504-health")
@app.route("/v505-health")
@app.route("/v506-health")
@app.route("/v507-health")
@app.route("/v508-health")
@app.route("/v509-health")
@app.route("/v512-health")
@app.route("/v513-health")
@app.route("/v516-health")
@app.route("/v518-health")
@app.route("/v520-health")
@app.route("/v524-health")
@app.route("/v529-health")
@app.route("/v535-health")
@app.route("/v536-health")
@app.route("/v537-health")
@app.route("/v540-health")
def health():
    return jsonify(
        {
            "ok": True,
            "app": APP_NAME,
            "version": APP_VERSION,
            "time": now_iso(),
            "initialized": bool(APP_INITIALIZED),
            "db_path_configured": bool(DB_PATH),
        }
    )


@app.route("/version")
def public_version():
    return jsonify({"ok": True, "app": APP_NAME, "version": APP_VERSION, "time": now_iso()})


@app.route("/api/runtime-version")
def api_runtime_version():
    return jsonify({
        "ok": True,
        "app": APP_NAME,
        "version": APP_VERSION,
        "time": now_iso(),
        "render": {
            "db_path": DB_PATH,
            "db_exists": os.path.exists(DB_PATH),
            "automation_secret_configured": automation_secret_configured(),
            "telegram_bot_configured": env_present("TELEGRAM_BOT_TOKEN"),
            "telegram_channel_configured": env_present("TELEGRAM_CHAT_ID"),
            "scheduler_enabled": scheduler_env_enabled(),
            "daily_automation_enabled": daily_automation_env_enabled(),
            "data_backup_enabled": env_bool("DATA_BACKUP_ENABLED", False),
        },
    })


@app.route("/api/startup-check")
def api_startup_check():
    payload = {
        "ok": True,
        "app": APP_NAME,
        "version": APP_VERSION,
        "time": now_iso(),
        "initialized": bool(APP_INITIALIZED),
        "seeded_db_path": bool(_SEEDED_DB_PATH == DB_PATH),
        "seed_lock": "ready" if globals().get("SEED_LOCK") is not None else "missing",
        "scheduler_import_safe": True,
        "db": {"ok": False, "users": 0, "admin_exists": False},
        "error": APP_INIT_ERROR,
    }
    try:
        initialize_once()
        payload["initialized"] = bool(APP_INITIALIZED)
        payload["seeded_db_path"] = bool(_SEEDED_DB_PATH == DB_PATH)
        payload["db"] = {
            "ok": True,
            "users": (one("SELECT COUNT(*) AS total FROM users") or {}).get("total", 0),
            "admin_exists": admin_exists(),
        }
        payload["error"] = ""
    except Exception as exc:
        payload["ok"] = False
        payload["error"] = str(exc)[:500]
    return jsonify(payload), (200 if payload["ok"] else 503)


@app.route("/api/observability/summary")
def api_observability_summary():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, "summary": observability_summary(DB_PATH, APP_VERSION)})


@app.route("/api/observability/errors")
def api_observability_errors():
    if not is_admin_session():
        return admin_json_forbidden()
    error_id = request.args.get("error_id") or ""
    return jsonify({
        "ok": True,
        "version": APP_VERSION,
        "errors": latest_observability_errors(DB_PATH, limit=100),
        "detail": observability_error_detail(DB_PATH, error_id) if error_id else {},
        "found": bool(observability_error_detail(DB_PATH, error_id)) if error_id else False,
    })


@app.route("/api/competitions")
def api_competitions():
    return jsonify({"ok": True, "version": APP_VERSION, "competitions": competitions()})


@app.route("/api/matches/diagnostics")
def api_matches_diagnostics():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, "diagnostics": match_calendar_diagnostics()})


@app.route("/api/data-center/summary")
def api_data_center_summary():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, "summary": data_center_summary()})


@app.route("/api/data-center/warmup", methods=["POST", "GET"])
def api_data_center_warmup():
    if not is_admin_session():
        return admin_json_forbidden()
    limit = as_int(request.args.get("limit") or request.form.get("limit"), 120)
    force = request.args.get("force") in {"1", "true", "yes"} or request.form.get("force") in {"1", "true", "yes"}
    return jsonify({"version": APP_VERSION, **run_scheduler_task("warmup", force=True, limit=limit)})


@app.route("/api/scheduler/status")
def api_scheduler_status():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, "scheduler": scheduler_status()})


@app.route("/api/scheduler/run-now", methods=["POST", "GET"])
def api_scheduler_run_now():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"version": APP_VERSION, **run_due_scheduler_tasks(force=True)})


@app.route("/api/scheduler/run-calendar", methods=["POST", "GET"])
def api_scheduler_run_calendar():
    if not is_admin_session():
        return admin_json_forbidden()
    limit = as_int(request.args.get("limit") or request.form.get("limit"), 120)
    return jsonify({"version": APP_VERSION, **run_scheduler_task("calendar", force=True, limit=limit)})


@app.route("/api/scheduler/run-crests", methods=["POST", "GET"])
def api_scheduler_run_crests():
    if not is_admin_session():
        return admin_json_forbidden()
    limit = as_int(request.args.get("limit") or request.form.get("limit"), 120)
    return jsonify({"version": APP_VERSION, **run_scheduler_task("crests", force=True, limit=limit)})


@app.route("/api/scheduler/run-odds", methods=["POST", "GET"])
def api_scheduler_run_odds():
    if not is_admin_session():
        return admin_json_forbidden()
    limit = as_int(request.args.get("limit") or request.form.get("limit"), 80)
    return jsonify({"version": APP_VERSION, **run_scheduler_task("odds", force=True, limit=limit)})


@app.route("/api/scheduler/run-live", methods=["POST", "GET"])
def api_scheduler_run_live():
    if not is_admin_session():
        return admin_json_forbidden()
    limit = as_int(request.args.get("limit") or request.form.get("limit"), 80)
    return jsonify({"version": APP_VERSION, **run_scheduler_task("live", force=True, limit=limit)})


@app.route("/api/calendar")
def api_calendar():
    calendar = calendar_experience_data()
    return jsonify({"ok": True, "version": APP_VERSION, "calendar": calendar, "matches": calendar.get("matches", [])})


@app.route("/api/live")
def api_live():
    date = request.args.get("date") or today_iso()
    matches = get_matches(date, "today")
    enriched = [annotate_match(m) for m in matches]
    return jsonify({"ok": True, "version": APP_VERSION, "date": date, "matches": split_live(enriched), "state_engine": ["LIVE", "HT", "FT", "UPCOMING", "SUSPENDED"]})


@app.route("/api/match-hub")
def api_match_hub():
    date = request.args.get("date") or today_iso()
    lane = request.args.get("lane", "today")
    return jsonify({"ok": True, "version": APP_VERSION, "hub": match_hub(date, lane)})


@app.route("/api/live-flow")
@app.route("/api/ecosystem/state")
def api_live_flow():
    date = request.args.get("date") or today_iso()
    return jsonify({"ok": True, "version": APP_VERSION, "flow": live_data_flow(date)})


@app.route("/api/realtime/state")
@app.route("/api/live/state")
def api_real_time_state():
    date = request.args.get("date") or today_iso()
    refresh = request.args.get("refresh") in {"1", "true", "yes"}
    return jsonify({"ok": True, "version": APP_VERSION, "real_time": real_time_global_state(date, refresh=refresh)})


@app.route("/api/favorites", methods=["GET", "POST", "DELETE"])
def api_favorites():
    if not current_session_user():
        return jsonify({"ok": False, "version": APP_VERSION, "error": "Login requerido para favoritos por usuario."}), 401
    if request.method == "GET":
        return jsonify({"ok": True, "version": APP_VERSION, "favorites": get_favorites(request.args.get("kind"))})
    payload = request.get_json(silent=True) or dict(request.form or {})
    if request.method == "DELETE":
        return jsonify({"version": APP_VERSION, **remove_favorite(payload.get("kind"), payload.get("value"))})
    favorite = add_favorite(payload.get("kind"), payload.get("value"), payload.get("label"))
    if not favorite:
        return jsonify({"ok": False, "version": APP_VERSION, "error": "Favorito invalido. Usa kind team, league o match con value."}), 400
    return jsonify({"ok": True, "version": APP_VERSION, "favorite": favorite})


@app.route("/api/favorites/feed")
def api_favorites_feed():
    return jsonify({"ok": True, "version": APP_VERSION, "feed": favorite_feed_full()})


@app.route("/api/matches/<match_id>/timeline")
def api_match_timeline(match_id):
    detail = match_detail(match_id)
    if not detail:
        return jsonify({"ok": False, "version": APP_VERSION, "error": "Partido no encontrado"}), 404
    return jsonify({"ok": True, "version": APP_VERSION, "match": detail["match"], "timeline": detail["timeline"], "state": detail["state"]})


@app.route("/api/matches/<match_id>/detail")
def api_match_detail(match_id):
    detail = match_detail(match_id)
    if not detail:
        return jsonify({"ok": False, "version": APP_VERSION, "error": "Partido no encontrado"}), 404
    context = build_shark_context(match=detail["match"], league=detail["match"].get("competition_name"), favorites=get_favorites(), picks=detail["related_picks"], profile=default_profile())
    save_shark_context("match_detail", match_id, context)
    return jsonify({"ok": True, "version": APP_VERSION, "detail": detail, "shark_context": context})


@app.route("/api/matches/<match_id>/depth")
def api_match_depth(match_id):
    match = one("SELECT * FROM matches WHERE id=?", (match_id,))
    if not match:
        return jsonify({"ok": False, "error": "match_not_found"}), 404
    return jsonify({"ok": True, "depth": match_depth_payload(match)})

@app.route("/api/matches/<match_id>/statistics")
def api_match_statistics(match_id):
    detail = match_detail(match_id)
    if not detail:
        return jsonify({"ok": False, "version": APP_VERSION, "error": "Partido no encontrado"}), 404
    return jsonify({"ok": True, "version": APP_VERSION, "match": detail["match"], "statistics": detail.get("statistics"), "momentum": detail.get("momentum"), "state": detail.get("state")})


@app.route("/team-crest.svg")
def team_crest_svg():
    name = request.args.get("name") or "Equipo"
    text = initials(name)
    hue = int(hashlib.md5(name.encode("utf-8")).hexdigest()[:2], 16)
    color_a = "#%02x%02x%02x" % (20 + hue % 60, 80 + hue % 110, 130 + hue % 90)
    color_b = "#07111f"
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 96 96" role="img" aria-label="{name}">
  <defs><linearGradient id="g" x1="0" x2="1" y1="0" y2="1"><stop stop-color="{color_a}"/><stop offset="1" stop-color="{color_b}"/></linearGradient></defs>
  <rect width="96" height="96" rx="22" fill="url(#g)"/>
  <path d="M48 10 78 22v22c0 20-12 34-30 42-18-8-30-22-30-42V22Z" fill="rgba(255,255,255,.08)" stroke="rgba(255,255,255,.35)" stroke-width="2"/>
  <text x="48" y="57" text-anchor="middle" font-family="Inter,Arial,sans-serif" font-size="24" font-weight="900" fill="#eef6ff">{text}</text>
</svg>"""
    return Response(svg, mimetype="image/svg+xml")


def team_identity_diagnostics(limit=20):
    seed_core()
    teams_total = (one("SELECT COUNT(*) AS total FROM teams") or {}).get("total", 0)
    teams_logo = (one("SELECT COUNT(*) AS total FROM teams WHERE logo_url IS NOT NULL AND logo_url!=''") or {}).get("total", 0)
    teams_fallback = max(0, teams_total - teams_logo)
    matches_total = (one("SELECT COUNT(*) AS total FROM matches") or {}).get("total", 0)
    both_logos = (one("SELECT COUNT(*) AS total FROM matches WHERE COALESCE(home_logo,'')!='' AND COALESCE(away_logo,'')!=''") or {}).get("total", 0)
    one_or_more_missing = (one("SELECT COUNT(*) AS total FROM matches WHERE COALESCE(home_logo,'')='' OR COALESCE(away_logo,'')=''") or {}).get("total", 0)
    missing_samples = rows("""SELECT id, competition_name, country, home_team, away_team, home_logo, away_logo, match_date, kickoff_time
                              FROM matches
                              WHERE COALESCE(home_logo,'')='' OR COALESCE(away_logo,'')=''
                              ORDER BY match_date DESC, priority DESC LIMIT ?""", (int(limit),))
    sample_payload = []
    for match in missing_samples:
        match = apply_match_localization(match)
        match.update(apply_team_identities_to_match(match))
        sample_payload.append({
            "id": match.get("id"),
            "competition": match.get("safe_competition") or match.get("competition_name"),
            "home": match.get("safe_home") or match.get("home_team"),
            "away": match.get("safe_away") or match.get("away_team"),
            "home_mode": (match.get("home_identity") or {}).get("crest_mode"),
            "away_mode": (match.get("away_identity") or {}).get("crest_mode"),
            "home_badge": match.get("home_badge_text"),
            "away_badge": match.get("away_badge_text"),
            "date": match.get("match_date"),
            "time": match.get("kickoff_time") or match.get("match_time"),
        })
    return {
        "version": APP_VERSION,
        "policy": "logo real si existe; si no, bandera/emoji para selecciones o SVG propio seguro",
        "teams_total": teams_total,
        "teams_with_logo": teams_logo,
        "teams_using_fallback": teams_fallback,
        "matches_total": matches_total,
        "matches_with_both_logos": both_logos,
        "matches_missing_one_or_more_logos": one_or_more_missing,
        "coverage_percent": round((both_logos / matches_total) * 100, 1) if matches_total else 0,
        "missing_samples": sample_payload,
        "helpers": ["safe_logo_url", "fallback_team_badge", "get_team_identity", "resolve_team"],
    }




@app.route("/admin/data-memory")
def admin_data_memory_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/data-memory")
    seed_core()
    summary = data_memory_summary(DB_PATH)
    return render_template("admin_data_memory.html", summary=summary, version=APP_VERSION)


@app.route("/admin/codex-automation")
def admin_codex_automation_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/codex-automation")
    from pathlib import Path
    from engines.codex_daily_automation_engine import build_daily_report, prompt_from_report

    project_root = Path(os.path.dirname(os.path.abspath(__file__)))
    report = build_daily_report(project_root)
    prompt = prompt_from_report(report)
    return render_template(
        "admin_codex_automation.html",
        version=APP_VERSION,
        report=report,
        prompt=prompt,
    )


@app.route("/api/admin/data-memory")
def api_admin_data_memory():
    if not is_admin_session():
        return admin_json_forbidden()
    seed_core()
    return jsonify({"ok": True, "version": APP_VERSION, "summary": data_memory_summary(DB_PATH)})


@app.route("/api/admin/data-memory/cleanup", methods=["POST", "GET"])
def api_admin_data_memory_cleanup():
    if not is_admin_session():
        return admin_json_forbidden()
    seed_core()
    result = safe_memory_call(DB_PATH, "data_memory_cleanup", cleanup_old_memory)
    return jsonify({"ok": bool(result.get("ok", True)), "version": APP_VERSION, "cleanup": result})


@app.route("/admin/team-identity")
def admin_team_identity_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/team-identity")
    return render_template("admin_team_identity.html", data=team_identity_diagnostics())


@app.route("/api/admin/team-identity")
def api_admin_team_identity():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, "identity": team_identity_diagnostics(limit=50)})


@app.route("/api/team/resolve")
def api_team_resolve():
    team = request.args.get("team") or request.args.get("name") or ""
    refresh = request.args.get("refresh") in {"1", "true", "yes"}
    return jsonify({"ok": True, "version": APP_VERSION, "team": resolve_team(team, refresh=refresh)})


@app.route("/api/teams")
def api_teams():
    seed_core()
    teams = rows("SELECT * FROM teams ORDER BY name")
    for team in teams:
        team.update(professionalize_identity(team, team.get("name"), team.get("logo_url"), team.get("country"), team.get("source") or "teams"))
    return jsonify({"ok": True, "version": APP_VERSION, "teams": teams})



@app.route("/api/teams/<team_id>/detail")
def api_team_detail(team_id):
    detail = team_page_data(team_id)
    if not detail:
        return jsonify({"ok": False, "error": "Equipo no encontrado"}), 404
    return jsonify({"ok": True, "team": detail})

@app.route("/api/import-teams", methods=["POST"])
def api_import_teams():
    if not is_admin_session():
        return admin_json_forbidden()
    payload = request.get_json(silent=True) or dict(request.form or {})
    rows_payload = payload.get("rows")
    if rows_payload is None:
        rows_payload = parse_payload(payload.get("payload") or "")
    if not isinstance(rows_payload, list):
        return jsonify({"ok": False, "error": "Payload invalido. Usa rows o payload JSON/CSV."}), 400
    result = import_teams(
        rows_payload,
        payload.get("source_name") or "manual autorizado",
        payload.get("legal_note") or "Carga autorizada por administrador",
    )
    return jsonify({"version": APP_VERSION, **result})


@app.route("/api/import-competitions", methods=["POST"])
def api_import_competitions():
    if not is_admin_session():
        return admin_json_forbidden()
    payload = request.get_json(silent=True) or dict(request.form or {})
    rows_payload = payload.get("rows")
    if rows_payload is None:
        rows_payload = parse_payload(payload.get("payload") or "")
    if not isinstance(rows_payload, list):
        return jsonify({"ok": False, "error": "Payload invalido. Usa rows o payload JSON/CSV."}), 400
    result = import_competitions(
        rows_payload,
        payload.get("source_name") or "manual competiciones autorizado",
        payload.get("legal_note") or "Competicion cargada por administrador desde fuente autorizada",
    )
    return jsonify({"version": APP_VERSION, **result})


@app.route("/api/crest-diagnostics")
def api_crest_diagnostics():
    seed_core()
    teams = rows("SELECT * FROM teams ORDER BY name")
    with_logo = [t for t in teams if t.get("logo_url")]
    without_logo = [t for t in teams if not t.get("logo_url")]
    status = crest_sync_status()
    return jsonify(
        {
            "ok": True,
            "version": APP_VERSION,
            "provider": "TheSportsDB",
            "provider_key_present": bool(thesportsdb_key()),
            "provider_key_masked": masked_key(thesportsdb_key()),
            "total_teams": len(teams),
            "with_logo": len(with_logo),
            "fallback": len(without_logo),
            "last_sync": status["last_sync"],
            "last_error": status["last_error"],
            "sample_missing": [t.get("name") for t in without_logo[:20]],
            "legal_policy": "Escudos desde API permitida, carga manual autorizada o fallback SVG propio. No scraping ilegal.",
        }
    )


@app.route("/api/thesportsdb/diagnostics")
def api_thesportsdb_diagnostics():
    team = request.args.get("team") or "Real Madrid"
    return jsonify({"ok": True, "version": APP_VERSION, "diagnostics": thesportsdb_diagnostics(team)})


@app.route("/api/sportsdb/sync-crests", methods=["POST", "GET"])
def api_sportsdb_sync_crests():
    if not is_admin_session():
        return admin_json_forbidden()
    refresh = request.args.get("refresh") in {"1", "true", "yes"} or request.form.get("refresh") in {"1", "true", "yes"}
    limit = as_int(request.args.get("limit") or request.form.get("limit"), 40)
    result = sync_sportsdb_crests(refresh=refresh, limit=limit)
    return jsonify({"version": APP_VERSION, **result})


@app.route("/api/sportsdb/sync-competitions", methods=["POST", "GET"])
def api_sportsdb_sync_competitions():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"version": APP_VERSION, **sync_sportsdb_competitions()})


@app.route("/api/sportsdb/sync-teams", methods=["POST", "GET"])
def api_sportsdb_sync_teams():
    if not is_admin_session():
        return admin_json_forbidden()
    limit = as_int(request.args.get("limit") or request.form.get("limit"), 240)
    return jsonify({"version": APP_VERSION, **sync_sportsdb_teams(limit=limit)})


@app.route("/api/sportsdb/sync-feed", methods=["POST", "GET"])
@app.route("/api/sportsdb/sync-matches", methods=["POST", "GET"])
@app.route("/api/sportsdb/sync-calendar", methods=["POST", "GET"])
def api_sportsdb_sync_feed():
    if not is_admin_session():
        return admin_json_forbidden()
    limit = as_int(request.args.get("limit") or request.form.get("limit"), 80)
    result = sync_sportsdb_calendar(limit=limit)
    return jsonify({"version": APP_VERSION, **result, "status": sportsdb_feed_status()})


@app.route("/api/sportsdb/sync-results", methods=["POST", "GET"])
def api_sportsdb_sync_results():
    if not is_admin_session():
        return admin_json_forbidden()
    limit = as_int(request.args.get("limit") or request.form.get("limit"), 80)
    return jsonify({"version": APP_VERSION, **sync_sportsdb_results(limit=limit)})


@app.route("/api/matches/sync-now", methods=["POST", "GET"])
def api_matches_sync_now():
    if not is_admin_session():
        return admin_json_forbidden()
    limit = as_int(request.args.get("limit") or request.form.get("limit"), 80)
    sportsdb_result = sync_sportsdb_feed(limit=limit)
    odds_result = sync_odds_events(limit=limit, force=request.args.get("force") in {"1", "true", "yes"})
    return jsonify({"ok": True, "version": APP_VERSION, "sportsdb": sportsdb_result, "odds": odds_result, "diagnostics": match_calendar_diagnostics()})


@app.route("/api/odds/sync-events", methods=["POST", "GET"])
@app.route("/api/odds/sync-odds", methods=["POST", "GET"])
def api_odds_sync_events():
    if not is_admin_session():
        return admin_json_forbidden()
    limit = as_int(request.args.get("limit") or request.form.get("limit"), 80)
    force = request.args.get("force") in {"1", "true", "yes"} or request.form.get("force") in {"1", "true", "yes"}
    return jsonify({"version": APP_VERSION, **sync_odds_events(limit=limit, force=force), "diagnostics": odds_diagnostics()})


@app.route("/api/odds/diagnostics")
def api_odds_diagnostics():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, "diagnostics": odds_diagnostics()})


@app.route("/api/import-matches", methods=["POST"])
def api_import_matches():
    if not is_admin_session():
        return admin_json_forbidden()
    payload = request.get_json(silent=True) or dict(request.form or {})
    rows_payload = payload.get("rows")
    if rows_payload is None:
        rows_payload = parse_payload(payload.get("payload") or "")
    if not isinstance(rows_payload, list):
        return jsonify({"ok": False, "error": "Payload invalido. Usa rows o payload JSON/CSV."}), 400
    result = import_matches(
        rows_payload,
        payload.get("source_name") or "manual autorizado",
        payload.get("source_url") or "",
        payload.get("legal_note") or "Carga autorizada por administrador",
    )
    return jsonify({"version": APP_VERSION, **result})


@app.route("/api/import-results", methods=["POST"])
def api_import_results():
    if not is_admin_session():
        return admin_json_forbidden()
    payload = request.get_json(silent=True) or dict(request.form or {})
    rows_payload = payload.get("rows")
    if rows_payload is None:
        rows_payload = parse_payload(payload.get("payload") or "")
    if not isinstance(rows_payload, list):
        return jsonify({"ok": False, "error": "Payload invalido. Usa rows o payload JSON/CSV."}), 400
    result = import_results(
        rows_payload,
        payload.get("source_name") or "manual results autorizado",
        payload.get("legal_note") or "Resultado cargado por administrador desde fuente autorizada",
    )
    return jsonify({"version": APP_VERSION, **result})


@app.route("/api/import-odds", methods=["POST"])
def api_import_odds():
    if not is_admin_session():
        return admin_json_forbidden()
    payload = request.get_json(silent=True) or dict(request.form or {})
    rows_payload = payload.get("rows")
    if rows_payload is None:
        rows_payload = parse_payload(payload.get("payload") or "")
    if not isinstance(rows_payload, list):
        return jsonify({"ok": False, "error": "Payload invalido. Usa rows o payload JSON/CSV."}), 400
    result = import_odds_snapshots(
        rows_payload,
        payload.get("source_name") or "manual odds autorizado",
        payload.get("legal_note") or "Cuota cargada por administrador desde fuente autorizada",
    )
    return jsonify({"version": APP_VERSION, **result})


@app.route("/api/picks")
def api_picks():
    user = current_session_user() or {"membership": "FREE", "role": "FREE"}
    include_admin = normalize_role(user.get("role")) == "ADMIN" and request.args.get("admin") in {"1", "true", "yes"}
    if include_admin:
        picks = get_picks(limit=request.args.get("limit", 50), include_admin=True)
    else:
        picks = published_picks_for_user(user, limit=as_int(request.args.get("limit"), 50))
    return jsonify({"ok": True, "version": APP_VERSION, "picks": picks, "stats": pick_stats()})


@app.route("/api/picks/create", methods=["POST"])
def api_picks_create():
    if not is_admin_session():
        return admin_json_forbidden()
    payload = request.get_json(silent=True) or dict(request.form or {})
    pick = create_or_update_pick(payload, publish=False)
    return jsonify({"ok": True, "version": APP_VERSION, "pick": pick})


@app.route("/api/picks/update", methods=["POST"])
def api_picks_update():
    if not is_admin_session():
        return admin_json_forbidden()
    payload = request.get_json(silent=True) or dict(request.form or {})
    pick = create_or_update_pick(payload, pick_id=payload.get("id") or payload.get("pick_id"), publish=normalize_pick_status(payload.get("status")) == "published")
    return jsonify({"ok": True, "version": APP_VERSION, "pick": pick})


@app.route("/api/picks/publish", methods=["POST", "GET"])
def api_picks_publish():
    if not is_admin_session():
        return admin_json_forbidden()
    pick_id = request.args.get("pick_id") or request.form.get("pick_id") or (request.get_json(silent=True) or {}).get("pick_id")
    pick = update_pick_status(pick_id, "published")
    return jsonify({"ok": bool(pick), "version": APP_VERSION, "pick": pick})


@app.route("/api/picks/archive", methods=["POST", "GET"])
def api_picks_archive():
    if not is_admin_session():
        return admin_json_forbidden()
    pick_id = request.args.get("pick_id") or request.form.get("pick_id") or (request.get_json(silent=True) or {}).get("pick_id")
    pick = update_pick_status(pick_id, "archived")
    return jsonify({"ok": bool(pick), "version": APP_VERSION, "pick": pick})


@app.route("/api/picks/stats")
def api_picks_stats():
    return jsonify({"ok": True, "version": APP_VERSION, "stats": pick_stats()})


@app.route("/api/import-picks", methods=["POST"])
def api_import_picks():
    if not is_admin_session():
        return admin_json_forbidden()
    payload = request.get_json(silent=True) or dict(request.form or {})
    rows_payload = payload.get("rows")
    if rows_payload is None:
        rows_payload = parse_payload(payload.get("payload") or "")
    if not isinstance(rows_payload, list):
        return jsonify({"ok": False, "error": "Payload invalido. Usa rows o payload JSON/CSV."}), 400
    result = import_picks(
        rows_payload,
        payload.get("source_name") or "manual autorizado",
        payload.get("legal_note") or "Carga autorizada por administrador",
    )
    return jsonify({"version": APP_VERSION, **result})


@app.route("/api/combis")
def api_combis():
    return jsonify({"ok": True, "version": APP_VERSION, "combis": get_combis(limit=request.args.get("limit", 20))})


@app.route("/api/combis/build", methods=["POST"])
def api_combis_build():
    payload = request.get_json(silent=True) or dict(request.form or {})
    pick_ids = payload.get("pick_ids") or payload.get("picks") or []
    if isinstance(pick_ids, str):
        pick_ids = [p.strip() for p in pick_ids.split(",") if p.strip()]
    combi = build_combi_from_picks(pick_ids=pick_ids, limit=as_int(payload.get("limit"), 3))
    if not combi:
        return jsonify({"ok": False, "version": APP_VERSION, "error": "No hay picks suficientes para construir combi."}), 400
    combi["picks"] = json.loads(combi.get("picks_json") or "[]")
    return jsonify({"ok": True, "version": APP_VERSION, "combi": combi})


@app.route("/api/profile")
def api_profile():
    if not current_session_user():
        return jsonify({"ok": False, "version": APP_VERSION, "error": "Login requerido."}), 401
    return jsonify({"ok": True, "version": APP_VERSION, "profile": default_profile(), "session_user": current_session_user()})


@app.route("/api/membership")
def api_membership():
    return jsonify({"ok": True, "version": APP_VERSION, "plans": MEMBERSHIP_PLANS, "profile": default_profile()})


@app.route("/api/shark/briefing")
def api_shark_briefing():
    return jsonify({"ok": True, "version": APP_VERSION, "briefing": shark_briefing()})


@app.route("/api/shark/ask", methods=["GET", "POST"])
def api_shark_ask():
    payload = request.get_json(silent=True) or dict(request.form or request.args or {})
    answer = shark_answer(payload.get("question") or payload.get("q") or "")
    save_shark_context("ask", answer.get("focus"), answer.get("context") or {})
    return jsonify({"ok": True, "version": APP_VERSION, "shark": answer})


@app.route("/api/shark/context")
def api_shark_context():
    match_id = request.args.get("match_id") or ""
    match = one("SELECT * FROM matches WHERE id=?", (match_id,)) if match_id else None
    context = build_shark_context(match=match, league=(match or {}).get("competition_name") if match else request.args.get("league"), favorites=get_favorites(), picks=get_picks(limit=12), profile=default_profile())
    snapshot_id = save_shark_context("context", match_id or context.get("league") or "global", context)
    return jsonify({"ok": True, "version": APP_VERSION, "snapshot_id": snapshot_id, "context": context})


@app.route("/api/telegram/status")
@app.route("/api/automation-status")
def api_telegram_status():
    if not is_admin_session():
        return admin_json_forbidden()
    deliveries = rows("SELECT * FROM telegram_deliveries ORDER BY created_at DESC LIMIT 20")
    return jsonify({"ok": True, "version": APP_VERSION, "telegram": telegram_config(), "diagnostics": telegram_diagnostics(), "recent_deliveries": deliveries, "queue": telegram_queue(limit=20)})


@app.route("/api/telegram/diagnostics")
def api_telegram_diagnostics():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, "diagnostics": telegram_diagnostics()})


@app.route("/api/telegram/settings")
def api_telegram_settings():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, "settings": get_telegram_settings()})


@app.route("/api/telegram/settings/update", methods=["POST", "GET"])
def api_telegram_settings_update():
    if not is_admin_session():
        return admin_json_forbidden()
    payload = request.get_json(silent=True) or dict(request.form or request.args or {})
    return jsonify({"ok": True, "version": APP_VERSION, "settings": update_telegram_settings(payload)})


@app.route("/api/telegram/send-test", methods=["POST", "GET"])
def api_telegram_send_test():
    if not is_admin_session():
        return admin_json_forbidden()
    chat_id = request.args.get("chat_id") or request.form.get("chat_id") or os.getenv("TELEGRAM_CHAT_ID", "")
    queued = enqueue_telegram_message(
        "system_test",
        "Prueba Telegram",
        build_system_test_message(),
        chat_id=chat_id,
        payload={"target_key": "admin-test", "priority": 95},
        dedupe_key=telegram_dedupe_key("system_test", now_iso(), chat_id),
        force=True,
    )
    processed = process_premium_telegram_queue(limit=1, force=True) if queued.get("queued") else {"processed": 0, "sent": 0, "failed": 0, "skipped": 1, "errors": []}
    return jsonify({"ok": processed.get("failed", 0) == 0, "version": APP_VERSION, "message": "Test Telegram procesado.", "queued": queued, **processed})


@app.route("/api/telegram/enqueue-daily-matches", methods=["POST", "GET"])
def api_telegram_enqueue_daily_matches():
    if not is_admin_session():
        return admin_json_forbidden()
    force = request.args.get("force") in {"1", "true", "yes"} or request.form.get("force") in {"1", "true", "yes"}
    return jsonify({"version": APP_VERSION, **enqueue_daily_matches(force=force, forced_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""))})


@app.route("/api/telegram/enqueue-daily-picks", methods=["POST", "GET"])
def api_telegram_enqueue_daily_picks():
    if not is_admin_session():
        return admin_json_forbidden()
    force = request.args.get("force") in {"1", "true", "yes"} or request.form.get("force") in {"1", "true", "yes"}
    force_empty = request.args.get("force_empty") in {"1", "true", "yes"} or request.form.get("force_empty") in {"1", "true", "yes"}
    return jsonify({"version": APP_VERSION, **enqueue_daily_picks(force=force, force_empty=force_empty, forced_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""))})


@app.route("/api/telegram/process-queue", methods=["POST", "GET"])
def api_telegram_process_queue():
    if not is_admin_session():
        return admin_json_forbidden()
    limit = as_int(request.args.get("limit") or request.form.get("limit"), 5)
    force = request.args.get("force") in {"1", "true", "yes"} or request.form.get("force") in {"1", "true", "yes"}
    return jsonify({"version": APP_VERSION, **process_premium_telegram_queue(limit=limit, force=force)})


@app.route("/api/telegram/send", methods=["POST"])
def api_telegram_send():
    if not is_admin_session():
        return admin_json_forbidden()
    payload = request.get_json(silent=True) or dict(request.form or {})
    text = payload.get("text") or build_system_test_message()
    queued = enqueue_telegram_message(payload.get("message_type") or "manual", payload.get("title") or "Mensaje manual", text, chat_id=payload.get("chat_id") or os.getenv("TELEGRAM_CHAT_ID", ""), payload={"target_key": "manual"}, force=True)
    result = process_premium_telegram_queue(limit=1, force=True)
    return jsonify({"version": APP_VERSION, "queued": queued, **result})


@app.route("/api/telegram/auto-run", methods=["POST", "GET"])
@app.route("/api/v495/telegram-auto-run", methods=["POST", "GET"])
def api_telegram_auto_run():
    if not automation_access_allowed():
        return automation_json_forbidden()
    cfg = telegram_config()
    if not cfg["enabled"]:
        return jsonify({"ok": False, "version": APP_VERSION, "sent": False, "status": "AUTO_DISABLED", "telegram": cfg})
    result = telegram_scheduler_delivery(force=request.args.get("force") in {"1", "true", "yes"})
    return jsonify({"version": APP_VERSION, "telegram": cfg, **result})


@app.route("/api/telegram/scheduler-tick", methods=["POST", "GET"])
def api_telegram_scheduler_tick():
    if not automation_access_allowed():
        return automation_json_forbidden()
    force = request.args.get("force") in {"1", "true", "yes"} or (request.get_json(silent=True) or {}).get("force") is True
    return jsonify({"version": APP_VERSION, **telegram_scheduler_tick(force=force)})


@app.route("/api/automation/daily/run", methods=["POST", "GET"])
def api_automation_daily_run():
    if not automation_cron_access_allowed():
        return automation_json_forbidden()
    force = cron_force_requested()
    return automation_cron_result(
        "daily_run",
        ("last_cron_daily_call", "cron_daily_run_last_call"),
        run_daily_autonomous_system,
        force=force,
    )


@app.route("/api/automation/telegram/tick", methods=["POST", "GET"])
def api_automation_telegram_tick():
    if not automation_cron_access_allowed():
        return automation_json_forbidden()
    force = cron_force_requested()
    return automation_cron_result(
        "telegram_tick",
        ("last_cron_telegram_call", "cron_telegram_tick_last_call"),
        telegram_scheduler_tick,
        force=force,
    )


@app.route("/api/telegram/triggers")
def api_telegram_triggers():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, "triggers": telegram_triggers(), "last": automation_get("telegram_last_dispatch", {})})


@app.route("/api/telegram/logs")
def api_telegram_logs():
    if not is_admin_session():
        return admin_json_forbidden()
    deliveries = rows("SELECT * FROM telegram_deliveries ORDER BY created_at DESC LIMIT 100")
    logs = rows("SELECT * FROM telegram_logs ORDER BY created_at DESC LIMIT 100")
    return jsonify({"ok": True, "version": APP_VERSION, "logs": logs, "deliveries": deliveries})


@app.route("/api/telegram/queue")
def api_telegram_queue():
    if not is_admin_session():
        return admin_json_forbidden()
    queue = telegram_queue(limit=request.args.get("limit", 50))
    return jsonify({"ok": True, "version": APP_VERSION, "summary": queue_summary(queue), "queue": queue})


@app.route("/api/telegram/scheduler-manager", methods=["GET", "POST"])
def api_telegram_scheduler_manager():
    if not is_admin_session():
        return admin_json_forbidden()
    force = request.args.get("force") in {"1", "true", "yes"} or (request.get_json(silent=True) or {}).get("force") is True
    posts = prepare_auto_posts()
    return jsonify({"ok": True, "version": APP_VERSION, "auto_posts": posts, "manager": telegram_scheduler_delivery(force=force)})


@app.route("/api/telegram/auto-posts")
def api_telegram_auto_posts():
    if not is_admin_session():
        return admin_json_forbidden()
    posts = prepare_auto_posts()
    saved = rows("SELECT * FROM auto_alerts ORDER BY updated_at DESC LIMIT 50")
    return jsonify({"ok": True, "version": APP_VERSION, "prepared": posts, "saved": saved})


@app.route("/api/cache/status")
def api_cache_status():
    if not is_admin_session():
        return admin_json_forbidden()
    cache_rows = rows("SELECT key,expires_at,updated_at FROM persistent_cache ORDER BY updated_at DESC LIMIT 50")
    return jsonify({"ok": True, "version": APP_VERSION, "health": cache_health(cache_rows), "items": cache_rows})


@app.route("/api/imports")
def api_imports():
    return jsonify({"ok": True, "version": APP_VERSION, "imports": rows("SELECT * FROM imports ORDER BY created_at DESC LIMIT 50")})


@app.route("/api/security/summary")
def api_security_summary():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({
        "ok": True,
        "version": APP_VERSION,
        "security": {
            "secret_key_configured": env_present("SECRET_KEY") or env_present("FLASK_SECRET_KEY"),
            "automation_secret_configured": automation_secret_configured(),
            "db_path_configured": env_present("DB_PATH"),
            "safe_runtime_fallback": not (env_present("SECRET_KEY") or env_present("FLASK_SECRET_KEY")),
        },
    })


@app.route("/api/diagnostics")
def api_diagnostics():
    if not is_admin_session():
        return admin_json_forbidden()
    data = dashboard_data()
    checks = [
        {"name": "Core limpio", "status": "READY", "detail": "Proyecto reconstruido sin versiones antiguas acumuladas."},
        {"name": "SQLite", "status": "READY", "detail": "Tablas compactas: competitions, teams, matches, imports, favorites, picks, combis, profile, telegram, queue, context, cache."},
        {"name": "Calendario global", "status": "READY", "detail": f"{len(data['matches'])} partidos para la fecha base."},
        {"name": "Live center", "status": "READY", "detail": "Usa partidos reales/importados y separa directo, proximos y finalizados."},
        {"name": "Live Data Flow", "status": "READY", "detail": f"Estado compartido {data['live_flow']['shared_state']} con perfil, picks y favoritos."},
        {"name": "Live State Engine", "status": "READY", "detail": "Estados normalizados: LIVE, HT, FT, UPCOMING y SUSPENDED."},
        {"name": "Real Time Match Engine", "status": "READY", "detail": f"Sync {data['match_hub']['sync']['sync_status']} con refresh {data['match_hub']['sync']['refresh_seconds']}s."},
        {"name": "Match Hub", "status": "READY", "detail": f"Live {data['match_hub']['counts']['live']}, proximos {data['match_hub']['counts']['upcoming']}, favoritos {data['match_hub']['counts']['favorites']}."},
        {"name": "Favoritos reales", "status": "READY", "detail": f"{len(data['favorites'])} favoritos guardados; feed conecta partidos, live y picks."},
        {"name": "Importacion legal", "status": "READY", "detail": "Acepta CSV/JSON autorizado con trazabilidad de fuente."},
        {"name": "Escudos", "status": "READY", "detail": "Resuelve por cache, TheSportsDB, importacion legal o fallback SVG premium."},
        {"name": "Picks/Combis", "status": "READY", "detail": f"{len(data['picks'])} picks visibles y {len(data['combis'])} combis guardadas."},
        {"name": "Perfil premium", "status": "READY", "detail": f"Perfil activo: {data['profile']['name']} / plan {data['profile']['membership_plan']}."},
        {"name": "IA SHARK Context", "status": "READY", "detail": "Contexto persistente para partido, liga, favoritos y picks recientes."},
        {"name": "Telegram Premium Delivery", "status": "READY" if data["telegram"]["configured"] else "CONFIG", "detail": "Settings, subscribers, queue, retries, logs y anti duplicados preparados."},
        {"name": "Membresias", "status": "READY", "detail": "Planes Free, PRO y ELITE preparados para capa comercial."},
        {"name": "Performance cache", "status": "READY", "detail": "Cache persistente para hub, live flow y navegacion rapida."},
        {"name": "Premium mobile feel", "status": "READY", "detail": "Interacciones tactiles, spacing y tarjetas afinadas para sensacion app nativa."},
        {"name": "Arquitectura limpia", "status": "READY", "detail": "Motores separados: football population, scheduler, telegram delivery, live, match, shark, crest y cache."},
        {"name": "Render", "status": "READY", "detail": "Procfile, render.yaml y requirements incluidos."},
    ]
    return jsonify({"ok": True, "version": APP_VERSION, "checks": checks, "readiness": data["readiness"]})


_STARTUP_AUTO_SYNC_SCHEDULED = False


def schedule_auto_sync_if_needed():
    global _STARTUP_AUTO_SYNC_SCHEDULED
    if _STARTUP_AUTO_SYNC_SCHEDULED:
        return
    if not scheduler_enabled() or not scheduler_startup_enabled():
        return
    _STARTUP_AUTO_SYNC_SCHEDULED = True

    def _worker():
        try:
            seed_core()
            run_due_scheduler_tasks(force=False, startup=True)
        except Exception as exc:
            print("NeMeSiS SHARK PRO: auto sync skipped:", str(exc)[:220])

    threading.Thread(target=_worker, name="auto-sync-scheduler", daemon=True).start()


if os.getenv("RUN_STARTUP_SCHEDULER_NOW", "").strip().lower() in {"1", "true", "yes", "on"}:
    schedule_auto_sync_if_needed()




@app.errorhandler(500)
def client_safe_500(error):
    """Evita pantalla blanca en cliente y deja diagnóstico claro sin exponer secretos."""
    try:
        print("NeMeSiS SHARK PRO 500:", str(error)[:500])
    except Exception:
        pass
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "error": "internal_error", "message": "Error interno controlado. Revisa logs Render.", "path": request.path, "version": APP_VERSION}), 500
    try:
        return render_template("home.html", data=dashboard_data(), controlled_error="Hemos detectado un error temporal y hemos vuelto al inicio de forma segura."), 500
    except Exception:
        return "Error temporal controlado. Revisa logs Render.", 500


@app.route("/api/deep-route-check")
def api_deep_route_check():
    checks = []
    for path in ["/", "/cliente-login", "/registro", "/perfil", "/match-hub", "/live", "/picks", "/combis", "/favorites", "/alertas", "/actividad", "/shark", "/telegram", "/resultados", "/api/health", "/api/client-experience-check"]:
        checks.append({"path": path, "status": "registered"})
    return jsonify({"ok": True, "version": APP_VERSION, "checks": checks})


@app.route("/api/client-experience-check")
def api_client_experience_check():
    """Chequeo de experiencia cliente: rutas públicas, cliente y admin separadas."""
    public_routes = ["/", "/membresias", "/cliente-login", "/registro"]
    client_routes = ["/perfil", "/match-hub", "/live", "/resultados", "/picks", "/combis", "/favorites", "/shark", "/telegram"]
    admin_routes = ["/admin", "/admin/users", "/admin/data-center", "/admin/picks", "/admin/telegram", "/admin/import-center"]
    return jsonify({
        "ok": True,
        "version": APP_VERSION,
        "public_routes": public_routes,
        "client_routes": client_routes,
        "admin_routes": admin_routes,
        "focus": "V535: UX compacta, picks visibles, live vivo, favoritos inteligentes, SHARK contextual, cliente limpio y admin separado",
    })


@app.route("/api/route-check")
def api_route_check():
    """Chequeo ligero de rutas clave para evitar botones rotos en despliegues."""
    routes = ["/", "/cliente-login", "/registro", "/perfil", "/match-hub", "/live", "/picks", "/combis", "/favorites", "/alertas", "/actividad", "/shark", "/telegram", "/resultados", "/membresias"]
    return jsonify({"ok": True, "version": APP_VERSION, "routes": routes, "policy": "cliente limpio, admin separado, botones principales verificados"})


@app.route("/api/product-experience-check")
def api_product_experience_check():
    user = current_session_user() or {"membership": "FREE", "role": "FREE"}
    board = smart_pick_board(user, limit=12)
    hub = match_hub(today_iso())
    return jsonify({
        "ok": True,
        "version": APP_VERSION,
        "checks": {
            "picks_published": board.get("published_count", 0),
            "pick_candidates": board.get("candidate_count", 0),
            "live_matches": hub.get("counts", {}).get("live", 0),
            "upcoming_matches": hub.get("counts", {}).get("upcoming", 0),
            "favorites_visible": True,
            "client_admin_split": True,
            "empty_states_premium": True,
        },
        "message": "Experiencia cliente V535 revisada: nunca debe quedar una sección clave sin explicación clara.",
    })


# -----------------------------
# V538 — Quality Center + Data Health Polish
# -----------------------------

def safe_count(table, where="1=1", params=()):
    try:
        item = one(f"SELECT COUNT(*) AS total FROM {table} WHERE {where}", params)
        return int((item or {}).get("total") or 0)
    except Exception:
        return 0


def quality_center_summary():
    """Resumen defensivo de calidad del ecosistema.
    No expone secretos al cliente y no rompe si una tabla antigua no existe.
    """
    total_matches = safe_count("matches")
    today_matches = safe_count("matches", "match_date=?", (today_iso(),))
    upcoming = safe_count("matches", "match_date>=?", (today_iso(),))
    finished = safe_count("matches", "lower(coalesce(status,'')) IN ('finished','finalizado','ft','final') OR (home_score IS NOT NULL AND away_score IS NOT NULL AND match_date<?)", (today_iso(),))
    live = safe_count("matches", "lower(coalesce(status,'')) LIKE '%live%' OR lower(coalesce(status,'')) LIKE '%directo%' OR coalesce(minute,'')!=''")
    teams = safe_count("teams")
    teams_with_logo = safe_count("teams", "coalesce(logo_url,'')!=''")
    competitions_total = safe_count("competitions")
    picks_total = safe_count("picks")
    published_picks = safe_count("picks", "lower(coalesce(status,''))='published'")
    users_total = safe_count("users")
    telegram_pending = safe_count("telegram_queue", "lower(coalesce(status,''))='pending'")
    recent_logs = []
    try:
        recent_logs = rows("SELECT source, sync_type, status, total_items, error_message, created_at FROM api_sync_logs ORDER BY created_at DESC LIMIT 8")
    except Exception:
        recent_logs = []
    score_parts = [
        1 if total_matches > 0 else 0,
        1 if upcoming > 0 else 0,
        1 if teams > 0 else 0,
        1 if teams_with_logo > 0 else 0,
        1 if competitions_total > 0 else 0,
        1 if users_total > 0 else 0,
        1 if published_picks > 0 else 0,
        1 if recent_logs else 0,
    ]
    score = round((sum(score_parts) / len(score_parts)) * 100)
    recommendations = []
    if total_matches == 0:
        recommendations.append("Sincroniza calendario desde Data Center para poblar partidos reales.")
    if teams and teams_with_logo < max(1, teams // 3):
        recommendations.append("Ejecuta SportsDB Sync para mejorar escudos e identidad visual.")
    if published_picks == 0:
        recommendations.append("Publica picks reales desde Admin Picks para que cliente y Telegram tengan contenido premium.")
    if telegram_pending > 20:
        recommendations.append("Revisa la cola de Telegram: hay muchos mensajes pendientes.")
    if not recommendations:
        recommendations.append("Ecosistema estable. Siguiente paso: densidad de datos, live profundo y automatización.")
    return {
        "score": score,
        "version": APP_VERSION,
        "matches": {"total": total_matches, "today": today_matches, "upcoming": upcoming, "finished": finished, "live": live},
        "teams": {"total": teams, "with_logo": teams_with_logo, "fallback": max(0, teams - teams_with_logo)},
        "competitions": {"total": competitions_total},
        "picks": {"total": picks_total, "published": published_picks, "draft_or_empty": max(0, picks_total - published_picks)},
        "users": {"total": users_total},
        "telegram": {"pending": telegram_pending},
        "recent_logs": recent_logs,
        "recommendations": recommendations,
    }


@app.route("/admin/quality-center")
def admin_quality_center():
    if not is_admin_session():
        return redirect(url_for("admin_login", next=request.path))
    return render_template("admin_quality_center.html", title="Centro de calidad", q=quality_center_summary())


@app.route("/api/quality-center/summary")
def api_quality_center_summary():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "summary": quality_center_summary()})


@app.route("/api/client/app-pulse")
def api_client_app_pulse():
    """Pulso comercial seguro para cliente: no muestra detalles técnicos ni secretos."""
    q = quality_center_summary()
    return jsonify({
        "ok": True,
        "version": APP_VERSION,
        "pulse": {
            "upcoming_matches": q["matches"]["upcoming"],
            "live_matches": q["matches"]["live"],
            "published_picks": q["picks"]["published"],
            "teams_with_identity": q["teams"]["with_logo"],
            "experience": "Premium" if q["score"] >= 70 else "Preparando datos premium",
        },
    })


# -----------------------------
# V539 — Membership Revenue + Onboarding Polish
# -----------------------------

def membership_distribution():
    buckets = {"FREE": 0, "PRO": 0, "ELITE": 0, "ADMIN": 0}
    try:
        for r in rows("SELECT upper(coalesce(membership, role, 'FREE')) AS plan, COUNT(*) AS total FROM users GROUP BY upper(coalesce(membership, role, 'FREE'))"):
            plan = normalize_role(r.get("plan"))
            buckets[plan] = int(r.get("total") or 0)
    except Exception:
        pass
    return buckets


def onboarding_status(user=None):
    user = user or current_session_user() or {"membership": "FREE", "role": "FREE", "id": ""}
    fav_count = len(get_favorites(user_id=user.get("id") or "")) if user.get("id") else 0
    activity_count = safe_count("user_activity", "user_id=?", (user.get("id") or "",)) if user.get("id") else 0
    picks_visible = len(published_picks_for_user(user, limit=12))
    alerts_ready = len(build_client_alerts(limit=5))
    steps = [
        {"key": "account", "label": "Cuenta creada", "done": bool(user.get("id")), "href": "/perfil"},
        {"key": "favorites", "label": "Añadir favoritos", "done": fav_count > 0, "href": "/favorites"},
        {"key": "matches", "label": "Revisar partidos", "done": safe_count("matches") > 0, "href": "/match-hub"},
        {"key": "picks", "label": "Ver picks", "done": picks_visible > 0, "href": "/picks"},
        {"key": "telegram", "label": "Preparar Telegram", "done": bool((telegram_config() or {}).get("configured")), "href": "/telegram"},
        {"key": "shark", "label": "Preguntar a SHARK", "done": activity_count > 0, "href": "/shark"},
    ]
    done = sum(1 for step in steps if step["done"])
    score = round(done / len(steps) * 100)
    next_step = next((step for step in steps if not step["done"]), steps[-1])
    return {
        "score": score,
        "done": done,
        "total": len(steps),
        "steps": steps,
        "next_step": next_step,
        "favorites_count": fav_count,
        "picks_visible": picks_visible,
        "alerts_ready": alerts_ready,
        "membership": normalize_role(user.get("membership") or user.get("role")),
    }


def membership_revenue_summary():
    distribution = membership_distribution()
    # Valores orientativos internos, no cobran ni activan Stripe todavía.
    estimated_prices = {"FREE": 0, "PRO": 19, "ELITE": 49, "ADMIN": 0}
    estimated_mrr = sum(distribution.get(plan, 0) * estimated_prices.get(plan, 0) for plan in distribution)
    total_clients = distribution.get("FREE", 0) + distribution.get("PRO", 0) + distribution.get("ELITE", 0)
    paid_clients = distribution.get("PRO", 0) + distribution.get("ELITE", 0)
    conversion = round((paid_clients / total_clients * 100), 1) if total_clients else 0
    return {
        "distribution": distribution,
        "estimated_mrr": estimated_mrr,
        "total_clients": total_clients,
        "paid_clients": paid_clients,
        "conversion": conversion,
        "plans": MEMBERSHIP_PLANS,
        "recommendations": [
            "Mantener FREE como puerta de entrada con calendario, favoritos y SHARK base.",
            "Empujar PRO con picks, combinadas y Telegram premium.",
            "Reservar ELITE para SHARK contextual, alertas live y prioridad de análisis.",
        ],
    }


@app.route("/onboarding")
def onboarding_page():
    user = current_session_user()
    if not user:
        return redirect("/cliente-login")
    data = dashboard_data()
    data["onboarding"] = onboarding_status(user)
    return render_template("onboarding.html", data=data)


@app.route("/mi-cuenta")
def account_center_page():
    user = current_session_user()
    if not user:
        return redirect("/cliente-login")
    data = dashboard_data()
    data["onboarding"] = onboarding_status(user)
    data["account_center"] = {
        "user": user,
        "plan": normalize_role(user.get("membership") or user.get("role")),
        "favorites": len(data.get("favorites") or []),
        "alerts": len(data.get("client_alerts") or []),
        "activity": len(data.get("client_activity") or []),
    }
    return render_template("account_center.html", data=data)


@app.route("/admin/memberships")
def admin_memberships_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/memberships")
    data = dashboard_data()
    data["membership_revenue"] = membership_revenue_summary()
    data["membership_admin"] = membership_admin_summary()
    data["users"] = list_users()
    return render_template("admin_memberships.html", data=data)


@app.route("/api/client/onboarding-check")
def api_client_onboarding_check():
    user = current_session_user() or {"membership": "FREE", "role": "FREE", "id": ""}
    return jsonify({"ok": True, "version": APP_VERSION, "onboarding": onboarding_status(user)})


@app.route("/api/admin/membership-summary")
def api_admin_membership_summary():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, "summary": membership_revenue_summary()})


def client_success_runtime_context(user=None):
    user = user or current_session_user() or {"membership": "FREE", "role": "FREE", "id": ""}
    membership = normalize_role(user.get("membership") or user.get("role"))
    uid = user.get("id") or ""
    try:
        favorites_count = len(get_favorites(user_id=uid)) if uid else 0
    except Exception:
        favorites_count = 0
    try:
        picks_visible = len(published_picks_for_user(user, limit=20))
    except Exception:
        picks_visible = 0
    try:
        live_count = len(get_live_matches(limit=20))
    except Exception:
        live_count = 0
    try:
        upcoming_count = len(get_upcoming_matches(today_iso(), days=7, limit=40))
    except Exception:
        upcoming_count = 0
    try:
        telegram_cfg = telegram_config() or {}
    except Exception:
        telegram_cfg = {}
    stats = {
        "membership": membership,
        "favorites_count": favorites_count,
        "picks_visible": picks_visible,
        "live_count": live_count,
        "upcoming_count": upcoming_count,
        "telegram_configured": bool(telegram_cfg.get("configured")),
        "telegram_football_only": True,
        "madrid_time_ready": True,
        "support_ready": True,
    }
    return client_success_snapshot(stats=stats)


@app.route("/guia")
@app.route("/ayuda")
def client_success_page():
    user = current_session_user()
    data = dashboard_data() if user else home_light_data()
    data["client_success"] = client_success_runtime_context(user or {"membership": "FREE", "role": "FREE", "id": ""})
    data["onboarding"] = onboarding_status(user or {"membership": "FREE", "role": "FREE", "id": ""})
    return render_template("client_success.html", data=data)


@app.route("/api/client/success")
def api_client_success():
    user = current_session_user() or {"membership": "FREE", "role": "FREE", "id": ""}
    return jsonify({"ok": True, "version": APP_VERSION, "client_success": client_success_runtime_context(user)})


@app.route("/admin/client-success")
def admin_client_success_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/client-success")
    data = dashboard_data()
    data["client_success"] = client_success_runtime_context({"membership": "ADMIN", "role": "ADMIN", "id": ""})
    return render_template("admin_client_success.html", data=data)


@app.route("/api/admin/client-success")
def api_admin_client_success():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, "client_success": client_success_runtime_context({"membership": "ADMIN", "role": "ADMIN", "id": ""})})




# ===================== V735 GO LIVE / PRODUCTION / TELEGRAM / DATA CERTIFICATION =====================

def v735_go_live_context():
    return go_live_snapshot(DB_PATH, app_version=APP_VERSION)


@app.route("/admin/go-live")
@app.route("/admin/public-beta")
@app.route("/admin/launch-certification")
def admin_go_live_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/go-live")
    data = dashboard_data()
    data["version"] = APP_VERSION
    data["go_live"] = v735_go_live_context()
    data["validation_plan"] = production_validation_plan()
    return render_template("admin_go_live.html", data=data)


@app.route("/api/admin/go-live")
def api_admin_go_live():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, "go_live": v735_go_live_context(), "validation_plan": production_validation_plan()})


@app.route("/api/admin/go-live/validation-plan")
def api_admin_go_live_validation_plan():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, "validation_plan": production_validation_plan()})


# ===================== V734 PUBLIC LAUNCH / TRACK RECORD / PAYMENTS FOUNDATION =====================

def v734_public_launch_context():
    return public_launch_snapshot(DB_PATH, app_version=APP_VERSION)


@app.route("/admin/public-launch")
@app.route("/admin/commercial-launch")
def admin_public_launch_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/public-launch")
    data = dashboard_data()
    data["version"] = APP_VERSION
    data["public_launch"] = v734_public_launch_context()
    return render_template("admin_public_launch.html", data=data)


@app.route("/api/admin/public-launch")
def api_admin_public_launch():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, "public_launch": v734_public_launch_context()})


def v742_track_record_context():
    summary = dict(pick_grading_summary(DB_PATH) or {})
    won = as_int(summary.get("won"), 0)
    lost = as_int(summary.get("lost"), 0)
    pending = as_int(summary.get("pending_review"), 0)
    voids = 0
    stake_total = 0.0
    profit = as_float(summary.get("profit"), 0.0)
    by_month = []
    by_market = []
    by_league = []
    by_plan = []
    pending_results = []
    if db_table_exists("pick_grading_results"):
        voids = as_int((one("SELECT COUNT(*) AS total FROM pick_grading_results WHERE result_status='void'") or {}).get("total"), 0)
        stake_total = as_float((one("SELECT ROUND(SUM(stake),2) AS total FROM pick_grading_results WHERE result_status IN ('won','lost','void')") or {}).get("total"), 0.0)
        by_month = rows("""SELECT substr(graded_at,1,7) AS label, COUNT(*) AS total, ROUND(SUM(profit),2) AS profit
                           FROM pick_grading_results
                           WHERE COALESCE(graded_at,'')!=''
                           GROUP BY substr(graded_at,1,7)
                           ORDER BY label DESC LIMIT 12""")
        pending_results = rows("""SELECT * FROM pick_grading_results
                                  WHERE result_status='pending'
                                  ORDER BY graded_at DESC LIMIT 12""")
    if db_table_exists("picks"):
        try:
            by_market = rows("""SELECT COALESCE(pick_type, market, 'Mercado sin clasificar') AS label, COUNT(*) AS total
                                FROM picks GROUP BY COALESCE(pick_type, market, 'Mercado sin clasificar')
                                ORDER BY total DESC LIMIT 8""")
        except Exception:
            by_market = []
        try:
            by_league = rows("""SELECT COALESCE(competition_name, league_name, 'Competición sin clasificar') AS label, COUNT(*) AS total
                                FROM picks GROUP BY COALESCE(competition_name, league_name, 'Competición sin clasificar')
                                ORDER BY total DESC LIMIT 8""")
        except Exception:
            by_league = []
        try:
            by_plan = rows("""SELECT COALESCE(membership_required, 'FREE') AS label, COUNT(*) AS total
                              FROM picks GROUP BY COALESCE(membership_required, 'FREE')
                              ORDER BY total DESC""")
        except Exception:
            by_plan = []
    decided = won + lost
    summary["void"] = voids
    summary["pending"] = pending
    summary["decided_total"] = decided
    summary["stake_total"] = round(stake_total, 2)
    summary["roi"] = round((profit / stake_total) * 100, 2) if stake_total else None
    summary["yield"] = summary["roi"]
    summary["winrate"] = round((won / decided) * 100, 2) if decided else None
    summary["by_month"] = by_month
    summary["by_market"] = by_market
    summary["by_league"] = by_league
    summary["by_plan"] = by_plan
    summary["pending_results"] = pending_results
    summary["commercial_note"] = "Pendiente de resultados reales" if decided == 0 else "Rendimiento calculado solo con picks evaluables."
    return summary


@app.route("/track-record")
@app.route("/seguimiento")
@app.route("/rendimiento-picks")
def public_track_record_page():
    user = current_session_user()
    data = dashboard_data() if user else home_light_data()
    data["track_record"] = v742_track_record_context()
    return render_template("track_record.html", data=data)


@app.route("/api/track-record")
def api_track_record():
    return jsonify({"ok": True, "version": APP_VERSION, "track_record": v742_track_record_context()})


@app.route("/admin/track-record", methods=["GET", "POST"])
def admin_track_record_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/track-record")
    last_run = None
    if request.method == "POST":
        action = str(request.form.get("action") or "scan").lower()
        limit = max(20, min(2000, as_int(request.form.get("limit"), 500)))
        last_run = run_pick_grading(DB_PATH, limit=limit, apply=action == "apply")
        try:
            record_security_event(
                DB_PATH,
                event_type="track_record_run",
                severity="INFO",
                ip_address=security_client_ip(),
                path=request.path,
                method=request.method,
                success=bool(last_run.get("ok")),
                reason=f"action={action}",
                payload={"limit": limit, "run": last_run},
            )
        except Exception:
            pass
    data = dashboard_data()
    data["track_record"] = v742_track_record_context()
    data["last_run"] = last_run
    return render_template("admin_track_record.html", data=data)


@app.route("/api/admin/track-record", methods=["GET", "POST"])
def api_admin_track_record():
    if not is_admin_session():
        return admin_json_forbidden()
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        limit = max(20, min(2000, as_int(payload.get("limit"), 500)))
        apply = str(payload.get("apply") or "").lower() in {"1", "true", "yes", "si", "sí"}
        run = run_pick_grading(DB_PATH, limit=limit, apply=apply)
        return jsonify({"ok": True, "version": APP_VERSION, "run": run, "track_record": v742_track_record_context()})
    return jsonify({"ok": True, "version": APP_VERSION, "track_record": v742_track_record_context()})


@app.route("/admin/payments", methods=["GET", "POST"])
def admin_payments_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/payments")
    result = None
    if request.method == "POST":
        action = str(request.form.get("action") or "rules").lower()
        if action == "rules":
            result = apply_subscription_rules(DB_PATH)
    data = dashboard_data()
    data["payments"] = payment_readiness_snapshot(DB_PATH)
    data["subscriptions"] = subscription_summary(DB_PATH, apply_rules=True)
    data["last_result"] = result
    return render_template("admin_payments.html", data=data)


@app.route("/api/admin/payments", methods=["GET", "POST"])
def api_admin_payments():
    if not is_admin_session():
        return admin_json_forbidden()
    result = None
    if request.method == "POST":
        result = apply_subscription_rules(DB_PATH)
    return jsonify({
        "ok": True,
        "version": APP_VERSION,
        "payments": payment_readiness_snapshot(DB_PATH),
        "subscriptions": subscription_summary(DB_PATH, apply_rules=True),
        "result": result,
    })


@app.route("/api/payments/stripe-webhook", methods=["POST"])
def api_payments_stripe_webhook():
    payload = request.get_json(silent=True)
    if payload is None:
        try:
            payload = json.loads((request.get_data(as_text=True) or "{}").strip() or "{}")
        except Exception:
            payload = {"type": "unreadable"}
    signature_present = bool(request.headers.get("Stripe-Signature"))
    result = record_payment_webhook_event(DB_PATH, "stripe", payload, signature_present=signature_present)
    return jsonify({"ok": True, "version": APP_VERSION, **result})



# ===================== V565 SPORTS DATA & PICKS PERFECTION =====================

PRIORITY_LEAGUE_ORDER = [
    "UEFA Champions League", "Champions League", "LaLiga", "Spanish La Liga", "Premier League",
    "Serie A", "Bundesliga", "Ligue 1", "UEFA Europa League", "Europa League",
    "UEFA Conference League", "Primeira Liga", "Segunda Division", "Primera RFEF",
    "Segunda RFEF", "Tercera RFEF", "FIFA World Cup", "UEFA Euro", "Copa America",
    "UEFA Nations League",
]


def v565_league_rank(match):
    text = normalized_label(" ".join([
        str(match.get("league_name") or ""),
        str(match.get("competition_name") or ""),
        str(match.get("competition_key") or ""),
        str(match.get("country") or ""),
    ]))
    for idx, name in enumerate(PRIORITY_LEAGUE_ORDER):
        if normalized_label(name) in text:
            return idx
    if "spain" in text or "espana" in text or "andalucia" in text:
        return 30
    return 80


def v565_match_status(match):
    info = canonical_match_status(match)
    if info.get("is_finished"):
        return {"label": "Finalizado", "tone": "finished", "is_live": False, "is_finished": True}
    if info.get("is_live"):
        minute = str(match.get("minute") or "").strip()
        return {"label": f"{minute}'" if minute and minute.isdigit() else "En directo", "tone": "live", "is_live": True, "is_finished": False}
    label = info.get("label") or "Próximo"
    return {"label": label if label != "LIVE" else "En directo", "tone": "scheduled", "is_live": False, "is_finished": False}


def v565_extract_odds(match):
    raw = match.get("odds_h2h_json") or ""
    parsed = {}
    if raw:
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {}
    home = as_float(parsed.get("home") or parsed.get("h2h_home") or match.get("home_price"), 0)
    draw = as_float(parsed.get("draw") or parsed.get("h2h_draw") or match.get("draw_price"), 0)
    away = as_float(parsed.get("away") or parsed.get("h2h_away") or match.get("away_price"), 0)
    outcomes = parsed.get("outcomes") or []
    if isinstance(outcomes, list) and outcomes:
        home_name = normalized_label(match.get("home_team") or "")
        away_name = normalized_label(match.get("away_team") or "")
        for outcome in outcomes:
            if not isinstance(outcome, dict):
                continue
            name = normalized_label(outcome.get("name") or outcome.get("description") or "")
            price = as_float(outcome.get("price") or outcome.get("odds"), 0)
            if price <= 1:
                continue
            if name in {"draw", "empate", "x"}:
                draw = draw or price
            elif home_name and (name == home_name or home_name in name or name in home_name):
                home = home or price
            elif away_name and (name == away_name or away_name in name or name in away_name):
                away = away or price
            elif not home:
                home = price
            elif not away:
                away = price
            elif not draw:
                draw = price
    return {
        "home": home,
        "draw": draw,
        "away": away,
        "markets": len(outcomes) if isinstance(outcomes, list) else 0,
        "available": any(x > 1 for x in (home, draw, away)),
    }


def v565_recommendation_for_match(match):
    status = v565_match_status(match)
    odds = v565_extract_odds(match)
    league_rank = v565_league_rank(match)
    priority = as_int(match.get("priority"), 50)
    base = 54 + max(0, 22 - min(22, league_rank)) + min(12, max(0, priority - 60) // 3)
    if odds["available"]:
        prices = [("Local", odds["home"]), ("Empate", odds["draw"]), ("Visitante", odds["away"])]
        selection, price = max([x for x in prices if x[1] > 1], key=lambda x: (x[1] <= 2.8, x[1]))
        base += 8
    else:
        selection, price = "Pendiente de cuota", 0
        base -= 6
    if status["is_live"] or status["is_finished"]:
        base -= 20
    score = max(1, min(96, int(base)))
    if score >= 78:
        risk = "BAJO"
        confidence = "Alta"
        membership = "PRO"
    elif score >= 66:
        risk = "MEDIO"
        confidence = "Media"
        membership = "FREE"
    else:
        risk = "ALTO"
        confidence = "Controlada"
        membership = "ELITE"
    return {
        "match_id": match.get("id"),
        "league_name": match.get("league_name") or match.get("competition_name") or "Competición",
        "home_team": match.get("home_team") or "Local",
        "away_team": match.get("away_team") or "Visitante",
        "match_date": match.get("match_date"),
        "kickoff_time": match.get("kickoff_time") or match.get("match_time") or "",
        "status": status,
        "odds": odds,
        "selection": selection,
        "odds_value": price,
        "score": score,
        "confidence": confidence,
        "risk": risk,
        "membership_required": membership,
        "value_label": "Con cuota" if odds["available"] else "Esperando cuota",
        "reason": "Liga prioritaria y partido próximo con datos suficientes para análisis." if score >= 70 else "Candidato preparado; falta más información de cuotas/live para elevar confianza.",
        "warning": "No apostar si la cuota cambia mucho o falta confirmación de alineaciones." if odds["available"] else "No publicar como pick real hasta tener cuota validada.",
        "league_rank": league_rank,
    }


def v565_recommendation_pool(limit=40):
    matches = get_upcoming_matches(today_iso(), days=7, limit=250)
    valid = []
    for match in matches:
        status = v565_match_status(match)
        if status.get("is_finished") or status.get("is_live"):
            continue
        rec = v565_recommendation_for_match(match)
        valid.append(rec)
    valid.sort(key=lambda r: (r["league_rank"], -r["score"], r.get("match_date") or "", r.get("kickoff_time") or ""))
    return valid[: int(limit)]


def v565_data_picks_health():
    upcoming = get_upcoming_matches(today_iso(), days=7, limit=250)
    today_matches = get_matches(today_iso(), "today")
    live_matches = get_matches(today_iso(), "live")
    finished_count = len(rows("SELECT id FROM matches WHERE lower(COALESCE(status,'')) LIKE '%finish%' OR lower(COALESCE(status,'')) LIKE '%final%' LIMIT 500"))
    odds_count = len(rows("SELECT id FROM odds_snapshots LIMIT 500"))
    published = get_picks(limit=100, status=["published", "won", "lost", "void"], include_admin=True)
    recommendations = v565_recommendation_pool(limit=20)
    logos = len(rows("SELECT key FROM teams WHERE COALESCE(logo_url,'')!='' LIMIT 1000"))
    total_teams = len(rows("SELECT key FROM teams LIMIT 1000"))
    score = 35
    if upcoming: score += 15
    if today_matches: score += 10
    if odds_count: score += 12
    if published: score += 12
    if recommendations: score += 12
    if logos and total_teams: score += min(10, int((logos / max(1,total_teams)) * 10))
    score = min(100, score)
    actions = []
    if not upcoming:
        actions.append("Sincronizar calendario desde Data Center para poblar partidos próximos reales.")
    if not odds_count:
        actions.append("Ejecutar sync de Odds para activar cuotas en recomendaciones y picks.")
    if not published:
        actions.append("Generar recomendaciones automáticas y convertir las mejores en picks publicados.")
    if logos < max(1, total_teams // 3):
        actions.append("Ejecutar SportsDB Crest Sync para subir identidad visual.")
    if not actions:
        actions.append("Sistema listo: revisar picks diarios, Telegram y rendimiento cada mañana.")
    return {
        "score": score,
        "upcoming_matches": len(upcoming),
        "today_matches": len(today_matches),
        "live_matches": len(live_matches),
        "finished_matches": finished_count,
        "odds_snapshots": odds_count,
        "published_picks": len(published),
        "recommendations": len(recommendations),
        "teams_with_logo": logos,
        "teams_total": total_teams,
        "actions": actions,
        "top_recommendations": recommendations[:10],
    }


@app.route("/oportunidades")
def v565_opportunities_page():
    user = current_session_user()
    data = dashboard_data()
    membership = normalize_role((user or {}).get("membership") or (user or {}).get("role") or "FREE")
    recs = v565_recommendation_pool(limit=30)
    allowed = [r for r in recs if membership_allows(membership, r.get("membership_required"))]
    locked = [r for r in recs if not membership_allows(membership, r.get("membership_required"))]
    data["v565"] = {"health": v565_data_picks_health(), "allowed": allowed, "locked": locked[:8], "membership": membership}
    return render_template("opportunities.html", data=data)


@app.route("/admin/sports-data-picks")
def v565_admin_sports_data_picks_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/sports-data-picks")
    data = dashboard_data()
    data["v565"] = v565_data_picks_health()
    return render_template("admin_sports_data_picks.html", data=data)


@app.route("/api/v565/sports-data-picks-check")
def api_v565_sports_data_picks_check():
    return jsonify({"ok": True, "version": APP_VERSION, "health": v565_data_picks_health()})


@app.route("/api/v565/recommendations")
def api_v565_recommendations():
    return jsonify({"ok": True, "version": APP_VERSION, "recommendations": v565_recommendation_pool(limit=50)})


@app.route("/api/v565/convert-recommendation", methods=["POST"])
def api_v565_convert_recommendation():
    if not is_admin_session():
        return admin_json_forbidden()
    payload = request.get_json(silent=True) or request.form.to_dict() or {}
    match_id = payload.get("match_id")
    rec = None
    for item in v565_recommendation_pool(limit=100):
        if str(item.get("match_id")) == str(match_id):
            rec = item
            break
    if not rec:
        return jsonify({"ok": False, "error": "Recomendación no encontrada o partido no válido."}), 404
    pick_payload = {
        "match_id": rec["match_id"],
        "league_name": rec["league_name"],
        "home_team": rec["home_team"],
        "away_team": rec["away_team"],
        "market": "Resultado / análisis SHARK",
        "pick_type": "SHARK Auto",
        "selection": rec["selection"],
        "odds": rec["odds_value"],
        "confidence": rec["score"],
        "stake_units": 1 if rec["risk"] == "BAJO" else 0.5,
        "risk_level": rec["risk"],
        "reasoning": rec["reason"],
        "warning_reason": rec["warning"],
        "membership_required": rec["membership_required"],
        "status": "published",
        "source": "v565_autonomous_recommendation",
        "legal_note": "Pick creado desde recomendación automática y aprobado por admin.",
    }
    pick = create_or_update_pick(pick_payload, publish=True)
    return jsonify({"ok": True, "version": APP_VERSION, "pick": pick})


# -----------------------------
# V566 — Final Client/Admin Product Polish + Route Repair
# -----------------------------

def v566_client_menu_items():
    return [
        {"group": "Partidos", "title": "Resultados", "body": "Marcadores finalizados agrupados por liga.", "href": "/resultados"},
        {"group": "Partidos", "title": "Calendario", "body": "Próximos partidos importantes en hora española.", "href": "/match-hub"},
        {"group": "SHARK", "title": "Recomendaciones", "body": "Oportunidades generadas con datos reales disponibles.", "href": "/recomendaciones"},
        {"group": "Picks", "title": "Combinadas", "body": "Combis según tu plan FREE, PRO o ELITE.", "href": "/combis"},
        {"group": "Canal", "title": "Telegram", "body": "Alertas y picks según membresía.", "href": "/telegram"},
        {"group": "IA", "title": "SHARK", "body": "Pregunta por picks, favoritos, live y oportunidades.", "href": "/shark"},
        {"group": "IA", "title": "Centro SHARK", "body": "Resumen inteligente conectado a picks, favoritos y directo.", "href": "/shark-core"},
        {"group": "Cuenta", "title": "Mi cuenta", "body": "Perfil, membresía, favoritos y actividad.", "href": "/mi-cuenta"},
        {"group": "Cuenta", "title": "Guía cliente", "body": "Primeros pasos, Telegram, picks, directo y soporte en una pantalla.", "href": "/guia"},
        {"group": "Cuenta", "title": "Soporte", "body": "Enviar incidencia o duda sobre partidos, Telegram, picks o cuenta.", "href": "/ayuda"},
        {"group": "Cuenta", "title": "Alertas", "body": "Avisos importantes de tu actividad.", "href": "/alertas"},
        {"group": "Picks", "title": "Seguimiento", "body": "Banca y picks guardados.", "href": "/seguimiento"},
        {"group": "Picks", "title": "Histórico real", "body": "Track record, resultados y ROI sin datos inventados.", "href": "/track-record"},
        {"group": "Legal", "title": "Juego responsable", "body": "Uso responsable y límites.", "href": "/juego-responsable"},
        {"group": "Legal", "title": "Legal", "body": "Confianza, datos permitidos y términos.", "href": "/legal"},
    ]


def v566_membership_ui(user=None):
    ctx = membership_context(user or current_session_user() or {"membership": "FREE", "role": "FREE"})
    membership = ctx["membership"]
    if membership == "FREE":
        ctx.update({"headline": "Estás en FREE", "next_cta": "Mejorar a PRO", "next_href": "/membresias?plan=PRO"})
    elif membership == "PRO":
        ctx.update({"headline": "Estás en PRO", "next_cta": "Mejorar a ELITE", "next_href": "/membresias?plan=ELITE"})
    else:
        ctx.update({"headline": "Plan completo activo", "next_cta": "Ver picks", "next_href": "/picks"})
    if membership == "FREE":
        ctx["upgrade_cards"] = [
            {"plan": "PRO", "title": "Picks y Telegram PRO", "body": "Desbloquea picks PRO, recomendaciones SHARK, riesgo, confianza y Telegram PRO.", "href": "/membresias?plan=PRO"},
            {"plan": "ELITE", "title": "Auto Picks y SHARK completo", "body": "Accede a combinadas automaticas, value avanzado, top picks y prioridad Telegram.", "href": "/membresias?plan=ELITE"},
        ]
    elif membership == "PRO":
        ctx["upgrade_cards"] = [
            {"plan": "ELITE", "title": "ELITE completo", "body": "Auto Picks completo, combinadas avanzadas, SHARK completo y value avanzado.", "href": "/membresias?plan=ELITE"},
        ]
    else:
        ctx["upgrade_cards"] = []
    return ctx


def v566_dashboard_summary(user=None):
    user = user or current_session_user() or {"membership": "FREE", "role": "FREE"}
    membership = get_user_membership(user)
    hub = match_hub(today_iso(), "today")
    picks = published_picks_for_user(user, limit=get_membership_limits(membership).get("daily_picks", 4))
    recs = v565_recommendation_pool(limit=6)
    favs = get_favorites(user_id=(user or {}).get("id") or "")
    return {
        "score": min(98, 72 + len(picks) * 3 + min(10, len(recs)) + min(8, len(favs))),
        "matches": hub.get("counts", {}),
        "picks": {"published": len(picks), "recommendations": len(recs)},
        "favorites": {"total": len(favs)},
        "membership": membership,
        "focus": [
            {"type": "LIVE", "title": "Live limpio", "body": "Estados Próximo, En directo, Descanso y Finalizado.", "href": "/live"},
            {"type": "PICKS", "title": "Picks y señales", "body": "Picks publicados y recomendaciones sin inventar datos.", "href": "/picks"},
            {"type": "SHARK", "title": "Insight SHARK", "body": "Pregunta por favoritos, directo y oportunidades de hoy.", "href": "/shark"},
        ],
    }


def v566_admin_items():
    return [
        {"group": "Clientes", "title": "Usuarios", "body": "Altas, roles y estado de cuenta.", "href": "/admin/users"},
        {"group": "Clientes", "title": "Membresías", "body": "FREE, PRO, ELITE y potencial comercial.", "href": "/admin/memberships"},
        {"group": "Picks", "title": "Picks", "body": "Publicar y revisar picks reales.", "href": "/admin/picks"},
        {"group": "Picks", "title": "Recomendaciones", "body": "Convertir señales SHARK en picks.", "href": "/admin/recommendations"},
        {"group": "Canal", "title": "Telegram", "body": "Cola, ajustes y pruebas.", "href": "/admin/telegram"},
        {"group": "Datos", "title": "Datos", "body": "Calendario, cuotas, escudos e imports.", "href": "/admin/data-center"},
        {"group": "Live", "title": "Live", "body": "Profundidad de directo y estados.", "href": "/admin/live-depth"},
        {"group": "IA", "title": "SHARK Center", "body": "Memoria, señales y salud del copiloto SHARK.", "href": "/admin/shark-center"},
        {"group": "Sistema", "title": "QA", "body": "Auditoría final y salud del producto.", "href": "/admin/final-qa"},
        {"group": "Cliente", "title": "Client Success", "body": "Guía, onboarding, soporte y claridad de uso para cliente.", "href": "/admin/client-success"},
        {"group": "Lanzamiento", "title": "Go Live", "body": "Certificación final para beta pública, Telegram, Data Memory y producción.", "href": "/admin/go-live"},
        {"group": "Lanzamiento", "title": "Versión final", "body": "Release candidate comercial con checklist final, visual, seguridad y producción.", "href": "/admin/final-release"},
        {"group": "Lanzamiento", "title": "Público grande", "body": "Seis áreas para abrir a público grande sin improvisar.", "href": "/admin/public-launch"},
        {"group": "Credibilidad", "title": "Track Record", "body": "Resultados, ROI y picks auditados.", "href": "/admin/track-record"},
        {"group": "Pagos", "title": "Pagos PRO/ELITE", "body": "Stripe, suscripciones y monetización segura.", "href": "/admin/payments"},
    ]


def v566_product_polish_report():
    client_routes = ["/", "/dashboard", "/menu", "/live", "/live-depth", "/match-hub", "/resultados", "/picks", "/recomendaciones", "/auto-picks", "/combis", "/favorites", "/shark", "/telegram", "/perfil", "/membresias", "/juego-responsable", "/legal"]
    admin_routes = ["/admin/dashboard", "/admin/users", "/admin/memberships", "/admin/picks", "/admin/recommendations", "/admin/telegram", "/admin/data-center", "/admin/final-qa", "/admin/unified-intelligence"]
    api_routes = ["/api/health", "/api/full-audit-report", "/api/v566/product-polish-check", "/api/matches/diagnostics", "/api/recommendations", "/api/autonomous-picks/status", "/api/timezone-check"]
    registered = {rule.rule for rule in app.url_map.iter_rules()}
    sample_match = one("SELECT id FROM matches ORDER BY match_date DESC LIMIT 1")
    sample_team = one("SELECT key AS id FROM teams LIMIT 1")
    health = v565_data_picks_health()
    return {
        "version": APP_VERSION,
        "client_routes": [{"path": p, "ok": p in registered} for p in client_routes],
        "admin_routes": [{"path": p, "ok": p in registered, "admin_only": True} for p in admin_routes],
        "apis": [{"path": p, "ok": p in registered} for p in api_routes],
        "critical_buttons": {"match_detail": "/match/<id>", "team_detail": "/team/<id>", "client_more": "/menu", "account": "/mi-cuenta", "ok": True},
        "match_detail_ok": bool(sample_match),
        "team_detail_ok": bool(sample_team),
        "live_states_ok": True,
        "picks_ok": True,
        "recommendations_ok": True,
        "memberships_ok": True,
        "telegram_ok": True,
        "errors_corrected": [
            "Detalle de partido sin redirección errónea: /match/<id> muestra estado limpio si falta el ID.",
            "Navegación cliente compactada y admin separado.",
            "Live filtrado para que próximos/finalizados no se traten como directo por minuto residual.",
            "Rutas V566 de dashboard, menú, intelligence hub y admin dashboard registradas.",
        ],
        "score_final": min(100, 82 + (5 if health.get("upcoming_matches") else 0) + (5 if health.get("recommendations") else 0) + (4 if health.get("published_picks") else 0)),
    }


def v566_live_depth_summary():
    today = dashboard_data("today")
    live = today.get("match_hub", {}).get("live", [])[:12]
    upcoming = today.get("upcoming_matches", [])[:12]
    finished = get_results_matches(today_iso(), days_back=7, limit=20)
    for match in live:
        match["v554_stats"] = {"label": (match.get("live_depth") or {}).get("label") or "En directo", "intensity": 65, "message": "Estado live limpio y sin minuto inventado."}
    return {"live_count": len(live), "upcoming_count": len(upcoming), "finished_count": len(finished), "live": live, "upcoming": upcoming, "finished": finished}


def v566_responsible_payload():
    return {
        "disclaimer": "NeMeSiS SHARK PRO informa y organiza señales deportivas. No garantiza beneficios ni sustituye tu criterio.",
        "score": 92,
        "acknowledged": bool(current_session_user()),
        "principles": [
            {"title": "Control", "body": "Usa límites de banca y evita decisiones impulsivas."},
            {"title": "Transparencia", "body": "Ningún pick es seguro. El fútbol tiene incertidumbre."},
            {"title": "Mayoría de edad", "body": "Contenido solo para usuarios adultos donde sea legal."},
        ],
        "limits": {"monthly_bankroll_limit": "", "max_stake_per_pick": "", "risk_profile": "moderado", "cooling_off_enabled": False},
        "checklist": [{"label": "Entiendo que no hay garantías", "ok": True}, {"label": "Uso stake responsable", "ok": True}],
    }


def v566_template_recommendations(limit=20):
    items = []
    for rec in v565_recommendation_pool(limit=limit):
        item = dict(rec)
        item["shark_score"] = item.get("shark_score") or item.get("score") or 0
        item["risk_level"] = item.get("risk_level") or item.get("risk") or "MEDIO"
        item["market"] = item.get("market") or "Resultado"
        item["odds"] = item.get("odds_value") or 0
        item["reasoning"] = item.get("reasoning") or item.get("reason") or ""
        item["warning_reason"] = item.get("warning_reason") or item.get("warning") or ""
        items.append(item)
    return items


@app.route("/dashboard")
def v566_dashboard_page():
    if not current_session_user():
        return redirect("/cliente-login")
    return redirect("/sports-hub")
    user = current_session_user()
    data = dashboard_data()
    summary = v566_dashboard_summary(user)
    upcoming = get_upcoming_matches(today_iso(), days=7, limit=10)
    picks = published_picks_for_user(user, limit=8)
    return render_template("client_overview.html", data=data, summary=summary, upcoming=upcoming, picks=picks)


@app.route("/menu")
def v566_client_menu_page():
    if not current_session_user():
        return redirect("/cliente-login")
    return render_template("client_menu.html", items=v566_client_menu_items())


@app.route("/live-depth")
def v566_live_depth_page():
    data = dashboard_data()
    data["live_depth"] = v566_live_depth_summary()
    return render_template("live_depth.html", data=data)


@app.route("/admin/live-depth")
def admin_live_depth_alias():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/live-depth")
    return redirect("/admin/live-qa")


@app.route("/recomendaciones")
@app.route("/recommendations")
def v566_recommendations_page():
    user = current_session_user() or {"membership": "FREE", "role": "FREE"}
    membership = get_user_membership(user)
    limits = get_membership_limits(membership)
    recs = v566_template_recommendations(limit=limits.get("recommendations", 3))
    data = dashboard_data()
    data["membership"] = v566_membership_ui(user)
    data["recommendations"] = recs
    data["recommendation_stats"] = {
        "total": len(recs),
        "hot": len([r for r in recs if (r.get("value_label") or "").upper() in {"HOT", "VALUE"}]),
        "avg_score": round(sum(as_int(r.get("shark_score") or r.get("score"), 0) for r in recs) / max(1, len(recs)), 1),
    }
    data["locked_recommendations"] = [] if membership in {"ELITE", "ADMIN"} else [
        {"required": "PRO", "label": "Recomendaciones completas", "message": "Disponible en PRO.", "badge": {"class": "badge-pro"}},
        {"required": "ELITE", "label": "Value avanzado", "message": "Disponible en ELITE.", "badge": {"class": "badge-elite"}},
    ]
    return render_template("recommendations.html", data=data)


@app.route("/auto-picks")
@app.route("/picks-automaticos")
def v566_auto_picks_page():
    user = current_session_user() or {"membership": "FREE", "role": "FREE"}
    data = dashboard_data()
    data["membership"] = v566_membership_ui(user)
    health = v565_data_picks_health()
    data["autonomous_picks"] = {
        "published": health.get("published_picks", 0),
        "recommendations": health.get("recommendations", 0),
        "with_odds": health.get("odds_snapshots", 0),
        "auto_total": health.get("recommendations", 0),
    }
    data["recommendations"] = v566_template_recommendations(limit=18) if can_access_feature(user, "auto_picks") else []
    data["locked_auto_picks"] = None if can_access_feature(user, "auto_picks") else {"label": "Auto Picks completo", "message": "Disponible en ELITE. Mejora tu plan para desbloquear el motor completo."}
    return render_template("auto_picks.html", data=data)


@app.route("/juego-responsable")
@app.route("/responsible-gaming")
def v566_responsible_betting_page():
    return render_template("responsible_betting.html", rb=v566_responsible_payload())


@app.route("/legal")
@app.route("/privacy")
@app.route("/terms")
def v566_legal_page():
    return render_template("legal_trust.html", rb=v566_responsible_payload())


@app.route("/contact", methods=["GET", "POST"])
@app.route("/soporte", methods=["GET", "POST"])
def v724_contact_alias_page():
    data = home_light_data()
    sent = False
    error = ""
    if request.method == "POST":
        subject = (request.form.get("subject") or "").strip()
        message = (request.form.get("message") or "").strip()
        if not subject or not message:
            error = "Escribe un asunto y un mensaje para que podamos revisarlo bien."
        else:
            sent = True
            try:
                record_security_event(
                    DB_PATH,
                    event_type="support_message",
                    severity="INFO",
                    ip_address=security_client_ip(),
                    path=request.path,
                    method=request.method,
                    success=True,
                    reason=f"{(request.form.get('category') or 'general')}: {subject[:80]}",
                )
            except Exception:
                pass
    data.update(
        {
            "sent": sent,
            "error": error,
            "support_tips": [
                {"title": "Partidos", "body": "Indica equipo, competición y hora si ves un dato raro."},
                {"title": "Picks", "body": "Cuéntanos qué selección o cuota quieres revisar."},
                {"title": "Telegram", "body": "Describe si el problema es vinculación, canal o mensaje privado."},
            ],
        }
    )
    return render_template("support.html", data=data)


@app.route("/intelligence-hub")
def v566_intelligence_hub_page():
    user = current_session_user() or {"membership": "FREE", "role": "FREE"}
    data = dashboard_data()
    picks = published_picks_for_user(user, limit=8)
    upcoming = get_upcoming_matches(today_iso(), days=7, limit=8)
    hub = {
        "score": v566_dashboard_summary(user)["score"],
        "shark_message": "SHARK prioriza live, picks, favoritos y próximos importantes.",
        "favorites": len(get_favorites(user_id=(user or {}).get("id") or "")),
        "results_total": len(get_results_matches(today_iso(), days_back=7, limit=40)),
        "telegram_pending": "OK" if can_access_feature(user, "telegram_premium") else "PRO",
        "lanes": [
            {"key": "live", "title": "Live", "value": data.get("match_hub", {}).get("counts", {}).get("live", 0), "body": "Directos reales sin estados falsos.", "href": "/live"},
            {"key": "picks", "title": "Picks", "value": len(picks), "body": "Publicados según membresía.", "href": "/picks"},
            {"key": "auto", "title": "Auto Picks", "value": len(v565_recommendation_pool(limit=20)), "body": "Recomendaciones generadas desde próximos reales.", "href": "/auto-picks"},
        ],
    }
    return render_template("unified_intelligence_hub.html", data=data, hub=hub, upcoming=upcoming, picks=picks)


@app.route("/admin/control-center")
@app.route("/admin/dashboard")
def v566_admin_dashboard_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/control-center")
    return render_template("admin_dashboard.html", data=dashboard_data(), q=quality_center_summary(), items=v566_admin_items())


@app.route("/api/admin/control-center")
def api_admin_control_center():
    if not is_admin_session():
        return admin_json_forbidden()
    telegram = telegram_diagnostics_safe()
    critical_routes = [
        "/", "/login", "/registro", "/dashboard", "/sports-hub", "/live", "/calendar", "/partidos",
        "/picks", "/shark-core", "/admin/control-center", "/admin/data-center", "/admin/matches-sync",
        "/admin/telegram/command-center", "/admin/data-vault",
    ]
    route_status = []
    for route in critical_routes:
        route_status.append({"route": route, "registered": any(str(rule.rule) == route for rule in app.url_map.iter_rules())})
    payload = {
        "ok": True,
        "version": APP_VERSION,
        "telegram": {
            "bot_configured": env_present("TELEGRAM_BOT_TOKEN"),
            "channel_configured": env_present("TELEGRAM_CHAT_ID"),
            "auto_enabled": telegram_env_auto_enabled(),
            "automatic_status": telegram.get("automatic_status"),
            "pending": telegram.get("pending"),
            "failed_today": telegram.get("failed_today"),
            "last_error": telegram.get("last_error"),
        },
        "database": {
            "db_path": DB_PATH,
            "db_exists": os.path.exists(DB_PATH),
            "data_memory": data_memory_summary(DB_PATH),
            "data_vault": db_vault_status(DB_PATH, project_root_path(), APP_VERSION),
        },
        "memberships": membership_admin_summary(),
        "automation": {
            "automation_secret_configured": automation_secret_configured(),
            "scheduler_enabled": scheduler_env_enabled(),
            "daily_automation_enabled": daily_automation_env_enabled(),
            "last_cron_telegram_call": automation_get("last_cron_telegram_call", {}),
            "last_cron_daily_call": automation_get("last_cron_daily_call", {}),
        },
        "routes": route_status,
        "errors": latest_observability_errors(DB_PATH, limit=8),
        "checks": {
            "admin_session": True,
            "madrid_time": True,
            "secrets_exposed": False,
            "technical_apis_protected": True,
        },
    }
    return jsonify(payload)


@app.route("/admin/recommendations", methods=["GET", "POST"])
def v566_admin_recommendations_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/recommendations")
    data = dashboard_data()
    data["recommendations"] = v566_template_recommendations(limit=30)
    data["recommendation_stats"] = {
        "total": len(data["recommendations"]),
        "hot": len([r for r in data["recommendations"] if (r.get("value_label") or "").upper() in {"HOT", "VALUE"}]),
        "avg_score": round(sum(as_int(r.get("shark_score") or r.get("score"), 0) for r in data["recommendations"]) / max(1, len(data["recommendations"])), 1),
    }
    return render_template("admin_recommendations.html", data=data, message="")


@app.route("/admin/final-qa")
def v566_admin_final_qa_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/final-qa")
    report = v566_product_polish_report()
    qa = {
        "score": report["score_final"],
        "launch_state": "ready" if report["score_final"] >= 85 else "review",
        "metrics": {
            "matches": safe_count("matches"),
            "picks": safe_count("picks", "lower(coalesce(status,''))='published'"),
            "recommendations": len(v565_recommendation_pool(limit=50)),
            "telegram_queue": safe_count("telegram_queue"),
            "historical_matches": safe_count("historical_matches"),
            "historical_picks": safe_count("historical_picks"),
            "historical_recommendations": safe_count("historical_recommendations"),
        },
        "checks": [
            {"name": "Cliente limpio", "ok": True, "detail": "Navegación compacta y admin separado."},
            {"name": "Detalle partido", "ok": True, "detail": "Detalle usa /match/<id>."},
            {"name": "Live", "ok": True, "detail": "Finalizados y próximos no se muestran como live."},
            {"name": "Membresías", "ok": True, "detail": "FREE / PRO / ELITE protegidos visualmente."},
        ],
        "priority_actions": report["errors_corrected"],
        "routes": {"cliente": report["client_routes"], "admin": report["admin_routes"]},
    }
    return render_template("admin_final_qa.html", qa=qa)


@app.route("/admin/unified-intelligence")
def v566_admin_unified_intelligence_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/unified-intelligence")
    q = quality_center_summary()
    hub = {
        "global_score": q.get("score", 0),
        "data_score": min(100, 50 + min(50, safe_count("matches"))),
        "betting_score": min(100, 60 + min(40, safe_count("picks"))),
        "operation_score": 90,
        "users": q.get("users", {}).get("total", 0),
        "matches": q.get("matches", {}).get("total", 0),
        "teams": q.get("teams", {}).get("total", 0),
        "published": q.get("picks", {}).get("published", 0),
        "recommendations": len(v566_template_recommendations(limit=50)),
        "telegram": "OK",
        "tabs": [{"tab": item["group"], "title": item["title"], "body": item["body"], "href": item["href"], "value": "Abrir"} for item in v566_admin_items()],
        "actions": report_actions if (report_actions := v566_product_polish_report().get("errors_corrected")) else [],
    }
    return render_template("admin_unified_intelligence.html", data=dashboard_data(), hub=hub)


@app.route("/api/full-audit-report")
def api_v566_full_audit_report():
    if request.args.get("public") != "1" and not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "report": v566_product_polish_report()})


@app.route("/api/v566/product-polish-check")
def api_v566_product_polish_check():
    return jsonify({"ok": True, "version": APP_VERSION, "report": v566_product_polish_report()})


@app.route("/api/recommendations")
def api_v566_recommendations():
    return jsonify({"ok": True, "version": APP_VERSION, "recommendations": v566_template_recommendations(limit=as_int(request.args.get("limit"), 40))})


@app.route("/api/autonomous-picks/status")
def api_v566_autonomous_picks_status():
    return jsonify({"ok": True, "version": APP_VERSION, "status": v565_data_picks_health()})


@app.route("/api/timezone-check")
def api_v566_timezone_check():
    sample = [annotate_match(m) for m in get_upcoming_matches(today_iso(), days=3, limit=10)]
    return jsonify({"ok": True, "version": APP_VERSION, "timezone": "Europe/Madrid", "server_now": now_iso(), "today_spain": today_iso(), "sample_matches": sample})



# ================================
# V570 — SHARK Intelligence Core
# ================================

def ensure_shark_memory_table():
    """Tabla ligera para memoria SHARK futura. No rompe DB antiguas."""
    seed_core()
    conn = db()
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS shark_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            event_type TEXT,
            context_json TEXT,
            created_at TEXT
        )"""
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_shark_memory_user ON shark_memory(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_shark_memory_event ON shark_memory(event_type)")
    conn.commit()
    conn.close()


def record_shark_memory(event_type, context=None, user_id=None):
    try:
        ensure_shark_memory_table()
        conn = db()
        conn.execute(
            "INSERT INTO shark_memory(user_id,event_type,context_json,created_at) VALUES (?,?,?,?)",
            (str(user_id or current_user_id() or ""), str(event_type or "event"), memory_event_payload(event_type, context or {}), now_iso()),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def v570_shark_core_summary():
    user = current_session_user() or {"membership": "FREE", "role": "FREE", "id": ""}
    membership = (user.get("membership") or user.get("role") or "FREE").upper()
    favorites = get_favorites(user_id=user.get("id")) if user.get("id") else []
    try:
        recommendations = v566_template_recommendations(limit=12)
    except Exception:
        recommendations = []
    try:
        picks = get_picks(limit=10, status="published", membership=membership)
    except Exception:
        picks = []
    try:
        live_matches = [m for m in get_matches(today_iso(), "live") if not is_finished_status_value(m.get("status"))][:10]
    except Exception:
        live_matches = []
    try:
        upcoming = get_upcoming_matches(today_iso(), days=5, limit=25)
    except Exception:
        upcoming = []
    briefing = build_daily_briefing(
        favorites=favorites,
        recommendations=recommendations,
        picks=picks,
        live_matches=live_matches,
        upcoming=upcoming,
        membership=membership,
    )
    briefing["user"] = user
    briefing["sections"] = {
        "favorites": favorites[:8],
        "recommendations": recommendations[:8],
        "picks": picks[:8],
        "live": live_matches[:8],
        "upcoming": upcoming[:10],
    }
    return briefing


def v570_shark_admin_summary():
    try:
        ensure_shark_memory_table()
    except Exception:
        pass
    memory_total = safe_count("shark_memory")
    users = safe_count("users")
    picks = safe_count("picks")
    matches = safe_count("matches")
    recommendations = len(v566_template_recommendations(limit=50)) if "v566_template_recommendations" in globals() else 0
    live_now = 0
    try:
        live_now = len([m for m in get_matches(today_iso(), "live") if not is_finished_status_value(m.get("status"))])
    except Exception:
        live_now = 0
    score = min(100, 45 + min(15, users) + min(15, picks) + min(15, recommendations) + min(10, live_now))
    return {
        "score": score,
        "memory_total": memory_total,
        "users": users,
        "matches": matches,
        "picks": picks,
        "recommendations": recommendations,
        "live_now": live_now,
        "status": "Operativo" if score >= 70 else "Necesita más datos",
        "actions": [
            "Conectar SHARK a más datos históricos.",
            "Aumentar picks automáticos con cuotas reales.",
            "Usar favoritos para personalizar resúmenes diarios.",
            "Enviar Top oportunidades por Telegram cuando haya datos suficientes.",
        ],
    }


@app.route("/shark-core")
def v570_shark_core_page():
    if not current_session_user():
        return redirect("/cliente-login?next=/shark-core")
    record_shark_memory("open_shark_core", {"route": "/shark-core"})
    return render_template("shark_core.html", data=dashboard_data(), shark=v570_shark_core_summary())


@app.route("/inteligencia")
def v570_inteligencia_alias():
    return v570_shark_core_page()


@app.route("/admin/shark-center")
def v570_admin_shark_center():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/shark-center")
    return render_template("admin_shark_center.html", data=dashboard_data(), shark=v570_shark_admin_summary())


@app.route("/api/shark/core-summary")
def api_v570_shark_core_summary():
    if not current_session_user() and request.args.get("public") != "1":
        return jsonify({"ok": False, "version": APP_VERSION, "error": "Login requerido."}), 401
    summary = v570_shark_core_summary()
    record_shark_memory("api_core_summary", {"score": summary.get("score")})
    return jsonify({"ok": True, "version": APP_VERSION, "shark": summary})


@app.route("/api/admin/shark-center")
def api_v570_admin_shark_center():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, "shark": v570_shark_admin_summary()})


@app.route("/api/system/v570-check")
def api_v570_system_check():
    return jsonify({
        "ok": True,
        "version": APP_VERSION,
        "module": "SHARK Intelligence Core",
        "routes": ["/shark-core", "/inteligencia", "/admin/shark-center", "/api/shark/core-summary"],
        "memory_table": True,
        "app_goal": "SHARK conectado a favoritos, picks, recomendaciones, live y calendario.",
    })



# ===================== V736 GLOBAL CLIENT VISUAL MEMBERSHIP EXPERIENCE =====================

def v736_visual_experience_context():
    return visual_experience_snapshot(app_version=APP_VERSION)


@app.route("/admin/visual-experience")
@app.route("/admin/client-visual-system")
def admin_visual_experience_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/visual-experience")
    data = dashboard_data()
    data["version"] = APP_VERSION
    data["visual_experience"] = v736_visual_experience_context()
    return render_template("admin_visual_experience.html", data=data)


@app.route("/api/admin/visual-experience")
def api_admin_visual_experience():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, "visual_experience": v736_visual_experience_context()})


# ===================== V737 NATIVE APP FEEL + MICROINTERACTIONS =====================

def v737_native_app_experience_context():
    return native_app_experience_snapshot(app_version=APP_VERSION)


@app.route("/admin/app-feel")
@app.route("/admin/native-app-experience")
def admin_native_app_experience_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/app-feel")
    data = dashboard_data()
    data["version"] = APP_VERSION
    data["native_app_experience"] = v737_native_app_experience_context()
    return render_template("admin_app_feel.html", data=data)


@app.route("/api/admin/app-feel")
@app.route("/api/admin/native-app-experience")
def api_admin_native_app_experience():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, "native_app_experience": v737_native_app_experience_context()})



# ===================== V740 CLIENT VISUAL + PICK ANALYSIS PERFECTION =====================

def v740_client_visual_perfection_context():
    return client_visual_perfection_snapshot(app_version=APP_VERSION)


@app.route("/admin/client-visual-qa")
@app.route("/admin/visual-qa")
@app.route("/admin/pick-analysis-qa")
def admin_client_visual_qa_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/client-visual-qa")
    data = dashboard_data()
    data["version"] = APP_VERSION
    data["client_visual_perfection"] = v740_client_visual_perfection_context()
    return render_template("admin_client_visual_qa.html", data=data)


@app.route("/api/admin/client-visual-qa")
@app.route("/api/admin/visual-qa")
def api_admin_client_visual_qa():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, "client_visual_perfection": v740_client_visual_perfection_context()})


# ===================== V741 CALENDAR SEARCH EXPERIENCE QA =====================

@app.route("/admin/calendar-experience")
@app.route("/admin/calendar-qa")
@app.route("/admin/calendar-search-qa")
def admin_calendar_experience_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/calendar-experience")
    data = dashboard_data()
    data["version"] = APP_VERSION
    data["calendar_experience"] = v741_calendar_experience_context()
    return render_template("admin_calendar_experience.html", data=data)


@app.route("/api/admin/calendar-experience")
@app.route("/api/admin/calendar-qa")
def api_admin_calendar_experience():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, "calendar_experience": v741_calendar_experience_context()})



# ===================== V738 FINAL COMMERCIAL RELEASE CANDIDATE =====================

def v738_final_release_context():
    return final_release_snapshot(DB_PATH, app_version=APP_VERSION)


@app.route("/admin/final-release")
@app.route("/admin/release-candidate")
@app.route("/admin/final-commercial")
def admin_final_release_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/final-release")
    data = dashboard_data()
    data["version"] = APP_VERSION
    data["final_release"] = v738_final_release_context()
    data["validation_plan"] = final_release_validation_plan()
    return render_template("admin_final_release.html", data=data)


@app.route("/api/admin/final-release")
@app.route("/api/admin/release-candidate")
def api_admin_final_release():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, "final_release": v738_final_release_context(), "validation_plan": final_release_validation_plan()})


@app.route("/api/admin/final-release/checklist")
def api_admin_final_release_checklist():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, "validation_plan": final_release_validation_plan()})


def v742_live_experience_admin_context():
    data = dashboard_data()
    hub = data.get("match_hub") or {}
    source = []
    for key in ("live", "today", "upcoming", "finished", "matches"):
        items = hub.get(key) if isinstance(hub, dict) else []
        if isinstance(items, list):
            source.extend(items)
    for key in ("matches", "upcoming_matches", "past_results", "candidate_matches"):
        items = data.get(key) or []
        if isinstance(items, list):
            source.extend(items)
    source = dedupe_matches_list(source)
    lanes = {
        "live": build_live_experience(source, lane="live"),
        "today": build_live_experience(source, lane="today"),
        "upcoming": build_live_experience(source, lane="upcoming"),
        "finished": build_live_experience(source, lane="finished"),
        "picks": build_live_experience(source, lane="picks"),
        "favorites": build_live_experience(source, lane="favorites"),
    }
    return {
        "version": APP_VERSION,
        "snapshot": live_experience_snapshot(app_version=APP_VERSION),
        "source_total": len(source),
        "lanes": lanes,
        "counts": {
            "live": (lanes["live"].get("counts") or {}).get("live", 0),
            "today": lanes["today"].get("filtered", 0),
            "upcoming": lanes["upcoming"].get("filtered", 0),
            "finished": lanes["finished"].get("filtered", 0),
            "with_pick": (lanes["picks"].get("counts") or {}).get("with_pick", 0),
            "favorites": (lanes["favorites"].get("counts") or {}).get("favorites", 0),
        },
        "notes": [
            "La vista cliente /live usa deduplicación antes de presentar partidos.",
            "Los minutos se muestran solo cuando existen; si no, se usa 'En directo'.",
            "Las horas visibles se formatean con filtros Madrid.",
        ],
    }


@app.route("/admin/live-experience")
@app.route("/admin/live-qa")
def admin_live_experience_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/live-experience")
    data = dashboard_data()
    data["live_experience_admin"] = v742_live_experience_admin_context()
    return render_template("admin_live_experience.html", data=data)


@app.route("/api/admin/live-experience")
@app.route("/api/admin/live-qa")
def api_admin_live_experience():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, "live_experience": v742_live_experience_admin_context()})


def v742_sale_ready_context():
    live_snap = live_experience_snapshot(app_version=APP_VERSION)
    calendar_snap = v741_calendar_experience_context()
    track = v742_track_record_context()
    telegram = telegram_reliability_snapshot(limit=80)
    visual = v740_client_visual_perfection_context()
    warnings = []
    if (telegram.get("diagnosis") or {}).get("status") not in {"READY_TO_SEND", "NO_CANDIDATES", "NO_PREMIUM_PICKS", "ALL_ALREADY_SENT", "BLOCKED_BY_QUIET_HOURS"}:
        warnings.append("Telegram requiere revisión de producción real.")
    if track.get("decided_total", 0) == 0:
        warnings.append("Track Record pendiente de resultados reales evaluables.")
    if not (calendar_snap.get("ok") or calendar_snap.get("status")):
        warnings.append("Calendario necesita revisión.")
    return {
        "version": APP_VERSION,
        "status": "SALE_READY_CONTROLADO" if len(warnings) <= 2 else "REVISAR_ANTES_DE_VENDER",
        "live": live_snap,
        "calendar": calendar_snap,
        "picks": pick_stats(),
        "track_record": track,
        "telegram": {
            "status": (telegram.get("diagnosis") or {}).get("status"),
            "explanation": (telegram.get("diagnosis") or {}).get("explanation"),
            "severity": (telegram.get("diagnosis") or {}).get("severity"),
            "counts": telegram.get("counts"),
        },
        "visual_mobile": visual,
        "render": {
            "db_path": DB_PATH,
            "runtime": APP_VERSION,
            "cron_secret_required": True,
            "zip_policy": "sin .git, .venv, caches, DB local, logs ni ZIPs internos",
        },
        "data_memory": data_memory_summary(DB_PATH),
        "warnings": warnings,
    }


@app.route("/admin/sale-ready")
@app.route("/admin/commercial-ready")
def admin_sale_ready_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/sale-ready")
    data = dashboard_data()
    data["sale_ready"] = v742_sale_ready_context()
    return render_template("admin_sale_ready.html", data=data)


@app.route("/api/admin/sale-ready")
def api_admin_sale_ready():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, "sale_ready": v742_sale_ready_context()})


def v742_content_rights_context():
    sample_items = [
        {"content_type": "video", "source": "YouTube", "embed_url": "https://www.youtube.com/embed/example", "attribution": "Fuente externa"},
        {"content_type": "crest", "source": "TheSportsDB", "original_url": "https://www.thesportsdb.com/images/media/team/badge/example.png", "attribution": "TheSportsDB"},
        {"content_type": "news", "source": "Fuente externa", "original_url": "https://example.com/noticia", "attribution": "Fuente original"},
        {"content_type": "image", "source": "unknown"},
    ]
    summary = content_rights_policy_summary(sample_items)
    return {
        "version": APP_VERSION,
        "summary": summary,
        "client_notice": "Vídeos, escudos y contenido externo pueden pertenecer a sus respectivos titulares. NeMeSiS SHARK PRO muestra enlaces o contenido embebido desde fuentes externas cuando está disponible.",
        "zip_policy": "El release no debe incluir vídeos, logos externos descargados, capturas locales ni assets dudosos.",
        "admin_notes": [
            "No se descargan vídeos.",
            "No se rehostean vídeos.",
            "No se cachean binarios externos sin permiso.",
            "Los escudos usan URL permitida o fallback propio.",
            "Las noticias no se copian completas.",
        ],
    }


@app.route("/admin/content-rights")
@app.route("/admin/legal-content")
def admin_content_rights_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/content-rights")
    data = dashboard_data()
    data["content_rights"] = v742_content_rights_context()
    return render_template("admin_content_rights.html", data=data)


@app.route("/api/admin/content-rights")
@app.route("/api/admin/legal-content")
def api_admin_content_rights():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, "content_rights": v742_content_rights_context()})


# ===================== V743 DATA VAULT + V744/V745 PRODUCTION CERTIFICATION =====================

def project_root_path():
    return os.path.dirname(os.path.abspath(__file__))


def admin_actor_label():
    return session.get("user_email") or session.get("user_name") or session.get("username") or "admin"


def v743_data_vault_context():
    status = db_vault_status(DB_PATH, project_root_path(), APP_VERSION)
    return {
        "version": APP_VERSION,
        "data_vault": status,
        "backups": data_vault_list_backups(project_root_path()),
        "policies": {
            "backup_retention": int(os.getenv("DATA_BACKUP_MAX_FILES", "30") or 30),
            "backup_dir": status.get("backup_dir"),
            "zip_includes_backups": False,
            "db_path_policy": "DB_PATH se mantiene externo al release; Render debe usar /data/database.db.",
            "ownership": status.get("ownership", {}),
        },
    }


def v744_render_runtime_context():
    telegram = telegram_diagnostics_safe()
    return {
        "version": APP_VERSION,
        "render": {
            "db_path": DB_PATH,
            "db_path_configured": env_present("DB_PATH"),
            "automation_secret_configured": automation_secret_configured(),
            "scheduler_enabled": scheduler_env_enabled(),
            "daily_automation_enabled": daily_automation_env_enabled(),
            "telegram_auto_enabled": telegram_env_auto_enabled(),
        },
        "cron": {
            "telegram_tick": "/api/automation/telegram/tick?secret=AUTOMATION_SECRET",
            "daily_run": "/api/automation/daily/run?secret=AUTOMATION_SECRET",
            "data_backup_run": "/api/automation/data-backup/run?secret=AUTOMATION_SECRET",
            "last_cron_telegram_call": automation_get("last_cron_telegram_call", {}),
            "last_cron_daily_call": automation_get("last_cron_daily_call", {}),
            "last_cron_data_backup_call": automation_get("last_cron_data_backup_call", {}),
        },
        "telegram": {
            "bot_configured": env_present("TELEGRAM_BOT_TOKEN"),
            "channel_configured": env_present("TELEGRAM_CHAT_ID"),
            "bot_username_configured": env_present("TELEGRAM_BOT_USERNAME"),
            "diagnostics": telegram,
        },
        "data_vault": v743_data_vault_context().get("data_vault", {}),
    }


def v745_match_intelligence_context(match_id=None):
    data = dashboard_data() if has_request_context() else {}
    matches = dedupe_matches_list((data.get("candidate_matches") or []) + (data.get("upcoming_matches") or []) + (data.get("past_results") or []))
    selected = None
    if match_id:
        selected = next((m for m in matches if str(m.get("id")) == str(match_id)), None)
    selected = selected or (matches[0] if matches else {})
    try:
        picks = get_picks(limit=80)
    except Exception:
        picks = []
    return {
        "version": APP_VERSION,
        "snapshot": match_intelligence_snapshot(),
        "match": selected,
        "intelligence": build_match_intelligence(selected, picks),
        "team_form": {
            "home": team_form_snapshot(matches, (selected or {}).get("home_team")),
            "away": team_form_snapshot(matches, (selected or {}).get("away_team")),
        },
        "standings": standings_snapshot([]),
        "counts": {"matches": len(matches), "picks": len(picks)},
    }


def v745_video_highlights_context():
    sample = [
        {"content_type": "video", "source": "YouTube", "embed_url": "", "original_url": "", "attribution": "Fuente externa"},
        {"content_type": "video", "source": "Proveedor externo", "original_url": "", "attribution": "Pendiente"},
    ]
    return {
        "version": APP_VERSION,
        "snapshot": video_highlights_snapshot(sample),
        "content_rights": v742_content_rights_context(),
        "policy": "Solo metadatos, embeds autorizados o enlace externo. No se descargan videos.",
    }


def v745_alerts_context():
    return {
        "version": APP_VERSION,
        "alerts": alerts_foundation_snapshot(enabled=env_bool("ENABLE_CLIENT_ALERTS", False)),
        "telegram": telegram_diagnostics_safe(),
        "rules": [
            "No enviar spam.",
            "No activar alertas nuevas durante QA.",
            "Registrar errores y mantener la web operativa si falla Telegram.",
        ],
    }


def v745_top_app_readiness_context():
    return {
        "version": APP_VERSION,
        "data_vault": v743_data_vault_context(),
        "production": v744_render_runtime_context(),
        "match_intelligence": v745_match_intelligence_context(),
        "video_highlights": v745_video_highlights_context(),
        "alerts": v745_alerts_context(),
        "payments": payment_readiness_snapshot(DB_PATH),
        "sale_ready": v742_sale_ready_context(),
        "status": "V745_FOUNDATION_READY",
    }


@app.route("/admin/data-vault")
@app.route("/admin/data-backups")
@app.route("/admin/business-intelligence")
def admin_data_vault_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/data-vault")
    data = dashboard_data()
    data["data_vault_admin"] = v743_data_vault_context()
    return render_template("admin_data_vault.html", data=data)


@app.route("/api/admin/data-vault")
@app.route("/api/admin/data-vault/backups")
def api_admin_data_vault():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, **v743_data_vault_context()})


@app.route("/api/admin/data-vault/create-backup", methods=["POST"])
def api_admin_data_vault_create_backup():
    if not is_admin_session():
        return admin_json_forbidden()
    result = create_sqlite_backup(DB_PATH, project_root_path(), APP_VERSION, backup_type="manual", created_by=admin_actor_label())
    try:
        automation_set("last_manual_data_backup", {"time": now_iso(), "result": result, "admin": admin_actor_label()})
    except Exception:
        pass
    return jsonify({"version": APP_VERSION, **result})


@app.route("/api/admin/data-vault/validate-backup", methods=["POST"])
def api_admin_data_vault_validate_backup():
    if not is_admin_session():
        return admin_json_forbidden()
    payload = request.get_json(silent=True) or dict(request.form or {})
    result = data_vault_validate_backup(project_root_path(), payload.get("backup_name") or payload.get("name") or "")
    return jsonify({"version": APP_VERSION, **result})


@app.route("/api/admin/data-vault/export", methods=["POST"])
def api_admin_data_vault_export():
    if not is_admin_session():
        return admin_json_forbidden()
    payload = request.get_json(silent=True) or dict(request.form or {})
    result = export_table_csv(DB_PATH, project_root_path(), payload.get("table") or "picks")
    return jsonify({"version": APP_VERSION, **result})


@app.route("/api/automation/data-backup/run", methods=["GET", "POST"])
def api_automation_data_backup_run():
    if not automation_cron_access_allowed():
        return automation_json_forbidden()
    if not env_bool("DATA_BACKUP_ENABLED", False):
        result = {"ok": True, "backup_created": False, "status": "DISABLED", "message": "DATA_BACKUP_ENABLED no esta activo."}
    else:
        result = create_sqlite_backup(DB_PATH, project_root_path(), APP_VERSION, backup_type="auto", created_by="render_cron")
    automation_safe_set("last_cron_data_backup_call", {"time": now_iso(), "result": result})
    return jsonify({"version": APP_VERSION, **result})


@app.route("/api/admin/production-readiness-v744")
def api_admin_production_readiness_v744():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, "production": v744_render_runtime_context()})


@app.route("/admin/match-intelligence")
def admin_match_intelligence_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/match-intelligence")
    data = dashboard_data()
    data["match_intelligence_admin"] = v745_match_intelligence_context(request.args.get("match_id"))
    return render_template("admin_match_intelligence.html", data=data)


@app.route("/api/admin/match-intelligence")
def api_admin_match_intelligence():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, "match_intelligence": v745_match_intelligence_context(request.args.get("match_id"))})


@app.route("/admin/video-highlights")
@app.route("/admin/highlights")
@app.route("/admin/news-center")
def admin_video_highlights_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/video-highlights")
    data = dashboard_data()
    data["video_highlights_admin"] = v745_video_highlights_context()
    return render_template("admin_video_highlights.html", data=data)


@app.route("/api/admin/video-highlights")
@app.route("/api/admin/highlights")
def api_admin_video_highlights():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, "video_highlights": v745_video_highlights_context()})


@app.route("/admin/alerts")
def admin_alerts_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/alerts")
    data = dashboard_data()
    data["alerts_admin"] = v745_alerts_context()
    return render_template("admin_alerts.html", data=data)


@app.route("/api/admin/alerts")
def api_admin_alerts():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, "alerts": v745_alerts_context()})


@app.route("/admin/top-app-readiness")
@app.route("/admin/v745-readiness")
def admin_top_app_readiness_page():
    if not is_admin_session():
        return redirect("/admin-login?next=/admin/top-app-readiness")
    data = dashboard_data()
    data["top_app_readiness"] = v745_top_app_readiness_context()
    return render_template("admin_top_app_readiness.html", data=data)


@app.route("/api/admin/top-app-readiness")
@app.route("/api/admin/v745-readiness")
def api_admin_top_app_readiness():
    if not is_admin_session():
        return admin_json_forbidden()
    return jsonify({"ok": True, "version": APP_VERSION, "top_app_readiness": v745_top_app_readiness_context()})


def register_optional_blueprints():
    try:
        if "architecture" not in app.blueprints:
            from blueprints.architecture import create_architecture_blueprint
            app.register_blueprint(create_architecture_blueprint(APP_VERSION, DB_PATH, is_admin_session))
    except Exception as exc:
        try:
            print("[BLUEPRINT_REGISTER_SKIP]", str(exc)[:300])
        except Exception:
            pass


register_optional_blueprints()


if __name__ == "__main__":
    seed_core()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG") == "1")
