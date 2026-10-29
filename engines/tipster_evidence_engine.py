"""Read-only tipster KPIs from the latest auditable pick results.

The sample is refused when any decided pick lacks a complete, consistent
settlement, including terminal picks with no grading row. Pending picks and
confirmed voids are excluded from the ROI denominator.
"""
from __future__ import annotations

import math
import sqlite3
from pathlib import Path
from typing import Any

from engines.pick_grading_engine import LATEST_GRADING_CTE

CONTRACT = "TIPSTER_AUDITED_METRICS_V1"
_MONEY_VALID = """
    g.auto_validated=1
    AND NULLIF(TRIM(COALESCE(g.graded_at,'')), '') IS NOT NULL
    AND typeof(g.odds) IN ('integer','real') AND g.odds>1 AND g.odds<1000000
    AND typeof(g.stake) IN ('integer','real') AND g.stake>0 AND g.stake<100000000
    AND typeof(g.profit) IN ('integer','real') AND abs(g.profit)<10000000000
    AND (
        (g.result_status='won' AND abs(g.profit-ROUND((g.odds-1)*g.stake,2))<=0.015)
        OR (g.result_status='lost' AND abs(g.profit+g.stake)<=0.015)
    )
    AND (
        lower(trim(COALESCE(p.status,''))) IN ('published','pending','publicado','pendiente')
        OR (lower(trim(COALESCE(p.status,''))) IN ('won','ganado') AND g.result_status='won')
        OR (lower(trim(COALESCE(p.status,''))) IN ('lost','perdido') AND g.result_status='lost')
    )
"""
_QUERY = LATEST_GRADING_CTE + f"""
SELECT
    COUNT(*) AS decided_count,
    COALESCE(SUM(CASE WHEN {_MONEY_VALID} THEN 1 ELSE 0 END),0) AS certified_count,
    COALESCE(SUM(CASE WHEN {_MONEY_VALID} THEN g.stake ELSE 0 END),0) AS settled_stake,
    COALESCE(SUM(CASE WHEN {_MONEY_VALID} THEN g.profit ELSE 0 END),0) AS settled_profit,
    COALESCE(SUM(CASE WHEN g.result_status='won' THEN 1 ELSE 0 END),0) AS won_count
FROM picks p
LEFT JOIN latest_grades g ON g.pick_id=p.id
WHERE lower(trim(COALESCE(p.status,''))) IN (
    'published','pending','won','lost','void','publicado','pendiente','ganado','perdido','nulo'
)
AND (
    g.result_status IN ('won','lost')
    OR lower(trim(COALESCE(p.status,''))) IN ('won','lost','ganado','perdido')
)
"""

def _unknown(state: str) -> dict[str, Any]:
    return {
        "contract": CONTRACT,
        "state": state,
        "read_only": True,
        "roi": None,
        "winrate": None,
        "decided_count": 0,
        "certified_count": 0,
        "stake_units": None,
        "profit_units": None,
    }


def audited_tipster_kpis(db_path: str) -> dict[str, Any]:
    """Return internally consistent metrics without dropping ungraded terminal picks."""
    try:
        path = Path(db_path).expanduser().resolve()
        if not path.is_file():
            return _unknown("DATABASE_NOT_FOUND")
        conn = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=1.5)
        conn.row_factory = sqlite3.Row
    except (TypeError, ValueError, OSError, sqlite3.Error):
        return _unknown("DATABASE_UNAVAILABLE")
    try:
        conn.execute("PRAGMA query_only=ON")
        row = conn.execute(_QUERY).fetchone()
        if row is None:
            return _unknown("NO_DECIDED_PICKS")
        decided = int(row["decided_count"] or 0)
        certified = int(row["certified_count"] or 0)
        stake = float(row["settled_stake"] or 0)
        profit = float(row["settled_profit"] or 0)
        if not decided:
            return _unknown("NO_DECIDED_PICKS")
        if certified != decided or stake <= 0 or not all(map(math.isfinite, (stake, profit))):
            result = _unknown("INCOMPLETE_SETTLEMENT_EVIDENCE")
            result.update(decided_count=decided, certified_count=certified)
            return result
        wins = int(row["won_count"] or 0)
        return {
            "contract": CONTRACT,
            "state": "CERTIFIED_SETTLEMENT_SAMPLE",
            "read_only": True,
            "decided_count": decided,
            "certified_count": certified,
            "winrate": round(wins / decided * 100, 2),
            "roi": round(profit / stake * 100, 2),
            "stake_units": round(stake, 2),
            "profit_units": round(profit, 2),
        }
    except (sqlite3.Error, TypeError, ValueError, OverflowError):
        return _unknown("EVIDENCE_UNAVAILABLE")
    finally:
        conn.close()
