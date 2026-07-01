from pathlib import Path
import json
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = "V843_PRODUCT_TEAM_COMMERCIAL_READY_FINAL_REVIEW"
default_zip = ROOT / "release_output" / f"NeMeSiS_SHARK_PRO_{VERSION}_RENDER_READY.zip"
zip_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_zip

forbidden_parts = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "release_output",
    "logs",
    "backups",
}
forbidden_suffixes = {".db", ".sqlite", ".sqlite3", ".wal", ".shm", ".log", ".mp4", ".mov", ".avi", ".zip"}
findings = []
if not zip_path.exists():
    findings.append(f"missing zip: {zip_path}")
else:
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            parts = set(Path(name).parts)
            lower = name.lower()
            if parts & forbidden_parts:
                findings.append(name)
            if any(lower.endswith(suffix) for suffix in forbidden_suffixes):
                findings.append(name)

payload = {"ok": not findings, "zip": str(zip_path), "forbidden_count": len(findings), "findings": findings[:100]}
print(json.dumps(payload, ensure_ascii=False, indent=2))
raise SystemExit(0 if payload["ok"] else 1)
