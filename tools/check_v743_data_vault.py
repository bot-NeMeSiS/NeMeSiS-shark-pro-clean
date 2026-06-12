#!/usr/bin/env python3
"""Safe V743 Data Vault QA using a temporary SQLite database."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="nemesis_v743_vault_", ignore_cleanup_errors=True) as tmp:
        tmp_path = Path(tmp)
        db_path = tmp_path / "database.db"
        backup_dir = tmp_path / "backups"
        os.environ["DATA_BACKUP_DIR"] = str(backup_dir)
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE users(id TEXT PRIMARY KEY, name TEXT)")
            conn.execute("CREATE TABLE picks(id TEXT PRIMARY KEY, market TEXT)")
            conn.execute("INSERT INTO users(id,name) VALUES('u1','QA')")
            conn.commit()
        from engines.data_vault_engine import create_sqlite_backup, db_vault_status, validate_backup

        status = db_vault_status(db_path, ROOT, "V743_CHECK")
        backup = create_sqlite_backup(db_path, ROOT, "V743_CHECK", backup_type="qa", created_by="tool")
        validation = validate_backup(ROOT)
        result = {
            "ok": bool(status.get("ok") and backup.get("ok") and validation.get("ok")),
            "status_tables": len(status.get("tables") or []),
            "backup_created": backup.get("backup_created"),
            "backup_file": backup.get("backup_file"),
            "validated": validation.get("validated"),
            "retention": backup.get("retention", {}),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
