#!/usr/bin/env python3
"""Audit match times and verify Europe/Madrid conversion for V725."""
from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.madrid_time_engine import madrid_conversion_selftest, madrid_time_diagnostics, normalize_kickoff_for_display


def db_path() -> Path:
    configured = os.getenv("DB_PATH", "/data/database.db")
    candidates = [Path(configured), ROOT / "data" / "database.db"]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


def load_matches(path: Path) -> tuple[list[dict], str]:
    if not path.exists():
        return fixture_matches(), "fixtures"
    try:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        table = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='matches'").fetchone()
        if not table:
            return fixture_matches(), "fixtures_no_matches_table"
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(matches)").fetchall()}
        wanted = [
            "id", "home_team", "away_team", "competition_name", "league_name", "country",
            "match_date", "kickoff_time", "match_time", "kickoff_iso", "commence_time",
            "start_time", "event_time", "status", "minute",
        ]
        selected = [name for name in wanted if name in cols]
        if not selected:
            return fixture_matches(), "fixtures_no_time_columns"
        order_candidates = [name for name in ("kickoff_iso", "match_date", "updated_at", "created_at") if name in cols]
        if len(order_candidates) > 1:
            order_sql = f"ORDER BY COALESCE({', '.join(order_candidates)}) DESC"
        elif order_candidates:
            order_sql = f"ORDER BY {order_candidates[0]} DESC"
        else:
            order_sql = ""
        query = f"SELECT {', '.join(selected)} FROM matches {order_sql} LIMIT 250"
        rows = [dict(row) for row in conn.execute(query).fetchall()]
        return rows or fixture_matches(), "database" if rows else "fixtures_empty_database"
    except sqlite3.Error as exc:
        return fixture_matches(error=str(exc)), "fixtures_db_error"
    finally:
        try:
            conn.close()
        except Exception:
            pass


def fixture_matches(error: str = "") -> list[dict]:
    return [
        {"id": "summer_case", "home_team": "Equipo Local", "away_team": "Equipo Visitante", "competition_name": "Test", "kickoff_iso": "2026-06-12T19:00:00Z", "status": "upcoming", "error": error},
        {"id": "winter_case", "home_team": "Equipo Local", "away_team": "Equipo Visitante", "competition_name": "Test", "kickoff_iso": "2026-12-12T20:00:00Z", "status": "upcoming", "error": error},
    ]


def render_markdown(report: dict) -> str:
    lines = [
        "# Auditoría de hora Madrid V725",
        "",
        f"- Fuente: `{report['source']}`",
        f"- DB: `{report['db_path']}`",
        f"- Selftest: {'OK' if report['selftest']['ok'] else 'FAIL'}",
        f"- Partidos revisados: {report['diagnostics']['total']}",
        f"- Alertas: {json.dumps(report['diagnostics']['warnings'], ensure_ascii=False)}",
        "",
        "## Casos obligatorios",
    ]
    for case in report["selftest"]["cases"]:
        lines.append(f"- `{case['input']}` -> `{case['got']}` Madrid | esperado `{case['expected']}` | {'OK' if case['ok'] else 'FAIL'}")
    lines.append("")
    lines.append("## Muestras")
    for item in report["diagnostics"]["matches"][:40]:
        warnings = ", ".join(item.get("warnings") or ["OK"])
        lines.append(f"- `{item.get('id')}` {item.get('home_team')} vs {item.get('away_team')} | original `{item.get('original')}` | Madrid `{item.get('display')}` | {warnings}")
    return "\n".join(lines) + "\n"


def main() -> int:
    path = db_path()
    matches, source = load_matches(path)
    diagnostics = madrid_time_diagnostics(matches)
    normalized_samples = [normalize_kickoff_for_display(match) for match in matches[:20]]
    report = {
        "ok": diagnostics["selftest"]["ok"],
        "source": source,
        "db_path": str(path),
        "selftest": madrid_conversion_selftest(),
        "diagnostics": diagnostics,
        "samples": normalized_samples,
    }
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    (reports / "MADRID_TIME_AUDIT_V725.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown = render_markdown(report)
    (reports / "MADRID_TIME_AUDIT_V725.md").write_text(markdown, encoding="utf-8")
    (ROOT / "MADRID_TIME_AUDIT_V725.md").write_text(markdown, encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "source": source, "db_path": str(path), "total": diagnostics["total"], "warnings": diagnostics["warnings"], "selftest": report["selftest"]}, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
