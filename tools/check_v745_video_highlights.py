#!/usr/bin/env python3
"""V745 safe video highlights check."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.video_highlights_engine import video_highlights_snapshot


def main() -> int:
    snapshot = video_highlights_snapshot([{"content_type": "video", "source": "YouTube", "embed_url": "https://www.youtube.com/embed/demo", "attribution": "Fuente"}])
    videos = snapshot.get("videos") or []
    result = {"ok": snapshot.get("ok") and videos and videos[0].get("downloads_video") is False, "status": snapshot.get("status")}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
