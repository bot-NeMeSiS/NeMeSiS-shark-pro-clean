"""A closed Admin action boundary on the existing operational database.

This module performs no network I/O and imports no application/runtime module.
Integration supplies explicit callbacks for registered operations. Model output is
never executable authority: a proposal is bound to an admin, version and expiry,
and a separate authenticated/CSRF-protected request must confirm its exact ID.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import re
import sqlite3
import time
import uuid


SETTING_DEFAULTS = {"highlights_enabled": True, "banner_enabled": False, "banner_text": ""}
SETTING_PREFIX = "admin_control.settings."
ORIGINS = frozenset(("manual", "SHARK proposal", "Sentinel", "AutoPilot"))
SECRET_PATTERN = re.compile(r"""(?ix)(?:
    \b(?:password|passwd|secret|token|api[_ -]?key|authorization|cookie|session[_ -]?id|
       [a-z0-9_]*(?:token|secret|password|api_key|cookie|session_id|_key)[a-z0-9_]*)\b["']?\s*[:=]|
    \b(?:sk|pk)_(?:live|test)_[A-Za-z0-9]+|\bsk-[A-Za-z0-9_-]{12,}|
    \bbot\d+:[A-Za-z0-9_-]+|\b\d{6,}:[A-Za-z0-9_-]{20,}|
    https?://[^\s/]+:[^\s/@]+@|\bBearer\s+\S+|-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----|
    \beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}
)""")

class Rejected(ValueError):
    def __init__(self, code, status=400):
        self.code = code
        self.status = status
        super().__init__(code)


def _meta(label, description, category, risk, schema, reversible=False, phrase=""):
    return {"label": label, "description": description, "category": category,
            "risk_level": risk, "parameters_schema": schema, "requires_confirmation": True,
            "reversible": reversible, "permission": "admin", "confirmation_phrase": phrase}


ACTIONS = {
    "sentinel.record_verification": _meta("Registrar verificacion", "Registra evidencia aportada por Admin, ligada al SHA y recurrencia. No ejecuta tests ni certifica produccion.", "sentinel", "MEDIUM", {"issue_id":"issue_id", "root_cause":"text", "corrective_action":"text", "regression_test":"text", "prevention":"text", "detection":"text", "fix_sha":"sha", "evidence_ref":"text", "checked_at":"datetime", "result":"result", "scope":"scope"}),
    "sentinel.resolve": _meta("Resolver incidencia verificada", "Solo permite cerrar con evidencia vigente; conserva historial y auditoria.", "sentinel", "MEDIUM", {"issue_id":"issue_id"}),
    "settings.update": _meta("Cambiar configuración", "Actualiza un ajuste visible y reversible.", "settings", "LOW", {"key": "allowed_setting", "value": "setting_type"}, True),
    "settings.rollback": _meta("Revertir configuración", "Restaura el valor anterior si nadie lo ha cambiado después.", "settings", "LOW", {"audit_id": "positive_integer"}, True),
    "sports.sync": _meta("Sincronizar partidos", "Actualiza partidos, cuotas y revisa resultados de picks con los motores existentes; puede consumir solicitudes. No envía Telegram ni realiza pagos.", "sports", "MEDIUM", {}),
    "telegram.dry_run": _meta("Comprobar Telegram", "Ejecuta el diagnóstico existente sin enviar mensajes.", "telegram", "LOW", {}),
    "telegram.retry_failed": _meta("Reintentar Telegram fallidos", "Puede enviar mensajes reales a destinatarios de la cola.", "telegram", "HIGH", {}, phrase="REINTENTAR TELEGRAM"),
    "sentinel.scan": _meta("Ejecutar Sentinel", "Ejecuta el diagnóstico existente y conserva su evidencia.", "sentinel", "MEDIUM", {}),
    "sentinel.create_improvement": _meta("Preparar mejora para Codex", "Crea o actualiza una incidencia en el workflow Sentinel existente.", "sentinel", "LOW", {"title": "text_160", "detail": "text_1200", "route": "local_route_180"}),
}


def registry():
    return [{"action_id": key, **deepcopy(value)} for key, value in ACTIONS.items()]


def _text(value, maximum, *, empty=False):
    if type(value) is not str or len(value) > maximum or (not value.strip() and not empty):
        raise Rejected("invalid_parameters")
    if any(ord(c) < 32 and c not in "\n\t" for c in value) or SECRET_PATTERN.search(value):
        raise Rejected("unsafe_parameters")
    return value.strip()


def _setting_value(key, value):
    if type(key) is not str or key not in SETTING_DEFAULTS:
        raise Rejected("setting_not_allowed")
    if key == "banner_text":
        return _text(value, 240, empty=True)
    if type(value) is not bool:
        raise Rejected("invalid_parameters")
    return value


def validate_parameters(action_id, parameters):
    if type(action_id) is not str or action_id not in ACTIONS:
        raise Rejected("action_not_allowed")
    if type(parameters) is not dict or set(parameters) != set(ACTIONS[action_id]["parameters_schema"]):
        raise Rejected("invalid_parameters")
    if action_id == "settings.update":
        return {"key": parameters["key"], "value": _setting_value(parameters["key"], parameters["value"])}
    if action_id == "settings.rollback":
        ident = parameters["audit_id"]
        if type(ident) is not int or ident < 1:
            raise Rejected("invalid_parameters")
        return {"audit_id": ident}
    if action_id == "sentinel.create_improvement":
        route = _text(parameters["route"], 180)
        if not re.fullmatch(r"/[A-Za-z0-9_/-]*", route) or "//" in route or ".." in route:
            raise Rejected("invalid_route")
        return {"title": _text(parameters["title"], 160), "detail": _text(parameters["detail"], 1200), "route": route}
    if action_id in ("sentinel.record_verification", "sentinel.resolve"):
        output = {k:_text(v, 900) for k,v in parameters.items()}
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", output["issue_id"]):
            raise Rejected("invalid_issue_id")
        if action_id == "sentinel.record_verification":
            from engines.reliability_engine import sha, stamp
            if not sha(output["fix_sha"]) or not stamp(output["checked_at"]) or output["result"] not in ("PASS", "FAIL") or output["scope"] not in ("LOCAL_QA", "CI", "PRODUCTION"):
                raise Rejected("invalid_verification")
        return output
    return {}


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _result_summary(result):
    """Never retain raw callback errors, payloads, credentials or user objects."""
    if type(result) is not dict:
        return {"ok": False, "code": "invalid_handler_result"}
    output = {"ok": result.get("ok") is True}
    for key in ("processed", "received", "stored", "external_calls", "pending", "failed", "sent", "skipped"):
        value = result.get(key)
        if type(value) in (int, bool) and (type(value) is bool or 0 <= value <= 10**9):
            output[key] = value
    # Status is an enum, not a free-form provider string. Identifiers must match
    # the existing Sentinel generators; even allowlisted fields can carry secrets.
    allowed_statuses = {"OK", "ERROR", "FAILED", "SUCCESS", "SYNCED", "COMPLETED", "SKIPPED",
                        "NOT_REQUIRED", "SAFE_SKIP_NO_LIVE_WINDOW", "DRY_RUN", "READY", "OPEN_REAL",
                        "INSUFFICIENT_EVIDENCE", "NO_DATA", "PARTIAL", "QUEUED", "pending_approval",
                        "ready_for_safe_review"}
    if type(result.get("status")) is str and result["status"] in allowed_statuses:
        output["status"] = result["status"]
    for key, pattern in (("issue_id", r"(?:SENT-\d{4}-[A-F0-9]{8}|ISSUE-[A-F0-9]{12}|AUTO-[A-F0-9]{12})"),
                         ("task_id", r"TASK-(?:[A-F0-9]{12}|SENT-\d{4}-[A-F0-9]{8}|ISSUE-[A-F0-9]{12}|AUTO-[A-F0-9]{12})")):
        value = result.get(key)
        if type(value) is str and re.fullmatch(pattern, value):
            output[key] = value
    return output


class AdminControlStore:
    def __init__(self, db_path, version, *, clock=None, ttl=600):
        self.path = Path(db_path)
        self.version = str(version)
        self.clock = clock or time.time
        self.ttl = min(900, max(30, int(ttl)))

    @contextmanager
    def connection(self, *, write=False):
        # Initialization is explicit; reads never create a database or schema.
        conn = sqlite3.connect(self.path.resolve().as_uri() + ("?mode=rw" if write else "?mode=ro"), uri=True, timeout=10 if write else .2)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("BEGIN IMMEDIATE" if write else "PRAGMA query_only=ON")
            yield conn
            if write:
                conn.commit()
        except Exception:
            if write:
                conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self):
        # The application owns DB_PATH and creates its parent, never the model.
        with sqlite3.connect(self.path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS automation_state (
                    key TEXT PRIMARY KEY, value_json TEXT, updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS admin_action_proposals (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL, action_id TEXT NOT NULL,
                    parameters_json TEXT NOT NULL, origin TEXT NOT NULL,
                    app_version TEXT NOT NULL, state TEXT NOT NULL,
                    created REAL NOT NULL, expires REAL NOT NULL,
                    request_key TEXT NOT NULL, preview_json TEXT NOT NULL,
                    result_json TEXT, audit_id INTEGER,
                    UNIQUE(owner,request_key)
                );
                CREATE TABLE IF NOT EXISTS admin_action_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL NOT NULL,
                    admin TEXT NOT NULL, proposal_id TEXT NOT NULL,
                    action_id TEXT NOT NULL, category TEXT NOT NULL, origin TEXT NOT NULL,
                    parameters_json TEXT NOT NULL, before_json TEXT NOT NULL,
                    after_json TEXT NOT NULL, result_json TEXT NOT NULL,
                    verification TEXT NOT NULL, app_version TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS admin_proposal_owner_time ON admin_action_proposals(owner,created);
                CREATE TRIGGER IF NOT EXISTS admin_audit_no_update BEFORE UPDATE ON admin_action_audit
                    BEGIN SELECT RAISE(ABORT,'audit_is_append_only'); END;
                CREATE TRIGGER IF NOT EXISTS admin_audit_no_delete BEFORE DELETE ON admin_action_audit
                    BEGIN SELECT RAISE(ABORT,'audit_is_append_only'); END;
            """)

    @staticmethod
    def registry():
        return registry()

    @staticmethod
    def _owner(owner):
        if type(owner) is not str or not re.fullmatch(r"[A-Za-z0-9_@.+:-]{1,120}", owner):
            raise Rejected("invalid_admin", 403)
        return owner

    def _read_setting(self, conn, key):
        row = conn.execute("SELECT value_json,updated_at FROM automation_state WHERE key=?", (SETTING_PREFIX + key,)).fetchone()
        if row is None:
            return {"value": SETTING_DEFAULTS[key], "revision": 0, "updated_at": None, "admin": None, "origin": "default", "version": None}
        try:
            value = json.loads(row["value_json"])
            if type(value) is not dict or type(value.get("revision")) is not int or value["revision"] < 1:
                raise ValueError()
            _setting_value(key, value.get("value"))
            return {"value": value["value"], "revision": value["revision"], "updated_at": row["updated_at"],
                    "admin": value.get("admin"), "origin": value.get("origin"), "version": value.get("version")}
        except (ValueError, TypeError, KeyError):
            raise Rejected("setting_state_invalid", 409)

    def settings(self):
        try:
            with self.connection() as conn:
                return {key: self._read_setting(conn, key) for key in SETTING_DEFAULTS}
        except sqlite3.OperationalError as exc:
            if self.path.exists() and str(exc).lower() != "no such table: automation_state":
                raise
            return {key: {"value": value, "revision": 0, "updated_at": None, "admin": None,
                          "origin": "default", "version": None} for key, value in SETTING_DEFAULTS.items()}

    def _preview(self, conn, action_id, parameters):
        if action_id == "settings.update":
            key = parameters["key"]
            before = self._read_setting(conn, key)
            return {"key": key, "before": before, "after": {"value": parameters["value"], "revision": before["revision"] + 1},
                    "impact": "Cambia la presentación cliente; no borra datos."}
        if action_id == "settings.rollback":
            row = conn.execute("SELECT * FROM admin_action_audit WHERE id=?", (parameters["audit_id"],)).fetchone()
            if row is None or row["action_id"] not in ("settings.update", "settings.rollback") or row["verification"] != "VERIFIED":
                raise Rejected("rollback_not_available", 409)
            prior = json.loads(row["before_json"])
            after = json.loads(row["after_json"])
            key = prior["key"]
            current = self._read_setting(conn, key)
            if current["revision"] != after["revision"] or current["value"] != after["value"]:
                raise Rejected("setting_changed_since_action", 409)
            return {"key": key, "before": current,
                    "after": {"value": prior["value"], "revision": current["revision"] + 1},
                    "reverts_audit_id": row["id"], "impact": "Restaura el ajuste anterior y conserva todo el historial."}
        return {"before": None, "after": None, "impact": ACTIONS[action_id]["description"]}

    @staticmethod
    def _public(row):
        data = dict(row)
        for key in ("parameters", "preview", "result"):
            raw = data.pop(key + "_json", None)
            data[key] = json.loads(raw) if raw is not None else None
        data.pop("owner", None)
        data.pop("request_key", None)
        # Risk and permissions are recomputed, never trusted from the client/store.
        data["action"] = {"action_id": data["action_id"], **deepcopy(ACTIONS[data["action_id"]])}
        return data

    def propose(self, owner, action_id, parameters, *, origin="manual", request_key=None):
        owner = self._owner(owner)
        parameters = validate_parameters(action_id, parameters)
        if type(origin) is not str or origin not in ORIGINS:
            raise Rejected("invalid_origin")
        request_key = request_key if request_key is not None else uuid.uuid4().hex
        if type(request_key) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{16,80}", request_key):
            raise Rejected("invalid_request_key")
        encoded = _json(parameters)
        with self.connection(write=True) as conn:
            previous = conn.execute("SELECT * FROM admin_action_proposals WHERE owner=? AND request_key=?", (owner, request_key)).fetchone()
            if previous:
                if previous["action_id"] != action_id or previous["parameters_json"] != encoded or previous["origin"] != origin:
                    raise Rejected("idempotency_conflict", 409)
                return self._public(previous)
            preview = self._preview(conn, action_id, parameters)
            now = self.clock()
            ident = uuid.uuid4().hex
            conn.execute("INSERT INTO admin_action_proposals(id,owner,action_id,parameters_json,origin,app_version,state,created,expires,request_key,preview_json) VALUES(?,?,?,?,?,?,'PENDING',?,?,?,?)",
                         (ident, owner, action_id, encoded, origin, self.version, now, now + self.ttl, request_key, _json(preview)))
            return self._public(conn.execute("SELECT * FROM admin_action_proposals WHERE id=?", (ident,)).fetchone())

    @staticmethod
    def _find(conn, owner, ident):
        if type(ident) is not str or not re.fullmatch(r"[a-f0-9]{32}", ident):
            raise Rejected("invalid_proposal_id")
        row = conn.execute("SELECT * FROM admin_action_proposals WHERE id=? AND owner=?", (ident, owner)).fetchone()
        if row is None:
            raise Rejected("proposal_not_found", 404)
        return row

    def _audit(self, conn, row, before, after, result, verification):
        action = ACTIONS[row["action_id"]]
        cursor = conn.execute("INSERT INTO admin_action_audit(timestamp,admin,proposal_id,action_id,category,origin,parameters_json,before_json,after_json,result_json,verification,app_version) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                              (self.clock(), row["owner"], row["id"], row["action_id"], action["category"], row["origin"], row["parameters_json"],
                               _json(before), _json(after), _json(result), verification, self.version))
        return cursor.lastrowid

    def _finish(self, conn, row, before, after, result, verified):
        verification = "VERIFIED" if verified else "VERIFICATION_FAILED"
        audit_id = self._audit(conn, row, before, after, result, verification)
        complete = {"ok": bool(result.get("ok") and verified), "proposal_id": row["id"], "audit_id": audit_id,
                    "verification": verification, "result": result}
        conn.execute("UPDATE admin_action_proposals SET state=?,result_json=?,audit_id=? WHERE id=?",
                     ("COMPLETED" if complete["ok"] else "FAILED", _json(complete), audit_id, row["id"]))
        return complete

    def confirm(self, owner, proposal_id, *, handlers=None, verifiers=None, confirmation=""):
        owner = self._owner(owner)
        handlers, verifiers = handlers or {}, verifiers or {}
        with self.connection(write=True) as conn:
            row = self._find(conn, owner, proposal_id)
            if row["state"] in ("COMPLETED", "FAILED"):
                return {**json.loads(row["result_json"]), "reused": True}
            if row["state"] != "PENDING":
                raise Rejected("proposal_not_pending", 409)
            if row["expires"] <= self.clock():
                raise Rejected("proposal_expired", 409)
            if row["app_version"] != self.version:
                raise Rejected("proposal_version_changed", 409)
            action_id = row["action_id"]
            parameters = validate_parameters(action_id, json.loads(row["parameters_json"]))
            phrase = ACTIONS[action_id]["confirmation_phrase"]
            if (phrase and confirmation != phrase) or (not phrase and confirmation is not True):
                raise Rejected("reinforced_confirmation_required", 409)
            preview = json.loads(row["preview_json"])
            if action_id.startswith("settings."):
                current_preview = self._preview(conn, action_id, parameters)
                if current_preview != preview:
                    raise Rejected("proposal_state_changed", 409)
                key = preview["key"]
                before = {"key": key, **self._read_setting(conn, key)}
                envelope = {"value": preview["after"]["value"], "revision": before["revision"] + 1,
                            "admin": owner, "origin": row["origin"], "version": self.version}
                from datetime import datetime, timezone
                stamp = datetime.fromtimestamp(self.clock(), timezone.utc).isoformat(timespec="seconds")
                conn.execute("INSERT INTO automation_state(key,value_json,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json,updated_at=excluded.updated_at",
                             (SETTING_PREFIX + key, _json(envelope), stamp))
                after = {"key": key, **self._read_setting(conn, key)}
                verified = after["value"] == preview["after"]["value"] and after["revision"] == envelope["revision"]
                if not verified:
                    raise Rejected("setting_verification_failed", 409)
                return self._finish(conn, row, before, after, {"ok": True, "status": "SETTING_APPLIED"}, verified)
            handler, verifier = handlers.get(action_id), verifiers.get(action_id)
            if not callable(handler) or not callable(verifier):
                raise Rejected("action_not_connected", 503)
            # Commit claim before any callback: concurrent/double-click requests
            # cannot invoke this proposal twice. An interrupted claim stays
            # EXECUTING for manual reconciliation, never automatic retry.
            conn.execute("UPDATE admin_action_proposals SET state='EXECUTING' WHERE id=? AND state='PENDING'", (proposal_id,))
            self._audit(conn, row, None, None, {"ok": True, "status": "EXECUTION_STARTED"}, "PENDING")
        raw, verified = None, False
        try:
            raw = handler(deepcopy(parameters))
            checked = verifier(deepcopy(parameters), raw)
            verified = (type(raw) is dict and raw.get("ok") is True) and (checked is True or (type(checked) is dict and checked.get("verified") is True))
            result = _result_summary(raw)
        except Exception:
            # Never persist traceback or text from provider exceptions.
            result = {"ok": False, "code": "action_failed"}
        with self.connection(write=True) as conn:
            final_row = self._find(conn, owner, proposal_id)
            return self._finish(conn, final_row, None, None, result, verified)

    def cancel(self, owner, proposal_id):
        owner = self._owner(owner)
        with self.connection(write=True) as conn:
            row = self._find(conn, owner, proposal_id)
            if row["state"] == "CANCELLED":
                return {"ok": True, "state": "CANCELLED", "reused": True}
            if row["state"] != "PENDING":
                raise Rejected("proposal_not_pending", 409)
            audit_id = self._audit(conn, row, None, None, {"ok": True, "status": "CANCELLED"}, "NOT_EXECUTED")
            conn.execute("UPDATE admin_action_proposals SET state='CANCELLED',audit_id=? WHERE id=?", (audit_id, proposal_id))
            return {"ok": True, "state": "CANCELLED", "audit_id": audit_id}

    def list_proposals(self, owner, limit=30):
        owner = self._owner(owner)
        with self.connection() as conn:
            return [self._public(row) for row in conn.execute("SELECT * FROM admin_action_proposals WHERE owner=? ORDER BY created DESC LIMIT ?", (owner, min(100, max(1, int(limit)))))]

    def list_audit(self, limit=50):
        with self.connection() as conn:
            result = []
            for row in conn.execute("SELECT * FROM admin_action_audit ORDER BY id DESC LIMIT ?", (min(200, max(1, int(limit))),)):
                item = dict(row)
                for key in ("parameters", "before", "after", "result"):
                    item[key] = json.loads(item.pop(key + "_json"))
                result.append(item)
            return result
