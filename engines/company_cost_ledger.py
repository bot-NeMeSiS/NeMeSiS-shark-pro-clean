"""Private, evidence-labelled company expense ledger.

Separate from existing recurring obligations (Founder OS) and verified Stripe
income. No prices are seeded, no provider requests, no payment/renewal actions.
Reads are immutable and use the existing production SQLite in mode=ro.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo
import re
import sqlite3
import uuid

PROVIDERS = {
    "render": "Render",
    "thesportsdb": "TheSportsDB",
    "api_football": "API-Football",
    "the_odds_api": "The Odds API",
    "chatgpt": "ChatGPT (trabajo, no uso de API)",
    "openai_api": "OpenAI API (consumo variable)",
    "other": "Otro proveedor",
}
STATUSES = {
    "ESTIMATED": "Estimación",
    "DECLARED": "Declarado sin factura verificada",
    "INVOICED": "Factura registrada por Admin",
    "PAID": "Pago declarado por Admin",
}
CURRENCIES = ("EUR", "USD")
SCHEMA = """
CREATE TABLE IF NOT EXISTS company_cost_entries (
    id TEXT PRIMARY KEY, request_id TEXT NOT NULL UNIQUE,
    provider TEXT NOT NULL, month TEXT NOT NULL, amount_cents INTEGER NOT NULL
    CHECK(amount_cents BETWEEN 1 AND 100000000),
    currency TEXT NOT NULL CHECK(currency IN ('EUR','USD')),
    evidence_status TEXT NOT NULL, reference_note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL, recorded_by TEXT NOT NULL,
    voided_at TEXT, void_reason TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS company_cost_month
    ON company_cost_entries(month,currency,evidence_status);
CREATE TABLE IF NOT EXISTS company_cost_audit (
    id INTEGER PRIMARY KEY, entry_id TEXT NOT NULL,
    action TEXT NOT NULL, actor TEXT NOT NULL, occurred_at TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT ''
);
"""

def _db_uri(path, mode):
    p = Path(path).resolve()
    if not p.is_file():
        raise ValueError("Base de datos de NeMeSiS no disponible.")
    return p.as_uri() + "?mode=" + mode

def _clock():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def _monthly_now():
    return datetime.now(ZoneInfo("Europe/Madrid")).strftime("%Y-%m")

def _amount(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,7}(?:[.,][0-9]{1,2})?", value):
        raise ValueError("Introduce un importe positivo con dos decimales como máximo.")
    try:
        parsed = Decimal(value.replace(",", "."))
        cents = parsed * 100
        if parsed <= 0 or cents > 100000000 or cents != cents.to_integral_value():
            raise ValueError("Importe fuera de rango.")
        return int(cents)
    except InvalidOperation as exc:
        raise ValueError("Importe no válido.") from exc

def _validated(payload):
    if not isinstance(payload, dict):
        raise ValueError("Registro no válido.")
    supplier = payload.get("provider")
    status = payload.get("status")
    currency = payload.get("currency")
    month = payload.get("month")
    nonce = payload.get("request_id")
    reference = payload.get("reference_note", "")
    if supplier not in PROVIDERS or status not in STATUSES or currency not in CURRENCIES:
        raise ValueError("Proveedor, moneda o tipo de evidencia no admitidos.")
    if not isinstance(month, str) or not re.fullmatch(r"20[0-9]{2}-(?:0[1-9]|1[0-2])", month):
        raise ValueError("Mes contable no válido.")
    if not isinstance(nonce, str) or not re.fullmatch(r"[a-f0-9]{32}", nonce):
        raise ValueError("Solicitud de registro no válida.")
    if not isinstance(reference, str) or len(reference) > 120 or any(
        token in reference.casefold() for token in ("bearer ", "api_key", "password=", "token=", "sk-")
    ) or "\n" in reference or "\r" in reference:
        raise ValueError("Referencia no válida. No introduzcas claves ni datos bancarios.")
    return {
        "provider": supplier, "month": month,
        "amount_cents": _amount(payload.get("amount")),
        "currency": currency, "evidence_status": status,
        "request_id": nonce, "reference_note": reference.strip(),
    }

def _connection(path, write=False):
    conn = sqlite3.connect(_db_uri(path, "rw" if write else "ro"),
                           uri=True, timeout=1.5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=1200")
    if not write:
        conn.execute("PRAGMA query_only=ON")
    return conn

def record_cost(path, payload, actor):
    """Append an expense on an explicit protected Admin POST, without charging."""
    if not isinstance(actor, str) or not actor or len(actor) > 128:
        raise ValueError("Se requiere identidad administrativa.")
    entry = _validated(payload)
    with _connection(path, write=True) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.executescript(SCHEMA)
        previous = conn.execute("SELECT * FROM company_cost_entries WHERE request_id=?",
                                (entry["request_id"],)).fetchone()
        if previous:
            if any(previous[key] != entry[key] for key in entry):
                raise ValueError("La solicitud de registro ya se utilizó para otro concepto.")
            return {"ok": True, "id": previous["id"], "repeated": True}
        entry_id = "cost:" + uuid.uuid4().hex
        now = _clock()
        conn.execute(
            "INSERT INTO company_cost_entries"
            "(id,request_id,provider,month,amount_cents,currency,evidence_status,"
            "reference_note,created_at,recorded_by) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (entry_id, entry["request_id"], entry["provider"], entry["month"],
             entry["amount_cents"], entry["currency"], entry["evidence_status"],
             entry["reference_note"], now, actor),
        )
        conn.execute("INSERT INTO company_cost_audit(entry_id,action,actor,occurred_at) "
                     "VALUES(?,?,?,?)", (entry_id, "CREATE", actor, now))
    return {"ok": True, "id": entry_id, "repeated": False}

def void_cost(path, entry_id, actor, reason):
    """Correct mistakes by voiding, retaining the original record and its audit."""
    if not isinstance(actor, str) or not actor or len(actor) > 128:
        raise ValueError("Se requiere identidad administrativa.")
    if not isinstance(entry_id, str) or not re.fullmatch(r"cost:[a-f0-9]{32}", entry_id):
        raise ValueError("Identificador no válido.")
    if not isinstance(reason, str) or not 4 <= len(reason.strip()) <= 120:
        raise ValueError("Indica un motivo breve para la corrección.")
    with _connection(path, write=True) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT id FROM company_cost_entries WHERE id=? AND voided_at IS NULL",
                           (entry_id,)).fetchone()
        if not row:
            raise ValueError("El registro ya fue anulado o no existe.")
        now = _clock()
        conn.execute("UPDATE company_cost_entries SET voided_at=?,void_reason=? WHERE id=?",
                     (now, reason.strip(), entry_id))
        conn.execute("INSERT INTO company_cost_audit(entry_id,action,actor,occurred_at,reason) "
                     "VALUES(?,?,?,?,?)", (entry_id, "VOID", actor, now, reason.strip()))
    return {"ok": True, "id": entry_id}

def snapshot(path, selected_month=None):
    """No provider calls, schema changes, or implicit zero when evidence is absent."""
    month = selected_month if (
        isinstance(selected_month, str) and
        re.fullmatch(r"20[0-9]{2}-(?:0[1-9]|1[0-2])", selected_month)
    ) else _monthly_now()
    empty = {"contract": "NEMESIS-COMPANY-COSTS-V1",
             "month": month, "state": "NOT_INITIALIZED", "rows": [],
             "totals": {}, "monthly": [], "entry_count": 0,
             "no_evidence_is_zero": False, "income_state": "NOT_RECONCILED",
             "provider_calls": 0, "payment_actions": 0}
    try:
        with _connection(path) as conn:
            present = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                                   "AND name='company_cost_entries'").fetchone()
            if not present:
                return empty
            rows = [dict(row) for row in conn.execute(
                "SELECT id,provider,month,amount_cents,currency,evidence_status,"
                "reference_note,created_at,voided_at FROM company_cost_entries "
                "WHERE month=? ORDER BY created_at DESC,id DESC LIMIT 100", (month,))]
            totals = {}
            for row in conn.execute(
                "SELECT currency,evidence_status,SUM(amount_cents) AS cents,"
                "COUNT(*) AS total FROM company_cost_entries "
                "WHERE month=? AND voided_at IS NULL "
                "GROUP BY currency,evidence_status", (month,)):
                totals.setdefault(row["currency"], {})[row["evidence_status"]] = {
                    "amount": f"{Decimal(row['cents']) / 100:.2f}",
                    "entries": row["total"],
                }
            months = [dict(row) for row in conn.execute(
                "SELECT month,currency,evidence_status,SUM(amount_cents) AS cents "
                "FROM company_cost_entries WHERE voided_at IS NULL "
                "GROUP BY month,currency,evidence_status ORDER BY month DESC LIMIT 180")]
            total = conn.execute("SELECT COUNT(*) FROM company_cost_entries "
                                 "WHERE voided_at IS NULL").fetchone()[0]
    except (OSError, ValueError, sqlite3.Error):
        return {**empty, "state": "READ_UNAVAILABLE"}
    for row in rows:
        row["amount"] = f"{Decimal(row.pop('amount_cents')) / 100:.2f}"
        row["provider_label"] = PROVIDERS.get(row["provider"], "Otro")
        row["status_label"] = STATUSES.get(row["evidence_status"], "Sin acreditar")
    return {**empty, "state": "READABLE", "rows": rows, "totals": totals,
            "monthly": [
                {**r, "amount": f"{Decimal(r.pop('cents')) / 100:.2f}"}
                for r in months
            ], "entry_count": total}
