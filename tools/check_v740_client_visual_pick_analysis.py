#!/usr/bin/env python3
"""V740 static validation for client visual polish and pick explanations."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = {
    "app.py": ["V740_CLIENT_VISUAL_PICK_ANALYSIS_PERFECTION", "enrich_pick_analysis", "client_visual_perfection_snapshot"],
    "engines/pick_analysis_experience_engine.py": ["pick_analysis_payload", "analysis_conclusion", "analysis_reasons"],
    "engines/client_visual_perfection_engine.py": ["client_visual_perfection_snapshot", "CLIENT_VISUAL_READY"],
    "templates/picks.html": ["v740-analysis-box", "analysis_reasons", "analysis_conclusion", "compact-crest"],
    "templates/match_detail.html": ["v740-analysis-box", "analysis_conclusion"],
    "templates/home.html": ["v740-home-match", "compact-crest", "competition_es"],
    "templates/base.html": ["/admin/client-visual-qa", "nsAppEnhance"],
    "templates/admin_client_visual_qa.html": ["QA visual", "client_visual_perfection"],
    "static/app.css": ["V740 Client Visual", "overflow-wrap:anywhere", "v740-analysis-box", "v740-home-match"],
}


def main() -> int:
    missing: list[str] = []
    for rel, needles in REQUIRED.items():
        path = ROOT / rel
        if not path.exists():
            missing.append(f"Falta {rel}")
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for needle in needles:
            if needle not in text:
                missing.append(f"{rel}: falta {needle}")
    if missing:
        print("V740 client visual/pick analysis check FAIL")
        for item in missing:
            print("-", item)
        return 1
    print("V740 client visual/pick analysis check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
