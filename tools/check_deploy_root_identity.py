from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


REQUIRED_ROOT = ["app.py", "VERSION.txt", "APP_VERSION", "requirements.txt", "templates", "static", "engines", "tools", "reports", "reference_images", "browser_qa", "automation_workforce", ".github/workflows"]
FORBIDDEN_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "release_output", "logs", "v636work", "tmp", "temp", "backups"}
FORBIDDEN_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm", ".log", ".zip"}


def read(rel: str) -> str:
    path = ROOT / rel
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def app_version_from_source() -> str:
    match = re.search(r"APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]", read("app.py"))
    return match.group(1) if match else ""


def git_remote_hint() -> str:
    match = re.search(r"url\s*=\s*(.+)", read(".git/config"))
    return match.group(1).strip() if match else "unavailable"


def git_branch_hint() -> str:
    head = read(".git/HEAD").strip()
    if head.startswith("ref: refs/heads/"):
        return head.rsplit("/", 1)[-1]
    return head or "unavailable"


def inspect_tree(path: Path) -> dict:
    missing = [rel for rel in REQUIRED_ROOT if not (path / rel).exists()]
    forbidden: list[str] = []
    if path.exists():
        for item in path.rglob("*"):
            rel = item.relative_to(path).as_posix()
            parts = set(Path(rel).parts)
            if parts & FORBIDDEN_DIRS:
                forbidden.append(rel)
            if item.is_file() and item.suffix.lower() in FORBIDDEN_SUFFIXES:
                forbidden.append(rel)
            if len(forbidden) >= 50:
                break
    return {"path": str(path), "exists": path.exists(), "missing_required_root": missing, "forbidden_count": len(forbidden), "forbidden_sample": forbidden[:20]}


def main() -> int:
    zip_candidates = sorted((ROOT / "release_output").glob("NeMeSiS_SHARK_PRO_*_RENDER_READY.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    zip_info = {"exists": False}
    if zip_candidates:
        z = zip_candidates[0]
        with zipfile.ZipFile(z) as zf:
            names = set(zf.namelist())
        def zip_has_root(rel: str) -> bool:
            return rel in names or any(name.startswith(f"{rel}/") for name in names)

        zip_info = {
            "exists": True,
            "path": str(z),
            "missing_required_root": [rel for rel in REQUIRED_ROOT if not zip_has_root(rel)],
            "has_nested_project_hint": any(name.count("/") > 1 and name.endswith("app.py") for name in names),
        }

    payload = {
        "ok": True,
        "root": str(ROOT),
        "version_txt": read("VERSION.txt").strip().lstrip("\ufeff"),
        "app_version_file": read("APP_VERSION").strip().lstrip("\ufeff"),
        "app_py_app_version": app_version_from_source(),
        "git_remote_hint": git_remote_hint(),
        "git_branch_hint": git_branch_hint(),
        "current_root": inspect_tree(ROOT),
        "deploy_root_v902b": inspect_tree(ROOT / "release_output" / "V902B_DEPLOY_ROOT_CONTENTS"),
        "deploy_root_v903": inspect_tree(ROOT / "release_output" / "V903_DEPLOY_ROOT_CONTENTS"),
        "deploy_root_v904": inspect_tree(ROOT / "release_output" / "V904_DEPLOY_ROOT_CONTENTS"),
        "deploy_root_v905": inspect_tree(ROOT / "release_output" / "V905_DEPLOY_ROOT_CONTENTS"),
        "deploy_root_v906": inspect_tree(ROOT / "release_output" / "V906_DEPLOY_ROOT_CONTENTS"),
        "deploy_root_v906b": inspect_tree(ROOT / "release_output" / "V906B_DEPLOY_ROOT_CONTENTS"),
        "deploy_root_v907": inspect_tree(ROOT / "release_output" / "V907_DEPLOY_ROOT_CONTENTS"),
        "deploy_root_v908": inspect_tree(ROOT / "release_output" / "V908_DEPLOY_ROOT_CONTENTS"),
        "deploy_root_v909": inspect_tree(ROOT / "release_output" / "V909_DEPLOY_ROOT_CONTENTS"),
        "deploy_root_v910": inspect_tree(ROOT / "release_output" / "V910_DEPLOY_ROOT_CONTENTS"),
        "deploy_root_v911": inspect_tree(ROOT / "release_output" / "V911_DEPLOY_ROOT_CONTENTS"),
        "deploy_root_v915": inspect_tree(ROOT / "release_output" / "V915_DEPLOY_ROOT_CONTENTS"),
        "deploy_root_v916": inspect_tree(ROOT / "release_output" / "V916_DEPLOY_ROOT_CONTENTS"),
        "deploy_root_v917": inspect_tree(ROOT / "release_output" / "V917_DEPLOY_ROOT_CONTENTS"),
        "deploy_root_v918": inspect_tree(ROOT / "release_output" / "V918_DEPLOY_ROOT_CONTENTS"),
        "deploy_root_v919": inspect_tree(ROOT / "release_output" / "V919_DEPLOY_ROOT_CONTENTS"),
        "deploy_root_v920": inspect_tree(ROOT / "release_output" / "V920_DEPLOY_ROOT_CONTENTS"),
        "latest_zip": zip_info,
    }
    payload["ok"] = not payload["current_root"]["missing_required_root"]
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
