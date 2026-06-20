from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
css = (ROOT / "static" / "app.css").read_text(encoding="utf-8", errors="replace")

required = {
    "v841_mobile_media": "@media(max-width:980px)" in css,
    "bottom_nav_five_items": "grid-template-columns:repeat(5" in css,
    "safe_area": "env(safe-area-inset-bottom" in css,
    "rails_hidden_mobile": ".v828-client-rail" in css and ".v808-admin-rail" in css and "display:none!important" in css,
    "main_mobile_padding": "padding-bottom:calc(108px + env(safe-area-inset-bottom" in css,
    "floating_shark_mobile": ".v825-public-floating-shark" in css and "bottom:calc(86px + env(safe-area-inset-bottom" in css,
    "overflow_guard": "overflow-x:hidden" in css,
}

payload = {"ok": all(required.values()), "checks": required}
print(json.dumps(payload, ensure_ascii=False, indent=2))
raise SystemExit(0 if payload["ok"] else 1)
