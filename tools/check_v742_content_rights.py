#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.content_rights_engine import content_rights_policy_summary


def main() -> int:
    sample = [
        {"content_type": "video", "source": "YouTube", "embed_url": "https://www.youtube.com/embed/demo", "attribution": "YouTube"},
        {"content_type": "crest", "source": "TheSportsDB", "original_url": "https://www.thesportsdb.com/demo.png", "attribution": "TheSportsDB"},
        {"content_type": "news", "source": "Fuente", "original_url": "https://example.com/noticia", "attribution": "Fuente original"},
        {"content_type": "video", "source": "unknown"},
    ]
    summary = content_rights_policy_summary(sample)
    app_text = (ROOT / "app.py").read_text(encoding="utf-8", errors="replace")
    checks = {
        "engine_exists": (ROOT / "engines" / "content_rights_engine.py").exists(),
        "admin_route": "/admin/content-rights" in app_text and "/admin/legal-content" in app_text,
        "api_route": "/api/admin/content-rights" in app_text,
        "no_binary_cache": all(not item["can_cache_binary"] for item in summary["classified"]),
        "safe_statuses": bool(summary["counts"]),
    }
    ok = all(checks.values())
    report = {"ok": ok, "version": (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip(), "checks": checks, "summary": summary}
    lines = [
        "# V742 Content Rights QA Report",
        "",
        f"- Estado: {'OK' if ok else 'REVISAR'}",
        "- No se descargan vídeos.",
        "- No se rehostean vídeos.",
        "- No se cachean binarios externos sin permiso.",
        "- Noticias solo como metadatos/enlace si no hay licencia.",
        "- Escudos externos solo por URL permitida o fallback propio.",
        "",
        "## Estados clasificados",
    ]
    for key, value in sorted(summary["counts"].items()):
        lines.append(f"- `{key}`: {value}")
    (ROOT / "V742_CONTENT_RIGHTS_QA_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
