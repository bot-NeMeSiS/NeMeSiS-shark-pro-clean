"""Read-only inventory for a local Codex checkout. NEVER deletes or prunes.

Run with Python 3.11+: python tools/inspect_local_worktrees.py --repo <path>
The JSON contains paths/refs and counts, never file contents, diffs or secrets.
An integrated, clean checkout still requires checking active Codex chats before
any independent human-approved cleanup. Ignored local files are NOT disposable.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
from typing import Any


class InspectionError(RuntimeError):
    pass


def git(repo: Path, *args: str) -> str:
    env = {**os.environ, "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"}
    try:
        result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                                timeout=30, env=env)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InspectionError("Git no está disponible o excedió el límite de lectura.") from exc
    if result.returncode:
        raise InspectionError("No se pudo verificar el estado de Git.")
    return result.stdout.decode("utf-8", errors="surrogateescape")


def parse_worktrees(raw: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for token in raw.split("\0"):
        if not token:
            if current:
                records.append(current)
                current = {}
            continue
        key, _, value = token.partition(" ")
        if key == "worktree" and current:
            records.append(current)
            current = {}
        if key in {"worktree", "HEAD", "branch"}:
            current[key] = value
        elif key in {"locked", "prunable", "bare", "detached"}:
            current[key] = True
    if current:
        records.append(current)
    if not records or any("worktree" not in row for row in records):
        raise InspectionError("Inventario de worktrees incompleto.")
    return records


def status_counts(raw: str) -> dict[str, int]:
    counts = {"tracked_changes": 0, "untracked_entries": 0, "ignored_entries": 0}
    tokens = iter(raw.split("\0"))
    for token in tokens:
        if not token:
            continue
        code = token[:2]
        if code == "??":
            counts["untracked_entries"] += 1
        elif code == "!!":
            counts["ignored_entries"] += 1
        else:
            counts["tracked_changes"] += 1
            if "R" in code or "C" in code:
                next(tokens, None)
    return counts


def is_ancestor(repo: Path, sha: str, target: str) -> bool:
    env = {**os.environ, "GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0"}
    result = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", sha, target],
                            capture_output=True, timeout=30, env=env)
    if result.returncode not in (0, 1):
        raise InspectionError("Ascendencia no verificable.")
    return result.returncode == 0


def inspect(repo: Path, base: str = "refs/remotes/origin/main") -> dict[str, Any]:
    repo = repo.expanduser().resolve()
    if not base.startswith("refs/"):
        raise InspectionError("La referencia base debe ser completa: refs/...")
    git(repo, "check-ref-format", base)
    shallow = git(repo, "rev-parse", "--is-shallow-repository").strip() == "true"
    base_sha = git(repo, "rev-parse", "--verify", base + "^{commit}").strip()
    worktrees = parse_worktrees(git(repo, "worktree", "list", "--porcelain", "-z"))
    results = []
    for index, item in enumerate(worktrees):
        path = Path(item["worktree"])
        row = {"path": str(path), "head": item.get("HEAD"), "branch": item.get("branch"),
               "locked": bool(item.get("locked")), "detached": bool(item.get("detached")),
               "registered_missing": not path.exists(), "active_chat_status": "NOT_OBSERVED",
               "classification": "KEEP_UNKNOWN", "safe_to_delete": False}
        reasons = []
        if index == 0: reasons.append("PRIMARY_WORKTREE")
        if path.resolve() == repo: reasons.append("CURRENT_WORKTREE")
        if item.get("bare"): reasons.append("BARE_REPOSITORY")
        if item.get("locked"): reasons.append("LOCKED")
        if item.get("prunable"): reasons.append("MISSING_OR_MOVED_REQUIRES_REVIEW")
        if not path.is_dir() or item.get("bare"):
            row["reasons"] = reasons + ["NOT_INSPECTABLE"]
            results.append(row)
            continue
        try:
            counts = status_counts(git(path, "status", "--porcelain=v1", "-z",
                                       "--untracked-files=all", "--ignored=matching"))
            row.update(counts)
            if counts["tracked_changes"]: reasons.append("TRACKED_CHANGES")
            if counts["untracked_entries"]: reasons.append("UNTRACKED_FILES")
            if counts["ignored_entries"]: reasons.append("IGNORED_LOCAL_FILES")
            if (path / ".gitmodules").exists(): reasons.append("SUBMODULES")
            branch = item.get("branch") or ""
            if branch in {"refs/heads/main", "refs/heads/master", "refs/heads/develop"} or branch.startswith(
                    ("refs/heads/rollback/", "refs/heads/release/", "refs/heads/codex/")):
                reasons.append("PROTECTED_BRANCH")
            if shallow:
                reasons.append("SHALLOW_HISTORY")
            else:
                contained = is_ancestor(path, item["HEAD"], base_sha)
                row["ancestor_of_base"] = contained
                if not contained: reasons.append("UNIQUE_OR_SQUASHED_HISTORY")
            row["classification"] = "KEEP" if reasons else "CLEAN_INTEGRATED_REVIEW_ACTIVITY"
        except (InspectionError, subprocess.TimeoutExpired, KeyError):
            reasons.append("READ_UNAVAILABLE")
        row["reasons"] = reasons
        results.append(row)
    return {"contract": "NEMESIS-LOCAL-WORKTREE-INVENTORY-V1", "read_only": True,
            "base_ref": base, "base_sha": base_sha, "base_freshness": "LOCAL_REF_NOT_REMOTE_VERIFIED",
            "shallow": shallow, "worktrees": results,
            "stash_entries": len(git(repo, "stash", "list", "--format=%gd").splitlines()),
            "files_deleted": 0, "branches_deleted": 0,
            "warning": "No prueba ausencia de chats activos ni inspecciona otros repositorios. No publicar rutas privadas."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--base", default="refs/remotes/origin/main")
    args = parser.parse_args()
    try:
        print(json.dumps(inspect(args.repo, args.base), ensure_ascii=True, indent=2))
        return 0
    except InspectionError as exc:
        print(json.dumps({"ok": False, "read_only": True, "error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
