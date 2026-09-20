"""Read the single project queue. Documents are evidence, never executable orders."""
from __future__ import annotations

import csv
from datetime import datetime
import io
import json
from pathlib import Path
import re
from zoneinfo import ZoneInfo

STATES = {"BACKLOG", "READY", "IN_PROGRESS", "BLOCKED", "QA", "PRODUCTION_VALIDATION", "DONE", "WONT_DO"}
SOURCES = {
    "truth": "project_control/CURRENT_TRUTH.md",
    "active": "project_control/ACTIVE_WORK.md",
    "queue": "project_control/CODEX_QUEUE.md",
    "decisions": "project_control/DECISIONS.md",
    "blockers": "project_control/BLOCKERS.md",
    "release": "project_control/RELEASE_STATE.md",
    "conversations": "project_control/CONVERSATION_INDEX.md",
    "contracts": "project_control/LOCKED_CONTRACTS.md",
    "roadmap": "project_control/ROADMAP.md",
    "data": "project_control/domains/DATA.md",
    "sports": "project_control/domains/SPORTS.md",
    "shark": "project_control/domains/SHARK.md",
    "business": "project_control/domains/BUSINESS.md",
    "local_close": "reports/LOCAL_CONTINUITY_20260919.md",
    "alignment": "reports/NEMESIS_OFFICIAL_VISUAL_REFERENCE_ALIGNMENT_REPORT.md",
}
QUEUE_COLUMNS = ["ID", "Alias", "Estado", "Responsable", "Ambito", "Bloqueo", "Evidencia", "Siguiente"]
BLOCK_COLUMNS = ["ID", "Motivo", "Desbloqueo"]
RELEASE_COLUMNS = ["ID", "Tipo", "Rama", "HEAD", "Estado", "Evidencia", "Limite"]


class ControlUnavailable(ValueError):
    pass


def read_local(root: Path, name: str, limit=350_000):
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()) or path.is_symlink():
        raise ControlUnavailable("source_outside_project")
    try:
        with path.open("rb") as stream:
            raw = stream.read(limit + 1)
        if len(raw) > limit:
            raise ControlUnavailable("source_too_large")
        return raw.decode("utf-8-sig")
    except (OSError, UnicodeError) as exc:
        raise ControlUnavailable("source_unavailable") from exc


def evidence(root, source_id):
    if source_id not in SOURCES:
        raise ControlUnavailable("unknown_source")
    return {"id": source_id, "path": SOURCES[source_id], "content": read_local(Path(root), SOURCES[source_id])}


def read_table(text, marker, columns):
    start, end = f"<!-- {marker}:start -->", f"<!-- {marker}:end -->"
    if text.count(start) != 1 or text.count(end) != 1 or text.index(start) >= text.index(end):
        raise ControlUnavailable("table_boundary_invalid")
    lines = text.split(start, 1)[1].split(end, 1)[0].strip().splitlines()
    if len(lines) < 3 or len(lines) > 250:
        raise ControlUnavailable("table_size_invalid")
    rows = []
    for line in lines:
        if not line.strip().startswith("|") or not line.strip().endswith("|"):
            raise ControlUnavailable("table_row_invalid")
        cells = next(csv.reader(io.StringIO(line), delimiter="|", quoting=csv.QUOTE_NONE, escapechar="\\"))[1:-1]
        cells = [value.strip() for value in cells]
        if len(cells) != len(columns) or any(len(value) > 2000 or not value for value in cells):
            raise ControlUnavailable("table_columns_invalid")
        rows.append(cells)
    if rows[0] != columns or any(not re.fullmatch(r":?-{3,}:?", value) for value in rows[1]):
        raise ControlUnavailable("table_header_invalid")
    records = [dict(zip(columns, row)) for row in rows[2:]]
    ids = [row["ID"] for row in records]
    if len(ids) != len(set(ids)) or any(not re.fullmatch(r"[A-Z0-9-]{2,40}", value) for value in ids):
        raise ControlUnavailable("duplicate_or_invalid_id")
    return records


def git_identity(root):
    """Only repository metadata; no Git command or subprocess from the web request."""
    try:
        pointer = root / ".git"
        if pointer.is_file():
            value = pointer.read_text(encoding="utf-8").strip()
            if not value.startswith("gitdir: "):
                raise ValueError()
            gitdir = (root / value[8:]).resolve()
        else:
            gitdir = pointer
        head = (gitdir / "HEAD").read_text(encoding="utf-8").strip()
        branch = "DETACHED"
        if head.startswith("ref: "):
            ref = head[5:]
            if not re.fullmatch(r"refs/heads/[A-Za-z0-9_./-]+", ref) or ".." in ref:
                raise ValueError()
            branch = ref.removeprefix("refs/heads/")
            common_file = gitdir / "commondir"
            common = (gitdir / common_file.read_text().strip()).resolve() if common_file.is_file() else gitdir
            loose = common / ref
            if loose.is_file():
                head = loose.read_text().strip()
            else:
                head = next(line.split(" ", 1)[0] for line in (common / "packed-refs").read_text().splitlines()
                            if line.endswith(" " + ref))
        if not re.fullmatch(r"[0-9a-f]{40}", head):
            raise ValueError()
        return {"branch": branch, "head": head, "status": "READ_FROM_GIT_METADATA", "working_tree": "NOT_REVALIDATED_BY_PAGE_READ"}
    except (OSError, UnicodeError, ValueError, StopIteration):
        return {"branch": None, "head": None, "status": "UNAVAILABLE", "working_tree": "NOT_REVALIDATED_BY_PAGE_READ"}


def snapshot(root):
    root = Path(root)
    queue = read_table(evidence(root, "queue")["content"], "queue", QUEUE_COLUMNS)
    blockers = read_table(evidence(root, "blockers")["content"], "blockers", BLOCK_COLUMNS)
    releases = read_table(evidence(root, "release")["content"], "releases", RELEASE_COLUMNS)
    blocker_ids = {row["ID"] for row in blockers}
    path_ids = {path: key for key, path in SOURCES.items()}
    availability = {}
    for row in queue + releases:
        path = row["Evidencia"]
        if path not in path_ids:
            raise ControlUnavailable("evidence_not_registered")
        source_id = path_ids[path]
        row["source_id"] = source_id
        if source_id not in availability:
            try:
                evidence(root, source_id)
                availability[source_id] = True
            except ControlUnavailable:
                availability[source_id] = False
        row["evidence_available"] = availability[source_id]
    for row in queue:
        if row["Estado"] not in STATES:
            raise ControlUnavailable("unknown_queue_state")
        row["blocker_ids"] = row["Bloqueo"].split(",") if row["Bloqueo"] != "NONE" else []
        if not set(row["blocker_ids"]).issubset(blocker_ids):
            raise ControlUnavailable("unknown_blocker")
    identity = git_identity(root)
    for row in releases:
        if not re.fullmatch(r"[0-9a-f]{40}", row["HEAD"]):
            raise ControlUnavailable("invalid_declared_revision")
        row["verification"] = "HISTORICAL_DECLARATION_NOT_REVALIDATED"
        if row["ID"] == "SENTINEL":
            row["verification"] = ("HEAD_MATCH_ONLY" if identity["head"] == row["HEAD"] and identity["branch"] == row["Rama"]
                                   else "CONFLICT_OR_UNVERIFIED")
    inventory = None
    try:
        raw = json.loads(read_local(root, "data/local_dev/organization-20260919/inventory.json", 8_000_000))
        inventory = {key: raw[key] for key in ("observed_at_madrid", "document_counts", "artifact_counts", "retired")}
        inventory["worktrees"] = [{key:w[key] for key in ("branch", "head", "dirty_records", "classification", "safe_to_retire")} for w in raw["worktrees"]]
        inventory["branch_count"] = len(raw["branches"])
        inventory["duplicate_document_groups"] = len(raw["byte_identical_document_groups"])
    except (ControlUnavailable, ValueError, KeyError, TypeError):
        pass
    return {"queue": queue, "blockers": blockers, "releases": releases, "identity": identity,
            "inventory": inventory, "sources": SOURCES, "environment": "LOCAL_ONLY",
            "read_at_madrid": datetime.now(ZoneInfo("Europe/Madrid")).isoformat(),
            "counts": {"active": sum(row["Estado"] in {"READY", "IN_PROGRESS", "QA", "PRODUCTION_VALIDATION"} for row in queue),
                       "blocked": sum(row["Estado"] == "BLOCKED" for row in queue),
                       "qa": sum(row["Estado"] == "QA" for row in queue),
                       "unassigned": sum(row["Responsable"] == "UNASSIGNED" for row in queue),
                       "publication_pending": sum("PUBLISH" in row["blocker_ids"] for row in queue),
                       "evidence_missing": sum(not row["evidence_available"] for row in queue)}}
