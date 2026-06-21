from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
manifest = ROOT / "static" / "manifest.json"

checks = {
    "shark_logo_exists": (ROOT / "static" / "img" / "shark-logo.svg").exists(),
    "base_references_logo": "shark-logo.svg" in base,
    "favicon_declared": "rel=\"icon\"" in base or "rel='icon'" in base,
    "v842_css_logo_block": "V842 SPANISH TEXT LOGOS BRAND IDENTITY FINAL QA START" in css,
    "manifest_if_present_is_readable": True,
}

if manifest.exists():
    checks["manifest_if_present_is_readable"] = "icons" in manifest.read_text(encoding="utf-8", errors="ignore")

payload = {"ok": all(checks.values()), "checks": checks}
print(json.dumps(payload, ensure_ascii=False, indent=2))
raise SystemExit(0 if payload["ok"] else 1)
