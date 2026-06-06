import os
import re
import sqlite3
import time
from datetime import datetime
from pathlib import Path


BACKUP_RETENTION_MAX = 30


def default_backup_dir(db_path, configured_dir=None):
    if configured_dir:
        return os.path.abspath(configured_dir)
    absolute_db = os.path.abspath(db_path)
    render_db = os.path.abspath("/data/database.db")
    if absolute_db.startswith(os.path.abspath("/data") + os.sep) or absolute_db == render_db:
        return "/data/backups"
    return os.path.join(os.path.dirname(absolute_db) or os.getcwd(), "data", "backups")


def ensure_backup_dir(folder):
    os.makedirs(folder, exist_ok=True)
    return folder


def backup_filename(now, prefix="database"):
    return f"{prefix}_{now.strftime('%Y%m%d_%H%M%S')}.db"


def next_available_backup_path(folder, now_factory, prefix="database"):
    ensure_backup_dir(folder)
    for _ in range(4):
        candidate = os.path.join(folder, backup_filename(now_factory(), prefix))
        if not os.path.exists(candidate):
            return candidate
        time.sleep(1.05)
    return os.path.join(folder, backup_filename(now_factory(), prefix))


def backup_name_is_safe(name):
    name = os.path.basename(str(name or ""))
    return bool(re.fullmatch(r"[A-Za-z0-9_.-]+\.db", name))


def list_database_backups(folder, tz=None):
    folder = ensure_backup_dir(folder)
    items = []
    for path in sorted(Path(folder).glob("database_*.db"), key=lambda item: item.stat().st_mtime, reverse=True):
        try:
            stat = path.stat()
            created = datetime.fromtimestamp(stat.st_mtime, tz) if tz else datetime.fromtimestamp(stat.st_mtime)
            items.append({
                "name": path.name,
                "path": str(path),
                "created_at": created.isoformat(timespec="seconds"),
                "size": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
            })
        except OSError:
            continue
    return items


def prune_old_backups(folder, max_backups=BACKUP_RETENTION_MAX, tz=None):
    backups = list_database_backups(folder, tz=tz)
    removed = []
    for item in backups[int(max_backups):]:
        try:
            os.remove(item["path"])
            removed.append(item["name"])
        except OSError:
            pass
    return removed


def create_database_backup(db_path, folder, now_factory, prefix="database", max_backups=BACKUP_RETENTION_MAX, tz=None):
    source = os.path.abspath(db_path)
    if not os.path.exists(source) or os.path.getsize(source) <= 0:
        return {"ok": False, "error": "database_missing", "message": "No existe una base de datos que copiar."}
    target = next_available_backup_path(folder, now_factory, prefix=prefix)
    src = sqlite3.connect(source)
    dst = sqlite3.connect(target)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()
    removed = prune_old_backups(folder, max_backups=max_backups, tz=tz)
    return {"ok": True, "name": os.path.basename(target), "path": target, "size": os.path.getsize(target), "removed": removed}


def safe_backup_file_path(folder, name):
    if not backup_name_is_safe(name):
        return ""
    folder = os.path.abspath(folder)
    path = os.path.abspath(os.path.join(folder, os.path.basename(name)))
    if os.path.dirname(path) != folder or not os.path.exists(path):
        return ""
    return path


def restore_database_backup(db_path, backup_path):
    target = os.path.abspath(db_path)
    tmp_target = f"{target}.restore_tmp"
    with open(backup_path, "rb") as src, open(tmp_target, "wb") as dst:
        while True:
            chunk = src.read(1024 * 1024)
            if not chunk:
                break
            dst.write(chunk)
    os.replace(tmp_target, target)
    return {"ok": True}

