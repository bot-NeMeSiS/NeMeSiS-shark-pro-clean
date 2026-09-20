"""Read-only project audit. Generates evidence, never retires files or worktrees."""
from __future__ import annotations

import ast
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
GIT = os.environ.get("NEMESIS_QA_GIT", "git")
OUT = ROOT / "data/local_dev/organization-20260919"
CANONICAL = {"MASTER_CONTROL.md", "CURRENT_TRUTH.md", "CONVERSATION_INDEX.md", "DECISIONS.md", "LOCKED_CONTRACTS.md"}
ACTIVE = {"ACTIVE_WORK.md", "CODEX_QUEUE.md", "BLOCKERS.md", "RELEASE_STATE.md", "ROADMAP.md"}


def git(*args, cwd=ROOT):
    run = subprocess.run([GIT, "-C", str(cwd), *args], capture_output=True,
                         env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"}, timeout=60)
    return run.returncode, run.stdout.decode("utf-8", errors="replace")


def document_class(path, text):
    if path.startswith("project_control/"):
        if Path(path).name in CANONICAL or "/domains/" in path:
            return "CANONICAL"
        if Path(path).name in ACTIVE:
            return "ACTIVE"
    if path == "docs/NEMESIS_RECONCILIATION_AUDIT.md":
        return "SUPERSEDED"
    if path.startswith("NEMESIS_CONTROL_PROYECTO/") and "ARCHIVO DE CONTINUIDAD" in text:
        return "HISTORICAL"
    if path.startswith("NEMESIS_DOCUMENTACION/"):
        return "HISTORICAL"
    if path.startswith("reports/") or "CERTIFICATION" in path:
        return "EVIDENCE"
    if path in {"CHATGPT_CONTINUATION_REPORT.md", "NEMESIS_LIVING_ROADMAP.md"}:
        return "HISTORICAL"
    if path in {"NEMESIS_MASTER_VISION.md", "NEMESIS_PRODUCT_BIBLE.md", "NEMESIS_SPORTS_UX_BIBLE.md", "NEMESIS_MATCH_CENTER_UX_BIBLE.md", "NEMESIS_X_IMPLEMENTATION_RULES.md"}:
        return "CANONICAL"
    return "UNKNOWN"


def audit():
    OUT.mkdir(parents=True, exist_ok=True)
    before = OUT / "before"
    if not before.exists():
        before.mkdir()
        for path in (ROOT / "project_control").glob("*.md"):
            shutil.copy2(path, before / path.name)
    _, tracked_raw = git("ls-files", "-z")
    _, untracked_raw = git("ls-files", "--others", "--exclude-standard", "-z")
    tracked = set(filter(None, tracked_raw.split("\0")))
    names = sorted(tracked | set(filter(None, untracked_raw.split("\0"))))
    _, raw = git("worktree", "list", "--porcelain")
    worktrees = []
    for block in raw.strip().split("\n\n"):
        fields = dict(line.split(" ", 1) for line in block.splitlines() if " " in line)
        path = fields.get("worktree", "")
        branch = fields.get("branch", "DETACHED").removeprefix("refs/heads/")
        present = Path(path).is_dir()
        code, status = git("status", "--porcelain=v1", "-z", "--untracked-files=all", cwd=path) if present else (1, "")
        records = [p for p in status.split("\0") if p]
        _, relation = git("rev-list", "--left-right", "--count", "main..." + fields.get("HEAD", "HEAD"))
        worktrees.append({"path":path, "branch":branch, "head":fields.get("HEAD"), "exists":present,
                          "dirty_records":len(records) if code == 0 else None,
                          "status_readable":code == 0, "behind_ahead_main":relation.strip(),
                          "classification":"ACTIVE" if branch in {"main", "codex/sentinel-operaciones-local"} else "PRESERVE",
                          "safe_to_retire":False})
    _, branches_raw = git("for-each-ref", "--format=%(refname:short)|%(objectname)", "refs/heads")
    branches = []
    for line in branches_raw.splitlines():
        name, sha = line.split("|")
        _, relation = git("rev-list", "--left-right", "--count", "main..." + sha)
        branches.append({"name":name, "head":sha, "behind_ahead_main":relation.strip(),
                         "worktree_dependency":any(w["branch"] == name for w in worktrees),
                         "classification":"ACTIVE" if name in {"main", "codex/sentinel-operaciones-local"} else "PRESERVE",
                         "safe_to_retire":False})
    documents = []
    by_hash = defaultdict(list)
    sources = {}
    for name in names:
        path = ROOT / name
        if not path.is_file() or path.is_symlink():
            continue
        if path.suffix.lower() in {".py", ".html", ".js", ".css"}:
            sources[name] = path.read_text(encoding="utf-8-sig", errors="replace")
        if path.suffix.lower() not in {".md", ".txt"} or path.stat().st_size > 2_000_000:
            continue
        if not (name.startswith(("project_control/", "reports/", "docs/", "NEMESIS_CONTROL_PROYECTO/", "NEMESIS_DOCUMENTACION/")) or "/" not in name):
            continue
        content = path.read_bytes()
        text = content.decode("utf-8-sig", errors="replace")
        digest = hashlib.sha256(content).hexdigest()
        by_hash[digest].append(name)
        documents.append({"path":name, "category":document_class(name, text), "sha256":digest,
                          "size":len(content), "tracked":name in tracked, "action":"KEEP"})
    artifacts = []
    errors = []
    nested = {Path(w["path"]).resolve() for w in worktrees if Path(w["path"]).resolve() != ROOT.resolve()}
    for parent, dirs, files in os.walk(ROOT, followlinks=False, onerror=lambda e: errors.append(type(e).__name__)):
        dirs[:] = [d for d in dirs if d not in {".git", ".venv", "venv", "node_modules"}
                   and not (Path(parent)/d).is_symlink() and (Path(parent)/d).resolve() not in nested
                   and (Path(parent)/d).resolve() != OUT.resolve()]
        for filename in files:
            path = Path(parent) / filename
            name = path.relative_to(ROOT).as_posix()
            suffix = path.suffix.lower()
            category = None
            if filename.startswith(".env"):
                category = "PROTECTED_ENV"
            elif suffix in {".db", ".sqlite", ".sqlite3", ".db-wal", ".db-shm"} or filename.endswith(("-wal", "-shm")):
                category = "DB_KEEP_NO_CONTENT_READ"
            elif suffix == ".pyc" or "__pycache__/" in name:
                category = "CACHE"
            elif suffix in {".zip", ".patch"}:
                category = "PACKAGE_OR_CANDIDATE_KEEP"
            elif name.startswith("release_output/"):
                category = "RELEASE_OUTPUT"
            elif suffix == ".log":
                category = "LOG_KEEP_NO_CONTENT_READ"
            elif name.startswith(("data/local_dev/", "data/qa_tmp/", ".tmp_reference_review/")):
                category = "QA_EVIDENCE_KEEP"
            if category:
                try:
                    artifacts.append({"path":name, "category":category, "size":path.stat().st_size,
                                      "tracked":name in tracked, "action":"KEEP_PENDING_DEPENDENCY_REVIEW", "safe_to_retire":False})
                except OSError:
                    errors.append("METADATA_UNREADABLE:"+name)
    imports = set()
    routes = defaultdict(list)
    functions = defaultdict(list)
    for name, content in sources.items():
        if not name.endswith(".py"):
            continue
        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
                imports.update(node.module + "." + a.name for a in node.names)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if name.startswith(("engines/", "services/")) and len(node.body) > 2:
                    fingerprint = hashlib.sha256(ast.dump(ast.Module(body=node.body, type_ignores=[])).encode()).hexdigest()
                    functions[fingerprint].append(name+":"+str(node.lineno)+":"+node.name)
                if name == "app.py":
                    for deco in node.decorator_list:
                        if isinstance(deco, ast.Call) and isinstance(deco.func, ast.Attribute) and deco.func.attr == "route" and deco.args and isinstance(deco.args[0], ast.Constant):
                            routes[node.name].append(str(deco.args[0].value))
    text_all = "\n".join(sources.values())
    legacy = {
        "engines_without_static_import":[name for name in sources if name.startswith("engines/") and name.endswith(".py") and Path(name).name != "__init__.py" and name[:-3].replace("/", ".") not in imports],
        "package_initializers_keep":[name for name in sources if Path(name).name == "__init__.py"],
        "templates_without_literal_reference":[name for name in sources if name.startswith("templates/") and name[10:] not in text_all],
        "css_without_literal_filename_reference":[name for name in sources if name.startswith("static/") and name.endswith(".css") and Path(name).name not in text_all],
        "same_handler_aliases":{key:value for key,value in routes.items() if len(value)>1},
        "same_helper_body_candidates":[value for value in functions.values() if len(value)>1],
        "verdict":"REVIEW_ONLY: dynamic imports, CLI, routes and assets may consume these; zero static references does not authorize removal",
        "safe_to_retire":0,
    }
    result = {"observed_at_madrid":datetime.now(ZoneInfo("Europe/Madrid")).isoformat(), "scope":"CURRENT_CANDIDATE; other registered worktrees Git metadata only",
              "worktrees":worktrees, "branches":branches, "documents":documents,
              "document_counts":dict(Counter(d["category"] for d in documents)),
              "byte_identical_document_groups":[v for v in by_hash.values() if len(v)>1],
              "artifacts":artifacts, "artifact_counts":dict(Counter(d["category"] for d in artifacts)),
              "legacy":legacy, "enumeration_errors":errors, "retired":0,
              "excluded":"Git objects, environments, node_modules, nested worktrees, audit output; DB/env/log bytes never read"}
    (OUT/"inventory.json").write_text(json.dumps(result, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps({k:result[k] for k in ("observed_at_madrid", "document_counts", "artifact_counts", "enumeration_errors", "retired")}))
    print(json.dumps({"worktrees":worktrees, "branches":branches, "duplicates":len(result["byte_identical_document_groups"]),
                      "legacy_candidates":{k:len(v) for k,v in legacy.items() if isinstance(v, (list,dict))}}))


if __name__ == "__main__":
    audit()
