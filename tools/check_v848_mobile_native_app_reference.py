from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
css = (ROOT / "static" / "app.css").read_text(encoding="utf-8", errors="replace")
checks = {
    "mobile_media": "@media(max-width:760px)" in css,
    "safe_area": "env(safe-area-inset-bottom)" in css,
    "bottom_nav_centered": "left:50%!important" in css and "translateX(-50%)" in css,
    "five_items": "grid-template-columns:repeat(5" in css,
    "touch_targets": "min-height:44px" in css,
    "floating_above_nav": "bottom:calc(env(safe-area-inset-bottom) + 78px)" in css,
}
failed = [k for k, v in checks.items() if not v]
print({"checks": checks, "failed": failed})
raise SystemExit(1 if failed else 0)
