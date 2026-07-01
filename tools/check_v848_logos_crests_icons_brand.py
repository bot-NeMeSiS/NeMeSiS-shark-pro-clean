from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8", errors="replace")
css = (ROOT / "static" / "app.css").read_text(encoding="utf-8", errors="replace")
checks = {
    "logo_asset": (ROOT / "static" / "img" / "shark-logo.svg").exists(),
    "favicon": "rel=\"icon\"" in base and "shark-logo.svg" in base,
    "brand_images": "brand" in base and "shark-logo.svg" in base,
    "crest_sizing": all(t in css for t in [".team-crest", ".league-logo", "object-fit:contain"]),
    "no_runtime_download": "download" not in css.lower(),
}
failed = [k for k, v in checks.items() if not v]
print({"checks": checks, "failed": failed})
raise SystemExit(1 if failed else 0)
