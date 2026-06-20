#!/usr/bin/env python3
"""Audit a release ZIP and fail if development trash or sensitive files slipped in."""
from __future__ import annotations

import json
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import PurePosixPath

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports"
VERSION_FILE = ROOT / "VERSION.txt"
VERSION = VERSION_FILE.read_text(encoding="utf-8-sig").strip() if VERSION_FILE.exists() else "DEV"
VERSION_PREFIX = VERSION.split("_", 1)[0] if VERSION else "DEV"
FORBIDDEN_PARTS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "logs",
    "backups",
    "release",
    "release_output",
    "releases",
    "tmp",
    "temp",
    "v636work",
    "archive_legacy",
    "reports/archive",
}
FORBIDDEN_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".db-wal",
    ".db-shm",
    ".sqlite-wal",
    ".sqlite-shm",
    ".log",
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".orig",
    ".bak",
    ".backup",
    ".old",
    ".tmp",
}
FORBIDDEN_NAMES = {".DS_Store", "Thumbs.db", ".env"}
SECRET_MARKERS = ("secret", "token", "private_key", "id_rsa")


def latest_zip() -> Path:
    search_dirs = [ROOT.parent / "releases", ROOT / "release_output", ROOT]
    zips = []
    for directory in search_dirs:
        if directory.exists():
            zips.extend(directory.glob("*RENDER_READY.zip"))
    zips = sorted(zips, key=lambda p: p.stat().st_mtime, reverse=True)
    if not zips:
        for directory in search_dirs:
            if directory.exists():
                zips.extend(directory.glob("*.zip"))
        zips = sorted(zips, key=lambda p: p.stat().st_mtime, reverse=True)
    if not zips:
        raise FileNotFoundError("No hay ZIP de release en releases, release_output ni la carpeta del proyecto.")
    return zips[0]


def is_forbidden(filename: str) -> tuple[bool, str]:
    path = PurePosixPath(filename)
    parts = set(path.parts)
    lower = filename.lower()
    lower_name = path.name.lower()
    if parts & FORBIDDEN_PARTS:
        return True, "directorio prohibido"
    if path.name in FORBIDDEN_NAMES:
        return True, "archivo prohibido"
    if any(lower_name.endswith(suffix) for suffix in FORBIDDEN_SUFFIXES):
        return True, "extension prohibida"
    if lower_name.endswith(".zip"):
        return True, "zip interno"
    if any(marker in lower_name for marker in SECRET_MARKERS) and path.name not in {".env.example", ".env.render.clean"}:
        return True, "nombre sensible"
    return False, ""


def audit_zip(target: Path) -> dict:
    bad = []
    sizes = []
    folder_sizes: defaultdict[str, int] = defaultdict(int)
    folder_counts: Counter[str] = Counter()
    with zipfile.ZipFile(target) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            sizes.append((info.file_size, info.filename))
            first = PurePosixPath(info.filename).parts[0] if PurePosixPath(info.filename).parts else "."
            folder_sizes[first] += info.file_size
            folder_counts[first] += 1
            forbidden, reason = is_forbidden(info.filename)
            if forbidden:
                bad.append({"path": info.filename, "reason": reason, "size": info.file_size})
    sizes.sort(reverse=True)
    return {
        "ok": not bad,
        "audited_at": datetime.now().isoformat(timespec="seconds"),
        "zip": str(target),
        "zip_size_bytes": target.stat().st_size,
        "file_count": len(sizes),
        "content_size_bytes": sum(size for size, _ in sizes),
        "forbidden_count": len(bad),
        "forbidden": bad[:200],
        "top_files": [{"path": name, "size": size} for size, name in sizes[:20]],
        "top_folders": [
            {"folder": name, "size": folder_sizes[name], "files": folder_counts[name]}
            for name in sorted(folder_sizes, key=folder_sizes.get, reverse=True)[:20]
        ],
    }


def write_reports(report: dict) -> None:
    REPORT_DIR.mkdir(exist_ok=True)
    (REPORT_DIR / f"RELEASE_ZIP_AUDIT_{VERSION_PREFIX}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        f"# Auditoría ZIP {VERSION_PREFIX}",
        "",
        f"- ZIP: `{Path(report['zip']).name}`",
        f"- Archivos: {report['file_count']}",
        f"- Tamaño ZIP: {report['zip_size_bytes']} bytes",
        f"- Prohibidos: {report['forbidden_count']}",
        f"- Resultado: {'OK' if report['ok'] else 'FAIL'}",
        "",
        "## Carpetas principales",
    ]
    for item in report["top_folders"][:10]:
        lines.append(f"- `{item['folder']}`: {item['files']} archivos, {item['size']} bytes")
    lines.append("")
    lines.append("## Archivos pesados")
    for item in report["top_files"][:10]:
        lines.append(f"- `{item['path']}`: {item['size']} bytes")
    if report["forbidden"]:
        lines.append("")
        lines.append("## Prohibidos")
        for item in report["forbidden"][:50]:
            lines.append(f"- `{item['path']}`: {item['reason']}")
    (REPORT_DIR / f"RELEASE_ZIP_AUDIT_{VERSION_PREFIX}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    target = Path(argv[0]).resolve() if argv else latest_zip()
    report = audit_zip(target)
    write_reports(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
