"""Non-destructive disaster-recovery readiness for NeMeSiS SHARK PRO.

The module never restores the configured production database implicitly. It can
inspect backups and, only when explicitly called with an isolated scratch path,
verify that a copied backup opens and passes SQLite integrity checks.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


try:
    MADRID_TZ = ZoneInfo("Europe/Madrid")
except ZoneInfoNotFoundError:  # Minimal Windows Python may not bundle tzdata.
    MADRID_TZ = datetime.now().astimezone().tzinfo
PRODUCTION_DB = Path("/data/database.db")


def madrid_now_iso() -> str:
    return datetime.now(MADRID_TZ).isoformat(timespec="seconds")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _masked_path(path: str | Path) -> str:
    value = str(path or "")
    try:
        value = value.replace(str(Path.home()), "~")
    except Exception:
        pass
    return value


def _backup_directories(root: str | Path) -> list[Path]:
    root_path = Path(root)
    candidates: list[Path] = []
    configured = str(os.getenv("DATA_BACKUP_DIR") or "").strip()
    if configured:
        candidates.append(Path(configured))
    candidates.extend([root_path / "data" / "backups", root_path / "backups"])
    unique: list[Path] = []
    for candidate in candidates:
        if candidate not in unique:
            unique.append(candidate)
    return unique


def list_backup_evidence(root: str | Path, limit: int = 30) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    suffixes = {".db", ".sqlite", ".sqlite3"}
    for directory in _backup_directories(root):
        if not directory.exists() or not directory.is_dir():
            continue
        for path in directory.iterdir():
            if not path.is_file() or path.suffix.lower() not in suffixes:
                continue
            manifest_path = path.with_suffix(".json")
            manifest: dict[str, Any] = {}
            if manifest_path.exists():
                try:
                    parsed = json.loads(manifest_path.read_text(encoding="utf-8"))
                    manifest = parsed if isinstance(parsed, dict) else {}
                except Exception:
                    manifest = {}
            expected = str(manifest.get("sha256") or "")
            actual = ""
            try:
                actual = sha256_file(path)
            except OSError:
                actual = ""
            items.append({
                "name": path.name,
                "path_masked": _masked_path(path),
                "size_bytes": path.stat().st_size,
                "modified_at_madrid": datetime.fromtimestamp(path.stat().st_mtime, MADRID_TZ).isoformat(timespec="seconds"),
                "manifest_present": manifest_path.exists(),
                "hash_present": bool(expected),
                "hash_matches": bool(actual and expected and actual == expected),
                "sha256_prefix": actual[:12] if actual else "",
                "version": str(manifest.get("version") or ""),
                "type": str(manifest.get("type") or "unspecified"),
            })
    items.sort(key=lambda item: item.get("modified_at_madrid") or "", reverse=True)
    return items[: max(1, int(limit))]


def _sqlite_readonly_status(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"ok": False, "status": "MISSING", "integrity": "not_run"}
    connection: sqlite3.Connection | None = None
    try:
        uri = f"file:{path.resolve().as_posix()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True, timeout=2)
        integrity = str(connection.execute("PRAGMA quick_check").fetchone()[0])
        tables = int(connection.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0])
        return {"ok": integrity.lower() == "ok", "status": "READABLE", "integrity": integrity, "tables": tables}
    except sqlite3.OperationalError as exc:
        text = str(exc).lower()
        return {
            "ok": False,
            "status": "LOCKED" if "locked" in text else "UNREADABLE",
            "integrity": "not_run",
            "error_type": exc.__class__.__name__,
        }
    except Exception as exc:
        return {"ok": False, "status": "UNREADABLE", "integrity": "not_run", "error_type": exc.__class__.__name__}
    finally:
        if connection is not None:
            connection.close()


def build_disaster_recovery_readiness(root: str | Path, db_path: str | Path, app_version: str) -> dict[str, Any]:
    database = Path(db_path)
    db_status = _sqlite_readonly_status(database)
    backups = list_backup_evidence(root)
    valid_hash_backups = [item for item in backups if item.get("hash_matches")]
    offsite_configured = bool(str(os.getenv("OFFSITE_BACKUP_TARGET") or os.getenv("BACKUP_S3_BUCKET") or "").strip())
    restore_evidence = Path(root) / "data" / "runtime" / "v938_isolated_restore_latest.json"
    isolated_restore: dict[str, Any] = {}
    if restore_evidence.exists():
        try:
            payload = json.loads(restore_evidence.read_text(encoding="utf-8"))
            isolated_restore = payload if isinstance(payload, dict) else {}
        except Exception:
            isolated_restore = {}

    rpo_hours = int(os.getenv("V938_TARGET_RPO_HOURS", "24") or 24)
    rto_hours = int(os.getenv("V938_TARGET_RTO_HOURS", "4") or 4)
    gaps: list[str] = []
    if not backups:
        gaps.append("No hay evidencia de backup local disponible.")
    elif not valid_hash_backups:
        gaps.append("Hay backups, pero ninguno aporta manifest y hash coincidente.")
    if not offsite_configured:
        gaps.append("No existe evidencia de un destino offsite independiente configurado.")
    if not isolated_restore.get("ok"):
        gaps.append("No existe evidencia vigente de una restauracion aislada correcta.")
    if not db_status.get("ok"):
        gaps.append("La base configurada no supera la lectura de integridad local.")

    return {
        "ok": db_status.get("ok") is True and bool(valid_hash_backups),
        "version": app_version,
        "checked_at_madrid": madrid_now_iso(),
        "database": {**db_status, "path_masked": _masked_path(database)},
        "backup_count": len(backups),
        "validated_backup_count": len(valid_hash_backups),
        "latest_backup": backups[0] if backups else {},
        "offsite": {
            "configured": offsite_configured,
            "evidence_state": "NO_CERTIFICADO" if offsite_configured else "NO_CERTIFICADO",
            "safe_message": "Configuracion detectada; una copia externa real exige certificacion independiente." if offsite_configured else "Destino offsite no demostrado.",
        },
        "isolated_restore": {
            "certified": bool(isolated_restore.get("ok")),
            "checked_at_madrid": isolated_restore.get("checked_at_madrid") or "",
            "evidence_state": "CONFIRMADO" if isolated_restore.get("ok") else "NO_CERTIFICADO",
        },
        "targets": {"rpo_hours": rpo_hours, "rto_hours": rto_hours},
        "gaps": gaps,
        "production_restore_executed": False,
    }


def run_isolated_restore_test(backup_path: str | Path, scratch_dir: str | Path | None = None) -> dict[str, Any]:
    """Copy one backup to a temporary location and inspect it there.

    The source must not be the configured live DB. The destination must be an
    isolated scratch directory and can never be `/data/database.db`.
    """
    source = Path(backup_path).resolve()
    configured_db = Path(str(os.getenv("DB_PATH") or PRODUCTION_DB)).resolve()
    if source == configured_db or source == PRODUCTION_DB:
        return {"ok": False, "status": "REFUSED", "reason": "production_database_is_not_a_restore_fixture"}
    if not source.exists():
        return {"ok": False, "status": "MISSING", "reason": "backup_not_found"}

    base = Path(scratch_dir).resolve() if scratch_dir else Path(tempfile.mkdtemp(prefix="nemesis_v938_restore_"))
    if base == Path("/data").resolve() or str(base).replace("\\", "/").startswith("/data/"):
        return {"ok": False, "status": "REFUSED", "reason": "production_disk_not_allowed_for_restore_test"}
    base.mkdir(parents=True, exist_ok=True)
    target = base / "isolated_restore.sqlite3"
    shutil.copy2(source, target)
    status = _sqlite_readonly_status(target)
    result = {
        "ok": status.get("ok") is True,
        "status": "PASS" if status.get("ok") else "FAIL",
        "checked_at_madrid": madrid_now_iso(),
        "source_name": source.name,
        "source_sha256_prefix": sha256_file(source)[:12],
        "isolated_copy_sha256_prefix": sha256_file(target)[:12],
        "integrity": status.get("integrity"),
        "tables": status.get("tables", 0),
        "production_database_touched": False,
    }
    return result
