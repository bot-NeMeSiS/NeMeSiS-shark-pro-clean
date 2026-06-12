"""Data Vault, backup and ownership helpers for NeMeSiS SHARK PRO."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

CRITICAL_TABLES = [
    "users", "matches", "picks", "favorites", "api_sync_runs",
    "match_snapshots", "odds_memory_snapshots", "live_memory_snapshots",
    "pick_decisions", "pick_discards", "telegram_delivery_memory",
    "team_identity_cache", "data_memory_errors", "persistent_cache",
    "pick_grading_results", "pick_grading_runs", "telegram_queue",
]

OWNERSHIP = {
    "users": "user_personal_data",
    "favorites": "user_personal_data",
    "matches": "external_api",
    "odds_memory_snapshots": "external_api",
    "match_snapshots": "external_api",
    "live_memory_snapshots": "external_api",
    "team_identity_cache": "external_api",
    "picks": "internal",
    "pick_decisions": "internal",
    "pick_discards": "internal",
    "pick_grading_results": "derived",
    "pick_grading_runs": "derived",
    "telegram_delivery_memory": "system_log",
    "telegram_queue": "system_log",
    "api_sync_runs": "system_log",
    "data_memory_errors": "system_log",
    "persistent_cache": "system_cache",
}


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def backup_dir(default_root: str | Path) -> Path:
    configured = os.getenv("DATA_BACKUP_DIR")
    if configured:
        return Path(configured)
    if Path("/data").exists():
        return Path("/data/backups")
    return Path(default_root) / "data" / "backups"


def connect_readonly(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def table_names(db_path: str | Path) -> list[str]:
    if not Path(db_path).exists():
        return []
    try:
        with connect_readonly(db_path) as conn:
            return [r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    except Exception:
        return []


def table_count(conn: sqlite3.Connection, table: str) -> int:
    try:
        row = conn.execute(f"SELECT COUNT(*) AS total FROM {table}").fetchone()
        return int(row["total"] or 0)
    except Exception:
        return 0


def db_vault_status(db_path: str | Path, root: str | Path, app_version: str = "") -> dict:
    path = Path(db_path)
    exists = path.exists()
    tables = table_names(path)
    counts = {}
    empty = []
    present = []
    missing = []
    if exists:
        try:
            with connect_readonly(path) as conn:
                for table in CRITICAL_TABLES:
                    if table in tables:
                        count = table_count(conn, table)
                        counts[table] = count
                        present.append(table)
                        if count == 0:
                            empty.append(table)
                    else:
                        missing.append(table)
        except Exception as exc:
            return {"ok": False, "error": str(exc)[:300], "db_path": str(path), "exists": exists}
    bdir = backup_dir(root)
    backups = list_backups(root)
    risk = []
    if not exists:
        risk.append("DB no encontrada.")
    if exists and path.stat().st_size < 1024 * 64:
        risk.append("La base de datos parece nueva o pequeña; revisar persistent disk antes de vender.")
    if not backups:
        risk.append("No hay backups válidos detectados.")
    return {
        "ok": exists,
        "version": app_version,
        "db_path": str(path),
        "db_path_masked": str(path).replace(str(Path.home()), "~"),
        "exists": exists,
        "size_bytes": path.stat().st_size if exists else 0,
        "modified_at": datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds") if exists else "",
        "tables": tables,
        "critical_present": present,
        "critical_missing": missing,
        "critical_empty": empty,
        "counts": counts,
        "backup_dir": str(bdir),
        "backups": backups[:20],
        "last_backup": backups[0] if backups else {},
        "risk": risk,
        "ownership": {table: OWNERSHIP.get(table, "unknown") for table in CRITICAL_TABLES},
    }


def list_backups(root: str | Path) -> list[dict]:
    bdir = backup_dir(root)
    if not bdir.exists():
        return []
    items = []
    backup_files = list(bdir.glob("database_*.db")) + list(bdir.glob("nemesis_backup_*.sqlite3"))
    for db_file in sorted(backup_files, key=lambda p: p.stat().st_mtime, reverse=True):
        manifest = db_file.with_suffix(".json")
        data = {}
        if manifest.exists():
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        items.append({
            "name": db_file.name,
            "path": str(db_file),
            "size_bytes": db_file.stat().st_size,
            "created_at": datetime.fromtimestamp(db_file.stat().st_mtime).isoformat(timespec="seconds"),
            "sha256": data.get("sha256") or "",
            "valid": data.get("valid", True),
            "manifest": manifest.name if manifest.exists() else "",
            "type": data.get("type") or "",
        })
    return items


def create_sqlite_backup(db_path: str | Path, root: str | Path, app_version: str, backup_type: str = "manual", created_by: str = "admin") -> dict:
    src = Path(db_path)
    if not src.exists():
        return {"ok": False, "backup_created": False, "error": "DB no encontrada", "db_path": str(src)}
    bdir = backup_dir(root)
    bdir.mkdir(parents=True, exist_ok=True)
    stamp = now_stamp()
    out = bdir / f"database_{stamp}.db"
    try:
        source = sqlite3.connect(str(src), timeout=15)
        dest = sqlite3.connect(str(out), timeout=15)
        with dest:
            source.backup(dest)
        source.close()
        dest.close()
        digest = sha256_file(out)
        status = db_vault_status(src, root, app_version)
        manifest = {
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "version": app_version,
            "db_path_source": str(src),
            "size_bytes": out.stat().st_size,
            "sha256": digest,
            "tables_included": status.get("tables", []),
            "records_summary": status.get("counts", {}),
            "type": backup_type,
            "environment": "production" if str(src).startswith("/data") else "local",
            "created_by": created_by,
            "valid": True,
            "notes": "Backup SQLite creado con API sqlite backup. No incluir en ZIP.",
        }
        manifest_path = out.with_suffix(".json")
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        retention = apply_backup_retention(root)
        return {"ok": True, "backup_created": True, "backup_file": out.name, "path": str(out), "sha256": digest, "manifest": manifest_path.name, "records_summary": status.get("counts", {}), "retention": retention}
    except Exception as exc:
        return {"ok": False, "backup_created": False, "error": str(exc)[:300]}


def validate_backup(root: str | Path, backup_name: str = "") -> dict:
    backups = list_backups(root)
    if backup_name:
        backups = [b for b in backups if b["name"] == backup_name]
    results = []
    for item in backups:
        path = Path(item["path"])
        expected = item.get("sha256")
        actual = sha256_file(path) if path.exists() else ""
        results.append({"name": item["name"], "ok": bool(actual and (not expected or expected == actual)), "expected": expected, "actual": actual})
    return {"ok": all(r["ok"] for r in results) if results else False, "validated": len(results), "results": results}


def apply_backup_retention(root: str | Path) -> dict:
    max_files = int(os.getenv("DATA_BACKUP_MAX_FILES", "30") or 30)
    backups = list_backups(root)
    removed = []
    if len(backups) <= max_files or max_files < 1:
        return {"ok": True, "removed": removed, "kept": len(backups)}
    # Never remove the newest valid backup.
    for item in backups[max_files:]:
        try:
            Path(item["path"]).unlink(missing_ok=True)
            manifest = Path(item["path"]).with_suffix(".json")
            manifest.unlink(missing_ok=True)
            removed.append(item["name"])
        except Exception:
            pass
    return {"ok": True, "removed": removed, "kept": min(len(backups), max_files)}


def export_table_csv(db_path: str | Path, root: str | Path, table: str) -> dict:
    if table not in CRITICAL_TABLES:
        return {"ok": False, "error": "Tabla no permitida para export seguro."}
    if not Path(db_path).exists():
        return {"ok": False, "error": "DB no encontrada."}
    out_dir = Path(root) / "data" / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"nemesis_export_{table}_{now_stamp()}.csv"
    try:
        with connect_readonly(db_path) as conn:
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            if not rows:
                out.write_text("", encoding="utf-8")
            else:
                columns = rows[0].keys()
                with out.open("w", encoding="utf-8", newline="") as fh:
                    writer = csv.DictWriter(fh, fieldnames=columns)
                    writer.writeheader()
                    for row in rows:
                        writer.writerow(dict(row))
        return {"ok": True, "file": out.name, "path": str(out), "classification": OWNERSHIP.get(table, "unknown")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:300]}
